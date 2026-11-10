"""Tests for the optional valve write hook contract."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import dataclasses
import inspect

import pytest

from src import vtherm_api
from src.vtherm_api.interfaces import InterfaceFeatureManager
from src.vtherm_api.underlying_hooks import ValveCommandCause
from src.vtherm_api.valve_write import (
    InterfaceValveWriteHook,
    ValveWriteDecision,
    ValveWriteRequest,
)


class PlainFeatureManager:
    """A feature manager which does not hook the valve write."""

    name = "plain"


class ClosingFeatureManager:
    """A feature manager which writes the valve itself when it closes."""

    name = "closing"

    def __init__(self) -> None:
        self.requests: list[ValveWriteRequest] = []

    async def async_before_valve_write(self, request: ValveWriteRequest) -> ValveWriteDecision | None:
        """Record the request and handle a full closing."""
        self.requests.append(request)
        if request.opening_degree == 0:
            return ValveWriteDecision(opening_degree=0, handled=True, settle_sec=30.0)
        return None


def _request(**overrides) -> ValveWriteRequest:
    values = {
        "climate_entity_id": "climate.trv",
        "opening_degree_entity_id": "number.trv_opening",
        "closing_degree_entity_id": "number.trv_closing",
        "percent_open": 40,
        "opening_degree": 40,
        "requested_opening_degree": 40,
        "max_opening_degree": 100.0,
        "hvac_mode": "heat",
        "cause": ValveCommandCause.REGULATION,
    }
    values.update(overrides)
    return ValveWriteRequest(**values)


def test_names_are_exported() -> None:
    for name, value in (
        ("InterfaceValveWriteHook", InterfaceValveWriteHook),
        ("ValveWriteRequest", ValveWriteRequest),
        ("ValveWriteDecision", ValveWriteDecision),
    ):
        assert name in vtherm_api.__all__
        assert getattr(vtherm_api, name) is value


def test_protocol_has_a_single_coroutine_method() -> None:
    assert set(InterfaceValveWriteHook.__protocol_attrs__) == {"async_before_valve_write"}
    method = InterfaceValveWriteHook.async_before_valve_write
    assert inspect.iscoroutinefunction(method)
    assert list(inspect.signature(method).parameters) == ["self", "request"]


def test_feature_manager_protocol_is_unchanged() -> None:
    assert "async_before_valve_write" not in InterfaceFeatureManager.__protocol_attrs__


def test_capability_is_detected_on_the_manager() -> None:
    assert isinstance(ClosingFeatureManager(), InterfaceValveWriteHook)
    assert hasattr(ClosingFeatureManager(), "async_before_valve_write")
    assert not isinstance(PlainFeatureManager(), InterfaceValveWriteHook)
    assert not hasattr(PlainFeatureManager(), "async_before_valve_write")


@pytest.mark.parametrize("instance", [_request(), ValveWriteDecision()], ids=["ValveWriteRequest", "ValveWriteDecision"])
def test_dataclasses_are_frozen_and_use_slots(instance) -> None:
    assert dataclasses.is_dataclass(instance)
    assert hasattr(type(instance), "__slots__")
    assert not hasattr(instance, "__dict__")
    first_field = dataclasses.fields(instance)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, first_field, "other")


def test_request_fields() -> None:
    assert [field.name for field in dataclasses.fields(ValveWriteRequest)] == [
        "climate_entity_id",
        "opening_degree_entity_id",
        "closing_degree_entity_id",
        "percent_open",
        "opening_degree",
        "requested_opening_degree",
        "max_opening_degree",
        "hvac_mode",
        "cause",
    ]
    request = _request(closing_degree_entity_id=None)
    assert request.closing_degree_entity_id is None


def test_decision_fields_and_defaults() -> None:
    assert [field.name for field in dataclasses.fields(ValveWriteDecision)] == ["opening_degree", "handled", "settle_sec"]
    decision = ValveWriteDecision()
    assert decision.opening_degree is None
    assert decision.handled is False
    assert decision.settle_sec is None


@pytest.mark.asyncio
async def test_manager_receives_the_request_passed_by_the_core() -> None:
    manager = ClosingFeatureManager()
    regular = _request()
    closing = _request(percent_open=0, opening_degree=0, requested_opening_degree=0, cause=ValveCommandCause.TURN_OFF)

    assert await manager.async_before_valve_write(regular) is None
    decision = await manager.async_before_valve_write(closing)

    assert manager.requests == [regular, closing]
    assert manager.requests[0] is regular
    assert decision == ValveWriteDecision(opening_degree=0, handled=True, settle_sec=30.0)
