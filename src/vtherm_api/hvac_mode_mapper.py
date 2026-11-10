"""Underlying HVAC mode translation.

Some devices name their HVAC modes differently from Versatile Thermostat, or
need a different mode to behave as expected. This module defines the contract
that lets a feature manager provided by a plugin translate the HVAC mode sent
to an underlying climate, and the one read from it.

The contract is optional. It lives in a dedicated protocol,
:class:`InterfaceUnderlyingHvacModeMapper`, next to the unchanged
:class:`InterfaceFeatureManager`. A feature manager that does not implement it
keeps satisfying :class:`InterfaceFeatureManager`; the core detects the
capability with ``hasattr`` on the method names.

Rules of the contract:

* The core calls the methods only on a feature manager whose ``is_configured``
  is True, in the order the managers were registered.
* The methods are plain functions, not coroutines, and do no input or output:
  they are called from properties and at each state change of the device.
* ``to_underlying_hvac_mode`` receives a VTherm HVAC mode and returns the mode
  to send to the device. ``from_underlying_hvac_mode`` receives a mode of the
  device and returns the VTherm HVAC mode it stands for.
* Returning ``None`` means no translation. The core keeps the first result that
  is not ``None`` and logs a warning when two managers translate differently.
* ``off`` is never translated: the core ignores a translation from or to
  ``off``.
* ``UNSUPPORTED_HVAC_MODE`` returned by ``from_underlying_hvac_mode`` marks a
  device mode with no VTherm equivalent. The core removes it from the list of
  modes, treats it as a drift in the repair, and ignores it when it follows the
  changes of the device.
* The core calls the methods when it sends a mode (``set_hvac_mode`` and its
  short-circuit), in the ``hvac_mode`` and ``hvac_modes`` properties, in
  ``check_and_repair``, ``check_initial_state`` and when the device changes.
* ``async_before_underlying_hvac_mode`` receives the mode really sent to the
  device, and ``current_hvac_mode`` stays the raw state of the device.
* An exception or an invalid value is logged, and the core goes on without
  translation.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

UNSUPPORTED_HVAC_MODE = ""
"""Device mode with no VTherm equivalent, returned by ``from_underlying_hvac_mode``."""


@runtime_checkable
class InterfaceUnderlyingHvacModeMapper(Protocol):
    """Optional feature manager extension translating the HVAC modes of an underlying."""

    def to_underlying_hvac_mode(self, climate_entity_id: str, hvac_mode: str) -> str | None:
        """Return the mode to send to the device for a VTherm mode, or None for no translation."""
        ...

    def from_underlying_hvac_mode(self, climate_entity_id: str, underlying_hvac_mode: str) -> str | None:
        """Return the VTherm mode for a device mode, None for no translation, or UNSUPPORTED_HVAC_MODE."""
        ...
