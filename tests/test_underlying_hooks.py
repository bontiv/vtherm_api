"""Tests for the optional underlying command hooks contract."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import dataclasses
import inspect
from enum import StrEnum

import pytest

from src import vtherm_api
from src.vtherm_api import const
from src.vtherm_api.interfaces import InterfaceFeatureManager
from src.vtherm_api.underlying_hooks import (
    InterfaceUnderlyingHvacModeHook,
    InterfaceUnderlyingPowerHook,
    InterfaceValveCommandHook,
    PowerCommandKind,
    UnderlyingPowerCommand,
    ValveCommand,
    ValveCommandCause,
)

PROTOCOLS = {
    InterfaceUnderlyingHvacModeHook: ("async_before_underlying_hvac_mode", ["self", "climate_entity_id", "hvac_mode", "current_hvac_mode", "command_cause"]),
    InterfaceValveCommandHook: ("async_after_valve_command", ["self", "command"]),
    InterfaceUnderlyingPowerHook: ("async_on_underlying_power", ["self", "command"]),
}


class PlainFeatureManager:
    """A feature manager which implements no hook."""

    name = "plain"


class HvacModeOnlyManager:
    """A feature manager which implements a single hook."""

    name = "hvac_mode_only"

    async def async_before_underlying_hvac_mode(self, climate_entity_id: str, hvac_mode: str, current_hvac_mode: str | None, command_cause: str | None) -> None:
        """Do nothing."""


class RecordingManager:
    """A feature manager which records what the three hooks receive."""

    name = "recording"

    def __init__(self) -> None:
        self.hvac_mode_calls: list[tuple] = []
        self.valve_commands: list[ValveCommand] = []
        self.power_commands: list[UnderlyingPowerCommand] = []

    async def async_before_underlying_hvac_mode(self, climate_entity_id: str, hvac_mode: str, current_hvac_mode: str | None, command_cause: str | None) -> None:
        """Record the call."""
        self.hvac_mode_calls.append((climate_entity_id, hvac_mode, current_hvac_mode, command_cause))

    async def async_after_valve_command(self, command: ValveCommand) -> None:
        """Record the command."""
        self.valve_commands.append(command)

    async def async_on_underlying_power(self, command: UnderlyingPowerCommand) -> None:
        """Record the command."""
        self.power_commands.append(command)


def _valve_command(**overrides) -> ValveCommand:
    values = {
        "climate_entity_id": "climate.trv",
        "opening_degree_entity_id": "number.trv_opening",
        "closing_degree_entity_id": "number.trv_closing",
        "percent_open": 40,
        "opening_degree": 40,
        "closing_degree": 60,
        "hvac_mode": "heat",
        "cause": ValveCommandCause.REGULATION,
    }
    values.update(overrides)
    return ValveCommand(**values)


def _power_command(**overrides) -> UnderlyingPowerCommand:
    values = {
        "underlying_entity_id": "switch.heater",
        "underlying_type": "switch",
        "climate_entity_id": None,
        "hvac_mode": "heat",
        "kind": PowerCommandKind.CYCLE_START,
        "requested_on_percent": 0.5,
        "applied_on_percent": 0.5,
        "on_time_sec": 150.0,
        "off_time_sec": 150.0,
        "cycle_duration_sec": 300.0,
        "start_offset_sec": 0.0,
        "is_repeat": False,
        "cycle_start_monotonic": 1000.0,
        "monotonic": 1002.5,
    }
    values.update(overrides)
    return UnderlyingPowerCommand(**values)


def test_names_are_exported() -> None:
    for name in (
        "InterfaceUnderlyingHvacModeHook",
        "InterfaceValveCommandHook",
        "InterfaceUnderlyingPowerHook",
        "ValveCommand",
        "ValveCommandCause",
        "UnderlyingPowerCommand",
        "PowerCommandKind",
        "UNDERLYING_HOOK_TIMEOUT_SEC",
    ):
        assert name in vtherm_api.__all__
        assert hasattr(vtherm_api, name)
    assert vtherm_api.InterfaceUnderlyingHvacModeHook is InterfaceUnderlyingHvacModeHook
    assert vtherm_api.InterfaceValveCommandHook is InterfaceValveCommandHook
    assert vtherm_api.InterfaceUnderlyingPowerHook is InterfaceUnderlyingPowerHook
    assert vtherm_api.ValveCommand is ValveCommand
    assert vtherm_api.ValveCommandCause is ValveCommandCause
    assert vtherm_api.UnderlyingPowerCommand is UnderlyingPowerCommand
    assert vtherm_api.PowerCommandKind is PowerCommandKind


def test_timeout_constant_is_exported() -> None:
    assert vtherm_api.UNDERLYING_HOOK_TIMEOUT_SEC == 10
    assert vtherm_api.UNDERLYING_HOOK_TIMEOUT_SEC is const.UNDERLYING_HOOK_TIMEOUT_SEC


@pytest.mark.parametrize("protocol", list(PROTOCOLS))
def test_protocol_has_a_single_coroutine_method(protocol) -> None:
    method_name, parameters = PROTOCOLS[protocol]
    assert set(protocol.__protocol_attrs__) == {method_name}
    method = getattr(protocol, method_name)
    assert inspect.iscoroutinefunction(method)
    assert list(inspect.signature(method).parameters) == parameters


def test_feature_manager_protocol_is_unchanged() -> None:
    for method_name, _ in PROTOCOLS.values():
        assert method_name not in InterfaceFeatureManager.__protocol_attrs__


def test_capabilities_are_detected_on_the_manager() -> None:
    for protocol, (method_name, _) in PROTOCOLS.items():
        assert not isinstance(PlainFeatureManager(), protocol)
        assert not hasattr(PlainFeatureManager(), method_name)
        assert isinstance(RecordingManager(), protocol)
        assert hasattr(RecordingManager(), method_name)

    assert isinstance(HvacModeOnlyManager(), InterfaceUnderlyingHvacModeHook)
    assert not isinstance(HvacModeOnlyManager(), InterfaceValveCommandHook)
    assert not isinstance(HvacModeOnlyManager(), InterfaceUnderlyingPowerHook)


@pytest.mark.parametrize(
    "instance",
    [_valve_command(), _power_command()],
    ids=["ValveCommand", "UnderlyingPowerCommand"],
)
def test_dataclasses_are_frozen_and_use_slots(instance) -> None:
    assert dataclasses.is_dataclass(instance)
    assert hasattr(type(instance), "__slots__")
    assert not hasattr(instance, "__dict__")
    first_field = dataclasses.fields(instance)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, first_field, "other")


def test_power_command_time_fields_are_frozen() -> None:
    power = _power_command()
    for name in ("cycle_start_monotonic", "monotonic"):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(power, name, 0.0)


def test_dataclass_fields() -> None:
    assert [field.name for field in dataclasses.fields(ValveCommand)] == [
        "climate_entity_id",
        "opening_degree_entity_id",
        "closing_degree_entity_id",
        "percent_open",
        "opening_degree",
        "closing_degree",
        "hvac_mode",
        "cause",
    ]
    assert [field.name for field in dataclasses.fields(UnderlyingPowerCommand)] == [
        "underlying_entity_id",
        "underlying_type",
        "climate_entity_id",
        "hvac_mode",
        "kind",
        "requested_on_percent",
        "applied_on_percent",
        "on_time_sec",
        "off_time_sec",
        "cycle_duration_sec",
        "start_offset_sec",
        "is_repeat",
        "cycle_start_monotonic",
        "monotonic",
    ]


def test_optional_fields_accept_none() -> None:
    command = _valve_command(closing_degree_entity_id=None, closing_degree=None)
    assert command.closing_degree_entity_id is None
    assert command.closing_degree is None

    power = _power_command(underlying_type="valve", start_offset_sec=None)
    assert power.start_offset_sec is None
    assert power.climate_entity_id is None

    stop = _power_command(kind=PowerCommandKind.STOP, cycle_start_monotonic=None)
    assert stop.cycle_start_monotonic is None
    assert stop.monotonic == 1002.5


def test_enum_values_are_stable() -> None:
    assert issubclass(ValveCommandCause, StrEnum)
    assert issubclass(PowerCommandKind, StrEnum)
    assert {cause.name: cause.value for cause in ValveCommandCause} == {
        "REGULATION": "regulation",
        "TURN_OFF": "turn_off",
        "STARTUP": "startup",
        "REPAIR": "repair",
    }
    assert {kind.name: kind.value for kind in PowerCommandKind} == {
        "CYCLE_START": "cycle_start",
        "UPDATE": "update",
        "STOP": "stop",
    }


@pytest.mark.asyncio
async def test_manager_receives_the_objects_passed_by_the_core() -> None:
    manager = RecordingManager()
    valve_command = _valve_command(cause=ValveCommandCause.TURN_OFF, percent_open=0, opening_degree=0, closing_degree=100)
    power_command = _power_command(kind=PowerCommandKind.STOP, applied_on_percent=0.0)

    assert isinstance(manager, InterfaceUnderlyingHvacModeHook)
    assert isinstance(manager, InterfaceValveCommandHook)
    assert isinstance(manager, InterfaceUnderlyingPowerHook)

    await manager.async_before_underlying_hvac_mode("climate.trv", "off", "heat", None)
    await manager.async_before_underlying_hvac_mode("climate.trv", "heat", "off", "underlying_tracking")
    await manager.async_after_valve_command(valve_command)
    await manager.async_on_underlying_power(power_command)

    assert manager.hvac_mode_calls == [
        ("climate.trv", "off", "heat", None),
        ("climate.trv", "heat", "off", "underlying_tracking"),
    ]
    assert manager.valve_commands == [valve_command]
    assert manager.valve_commands[0] is valve_command
    assert manager.valve_commands[0].cause == "turn_off"
    assert manager.power_commands == [power_command]
    assert manager.power_commands[0].kind == "stop"
