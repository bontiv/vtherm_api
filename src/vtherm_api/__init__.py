"""Public package for the Versatile Thermostat API."""

from .command_receipt import (
    AppliedCommandReceipt,
    CommandAlteration,
    CommandReceiptCallback,
    CommandReceiptKind,
    InterfaceCommandReceiptScheduler,
)
from .interfaces import (
    InterfaceCycleScheduler,
    InterfaceFeatureManager,
    InterfaceFeatureManagerFactory,
    InterfacePropAlgorithmFactory,
    InterfacePropAlgorithmHandler,
    InterfaceThermostat,
    InterfaceThermostatRuntime,
    ValveDiagnosticState,
)
from .const import UNDERLYING_HOOK_TIMEOUT_SEC
from .inhibition import InhibitionNotStartedError
from .log_collector import (
    VThermLogEntry,
    VThermLogHandler,
    VThermLogger,
    async_export_logs,
    get_vtherm_logger,
    write_event_log,
)
from .plugin_climate import PluginClimate
from .setpoint_modifier import InterfaceSetpointModifier
from .underlying_hooks import (
    InterfaceUnderlyingHvacModeHook,
    InterfaceUnderlyingPowerHook,
    InterfaceValveCommandHook,
    PowerCommandKind,
    UnderlyingPowerCommand,
    ValveCommand,
    ValveCommandCause,
)
from .vtherm_api import VThermAPI

__version__ = "0.9.0"

__all__ = [
    "AppliedCommandReceipt",
    "CommandAlteration",
    "CommandReceiptCallback",
    "CommandReceiptKind",
    "InhibitionNotStartedError",
    "InterfaceCommandReceiptScheduler",
    "InterfaceCycleScheduler",
    "InterfaceFeatureManager",
    "InterfaceFeatureManagerFactory",
    "InterfacePropAlgorithmFactory",
    "InterfacePropAlgorithmHandler",
    "InterfaceSetpointModifier",
    "InterfaceThermostat",
    "InterfaceThermostatRuntime",
    "InterfaceUnderlyingHvacModeHook",
    "InterfaceUnderlyingPowerHook",
    "InterfaceValveCommandHook",
    "PowerCommandKind",
    "UNDERLYING_HOOK_TIMEOUT_SEC",
    "UnderlyingPowerCommand",
    "ValveCommand",
    "ValveCommandCause",
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
]
