"""Tests for the optional underlying HVAC mode mapper contract."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import inspect

from src import vtherm_api
from src.vtherm_api.hvac_mode_mapper import UNSUPPORTED_HVAC_MODE, InterfaceUnderlyingHvacModeMapper
from src.vtherm_api.interfaces import InterfaceFeatureManager

METHODS = {
    "to_underlying_hvac_mode": ["self", "climate_entity_id", "hvac_mode"],
    "from_underlying_hvac_mode": ["self", "climate_entity_id", "underlying_hvac_mode"],
}


class PlainFeatureManager:
    """A feature manager which does not translate the HVAC modes."""

    name = "plain"


class ToOnlyFeatureManager:
    """A feature manager which implements only one of the two methods."""

    name = "to_only"

    def to_underlying_hvac_mode(self, climate_entity_id: str, hvac_mode: str) -> str | None:
        """Translate nothing."""
        return None


class AutoForHeatFeatureManager:
    """A feature manager for a device which wants auto instead of heat."""

    name = "auto_for_heat"

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def to_underlying_hvac_mode(self, climate_entity_id: str, hvac_mode: str) -> str | None:
        """Send auto instead of heat."""
        self.calls.append(("to", climate_entity_id, hvac_mode))
        return "auto" if hvac_mode == "heat" else None

    def from_underlying_hvac_mode(self, climate_entity_id: str, underlying_hvac_mode: str) -> str | None:
        """Read auto as heat, and heat as unsupported."""
        self.calls.append(("from", climate_entity_id, underlying_hvac_mode))
        if underlying_hvac_mode == "auto":
            return "heat"
        if underlying_hvac_mode == "heat":
            return UNSUPPORTED_HVAC_MODE
        return None


def test_names_are_exported() -> None:
    assert vtherm_api.InterfaceUnderlyingHvacModeMapper is InterfaceUnderlyingHvacModeMapper
    assert vtherm_api.UNSUPPORTED_HVAC_MODE is UNSUPPORTED_HVAC_MODE
    assert "InterfaceUnderlyingHvacModeMapper" in vtherm_api.__all__
    assert "UNSUPPORTED_HVAC_MODE" in vtherm_api.__all__


def test_unsupported_mode_value() -> None:
    assert UNSUPPORTED_HVAC_MODE == ""
    assert isinstance(UNSUPPORTED_HVAC_MODE, str)


def test_protocol_has_exactly_two_synchronous_methods() -> None:
    assert set(InterfaceUnderlyingHvacModeMapper.__protocol_attrs__) == set(METHODS)
    for method_name, parameters in METHODS.items():
        method = getattr(InterfaceUnderlyingHvacModeMapper, method_name)
        assert not inspect.iscoroutinefunction(method)
        assert list(inspect.signature(method).parameters) == parameters


def test_feature_manager_protocol_is_unchanged() -> None:
    for method_name in METHODS:
        assert method_name not in InterfaceFeatureManager.__protocol_attrs__


def test_capability_is_detected_on_the_manager() -> None:
    assert isinstance(AutoForHeatFeatureManager(), InterfaceUnderlyingHvacModeMapper)
    assert not isinstance(PlainFeatureManager(), InterfaceUnderlyingHvacModeMapper)
    assert not isinstance(ToOnlyFeatureManager(), InterfaceUnderlyingHvacModeMapper)
    for method_name in METHODS:
        assert hasattr(AutoForHeatFeatureManager(), method_name)
        assert not hasattr(PlainFeatureManager(), method_name)
    assert hasattr(ToOnlyFeatureManager(), "to_underlying_hvac_mode")
    assert not hasattr(ToOnlyFeatureManager(), "from_underlying_hvac_mode")


def test_manager_translates_the_modes() -> None:
    manager = AutoForHeatFeatureManager()

    assert manager.to_underlying_hvac_mode("climate.trv", "heat") == "auto"
    assert manager.to_underlying_hvac_mode("climate.trv", "cool") is None
    assert manager.from_underlying_hvac_mode("climate.trv", "auto") == "heat"
    assert manager.from_underlying_hvac_mode("climate.trv", "heat") == UNSUPPORTED_HVAC_MODE
    assert manager.from_underlying_hvac_mode("climate.trv", "cool") is None
    assert manager.calls[0] == ("to", "climate.trv", "heat")
    assert manager.calls[-1] == ("from", "climate.trv", "cool")
