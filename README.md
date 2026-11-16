# vtherm_api

Developer-facing API for integrating with Versatile Thermostat inside Home Assistant.

This package currently exposes two main building blocks:

- `VThermAPI`: a singleton stored in `hass.data` that gives an integration access to the Home Assistant runtime, the proportional algorithm registry, feature-manager registration, and optional plugin-climate linking helpers.
- `PluginClimate`: an event-driven helper that subscribes to Versatile Thermostat events for one linked thermostat and forwards service calls back to that thermostat.
- A proportional algorithm plugin surface: runtime protocols plus a registry that lets an external integration register a proportional control handler by name.
- A minimal inhibition façade (issue #2087): `await VThermAPI.set_inhibition(vtherm_entity_id, stop_underlyings)` and `await VThermAPI.unset_inhibition(vtherm_entity_id)`. The plugin owns detection, policy, and `ACTIVE` / `INACTIVE` / `UNKNOWN`; the VTherm core owns the inhibition state and command gate. See [the API reference](documentation/en/api-reference.md#inhibition-issue-2087).
- An optional command-receipt surface: `InterfaceCommandReceiptScheduler` extends `InterfaceCycleScheduler` so that a proportional algorithm plugin can tag a `start_cycle` request with a `request_id` and receive an `AppliedCommandReceipt` describing the command the scheduler really applied. See [the API reference](documentation/en/api-reference.md#command-receipts).
- An optional regulated-temperature surface: `InterfaceSetpointModifier` lets a feature manager adjust the temperature an `over_climate` thermostat sends to its underlyings. See [the API reference](documentation/en/api-reference.md#regulated-temperature-modifier).
- Optional underlying-command hooks: `InterfaceUnderlyingHvacModeHook`, `InterfaceValveCommandHook` and `InterfaceUnderlyingPowerHook` let a feature manager follow the HVAC mode, valve and power commands the core sends to the underlyings. See [the API reference](documentation/en/api-reference.md#underlying-hooks).
- An optional valve-write hook: `InterfaceValveWriteHook` lets a feature manager change the opening degree before the core writes it to a valve-regulation underlying, or write the valve itself. See [the API reference](documentation/en/api-reference.md#valve-write-hook).
- An optional calibration-offset modifier: `InterfaceCalibrationOffsetModifier` lets a feature manager adjust the offset written to the calibration entity of a device. See [the API reference](documentation/en/api-reference.md#calibration-offset-modifier).

The package is designed for Home Assistant integration code, not as a standalone HTTP or REST API.

**Full documentation**: [documentation/en/index.md](documentation/en/index.md)

## Table of contents

- [vtherm\_api](#vtherm_api)
  - [Table of contents](#table-of-contents)
  - [What this package solves](#what-this-package-solves)
  - [Requirements](#requirements)
  - [Installation for development](#installation-for-development)
  - [Architecture](#architecture)
  - [Public imports](#public-imports)
  - [Using VThermAPI](#using-vthermapi)
    - [Main responsibilities](#main-responsibilities)
    - [Create or retrieve the singleton](#create-or-retrieve-the-singleton)
    - [Reset the singleton](#reset-the-singleton)
  - [Registering a proportional algorithm plugin](#registering-a-proportional-algorithm-plugin)
    - [Link a plugin climate through the API helper](#link-a-plugin-climate-through-the-api-helper)
  - [Creating a FeatureManager](#creating-a-featuremanager)
    - [Example: OddMinuteFeatureManager](#example-oddminutefeaturemanager)
    - [Register the manager through VThermAPI](#register-the-manager-through-vthermapi)
    - [Minimal thermostat side contract](#minimal-thermostat-side-contract)
  - [Registering a FeatureManager factory (per-thermostat)](#registering-a-featuremanager-factory-per-thermostat)
  - [Using PluginClimate](#using-pluginclimate)
    - [What happens when you link it](#what-happens-when-you-link-it)
    - [Basic usage](#basic-usage)
    - [Subclass PluginClimate to react to events](#subclass-pluginclimate-to-react-to-events)
    - [Simulate a VTherm event](#simulate-a-vtherm-event)
    - [Forward an action to the linked thermostat](#forward-an-action-to-the-linked-thermostat)
    - [Remove listeners on unload](#remove-listeners-on-unload)
  - [Supported VTherm events](#supported-vtherm-events)
  - [Practical patterns](#practical-patterns)
    - [Pattern 1: register a proportional algorithm factory](#pattern-1-register-a-proportional-algorithm-factory)
    - [Pattern 2: build a plugin that mirrors temperature updates](#pattern-2-build-a-plugin-that-mirrors-temperature-updates)
    - [Pattern 3: replicate another climate entity to a target VTherm](#pattern-3-replicate-another-climate-entity-to-a-target-vtherm)
    - [Pattern 4: expose a command through your own integration code](#pattern-4-expose-a-command-through-your-own-integration-code)
  - [Testing your integration](#testing-your-integration)
  - [Summary](#summary)

## What this package solves

When you build custom Home Assistant code around Versatile Thermostat, you usually need to:

1. Keep a stable reference to the integration runtime.
2. Track one specific VTherm climate entity.
3. Listen only to that thermostat's events.
4. Relay actions such as HVAC mode or target temperature changes back to the linked thermostat.

This package provides those responsibilities out of the box.
It also lets an external integration register a proportional algorithm factory that VT can resolve dynamically.

## Requirements

- Python 3.14+
- Home Assistant runtime objects such as `HomeAssistant`, `ConfigEntry`, `Event`, and the service bus
- A Versatile Thermostat entity already registered in Home Assistant

For local development, the repository uses Home Assistant `2026.3.1`.

## Installation for development

Install the local development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

Run the test suite:

```bash
pytest
```

## Architecture

```mermaid
flowchart LR
    CE[ConfigEntry] --> API[VThermAPI singleton]
    API --> HD[hass.data]
    VT[Versatile Thermostat entity] -->|emits HA events| BUS[Home Assistant event bus]
    BUS --> PC[PluginClimate]
    PC -->|stores latest payload by event type| STATE[In-memory event cache]
    PC -->|calls services on domain versatile_thermostat| SVC[Home Assistant service registry]
    SVC --> VT
```

```mermaid
sequenceDiagram
    participant VT as Linked VTherm entity
    participant BUS as HA event bus
    participant PC as PluginClimate
    participant HA as HA services

    VT->>BUS: versatile_thermostat_temperature_event
    BUS->>PC: event with entity_id
    PC->>PC: ignore if entity_id does not match
    PC->>PC: store payload in get_event_data cache
    PC->>PC: call matching handle_* method
    PC->>HA: async_call(versatile_thermostat, action, target)
    HA->>VT: execute service for linked entity
```

## Public imports

The package root exports `PluginClimate` and `__version__`.

Use these imports in integration code:

```python
from vtherm_api import (
    InterfaceFeatureManager,
    InterfaceFeatureManagerFactory,
    InterfacePropAlgorithmFactory,
    InterfacePropAlgorithmHandler,
    InterfaceThermostatRuntime,
    PluginClimate,
    VThermAPI,
)
from vtherm_api.const import DOMAIN, EventType
```

## Using VThermAPI

`VThermAPI` is a singleton attached to the Home Assistant runtime through `hass.data[DOMAIN][VTHERM_API_NAME]`.

### Main responsibilities

- attach the API instance to a `HomeAssistant` object
- expose the active `HomeAssistant` object through `api.hass`
- expose a timezone-aware `api.now`
- register and unregister proportional algorithm factories
- register feature managers on compatible VTherm entities
- optionally link a plugin climate entity to a VTherm climate entity

### Create or retrieve the singleton

```python
from vtherm_api.vtherm_api import VThermAPI


async def async_setup_entry(hass, entry) -> bool:
    api = VThermAPI.get_vtherm_api(hass)
    if api is None:
        return False

    print(api.name)  # VThermAPI
    print(api.hass is hass)  # True
    print(api.now)  # timezone-aware datetime from HA
    return True


async def async_unload_entry(hass, entry) -> bool:
    # No explicit unregister call is required for the singleton itself.
    return True
```

### Reset the singleton

This is mainly useful in tests:

```python
from vtherm_api.vtherm_api import VThermAPI


def teardown_function() -> None:
    VThermAPI.reset_vtherm_api()
```

## Registering a proportional algorithm plugin

`VThermAPI` exposes a small registry for proportional algorithm factories:

- `register_prop_algorithm(factory)`
- `unregister_prop_algorithm(name)`
- `get_prop_algorithm(name)`
- `list_prop_algorithms()`

Each registered factory must expose a stable `name` and a `create(thermostat)` method.
The thermostat object passed to the factory implements `InterfaceThermostatRuntime`.

```python
from typing import Any

from vtherm_api import (
    InterfacePropAlgorithmFactory,
    InterfacePropAlgorithmHandler,
    InterfaceThermostatRuntime,
    VThermAPI,
)


class SmartPIHandler(InterfacePropAlgorithmHandler):
    def __init__(self, thermostat: InterfaceThermostatRuntime) -> None:
        self._thermostat = thermostat

    def init_algorithm(self) -> None:
        self._thermostat.prop_algorithm = object()

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

    def on_scheduler_ready(self, scheduler) -> None:
        return None

    def should_publish_intermediate(self) -> bool:
        return True


class SmartPIFactory(InterfacePropAlgorithmFactory):
    @property
    def name(self) -> str:
        return "smart_pi"

    def create(
        self,
        thermostat: InterfaceThermostatRuntime,
    ) -> InterfacePropAlgorithmHandler:
        return SmartPIHandler(thermostat)


def register_plugin(hass: Any) -> None:
    api = VThermAPI.get_vtherm_api(hass)
    if api is not None:
        api.register_prop_algorithm(SmartPIFactory())
```

### Link a plugin climate through the API helper

`VThermAPI.link_to_vtherm(vtherm, plugin_vtherm_entity_id)` searches registered climate entities and links the matching plugin entity to the provided VTherm object.

Use this helper only if your plugin climate is already registered as a Home Assistant climate entity and can be found in the climate component.

```python
from types import SimpleNamespace

from vtherm_api.vtherm_api import VThermAPI


async def async_bind_plugin(hass):
    api = VThermAPI.get_vtherm_api(hass)

    linked_vtherm = SimpleNamespace(entity_id="climate.living_room")
    api.link_to_vtherm(
        linked_vtherm,
        plugin_vtherm_entity_id="climate.living_room_plugin",
    )
```

If you are working with a subclass of `PluginClimate`, direct linking is usually simpler and more explicit. That pattern is shown below.

## Creating a FeatureManager

`InterfaceFeatureManager` defines the contract expected by `VThermAPI.register_manager(...)`.

When you call `api.register_manager(manager)`, the API scans the Home Assistant climate component and forwards the manager to every entity that:

- exposes `device_info["model"] == DOMAIN`
- implements `InterfaceThermostat`

In practice, your custom manager only needs to implement the protocol and then be registered once.

### Example: OddMinuteFeatureManager

The example below toggles `is_detected` to `True` when the current minute is even, and to `False` when it is odd.

```python
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant

from vtherm_api.interfaces import InterfaceFeatureManager
from vtherm_api.vtherm_api import VThermAPI


class OddMinuteFeatureManager(InterfaceFeatureManager):
    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._is_configured = False
        self._is_detected = False
        self._listeners: list[CALLBACK_TYPE] = []

    def post_init(self, entry_infos: dict[str, Any]) -> None:
        self._is_configured = bool(entry_infos)

    async def start_listening(self, force: bool = False) -> None:
        return None

    def stop_listening(self) -> bool:
        for listener in list(self._listeners):
            listener()
        self._listeners.clear()
        return True

    async def refresh_state(self) -> bool:
        api = VThermAPI.get_vtherm_api(self._hass)
        self._is_detected = bool(api and api.now.minute % 2 == 0)
        return self._is_detected

    def restore_state(self, old_state: Any) -> None:
        return None

    def add_listener(self, func: CALLBACK_TYPE) -> None:
        self._listeners.append(func)

    @property
    def is_configured(self) -> bool:
        return self._is_configured

    @property
    def is_detected(self) -> bool:
        return self._is_detected

    @property
    def name(self) -> str:
        return "OddMinuteFeatureManager"

    @property
    def hass(self) -> HomeAssistant:
        return self._hass
```

### Register the manager through VThermAPI

```python
from homeassistant.core import HomeAssistant

from vtherm_api.vtherm_api import VThermAPI


async def async_setup_entry(hass: HomeAssistant) -> None:
    api = VThermAPI.get_vtherm_api(hass)

    manager = OddMinuteFeatureManager(hass)
    manager.post_init({"enabled": True})
    await manager.refresh_state()

    api.register_manager(manager)
```

### Minimal thermostat side contract

The thermostat receiving the manager must implement `InterfaceThermostat` and expose a `register_manager(...)` method. A minimal test double looks like this:

```python
from vtherm_api.const import DOMAIN
from vtherm_api.interfaces import InterfaceFeatureManager, InterfaceThermostat


class FakeVTherm(InterfaceThermostat):
    def __init__(self) -> None:
        self._registered_managers: list[InterfaceFeatureManager] = []

    @property
    def name(self) -> str:
        return "FakeVTherm"

    def register_manager(self, manager: InterfaceFeatureManager) -> None:
        self._registered_managers.append(manager)

    @property
    def unique_id(self) -> str:
        return "fake-vtherm"

    @property
    def device_info(self) -> dict[str, str]:
        return {"model": DOMAIN}
```

This is the same registration flow used in the test suite to validate manager instantiation and registration.

## Registering a FeatureManager factory (per-thermostat)

`api.register_manager(...)` attaches a single manager instance to the thermostats that already exist. When a feature must be instantiated **once per thermostat** (including thermostats built later), and optionally restricted to a given scope (for example `over_climate`), use the **feature manager factory** registry instead.

This mechanism mirrors the proportional algorithm factory: the plugin registers a factory, and the core iterates over the registered factories when building each thermostat, calling `factory.create(runtime)` for every eligible thermostat.

```python
from typing import Any

from vtherm_api.interfaces import (
    InterfaceFeatureManager,
    InterfaceFeatureManagerFactory,
    InterfaceThermostatRuntime,
)
from vtherm_api.vtherm_api import VThermAPI


class AutoFanFeatureManager(InterfaceFeatureManager):
    def __init__(self, thermostat: InterfaceThermostatRuntime) -> None:
        self._thermostat = thermostat

    # ... implement the InterfaceFeatureManager contract ...


class AutoFanManagerFactory(InterfaceFeatureManagerFactory):
    @property
    def name(self) -> str:
        return "auto_fan"

    def supports(self, thermostat: InterfaceThermostatRuntime) -> bool:
        # Restrict the manager to thermostats exposing underlying fan modes.
        return thermostat.underlying_fan_modes is not None

    def create(
        self,
        thermostat: InterfaceThermostatRuntime,
    ) -> InterfaceFeatureManager:
        return AutoFanFeatureManager(thermostat)


def register_plugin(hass: Any) -> None:
    api = VThermAPI.get_vtherm_api(hass)
    if api is not None:
        api.register_feature_manager(AutoFanManagerFactory())
```

The registry exposes:

- `register_feature_manager(factory)` / `unregister_feature_manager(name)`
- `get_feature_manager(name)` / `list_feature_managers()`
- `get_feature_manager_factories()` — used by the core to iterate over the registered factories when constructing a thermostat.

To drive an underlying climate fan from the manager, `InterfaceThermostatRuntime` exposes `regulated_target_temperature`, `underlying_fan_modes`, and `async_set_underlying_fan_mode(fan_mode)`.

## Using PluginClimate

`PluginClimate` is an event listener and service forwarder bound to one linked thermostat.

### What happens when you link it

When you call `plugin.link_to_vtherm(vtherm)`:

1. Existing listeners are removed.
2. The new thermostat reference is stored in `plugin.linked_vtherm`.
3. One Home Assistant listener is registered for each `EventType`.

Only events whose `entity_id` matches `linked_vtherm.entity_id` are handled.

### Basic usage

```python
from types import SimpleNamespace

from homeassistant.core import HomeAssistant

from vtherm_api import PluginClimate


def create_plugin(hass: HomeAssistant) -> PluginClimate:
    plugin = PluginClimate(hass)
    plugin.link_to_vtherm(SimpleNamespace(entity_id="climate.living_room"))
    return plugin
```

### Subclass PluginClimate to react to events

The default handler methods are intentionally empty. Override the handlers you need.

```python
from typing import Any

from homeassistant.core import Event, HomeAssistant

from vtherm_api.const import EventType
from vtherm_api.plugin_climate import PluginClimate


class RecordingPluginClimate(PluginClimate):
    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass)
        self.temperature_updates: list[dict[str, Any]] = []
        self.mode_updates: list[dict[str, Any]] = []

    def handle_temperature_event(self, event: Event) -> None:
        payload = self.get_event_data(EventType.TEMPERATURE_EVENT)
        self.temperature_updates.append(payload)

    def handle_hvac_mode_event(self, event: Event) -> None:
        payload = self.get_event_data(EventType.HVAC_MODE_EVENT)
        self.mode_updates.append(payload)
```

Then link it explicitly:

```python
from types import SimpleNamespace


plugin = RecordingPluginClimate(hass)
plugin.link_to_vtherm(SimpleNamespace(entity_id="climate.living_room"))
```

### Simulate a VTherm event

This is useful in tests or when validating your integration wiring.

```python
from vtherm_api.const import EventType


hass.bus.async_fire(
    EventType.TEMPERATURE_EVENT.value,
    {
        "entity_id": "climate.living_room",
        "current_temperature": 20.5,
        "target_temperature": 21.0,
    },
)
```

After the event is handled:

- `plugin.last_event_type` becomes `EventType.TEMPERATURE_EVENT`
- `plugin.get_event_data(EventType.TEMPERATURE_EVENT)` returns the last payload for that event type

### Forward an action to the linked thermostat

`PluginClimate.call_linked_vtherm_action(...)` delegates a Home Assistant service call to the `versatile_thermostat` domain and automatically targets the linked thermostat entity.

```python
await plugin.call_linked_vtherm_action(
    "set_hvac_mode",
    action_data={"hvac_mode": "heat"},
)

await plugin.call_linked_vtherm_action(
    "set_target_temperature",
    action_data={"temperature": 19.5},
    blocking=True,
)

await plugin.call_linked_vtherm_action(
    "set_preset_mode",
    action_data={"preset_mode": "eco"},
    return_response=True,
)
```

Under the hood, the service call is equivalent to:

```python
await hass.services.async_call(
    DOMAIN,
    action_name,
    action_data,
    blocking,
    context,
    {"entity_id": linked_vtherm.entity_id},
    return_response,
)
```

If no thermostat is linked, the method raises `RuntimeError`.

### Remove listeners on unload

If your integration unloads a plugin climate, remove the listeners explicitly:

```python
plugin.remove_listeners()
```

## Supported VTherm events

The plugin listens to every event defined by `EventType`.

| Event type                        | Home Assistant event name                    | Handler method                 |
| --------------------------------- | -------------------------------------------- | ------------------------------ |
| `EventType.SAFETY_EVENT`          | `versatile_thermostat_safety_event`          | `handle_safety_event`          |
| `EventType.POWER_EVENT`           | `versatile_thermostat_power_event`           | `handle_power_event`           |
| `EventType.TEMPERATURE_EVENT`     | `versatile_thermostat_temperature_event`     | `handle_temperature_event`     |
| `EventType.HVAC_MODE_EVENT`       | `versatile_thermostat_hvac_mode_event`       | `handle_hvac_mode_event`       |
| `EventType.CENTRAL_BOILER_EVENT`  | `versatile_thermostat_central_boiler_event`  | `handle_central_boiler_event`  |
| `EventType.PRESET_EVENT`          | `versatile_thermostat_preset_event`          | `handle_preset_event`          |
| `EventType.WINDOW_AUTO_EVENT`     | `versatile_thermostat_window_auto_event`     | `handle_window_auto_event`     |
| `EventType.AUTO_START_STOP_EVENT` | `versatile_thermostat_auto_start_stop_event` | `handle_auto_start_stop_event` |
| `EventType.TIMED_PRESET_EVENT`    | `versatile_thermostat_timed_preset_event`    | `handle_timed_preset_event`    |
| `EventType.HEATING_FAILURE_EVENT` | `versatile_thermostat_heating_failure_event` | `handle_heating_failure_event` |

## Practical patterns

### Pattern 1: register a proportional algorithm factory

```python
from vtherm_api.vtherm_api import VThermAPI


async def async_setup_entry(hass, entry) -> bool:
    api = VThermAPI.get_vtherm_api(hass)
    if api is None:
        return False

    api.register_prop_algorithm(SmartPIFactory())
    return True


async def async_unload_entry(hass, entry) -> bool:
    api = VThermAPI.get_vtherm_api()
    if api is not None:
        api.unregister_prop_algorithm("smart_pi")
    return True
```

### Pattern 2: build a plugin that mirrors temperature updates

```python
from types import SimpleNamespace

from homeassistant.core import Event

from vtherm_api.const import EventType
from vtherm_api.plugin_climate import PluginClimate


class MirrorPluginClimate(PluginClimate):
    def __init__(self, hass):
        super().__init__(hass)
        self.last_target_temperature = None

    def handle_temperature_event(self, event: Event) -> None:
        payload = self.get_event_data(EventType.TEMPERATURE_EVENT)
        self.last_target_temperature = payload.get("target_temperature")


plugin = MirrorPluginClimate(hass)
plugin.link_to_vtherm(SimpleNamespace(entity_id="climate.office"))
```

### Pattern 3: replicate another climate entity to a target VTherm

This is the pattern used by `vtherm_climate_replication`: track a physical climate entity, then forward selected state changes to the linked VTherm.

```python
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE


async def async_replicate_state(plugin: PluginClimate, state) -> None:
    await plugin.call_linked_vtherm_action(
        SERVICE_SET_HVAC_MODE,
        action_data={ATTR_HVAC_MODE: state.attributes.get(ATTR_HVAC_MODE, state.state)},
    )

    temperature = state.attributes.get(ATTR_TEMPERATURE)
    if temperature is not None:
        await plugin.call_linked_vtherm_action(
            SERVICE_SET_TEMPERATURE,
            action_data={ATTR_TEMPERATURE: temperature},
        )
```

### Pattern 4: expose a command through your own integration code

```python
async def async_set_eco(plugin: PluginClimate) -> None:
    await plugin.call_linked_vtherm_action(
        "set_preset_mode",
        action_data={"preset_mode": "eco"},
        blocking=True,
    )
```

## Testing your integration

The repository tests show the intended behavior clearly:

- `PluginClimate.link_to_vtherm(...)` registers one listener per event type
- unrelated thermostat events are ignored
- the last payload is stored per event type
- `call_linked_vtherm_action(...)` forwards parameters to `hass.services.async_call(...)`

Minimal async test example:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from vtherm_api.plugin_climate import PluginClimate


@pytest.mark.asyncio
async def test_plugin_forwards_hvac_mode() -> None:
    hass = MagicMock()
    hass.services.async_call = AsyncMock(return_value="ok")

    plugin = PluginClimate(hass)
    plugin.link_to_vtherm(SimpleNamespace(entity_id="climate.salon"))

    result = await plugin.call_linked_vtherm_action(
        "set_hvac_mode",
        action_data={"hvac_mode": "heat"},
    )

    assert result == "ok"
```

## Summary

Use `VThermAPI` when you need a stable Home Assistant-scoped singleton for Versatile Thermostat integration state.

Use `PluginClimate` when you need to:

- subscribe to VTherm events for one thermostat
- keep the latest event payloads in memory
- override dedicated handlers for domain-specific behavior
- forward service calls to the linked thermostat without rebuilding the Home Assistant target payload yourself
