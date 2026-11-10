"""Calibration offset modifier contract.

An ``over_climate`` thermostat that synchronizes the temperature of the device
with a calibration entity computes an offset and writes it to that entity. This
module defines the contract that lets a feature manager provided by a plugin
adjust that offset before it is compared and written, for example for a device
that reads the offset with the opposite sign.

The contract is optional. It lives in a dedicated protocol,
:class:`InterfaceCalibrationOffsetModifier`, next to the unchanged
:class:`InterfaceFeatureManager`. A feature manager that does not implement it
keeps satisfying :class:`InterfaceFeatureManager`; the core detects the
capability with ``hasattr(manager, "adjust_calibration_offset")``.

Rules of the contract:

* The core calls the method only on a feature manager whose ``is_configured``
  is True, in the order the managers were registered.
* The method is called by ``synchronize_device_temperature`` of an
  ``over_climate`` thermostat, only in calibration mode
  (``sync_with_calibration``), after the offset has been computed and before it
  is compared with ``current_offset``.
* The method is a plain function, not a coroutine, and does no input or output.
* The managers form a chain. Each one receives in ``offset`` the value left by
  the previous one; the first one receives the value of the core, which is also
  in ``requested_offset``. Returning ``None`` keeps the value.
* The values are in the unit and the direction of the device. A device with an
  inverted sign receives ``current_offset`` as it is, and has all the data to
  compute the offset again.
* The core clamps the result to ``min_offset..max_offset``, rounds it to
  ``step``, and writes it only if it differs from ``current_offset``.
* An exception or an invalid value is logged, and the core goes on with the
  value it had before that manager.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class CalibrationOffsetRequest:
    """Calibration offset about to be written by the core."""

    climate_entity_id: str
    calibration_entity_id: str
    offset: float
    """Proposed offset: the one of the core, or the one left by the previous manager."""
    requested_offset: float
    """Offset computed by the core, clamped and rounded."""
    current_offset: float
    """Raw value read from the calibration entity."""
    local_temperature: float
    """Temperature read from the device."""
    room_temperature: float
    """Temperature of the room, from the sensor of the VTherm."""
    min_offset: float
    max_offset: float
    step: float


@runtime_checkable
class InterfaceCalibrationOffsetModifier(Protocol):
    """Optional feature manager extension adjusting the calibration offset."""

    def adjust_calibration_offset(self, request: CalibrationOffsetRequest) -> float | None:
        """Return the offset to use, or None to keep ``request.offset``."""
        ...
