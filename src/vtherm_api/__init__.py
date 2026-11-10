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
from .calibration_modifier import CalibrationOffsetRequest, InterfaceCalibrationOffsetModifier
from .const import UNDERLYING_HOOK_TIMEOUT_SEC
from .hvac_mode_mapper import UNSUPPORTED_HVAC_MODE, InterfaceUnderlyingHvacModeMapper
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
from .valve_write import InterfaceValveWriteHook, ValveWriteDecision, ValveWriteRequest
from .vtherm_api import VThermAPI

__version__ = "0.9.0"

__all__ = [
    "AppliedCommandReceipt",
    "CalibrationOffsetRequest",
    "CommandAlteration",
    "CommandReceiptCallback",
    "CommandReceiptKind",
    "InhibitionNotStartedError",
    "InterfaceCalibrationOffsetModifier",
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
    "InterfaceUnderlyingHvacModeMapper",
    "InterfaceUnderlyingPowerHook",
    "InterfaceValveCommandHook",
    "InterfaceValveWriteHook",
    "PowerCommandKind",
    "UNDERLYING_HOOK_TIMEOUT_SEC",
    "UNSUPPORTED_HVAC_MODE",
    "UnderlyingPowerCommand",
    "ValveCommand",
    "ValveCommandCause",
    "ValveDiagnosticState",
    "ValveWriteDecision",
    "ValveWriteRequest",
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
