"""Underlying command hooks.

The Versatile Thermostat core sends commands to its underlying entities
(climate, switch, valve). This module defines three optional contracts that let
a feature manager provided by a plugin follow those commands, for example to
work around the quirks of a given device model.

The contracts are optional and independent. Each one lives in a dedicated
protocol next to the unchanged :class:`InterfaceFeatureManager`, like
:class:`InterfaceSetpointModifier`. A feature manager implements only the hooks
it needs and keeps satisfying :class:`InterfaceFeatureManager`; the core detects
each capability with ``hasattr`` on the method name.

The hooks are notifications: none of them modifies or cancels the command of
the core.

Common rules:

* Each hook is optional and independent. A manager may implement only one.
* The core calls a hook only on a feature manager whose ``is_configured`` is
  True.
* Hooks are coroutines awaited by the core. They must return quickly: a long
  treatment (waiting, kick) must be scheduled with ``async_call_later`` or a
  task, without blocking the hook. The core cuts the call after
  ``UNDERLYING_HOOK_TIMEOUT_SEC`` seconds (10, exported by ``const.py``).
* An exception or a timeout is logged and never prevents the command of the
  core.
* A hook is called only if the command of the core is really sent. It is not
  called if the inhibition gate blocks the command, if the requested mode is
  already in place or if the load shedding refuses to switch on.
* HVAC modes are passed as ``str``, like ``vtherm_hvac_mode`` in
  :class:`InterfaceThermostatRuntime`.

``async_before_underlying_hvac_mode``:

* Called just before ``climate.set_hvac_mode`` is sent to the underlying
  climate, while this one is still in ``current_hvac_mode``.
* ``command_cause`` is ``None`` for a regular command and
  ``"underlying_tracking"`` when the VTherm copies a change made on the device.
* For an ``over_climate`` with direct valve control going OFF, this hook is
  called before the OFF mode is sent, while the climate is still in
  ``current_hvac_mode``. The valve is closed afterwards, by the regulation,
  with a :class:`ValveCommand` whose ``cause`` is ``REGULATION`` and whose
  ``hvac_mode`` is ``"off"``. A plugin that needs to act before OFF must do it
  in this hook. This hook receives no command object: the target mode is its
  ``hvac_mode`` parameter (``"off"`` here), to be used instead of the Home
  Assistant state of the climate, which can still be on. ``command.hvac_mode``
  only exists on the :class:`ValveCommand` of ``async_after_valve_command``.

``async_after_valve_command``:

* Called after the opening and closing degrees have been sent to a
  ``valve_regulation`` underlying.
* The valve recalibration and the initial priming of unknown degrees do not
  call this hook.

``async_on_underlying_power``:

* ``CYCLE_START``: at each cycle start, including the automatic restart
  (``is_repeat=True``). For a switch, one call per underlying with its
  ``start_offset_sec``.
* ``UPDATE``: at each valve update during a running cycle, even if the value
  does not change.
* ``STOP``: when a running cycle is cancelled (OFF, load shedding, shutdown).
  ``applied_on_percent`` is then 0.
* The on/off toggles of a switch during the cycle do not trigger a
  notification: a manager deduces them from ``cycle_start_monotonic``,
  ``start_offset_sec`` and ``on_time_sec`` (see below).
* The hook is called after the cycle start has been actuated, and the core
  awaits the managers one after the other, so a notification can reach a
  manager several seconds after the actuation. A manager must therefore use
  the timestamps of the command and never its reception time.
* ``cycle_start_monotonic`` is ``time.monotonic()`` at the start of the master
  cycle the command belongs to. It is ``None`` when no cycle is running: for
  a ``STOP`` (the cycle is over) and for an ``UPDATE`` emitted outside a cycle.
  ``monotonic`` is ``time.monotonic()`` when the notification is built.
* A switch turns on at ``cycle_start_monotonic + start_offset_sec`` and turns
  off ``on_time_sec`` later. The cycle is circular: when
  ``start_offset_sec + on_time_sec`` exceeds ``cycle_duration_sec``, the off
  time wraps to the beginning of the cycle. These times are nominal: the
  minimal activation and deactivation delays of the core can shift a toggle.
* This hook is distinct from :class:`AppliedCommandReceipt`: the receipt is for
  the algorithm plugin and describes the whole thermostat, this hook is for
  feature managers and describes each underlying.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


class ValveCommandCause(StrEnum):
    """Why the core sent a valve command."""

    REGULATION = "regulation"
    """Command computed by the regulation cycle (TPI or algorithm plugin)."""

    TURN_OFF = "turn_off"
    """Valve closed because an underlying is turned off directly, or because an
    inhibition stops."""

    STARTUP = "startup"
    """Command sent by the initial state check of the underlying."""

    REPAIR = "repair"
    """Command sent to repair a valve that drifted from the requested value,
    or to resynchronize after an inhibition."""


@dataclass(frozen=True, slots=True)
class ValveCommand:
    """Valve command really sent to an over_climate valve-regulation underlying."""

    climate_entity_id: str
    opening_degree_entity_id: str
    closing_degree_entity_id: str | None
    percent_open: int
    """Raw requested opening, 0..100, before the opening/closing degree calculation."""
    opening_degree: int
    """Value sent to the opening degree entity."""
    closing_degree: int | None
    """Value sent to the closing degree entity, None when there is no such entity."""
    hvac_mode: str
    """VTherm HVAC mode when the command is sent."""
    cause: ValveCommandCause


class PowerCommandKind(StrEnum):
    """Origin of a power notification."""

    CYCLE_START = "cycle_start"
    UPDATE = "update"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class UnderlyingPowerCommand:
    """Power requested from and applied to one underlying by the cycle scheduler."""

    underlying_entity_id: str
    underlying_type: str
    """"switch", "valve" or "valve_regulation"."""
    climate_entity_id: str | None
    """Climate entity driven by a valve_regulation underlying, None otherwise."""
    hvac_mode: str
    kind: PowerCommandKind
    requested_on_percent: float
    """Request received by the scheduler, clamped to [0, 1]."""
    applied_on_percent: float
    """Power really applied: on_time / cycle for a switch, retained ratio for a valve."""
    on_time_sec: float
    off_time_sec: float
    cycle_duration_sec: float
    start_offset_sec: float | None
    """Offset of this underlying in the cycle (switch only), None for a valve."""
    is_repeat: bool
    cycle_start_monotonic: float | None
    """``time.monotonic()`` at the start of the master cycle the command belongs to.

    None when no cycle is running: for ``STOP`` and for an ``UPDATE`` emitted
    outside a cycle. A switch turns on at ``cycle_start_monotonic +
    start_offset_sec`` and off ``on_time_sec`` later (wrapping at the end of
    the cycle). The notification can arrive after the actuation: use this
    timestamp, not the reception time."""
    monotonic: float
    """``time.monotonic()`` when the notification is built."""


@runtime_checkable
class InterfaceUnderlyingHvacModeHook(Protocol):
    """Optional feature manager extension called before an underlying HVAC mode change."""

    async def async_before_underlying_hvac_mode(
        self,
        climate_entity_id: str,
        hvac_mode: str,
        current_hvac_mode: str | None,
        command_cause: str | None,
    ) -> None:
        """Called before ``climate.set_hvac_mode`` is sent to ``climate_entity_id``."""
        ...


@runtime_checkable
class InterfaceValveCommandHook(Protocol):
    """Optional feature manager extension called after a valve command."""

    async def async_after_valve_command(self, command: ValveCommand) -> None:
        """Called after the opening and closing degrees have been sent."""
        ...


@runtime_checkable
class InterfaceUnderlyingPowerHook(Protocol):
    """Optional feature manager extension notified of the power of each underlying."""

    async def async_on_underlying_power(self, command: UnderlyingPowerCommand) -> None:
        """Called at cycle start, valve update and cycle stop, for each underlying."""
        ...
