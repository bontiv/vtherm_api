"""Backward compatibility of the public API.

Plugins written against vtherm_api 0.6.0 (adaptive TPI, hysteresis, SmartPI,
heating failure detection, third-party code) must keep importing,
type-checking and registering unchanged. These tests freeze the 0.6.0 public
surface and the 0.6.2 inhibition facade additions, and exercise plugin-style
implementations that know nothing about later additions.

The inhibition provider surface of 0.6.0 (provider/factory protocols, status,
stop policy, thermostat view and the provider factory registry) was replaced
by the ``set_inhibition`` / ``unset_inhibition`` facade before 0.6.2 and is
therefore not part of the frozen baseline.
"""

# pylint: disable=too-few-public-methods,unused-argument

from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.exceptions import HomeAssistantError

from src import vtherm_api
from src.vtherm_api import interfaces
from src.vtherm_api.const import DOMAIN
from src.vtherm_api.inhibition import InhibitionNotStartedError
from src.vtherm_api.interfaces import (
    InterfaceCycleScheduler,
    InterfaceFeatureManager,
    InterfaceFeatureManagerFactory,
    InterfacePropAlgorithmFactory,
    InterfacePropAlgorithmHandler,
    InterfaceThermostat,
    InterfaceThermostatRuntime,
    ValveDiagnosticState,
)
from src.vtherm_api.vtherm_api import VThermAPI

API_0_6_EXPORTS = {
    "InterfaceCycleScheduler",
    "InterfaceFeatureManager",
    "InterfaceFeatureManagerFactory",
    "InterfacePropAlgorithmFactory",
    "InterfacePropAlgorithmHandler",
    "InterfaceThermostat",
    "InterfaceThermostatRuntime",
    "ValveDiagnosticState",
    "PluginClimate",
    "VThermAPI",
    "VThermLogEntry",
    "VThermLogHandler",
    "VThermLogger",
    "async_export_logs",
    "get_vtherm_logger",
    "write_event_log",
    "__version__",
}

API_0_6_2_EXPORTS = {"InhibitionNotStartedError"}

API_0_6_PROTOCOL_MEMBERS = {
    InterfaceCycleScheduler: {"cancel_cycle", "is_cycle_running", "register_cycle_end_callback", "register_cycle_start_callback", "start_cycle"},
    InterfaceFeatureManager: {
        "add_listener",
        "hass",
        "is_configured",
        "is_detected",
        "name",
        "post_init",
        "refresh_state",
        "restore_state",
        "start_listening",
        "stop_listening",
    },
    InterfaceFeatureManagerFactory: {"create", "name", "supports"},
    InterfacePropAlgorithmFactory: {"create", "name"},
    InterfacePropAlgorithmHandler: {
        "async_added_to_hass",
        "async_startup",
        "control_heating",
        "init_algorithm",
        "on_scheduler_ready",
        "on_state_changed",
        "remove",
        "should_publish_intermediate",
    },
    InterfaceThermostat: {"device_info", "name", "register_manager", "unique_id"},
    InterfaceThermostatRuntime: {
        "async_control_heating",
        "async_set_underlying_fan_mode",
        "async_underlying_entity_turn_off",
        "async_write_ha_state",
        "current_outdoor_temperature",
        "current_temperature",
        "cycle_min",
        "cycle_scheduler",
        "entity_id",
        "entry_infos",
        "get_feature_manager",
        "has_prop",
        "hass",
        "hvac_action",
        "hvac_off_reason",
        "is_device_active",
        "is_overpowering_detected",
        "last_temperature_slope",
        "minimal_activation_delay",
        "minimal_deactivation_delay",
        "name",
        "now",
        "on_percent",
        "prop_algorithm",
        "regulated_target_temperature",
        "requested_hvac_mode",
        "send_event",
        "target_temperature",
        "underlying_fan_modes",
        "unique_id",
        "update_custom_attributes",
        "valve_diagnostics",
        "vtherm_hvac_mode",
    },
}


def test_0_6_exports_are_still_exported() -> None:
    assert (API_0_6_EXPORTS | API_0_6_2_EXPORTS) <= set(vtherm_api.__all__)
    for name in API_0_6_EXPORTS | API_0_6_2_EXPORTS:
        assert hasattr(vtherm_api, name)


def test_0_6_import_paths_are_unchanged() -> None:
    for name in ("InterfaceCycleScheduler", "InterfaceFeatureManager", "InterfaceFeatureManagerFactory", "InterfacePropAlgorithmFactory"):
        assert getattr(vtherm_api, name) is getattr(interfaces, name)
    assert vtherm_api.ValveDiagnosticState is interfaces.ValveDiagnosticState
    assert vtherm_api.InhibitionNotStartedError is InhibitionNotStartedError
    assert vtherm_api.VThermAPI is VThermAPI


def test_existing_protocols_have_exactly_their_0_6_members() -> None:
    for protocol, members in API_0_6_PROTOCOL_MEMBERS.items():
        assert set(protocol.__protocol_attrs__) == members, protocol.__name__


def test_existing_signatures_are_unchanged() -> None:
    assert list(inspect.signature(InterfaceCycleScheduler.start_cycle).parameters) == ["self", "hvac_mode", "on_percent", "force"]
    assert inspect.signature(InterfaceCycleScheduler.start_cycle).parameters["force"].default is False
    assert list(inspect.signature(InterfacePropAlgorithmHandler.control_heating).parameters) == ["self", "timestamp", "force"]
    assert list(inspect.signature(InterfacePropAlgorithmFactory.create).parameters) == ["self", "thermostat"]
    assert list(inspect.signature(InterfaceFeatureManagerFactory.supports).parameters) == ["self", "thermostat"]
    assert [field for field in ValveDiagnosticState.__dataclass_fields__] == ["entity_id", "should_be_active", "is_active"]


