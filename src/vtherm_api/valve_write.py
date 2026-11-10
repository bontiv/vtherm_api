"""Valve write hook.

An ``over_climate`` thermostat with valve regulation computes an opening degree
(and a closing degree) and writes them to the valve entities of the underlying.
This module defines the contract that lets a feature manager provided by a
plugin change the opening degree before it is written, or write the valve
itself, for example to run a device specific closing sequence.

The contract is optional. It lives in a dedicated protocol,
:class:`InterfaceValveWriteHook`, next to the unchanged
:class:`InterfaceFeatureManager`. A feature manager that does not implement it
keeps satisfying :class:`InterfaceFeatureManager`; the core detects the
capability with ``hasattr(manager, "async_before_valve_write")``. Unlike the
hooks of :mod:`vtherm_api.underlying_hooks`, this one can change the command of
the core.

Rules of the contract:

* The core calls the method only on a feature manager whose ``is_configured``
  is True, in the order of the names of their factories (alphabetical), as
  returned by ``VThermAPI.get_feature_manager_factories()``.
* The method is called by ``send_percent_open`` of a ``valve_regulation``
  underlying, for every cause, after the opening and closing degrees have been
  computed and before they are written. It is not called for the valve
  recalibration, for the initial priming of unknown degrees, nor when the
  inhibition gate blocks the write. ``over_valve`` underlyings are not covered.
* The method is a coroutine awaited by the core, which cuts the call after
  ``UNDERLYING_HOOK_TIMEOUT_SEC`` seconds. A long sequence must be run in a
  background task of the plugin.
* The managers form a chain. Each one receives in ``opening_degree`` the value
  left by the previous one; the first one receives the value of the core, which
  is also in ``requested_opening_degree``.
* Returning ``None`` or an empty :class:`ValveWriteDecision` leaves the value
  unchanged.
* ``ValveWriteDecision.opening_degree`` is the value proposed to the next
  manager. The core clamps it to ``0..max_opening_degree`` and rounds it to an
  integer.
* ``ValveWriteDecision.handled=True`` means the plugin writes the valve itself.
  The chain stops and the core writes neither the opening nor the closing
  degree. ``opening_degree``, when given, is the value the valve will end at,
  otherwise it is the proposed value.
* After the chain, the final value becomes the last value sent to the
  underlying, with the time of the command. When there is a closing degree
  entity and the core writes, it writes ``max_opening_degree`` minus the final
  value.
* The core does not repair the valve before ``settle_sec`` seconds after the
  decision. ``settle_sec`` defaults to the resend delay of the core (2 seconds).
  A plugin running a longer sequence announces its duration with it.
* :meth:`InterfaceValveCommandHook.async_after_valve_command` is called in all
  cases, with the final value. ``ValveCommand.requested_opening_degree`` then
  holds the value of the core when a manager changed it, and
  ``ValveCommand.written_by_plugin`` is True when a plugin wrote the valve.
* An exception, an invalid value or a timeout is logged, and the core goes on
  with the value it had before that manager.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .underlying_hooks import ValveCommandCause


@dataclass(frozen=True, slots=True)
class ValveWriteRequest:
    """Valve write about to be done by the core on a valve-regulation underlying."""

    climate_entity_id: str
    opening_degree_entity_id: str
    closing_degree_entity_id: str | None
    percent_open: int
    """Raw requested opening, 0..100, from the regulation."""
    opening_degree: int
    """Proposed value: the one of the core, or the one left by the previous manager."""
    requested_opening_degree: int
    """Value computed by the core, before any manager."""
    max_opening_degree: float
    """Maximum of the opening degree entity."""
    hvac_mode: str
    """VTherm HVAC mode when the write is requested."""
    cause: ValveCommandCause


@dataclass(frozen=True, slots=True)
class ValveWriteDecision:
    """Answer of a feature manager to a :class:`ValveWriteRequest`."""

    opening_degree: int | None = None
    """New proposed opening degree, None to leave the value unchanged."""
    handled: bool = False
    """True when the plugin writes the valve itself: the core writes nothing."""
    settle_sec: float | None = None
    """Time the core waits before repairing the valve, None for its resend delay."""


@runtime_checkable
class InterfaceValveWriteHook(Protocol):
    """Optional feature manager extension called before the valve is written."""

    async def async_before_valve_write(self, request: ValveWriteRequest) -> ValveWriteDecision | None:
        """Return a decision, or None to leave the value of the core unchanged."""
        ...
