# Guide: Create a FeatureManager

## Goal

Extend VTherm thermostat behavior with a custom feature manager that can react to Home Assistant state and expose a detected or not-detected condition back to VTherm.

## Concepts

- `InterfaceFeatureManager` defines the manager contract
- there are two registration mechanisms:
  - `api.register_manager(manager)` scans the HA climate component and forwards **a single manager instance** to the compatible VTherm entities that already exist
  - `api.register_feature_manager(factory)` registers a **factory** so the core instantiates **one manager per eligible thermostat**, including thermostats built later
- the current API does not require `add_entry(...)` or `remove_entry(...)`

> Use `register_manager(...)` for a shared, singleton-like feature. Use `register_feature_manager(...)` when each thermostat needs its own manager instance or when the feature must be restricted to a scope such as `over_climate`.

## Step 1: Implement the manager

```python
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant

from vtherm_api import VThermAPI


class MyFeatureManager:
    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._is_configured = False
        self._is_detected = False
        self._listeners: list[CALLBACK_TYPE] = []

    def post_init(self, entry_infos: dict[str, Any]) -> None:
        self._is_configured = entry_infos.get("my_feature_enabled", False)

    async def start_listening(self, force: bool = False) -> None:
        return None

    def stop_listening(self) -> bool:
        for cancel in list(self._listeners):
            cancel()
        self._listeners.clear()
        return True

    async def refresh_state(self) -> bool:
        previous = self._is_detected
        api = VThermAPI.get_vtherm_api(self._hass)
        self._is_detected = api is not None and self._is_configured
        return self._is_detected != previous

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
        return "MyFeatureManager"

    @property
    def hass(self) -> HomeAssistant:
        return self._hass
```

## Step 2: Register the manager

```python
from vtherm_api import VThermAPI


async def async_setup_entry(hass, entry) -> bool:
    api = VThermAPI.get_vtherm_api(hass)
    if api is None:
        return False

    manager = MyFeatureManager(hass)
    manager.post_init(dict(entry.data))
    await manager.refresh_state()
    api.register_manager(manager)
    return True
```

## Step 3: Unload

VTherm is responsible for the lifecycle of registered managers on the thermostat side.
Your integration normally only unloads its own resources:

```python
async def async_unload_entry(hass, entry) -> bool:
    return True
```

## How registration works

When `api.register_manager(manager)` is called, the API:

1. scans the Home Assistant `climate` component
2. keeps entities implementing `InterfaceThermostat`
3. keeps only entities whose `device_info["model"] == DOMAIN`
4. calls `entity.register_manager(manager)` on each matching thermostat

## Minimal thermostat test double

```python
from vtherm_api.const import DOMAIN
from vtherm_api.interfaces import InterfaceFeatureManager


class FakeVTherm:
    def __init__(self) -> None:
        self.managers: list[InterfaceFeatureManager] = []

    @property
    def name(self) -> str:
        return "FakeVTherm"

    @property
    def unique_id(self) -> str:
        return "fake-vtherm-001"

    @property
    def device_info(self) -> dict:
        return {"model": DOMAIN}

    def register_manager(self, manager: InterfaceFeatureManager) -> None:
        self.managers.append(manager)
```

## Per-thermostat registration with a factory

When a feature must be instantiated once per thermostat (including thermostats built later), and optionally restricted to a scope such as `over_climate`, register a **feature manager factory** instead of a single instance. This mirrors the proportional algorithm factory: the plugin registers a factory, and the core iterates over the registered factories when building each thermostat, calling `factory.create(runtime)` for every eligible thermostat.

### Step 1: Implement the factory

The factory implements `InterfaceFeatureManagerFactory`: a stable `name`, a `supports(thermostat)` predicate used by the core to skip incompatible thermostats, and a `create(thermostat)` method that returns an `InterfaceFeatureManager` bound to the runtime.

```python
from vtherm_api.interfaces import (
    InterfaceFeatureManager,
    InterfaceFeatureManagerFactory,
    InterfaceThermostatRuntime,
)


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
```

### Step 2: Register the factory

```python
from vtherm_api import VThermAPI


async def async_setup_entry(hass, entry) -> bool:
    api = VThermAPI.get_vtherm_api(hass)
    if api is None:
        return False

    factory = AutoFanManagerFactory()
    if api.get_feature_manager(factory.name) is None:
        api.register_feature_manager(factory)
    return True


async def async_unload_entry(hass, entry) -> bool:
    api = VThermAPI.get_vtherm_api()
    if api is not None:
        api.unregister_feature_manager("auto_fan")
    return True
```

### Registry methods

- `register_feature_manager(factory)` / `unregister_feature_manager(name)`
- `get_feature_manager(name)` / `list_feature_managers()`
- `get_feature_manager_factories()` — used by the core to iterate over the registered factories when constructing a thermostat

### Driving the underlying fan

To drive an underlying climate fan from the manager, `InterfaceThermostatRuntime` exposes:

- `regulated_target_temperature` — the regulated setpoint used to drive the underlying
- `underlying_fan_modes` — the fan modes exposed by the underlying climate(s)
- `async_set_underlying_fan_mode(fan_mode)` — send a fan mode to the underlying climate(s)

### Adjusting the regulated temperature

An `over_climate` thermostat computes a regulated temperature and sends it to the underlying climate. A feature manager can adjust it, for example to limit how fast it moves, by implementing `InterfaceSetpointModifier`:

```python
class RampingFeatureManager(MyFeatureManager):
    def adjust_regulated_temperature(
        self,
        desired: float,
        regulation_step: float,
        command_cause: str | None,
    ) -> float | None:
        # Return the temperature to send, or None to keep `desired`
        return desired
```

The core calls the method only while `is_configured` is `True`, after the self-regulation and before the rounding, the regulation delta filter and the send. See [Regulated temperature modifier](../api-reference.md#regulated-temperature-modifier) for the full contract.

### Following the underlying commands

A feature manager can follow the commands the core sends to the underlyings by implementing one or more optional hooks. The hooks are notifications: they never change or cancel the command. Each one is a coroutine, so implement only the ones you need:

```python
from vtherm_api import UnderlyingPowerCommand, ValveCommand


class QuirkFeatureManager(MyFeatureManager):
    async def async_before_underlying_hvac_mode(
        self,
        climate_entity_id: str,
        hvac_mode: str,
        current_hvac_mode: str | None,
        command_cause: str | None,
    ) -> None:
        # Called just before climate.set_hvac_mode is sent to the underlying
        ...

    async def async_after_valve_command(self, command: ValveCommand) -> None:
        # Called after the opening and closing degrees have been sent.
        # When the thermostat goes OFF, the valve is closed after the OFF mode,
        # with cause REGULATION and hvac_mode "off".
        if command.hvac_mode == "off":
            ...

    async def async_on_underlying_power(self, command: UnderlyingPowerCommand) -> None:
        # Called at cycle start, valve update and cycle stop, for each underlying
        ...
```

The core calls a hook only while `is_configured` is `True` and only if its own command is really sent. It waits for the hook, so return quickly and run any long treatment (waiting, retry) in a task or with `async_call_later`. After `UNDERLYING_HOOK_TIMEOUT_SEC` seconds the core stops waiting, logs an error and sends its command. See [Underlying hooks](../api-reference.md#underlying-hooks) for the full contract.