def test_0_6_2_inhibition_facade_is_unchanged() -> None:
    assert issubclass(InhibitionNotStartedError, HomeAssistantError)
    assert list(inspect.signature(VThermAPI.set_inhibition).parameters) == ["self", "vtherm_entity_id", "stop_underlyings"]
    assert list(inspect.signature(VThermAPI.unset_inhibition).parameters) == ["self", "vtherm_entity_id"]
    assert list(inspect.signature(VThermAPI.is_inhibition_started).parameters) == ["self", "vtherm_entity_id"]
    assert inspect.iscoroutinefunction(VThermAPI.set_inhibition)
    assert inspect.iscoroutinefunction(VThermAPI.unset_inhibition)
    assert not inspect.iscoroutinefunction(VThermAPI.is_inhibition_started)


class LegacyScheduler:
    """Scheduler written for 0.6.0: no receipt support."""

    @property
    def is_cycle_running(self) -> bool:
        return False

    def register_cycle_start_callback(self, callback) -> None:
        del callback

    def register_cycle_end_callback(self, callback) -> None:
        del callback

    async def start_cycle(self, hvac_mode, on_percent: float, force: bool = False) -> None:
        del hvac_mode, on_percent, force

    async def cancel_cycle(self) -> None:
        return None


class LegacyHandler(InterfacePropAlgorithmHandler):
    """Handler written for 0.6.0, explicitly subclassing the protocol."""

    def init_algorithm(self) -> None:
        return None

    async def async_added_to_hass(self) -> None:
        return None

    async def async_startup(self) -> None:
        return None

    def remove(self) -> None:
        return None

    async def control_heating(self, timestamp=None, force: bool = False) -> None:
        return None

    async def on_state_changed(self, changed: bool) -> None:
        return None

    def on_scheduler_ready(self, scheduler: InterfaceCycleScheduler) -> None:
        return None

    def should_publish_intermediate(self) -> bool:
        return True


class LegacyPropFactory(InterfacePropAlgorithmFactory):
    @property
    def name(self) -> str:
        return "legacy"

    def create(self, thermostat: InterfaceThermostatRuntime) -> InterfacePropAlgorithmHandler:
        return LegacyHandler()


class LegacyFeatureManager:
    """Feature manager written for 0.6.0 (structural conformance only)."""

    def post_init(self, entry_infos: Any) -> None:
        return None

    async def start_listening(self, force: bool = False) -> None:
        return None

    def stop_listening(self) -> bool | None:
        return None

    async def refresh_state(self) -> bool:
        return False

    def restore_state(self, old_state: Any) -> None:
        return None

    def add_listener(self, func) -> None:
        return None

    @property
    def is_configured(self) -> bool:
        return True

    @property
    def is_detected(self) -> bool:
        return False

    @property
    def name(self) -> str:
        return "legacy"

    @property
    def hass(self) -> Any:
        return None


class LegacyFeatureFactory:
    @property
    def name(self) -> str:
        return "legacy_feature"

    def supports(self, thermostat: InterfaceThermostatRuntime) -> bool:
        return True

    def create(self, thermostat: InterfaceThermostatRuntime) -> InterfaceFeatureManager:
        return LegacyFeatureManager()  # type: ignore[return-value]


def test_legacy_implementations_satisfy_existing_protocols() -> None:
    assert isinstance(LegacyScheduler(), InterfaceCycleScheduler)
    assert isinstance(LegacyHandler(), InterfacePropAlgorithmHandler)
    assert isinstance(LegacyPropFactory(), InterfacePropAlgorithmFactory)
    assert isinstance(LegacyFeatureManager(), InterfaceFeatureManager)
    assert isinstance(LegacyFeatureFactory(), InterfaceFeatureManagerFactory)


def test_legacy_implementations_register_unchanged() -> None:
    VThermAPI.reset_vtherm_api()
    api = VThermAPI.get_vtherm_api(SimpleNamespace(data={DOMAIN: {}}, config=SimpleNamespace(time_zone="UTC")))

    prop_factory = LegacyPropFactory()
    feature_factory = LegacyFeatureFactory()
    api.register_prop_algorithm(prop_factory)
    api.register_feature_manager(feature_factory)

    assert api.get_prop_algorithm("legacy") is prop_factory
    assert api.get_feature_manager("legacy_feature") is feature_factory

    handler = prop_factory.create(SimpleNamespace())  # type: ignore[arg-type]
    handler.on_scheduler_ready(LegacyScheduler())

    VThermAPI.reset_vtherm_api()


def test_legacy_scheduler_is_not_a_receipt_scheduler() -> None:
    assert not isinstance(LegacyScheduler(), vtherm_api.InterfaceCommandReceiptScheduler)
    assert not hasattr(LegacyScheduler(), "register_command_receipt_callback")


@pytest.mark.asyncio
async def test_legacy_scheduler_start_cycle_keeps_working_without_request_id() -> None:
    scheduler = LegacyScheduler()

    await scheduler.start_cycle("heat", 0.5)
    await scheduler.start_cycle("heat", 0.5, force=True)


def test_legacy_feature_manager_implements_no_underlying_hook() -> None:
    manager = LegacyFeatureManager()
    assert isinstance(manager, InterfaceFeatureManager)
    assert not isinstance(manager, vtherm_api.InterfaceUnderlyingHvacModeHook)
    assert not isinstance(manager, vtherm_api.InterfaceValveCommandHook)
    assert not isinstance(manager, vtherm_api.InterfaceUnderlyingPowerHook)
    assert not hasattr(manager, "async_before_underlying_hvac_mode")
    assert not hasattr(manager, "async_after_valve_command")
    assert not hasattr(manager, "async_on_underlying_power")
