""" Some constants for the VThermAPI library """

from datetime import datetime
from enum import Enum
from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant
DEVICE_MANUFACTURER = "JMCOLLIN"
DEVICE_MODEL = "Versatile Thermostat"

DOMAIN = "versatile_thermostat"

VTHERM_API_NAME = "vtherm_api"
CONF_NAME = "name"

UNDERLYING_HOOK_TIMEOUT_SEC = 10
"""Seconds after which the core stops waiting for an underlying hook."""


class EventType(Enum):
    """The event type that can be sent"""

    SAFETY_EVENT = "versatile_thermostat_safety_event"
    POWER_EVENT = "versatile_thermostat_power_event"
    TEMPERATURE_EVENT = "versatile_thermostat_temperature_event"
    HVAC_MODE_EVENT = "versatile_thermostat_hvac_mode_event"
    CENTRAL_BOILER_EVENT = "versatile_thermostat_central_boiler_event"
    PRESET_EVENT = "versatile_thermostat_preset_event"
    WINDOW_AUTO_EVENT = "versatile_thermostat_window_auto_event"
    AUTO_START_STOP_EVENT = "versatile_thermostat_auto_start_stop_event"
    TIMED_PRESET_EVENT = "versatile_thermostat_timed_preset_event"
    HEATING_FAILURE_EVENT = "versatile_thermostat_heating_failure_event"


def get_tz(hass: HomeAssistant):
    """Get the current timezone"""

    return dt_util.get_time_zone(hass.config.time_zone)


class NowClass:
    """For testing purpose only"""

    @staticmethod
    def get_now(hass: HomeAssistant) -> datetime:
        """A test function to get the now.
        For testing purpose this method can be overriden to get a specific
        timestamp.
        """
        return datetime.now(get_tz(hass))
