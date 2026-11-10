"""Tests for the optional calibration offset modifier contract."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import dataclasses
import inspect

import pytest

from src import vtherm_api
from src.vtherm_api.calibration_modifier import CalibrationOffsetRequest, InterfaceCalibrationOffsetModifier
from src.vtherm_api.interfaces import InterfaceFeatureManager


class PlainFeatureManager:
    """A feature manager which does not adjust the calibration offset."""

    name = "plain"


class InvertedSignFeatureManager:
    """A feature manager for a device which reads the offset with the opposite sign."""

    name = "inverted_sign"

    def __init__(self) -> None:
        self.requests: list[CalibrationOffsetRequest] = []

    def adjust_calibration_offset(self, request: CalibrationOffsetRequest) -> float | None:
        """Compute the offset again with the opposite sign."""
        self.requests.append(request)
        if request.local_temperature == request.room_temperature:
            return None
        return request.current_offset - (request.room_temperature - request.local_temperature)


def _request(**overrides) -> CalibrationOffsetRequest:
    values = {
        "climate_entity_id": "climate.trv",
        "calibration_entity_id": "number.trv_calibration",
        "offset": 1.5,
        "requested_offset": 1.5,
        "current_offset": 0.5,
        "local_temperature": 20.0,
        "room_temperature": 21.0,
        "min_offset": -9.0,
        "max_offset": 9.0,
        "step": 0.5,
    }
    values.update(overrides)
    return CalibrationOffsetRequest(**values)


def test_names_are_exported() -> None:
    assert vtherm_api.InterfaceCalibrationOffsetModifier is InterfaceCalibrationOffsetModifier
    assert vtherm_api.CalibrationOffsetRequest is CalibrationOffsetRequest
    assert "InterfaceCalibrationOffsetModifier" in vtherm_api.__all__
    assert "CalibrationOffsetRequest" in vtherm_api.__all__


def test_protocol_has_a_single_synchronous_method() -> None:
    assert set(InterfaceCalibrationOffsetModifier.__protocol_attrs__) == {"adjust_calibration_offset"}
    method = InterfaceCalibrationOffsetModifier.adjust_calibration_offset
    assert not inspect.iscoroutinefunction(method)
    assert list(inspect.signature(method).parameters) == ["self", "request"]


def test_feature_manager_protocol_is_unchanged() -> None:
    assert "adjust_calibration_offset" not in InterfaceFeatureManager.__protocol_attrs__


def test_capability_is_detected_on_the_manager() -> None:
    assert isinstance(InvertedSignFeatureManager(), InterfaceCalibrationOffsetModifier)
    assert hasattr(InvertedSignFeatureManager(), "adjust_calibration_offset")
    assert not isinstance(PlainFeatureManager(), InterfaceCalibrationOffsetModifier)
    assert not hasattr(PlainFeatureManager(), "adjust_calibration_offset")


def test_request_is_frozen_and_uses_slots() -> None:
    request = _request()
    assert dataclasses.is_dataclass(request)
    assert hasattr(CalibrationOffsetRequest, "__slots__")
    assert not hasattr(request, "__dict__")
    with pytest.raises(dataclasses.FrozenInstanceError):
        request.offset = 0.0  # type: ignore[misc]


def test_request_fields() -> None:
    assert [field.name for field in dataclasses.fields(CalibrationOffsetRequest)] == [
        "climate_entity_id",
        "calibration_entity_id",
        "offset",
        "requested_offset",
        "current_offset",
        "local_temperature",
        "room_temperature",
        "min_offset",
        "max_offset",
        "step",
    ]
    assert all(field.default is dataclasses.MISSING for field in dataclasses.fields(CalibrationOffsetRequest))


def test_manager_receives_the_request_passed_by_the_core() -> None:
    manager = InvertedSignFeatureManager()
    request = _request()

    assert manager.adjust_calibration_offset(request) == -0.5
    assert manager.adjust_calibration_offset(_request(local_temperature=21.0)) is None
    assert manager.requests[0] is request
    assert len(manager.requests) == 2
