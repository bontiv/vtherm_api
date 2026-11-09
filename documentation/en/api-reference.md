# API Reference

## VThermAPI

**Module**: `vtherm_api.vtherm_api`

Singleton stored in `hass.data[DOMAIN][VTHERM_API_NAME]`.

### Class methods

#### `VThermAPI.get_vtherm_api(hass=None) -> VThermAPI | None`

Get or create the singleton instance.

- If `hass` is provided, the singleton is created on first call and stored in `hass.data`.
- If `hass` is omitted, the existing singleton is returned if already created.

#### `VThermAPI.reset_vtherm_api() -> None`

Reset the singleton and clear the proportional-algorithm and feature-manager factory registries.
Mainly useful in tests.

### Properties

| Property | Type            | Description                                           |
| -------- | --------------- | ----------------------------------------------------- |
| `hass`   | `HomeAssistant` | Home Assistant instance associated with the singleton |
| `name`   | `str`           | Always `"VThermAPI"`                                  |
| `now`    | `datetime`      | Timezone-aware datetime from Home Assistant           |

### Instance methods

#### `register_prop_algorithm(factory: InterfacePropAlgorithmFactory) -> None`

Register or replace a proportional algorithm factory by name.

#### `unregister_prop_algorithm(name: str) -> None`

Remove a proportional algorithm factory by name.

#### `get_prop_algorithm(name: str) -> InterfacePropAlgorithmFactory | None`

Return the factory registered for `name`, or `None`.

#### `list_prop_algorithms() -> list[str]`

Return registered factory names in sorted order.

#### `register_feature_manager(factory: InterfaceFeatureManagerFactory) -> None`

Register or replace a feature manager factory by name.

Unlike `register_manager(...)`, which attaches a single manager instance to the thermostats that already exist, this registry lets the core instantiate **one manager per thermostat** by calling `factory.create(runtime)` for every eligible thermostat (including thermostats built later).

Raises `ValueError` if `factory.name` is empty.

#### `unregister_feature_manager(name: str) -> None`

Remove a feature manager factory by name.

#### `get_feature_manager(name: str) -> InterfaceFeatureManagerFactory | None`

Return the feature manager factory registered for `name`, or `None`.

#### `list_feature_managers() -> list[str]`

Return registered feature manager factory names in sorted order.

#### `get_feature_manager_factories() -> list[InterfaceFeatureManagerFactory]`

Return the registered feature manager factories, sorted by name.
The core iterates over these factories when building a thermostat to instantiate one feature manager per eligible thermostat.

#### `await set_inhibition(vtherm_entity_id: str, stop_underlyings: bool) -> None`

Ask the targeted VTherm core to enter inhibition. `stop_underlyings` authorizes
only the optional physical entry stop; the core independently closes its command
gate, resolves the effective HVAC state, and suspends normal control.

Raises `LookupError` when no climate entity matches `vtherm_entity_id`, `TypeError`
when the matched entity does not implement the updated core operations or when
`stop_underlyings` is not a boolean, and `ValueError` for an empty entity ID.

Raises `InhibitionNotStartedError` while the VTherm has not restored its
inhibition state at startup; nothing is changed (see `is_inhibition_started`).

#### `await unset_inhibition(vtherm_entity_id: str) -> None`

Ask the targeted VTherm core to leave inhibition. Plugins call this only after
they confirm their own `INACTIVE` state. The core performs the exit
reconciliation and opens its command gate only when that operation succeeds.

Raises `InhibitionNotStartedError` while the VTherm has not restored its
inhibition state at startup; nothing is changed. Other errors are raised like
`set_inhibition`, plus the core's error when the exit reconciliation fails.

#### `is_inhibition_started(vtherm_entity_id: str) -> bool`

Return `True` once the targeted VTherm accepts `set_inhibition` and
`unset_inhibition`. A VTherm restores its inhibition state at the very
beginning of its startup; before that, both operations raise
`InhibitionNotStartedError`. A plugin checks this before calling, and checks
again later (for example at the VTherm's next state change) while it is
`False`. A core that does not expose this state accepts the operations at any
time and is reported started. Raises like `set_inhibition` when the target is
missing or does not support inhibition.

#### `link_to_vtherm(vtherm, plugin_vtherm_entity_id: str) -> None`

Search the Home Assistant climate component for a plugin climate entity matching `plugin_vtherm_entity_id`, then call `plugin.link_to_vtherm(vtherm)`.

This helper is only useful when your plugin climate is itself an HA climate entity.
For many integrations, direct linking through `PluginClimate.link_to_vtherm(...)` is simpler.

#### `register_manager(manager: InterfaceFeatureManager) -> None`

Register a feature manager across VTherm thermostat entities found in the Home Assistant climate component.

Only entities implementing `InterfaceThermostat` and exposing `device_info["model"] == DOMAIN` receive the manager.

#### `_set_now(now: datetime) -> None`

Testing helper that overrides the value returned by `api.now`.

---

## PluginClimate

**Module**: `vtherm_api.plugin_climate`

Helper bound to exactly one linked VTherm thermostat.
It can subscribe to VTherm events, cache the latest payload for each event type, and forward HA service calls to the linked thermostat.

### Constructor

```python
plugin = PluginClimate(hass)
```

### Linking methods

#### `link_to_vtherm(vtherm: Any) -> None`

Link the helper to a VTherm object.

- removes previous listeners
- stores the VTherm reference in `linked_vtherm`
- registers one HA listener for every `EventType`

Only events whose payload `entity_id` matches `linked_vtherm.entity_id` are processed.

#### `remove_listeners() -> None`

Remove all registered HA listeners.

### Properties

#### `linked_vtherm`

Return the currently linked VTherm object, or `None`.

#### `last_event_type`

Return the last handled `EventType`, or `None`.

### Event data helpers

#### `get_event_data(event_type: EventType) -> dict[str, Any]`

Return the most recent payload received for the given event type.
Returns `{}` if no event of that type has been seen yet.

### Event entrypoint

#### `handle_vtherm_event(event: Event) -> None`

Public wrapper around the internal event handling path.
Useful in tests or when invoking the dispatcher manually.

### Event handlers

Override only the handlers you need in a subclass:

| Method                                | Triggered by                      |
| ------------------------------------- | --------------------------------- |
| `handle_safety_event(event)`          | `EventType.SAFETY_EVENT`          |
| `handle_power_event(event)`           | `EventType.POWER_EVENT`           |
| `handle_temperature_event(event)`     | `EventType.TEMPERATURE_EVENT`     |
| `handle_hvac_mode_event(event)`       | `EventType.HVAC_MODE_EVENT`       |
| `handle_central_boiler_event(event)`  | `EventType.CENTRAL_BOILER_EVENT`  |
| `handle_preset_event(event)`          | `EventType.PRESET_EVENT`          |
| `handle_window_auto_event(event)`     | `EventType.WINDOW_AUTO_EVENT`     |
| `handle_auto_start_stop_event(event)` | `EventType.AUTO_START_STOP_EVENT` |
| `handle_timed_preset_event(event)`    | `EventType.TIMED_PRESET_EVENT`    |
| `handle_heating_failure_event(event)` | `EventType.HEATING_FAILURE_EVENT` |

### Action forwarding

#### `await call_linked_vtherm_action(action_name, action_data=None, blocking=False, context=None, return_response=False) -> Any`

Forward a service call to the linked VTherm thermostat.

Internally this becomes:

```python
await hass.services.async_call(
    domain=DOMAIN,
    service=action_name,
    service_data=action_data,
    blocking=blocking,
    context=context,
    target={"entity_id": linked_vtherm.entity_id},
    return_response=return_response,
)
```

Raises `RuntimeError` if no thermostat is linked.

---

## Interfaces

All interfaces are defined as runtime-checkable `Protocol` classes in `vtherm_api.interfaces`.

### InterfaceThermostat

Minimal contract expected of a VTherm thermostat entity.

| Member                      | Type           | Description               |
| --------------------------- | -------------- | ------------------------- |
| `name`                      | `str` property | Human-readable name       |
| `unique_id`                 | `str` property | Unique identifier         |
| `device_info`               | `DeviceInfo    | None` property            | HA device info |
| `register_manager(manager)` | method         | Accepts a feature manager |

### InterfaceFeatureManager

Contract for a feature manager registered through `VThermAPI.register_manager(...)`.

| Member                     | Signature                 | Description                                 |
| -------------------------- | ------------------------- | ------------------------------------------- |
| `name`                     | `str` property            | Logical manager name                        |
| `hass`                     | `HomeAssistant` property  | Home Assistant instance                     |
| `is_configured`            | `bool` property           | Whether the manager is configured           |
| `is_detected`              | `bool` property           | Whether the condition is currently detected |
| `post_init(entry_infos)`   | `(dict) -> None`          | Receive merged config                       |
| `start_listening(force)`   | `async (bool) -> None`    | Start subscriptions                         |
| `stop_listening()`         | `() -> bool               | None`                                       | Stop subscriptions |
| `refresh_state()`          | `async () -> bool`        | Refresh internal state                      |
| `restore_state(old_state)` | `(Any) -> None`           | Restore old state                           |
| `add_listener(func)`       | `(CALLBACK_TYPE) -> None` | Register cleanup callbacks                  |

### InterfaceThermostatRuntime

Runtime view exposed to proportional algorithm handlers.

#### Writable attributes

| Attribute                    | Type  | Description                |
| ---------------------------- | ----- | -------------------------- |
| `prop_algorithm`             | `Any` | Current algorithm object   |
| `minimal_activation_delay`   | `int` | Minimum activation delay   |
| `minimal_deactivation_delay` | `int` | Minimum deactivation delay |

#### Read-only properties

| Property                       | Type                     | Description                         |
| ------------------------------ | ------------------------ | ----------------------------------- |
| `hass`                         | `HomeAssistant`          | Home Assistant instance             |
| `entity_id`                    | `str`                    | Entity id                           |
| `name`                         | `str`                    | Thermostat name                     |
| `unique_id`                    | `str`                    | Unique id                           |
| `entry_infos`                  | `ConfigData              | dict`                               | Merged thermostat config                                  |
| `current_temperature`          | `float                   | None`                               | Room temperature                                          |
| `current_outdoor_temperature`  | `float                   | None`                               | Outdoor temperature                                       |
| `target_temperature`           | `float                   | None`                               | Target temperature                                        |
| `regulated_target_temperature` | `float                   | None`                               | Regulated target temperature used to drive the underlying |
| `last_temperature_slope`       | `float                   | None`                               | Latest temperature slope                                  |
| `vtherm_hvac_mode`             | `str                     | None`                               | VTherm HVAC mode                                          |
| `hvac_action`                  | `str                     | None`                               | HVAC action                                               |
| `hvac_off_reason`              | `str                     | None`                               | HVAC off reason                                           |
| `cycle_min`                    | `int`                    | Cycle length in minutes             |
| `cycle_scheduler`              | `InterfaceCycleScheduler | None`                               | Cycle scheduler                                           |
| `is_device_active`             | `bool`                   | Whether the underlying device is on |
| `is_overpowering_detected`     | `bool`                   | Whether power shedding is active    |
| `underlying_fan_modes`         | `list[str]               | None`                               | Fan modes exposed by the underlying climate(s)            |

#### Methods

| Method                                    | Signature             | Description                                  |
| ----------------------------------------- | --------------------- | -------------------------------------------- |
| `async_set_underlying_fan_mode(fan_mode)` | `async (str) -> None` | Send a fan mode to the underlying climate(s) |
| `async_underlying_entity_turn_off()`      | `async () -> None`    | Turn off the underlying entities             |
| `async_control_heating(timestamp, force)` | `async (datetime      | None, bool) -> bool`                         | Trigger VTherm control |
| `update_custom_attributes()`              | `() -> None`          | Refresh custom state attributes              |
| `async_write_ha_state()`                  | `() -> None`          | Publish state to Home Assistant              |

### InterfacePropAlgorithmHandler

Lifecycle contract for one proportional algorithm handler instance.

| Method                              | Signature                           | Description                                           |
| ----------------------------------- | ----------------------------------- | ----------------------------------------------------- |
| `init_algorithm()`                  | `() -> None`                        | Initialize algorithm state                            |
| `async_added_to_hass()`             | `async () -> None`                  | Called when entity is added to HA                     |
| `async_startup()`                   | `async () -> None`                  | Called after VTherm startup                           |
| `remove()`                          | `() -> None`                        | Cleanup resources                                     |
| `control_heating(timestamp, force)` | `async (datetime                    | None, bool) -> None`                                  | Run one control iteration |
| `on_state_changed(changed)`         | `async (bool) -> None`              | React to thermostat state refreshes and state changes |
| `on_scheduler_ready(scheduler)`     | `(InterfaceCycleScheduler) -> None` | Receive scheduler                                     |
| `should_publish_intermediate()`     | `() -> bool`                        | Allow intermediate state publication                  |

### InterfacePropAlgorithmFactory

Factory registered in `VThermAPI`.

| Member               | Signature                                                       | Description                 |
| -------------------- | --------------------------------------------------------------- | --------------------------- |
| `name`               | `str` property                                                  | Unique algorithm identifier |
| `create(thermostat)` | `(InterfaceThermostatRuntime) -> InterfacePropAlgorithmHandler` | Create a handler            |

### InterfaceFeatureManagerFactory

Factory used by external integrations to register a feature manager instantiated **once per thermostat**. Registered through `VThermAPI.register_feature_manager(...)`.

| Member                 | Signature                                                 | Description                                                                                                                                                                  |
| ---------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                 | `str` property                                            | Feature manager identifier (e.g. `"auto_fan"`)                                                                                                                               |
| `supports(thermostat)` | `(InterfaceThermostatRuntime) -> bool`                    | Return `True` when the manager is eligible for the thermostat, letting the core skip incompatible thermostats (for example a manager restricted to the `over_climate` scope) |
| `create(thermostat)`   | `(InterfaceThermostatRuntime) -> InterfaceFeatureManager` | Create a feature manager bound to the runtime thermostat                                                                                                                     |

### InterfaceCycleScheduler

Contract exposed by the VTherm cycle scheduler.

| Member                                      | Signature                          | Description                   |
| ------------------------------------------- | ---------------------------------- | ----------------------------- |
| `is_cycle_running`                          | `bool` property                    | Whether a cycle is active     |
| `register_cycle_start_callback(callback)`   | `(Callable) -> None`               | Register cycle start callback |
| `register_cycle_end_callback(callback)`     | `(Callable) -> None`               | Register cycle end callback   |
| `start_cycle(hvac_mode, on_percent, force)` | `async (Any, float, bool) -> None` | Start or update a cycle       |
| `cancel_cycle()`                            | `async () -> None`                 | Cancel the current cycle      |

### Command receipts

Module `vtherm_api.command_receipt`, all names re-exported from `vtherm_api`.

An optional extension of `InterfaceCycleScheduler`. `InterfaceCycleScheduler` itself is unchanged: a scheduler that does not implement the extension still satisfies it, and an algorithm plugin that ignores the extension keeps working as before.

A plugin tags each request with an opaque `request_id`; the scheduler echoes it in a receipt for the command it really applies, with the applied actuator power and the reasons why it differs from the request.

| Name                               | Kind             | Values / members                                                                                                                                                                                            |
| ---------------------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CommandReceiptKind`               | `StrEnum`        | `CYCLE_START="cycle_start"`, `UPDATE="update"`                                                                                                                                                              |
| `CommandAlteration`                | `StrEnum`        | `MIN_ON_OFF="min_on_off"` (switch), `VALVE_RETAINED="valve_retained"` (valve)                                                                                                                               |
| `AppliedCommandReceipt`            | frozen dataclass | `kind`, `request_id`, `hvac_mode`, `requested_on_percent`, `applied_on_percent`, `on_time_sec`, `off_time_sec`, `cycle_duration_sec`, `cycle_start_monotonic`, `monotonic`, `is_repeat`, `alterations`       |
| `CommandReceiptCallback`           | type             | `Callable[[AppliedCommandReceipt], Awaitable[None]]`                                                                                                                                                        |
| `InterfaceCommandReceiptScheduler` | runtime protocol | extends `InterfaceCycleScheduler` with `is_valve_mode`, `register_command_receipt_callback(callback)` and `start_cycle(hvac_mode, on_percent, force=False, *, request_id=None)`                              |

`AppliedCommandReceipt` fields:

| Field                   | Type                          | Description                                                                                                          |
| ----------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `kind`                  | `CommandReceiptKind`          | Origin of the receipt                                                                                                |
| `request_id`            | `int` or `None`                  | Echo of the `request_id` of `start_cycle`; `None` for an internal scheduler path or an untagged request             |
| `hvac_mode`             | `str`                         | HVAC mode of the applied command                                                                                     |
| `requested_on_percent`  | `float`                       | Request received for this `request_id`, clamped to [0, 1]                                                            |
| `applied_on_percent`    | `float`                       | Actuator power applied: `on_time / cycle_duration` for a switch, the retained ratio for a valve                      |
| `on_time_sec`           | `int`                         | On time of the cycle in seconds (diagnostic for a valve)                                                             |
| `off_time_sec`          | `int`                         | Off time of the cycle in seconds (diagnostic for a valve)                                                            |
| `cycle_duration_sec`    | `float`                       | Master cycle duration in seconds                                                                                     |
| `cycle_start_monotonic` | `float` or `None`                | `time.monotonic()` at the start of the current master cycle; `None` for an `UPDATE` outside a cycle                  |
| `monotonic`             | `float`                       | `time.monotonic()` at the emission of the receipt                                                                    |
| `is_repeat`             | `bool`                        | `True` for an automatic restart at the end of a master cycle                                                         |
| `alterations`           | `frozenset[CommandAlteration]` | Reasons why applied differs from requested; empty when only the normal quantization applies                         |

Rules:

- **Tagging.** The plugin passes `request_id=` to `start_cycle`. The scheduler never interprets it: it stores it with the pending and the active request and echoes it in the receipt of the command it really applies. When the scheduler applies an older request than the latest one received, the receipt carries the older identifier.
- **`CYCLE_START`.** Emitted for each master-cycle start, including the automatic restart at the end of a master cycle (`is_repeat=True`, same `request_id`). It is emitted right after the cycle start callbacks and before the actuation.
- **`UPDATE`.** Emitted for each valve `start_cycle` that goes through the running-cycle path, even when the value is unchanged, and for each deferred valve update (`request_id=None`).
- **No receipt** for a switch request stored as pending during an active cycle; its receipt is emitted when it is applied.
- **Sticky alterations.** Alterations are sticky per `request_id`: an automatic restart inherits the alterations of the cycle that first applied the request.
- **Not covered.** Cancellation, HVAC OFF and power shedding are reported by the cycle end callback (`elapsed_ratio < 1`), not by receipts.
- **Callbacks** are coroutines and are awaited. An exception raised by a callback is logged and does not break the cycle.
- **Capability detection.** Check `isinstance(scheduler, InterfaceCommandReceiptScheduler)` (or `hasattr(scheduler, "register_command_receipt_callback")`) before passing `request_id`, since a scheduler without the extension does not accept it.
- The receipt callback is registered separately from the cycle start callback, whose keyword signature is unchanged.

```python
from vtherm_api import AppliedCommandReceipt, InterfaceCommandReceiptScheduler


def on_scheduler_ready(self, scheduler) -> None:
    if isinstance(scheduler, InterfaceCommandReceiptScheduler):
        self._remove_receipt = scheduler.register_command_receipt_callback(self._on_receipt)


async def _on_receipt(self, receipt: AppliedCommandReceipt) -> None:
    ...
```

### Regulated temperature modifier

Module `vtherm_api.setpoint_modifier`, name re-exported from `vtherm_api`.

An optional extension of the feature manager contract. `InterfaceFeatureManager` itself is unchanged: a manager that does not implement the extension still satisfies it, and the core detects the capability with `hasattr(manager, "adjust_regulated_temperature")`.

| Name                       | Kind             | Members                                                                                                  |
| -------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------- |
| `InterfaceSetpointModifier` | runtime protocol | `adjust_regulated_temperature(desired, regulation_step, command_cause) -> float \| None`                 |

Rules:

- The core calls the method on a feature manager whose `is_configured` is `True`, each time an `over_climate` thermostat computes the regulated temperature. The call comes after the self-regulation and before the core adds the device temperature offset, rounds to `regulation_step`, filters a change smaller than the regulation delta and sends the result. The regulation period, the delta filter and the cycle stay under the control of the core.
- `desired` is the regulated temperature computed by the core. `regulation_step` is the step the core rounds to: a change smaller than this step is swallowed. `command_cause` is `None` for a regular regulation and `"underlying_tracking"` when the thermostat follows a change made on the device itself.
- The method returns the temperature to use, or `None` to keep `desired`.
- The method is a plain function, not a coroutine. It must be quick and must not block.
- When at least one configured manager implements the method, the core sends the regulated temperature to the underlyings before it changes their HVAC mode, so that a device does not start at its own stored setpoint. This does not happen when the device itself changed its mode.
- The manager sees the thermostat go OFF through `refresh_state`, which the core calls on every control cycle.
- An exception raised by the method is logged and does not break the regulation: `desired` is used.

### Underlying hooks

Module `vtherm_api.underlying_hooks`, names re-exported from `vtherm_api`. `UNDERLYING_HOOK_TIMEOUT_SEC` is in `vtherm_api.const` and re-exported too.

Three optional extensions of the feature manager contract that let a plugin follow the commands the core sends to the underlyings, for example to work around the quirks of a device model. `InterfaceFeatureManager` itself is unchanged: a manager implements only the hooks it needs, and the core detects each capability with `hasattr` on the method name.

| Name                              | Kind             | Members                                                                                                  |
| --------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------- |
| `InterfaceUnderlyingHvacModeHook` | runtime protocol | `async_before_underlying_hvac_mode(climate_entity_id, hvac_mode, current_hvac_mode, command_cause) -> None` |
| `InterfaceValveCommandHook`       | runtime protocol | `async_after_valve_command(command: ValveCommand) -> None`                                               |
| `InterfaceUnderlyingPowerHook`    | runtime protocol | `async_on_underlying_power(command: UnderlyingPowerCommand) -> None`                                     |
| `ValveCommand`                    | frozen dataclass | valve command really sent to a `valve_regulation` underlying                                             |
| `ValveCommandCause`               | `StrEnum`        | `REGULATION`, `TURN_OFF`, `STARTUP`, `REPAIR`                                                            |
| `UnderlyingPowerCommand`          | frozen dataclass | power requested from and applied to one underlying                                                       |
| `PowerCommandKind`                | `StrEnum`        | `CYCLE_START`, `UPDATE`, `STOP`                                                                          |
| `UNDERLYING_HOOK_TIMEOUT_SEC`     | constant         | `10`                                                                                                     |

Common rules:

- The hooks are notifications. None of them modifies or cancels the command of the core.
- Each hook is optional and independent. A manager can implement only one.
- The core calls a hook only on a feature manager whose `is_configured` is `True`.
- A hook is a coroutine awaited by the core. It must return quickly: a long treatment (waiting, kick) is scheduled with `async_call_later` or a task, without blocking the hook. The core stops waiting after `UNDERLYING_HOOK_TIMEOUT_SEC` seconds.
- An exception or a timeout is logged and never prevents the command of the core.
- A hook is called only if the command of the core is really sent. It is not called if the inhibition gate blocks the command, if the requested mode is already in place or if the load shedding refuses to switch on.
- HVAC modes are passed as `str`, like `InterfaceThermostatRuntime.vtherm_hvac_mode`.

`async_before_underlying_hvac_mode`:

- Called just before `climate.set_hvac_mode` is sent to the underlying climate, while this one is still in `current_hvac_mode`.
- `command_cause` is `None` for a regular command and `"underlying_tracking"` when the thermostat copies a change made on the device.
- For an `over_climate` with direct valve control going OFF, this hook is called before the OFF mode is sent, while the climate is still in `current_hvac_mode`. The valve is closed afterwards, by the regulation, with a `ValveCommand` whose `cause` is `REGULATION` and whose `hvac_mode` is `"off"`.
- A plugin that needs to act before OFF must do it in this hook. This hook receives no command object: the target mode is its `hvac_mode` parameter (`"off"` here). Use it, and not the Home Assistant state of the climate, which can still be on. `command.hvac_mode` only exists on the `ValveCommand` of `async_after_valve_command`.

`async_after_valve_command`:

- Called after the opening and closing degrees have been sent to a `valve_regulation` underlying.
- `ValveCommand` carries `climate_entity_id`, `opening_degree_entity_id`, `closing_degree_entity_id` (or `None`), `percent_open` (raw request, 0..100), `opening_degree`, `closing_degree` (or `None`), `hvac_mode` and `cause`.
- `cause` is `REGULATION` for the regulation cycle, `TURN_OFF` when an underlying is turned off directly or when an inhibition stops, `STARTUP` for the initial state check, and `REPAIR` for a valve that drifted from the requested value or that is resynchronized after an inhibition.
- To know the mode of the thermostat in this hook, read `command.hvac_mode` of the `ValveCommand` rather than the Home Assistant state of the climate.
- The valve recalibration and the initial priming of unknown degrees do not call this hook.

`async_on_underlying_power`:

- `UnderlyingPowerCommand` carries `underlying_entity_id`, `underlying_type` (`"switch"`, `"valve"` or `"valve_regulation"`), `climate_entity_id` (the climate driven by a `valve_regulation` underlying, otherwise `None`), `hvac_mode`, `kind`, `requested_on_percent` (clamped to [0, 1]), `applied_on_percent`, `on_time_sec`, `off_time_sec`, `cycle_duration_sec`, `start_offset_sec` (switch only, otherwise `None`), `is_repeat`, `cycle_start_monotonic` (`time.monotonic()` at the start of the master cycle the command belongs to, `None` when no cycle is running) and `monotonic` (`time.monotonic()` when the notification is built).
- `CYCLE_START`: at each cycle start, including the automatic restart (`is_repeat=True`). For a switch, one call per underlying with its `start_offset_sec`.
- `UPDATE`: at each valve update during a running cycle, even if the value does not change.
- `STOP`: when a running cycle is cancelled (OFF, load shedding, shutdown). `applied_on_percent` is then 0 and `cycle_start_monotonic` is `None`, as the cycle is over.
- `cycle_start_monotonic` is also `None` for an `UPDATE` emitted outside a cycle, like `AppliedCommandReceipt.cycle_start_monotonic`.
- The on/off toggles of a switch during the cycle do not trigger a notification. A switch turns on at `cycle_start_monotonic + start_offset_sec` and turns off `on_time_sec` later. The cycle is circular: when `start_offset_sec + on_time_sec` exceeds `cycle_duration_sec`, the off time wraps to the beginning of the cycle. These times are nominal, as the minimal activation and deactivation delays of the core can shift a toggle.
- The hook is called after the cycle start has been actuated, and the core awaits the managers one after the other (up to `UNDERLYING_HOOK_TIMEOUT_SEC` each). A notification can therefore arrive several seconds after the actuation: use `cycle_start_monotonic` and `monotonic`, never the reception time, to synchronize a device.
- It is distinct from `AppliedCommandReceipt`: the receipt is for the algorithm plugin and describes the whole thermostat, this hook is for feature managers and describes each underlying.

---

## Constants and EventType

**Module**: `vtherm_api.const`

### Domain constants

| Constant          | Value                    | Description                          |
| ----------------- | ------------------------ | ------------------------------------ |
| `DOMAIN`          | `"versatile_thermostat"` | VTherm service domain                |
| `VTHERM_API_NAME` | `"vtherm_api"`           | Singleton key in `hass.data[DOMAIN]` |

### EventType enum

```python
from vtherm_api.const import EventType

EventType.SAFETY_EVENT
EventType.POWER_EVENT
EventType.TEMPERATURE_EVENT
EventType.HVAC_MODE_EVENT
EventType.CENTRAL_BOILER_EVENT
EventType.PRESET_EVENT
EventType.WINDOW_AUTO_EVENT
EventType.AUTO_START_STOP_EVENT
EventType.TIMED_PRESET_EVENT
EventType.HEATING_FAILURE_EVENT
```

---

## Logging helpers

**Module**: `vtherm_api.log_collector`

#### `get_vtherm_logger(name: str) -> VThermLogger`

Return a `VThermLogger` whose records are also captured by the in-memory ring buffer used by VTherm.

#### `write_event_log(logger: logging.Logger, vtherm: object, message: str) -> None`

Write a highlighted `NEW EVENT` entry for a thermostat into the logs.
This mirrors the historical `write_event_log` helper of the Versatile Thermostat core so that plugins can emit the same recognizable event lines captured by the in-memory collector.

```python
import logging

from vtherm_api.log_collector import get_vtherm_logger, write_event_log

_LOGGER = get_vtherm_logger(__name__)

write_event_log(_LOGGER, thermostat, "auto_fan set to high")
```


### Inhibition (issue #2087)

`VThermAPI` exposes two inhibition operations and one check:

- `await api.set_inhibition(vtherm_entity_id, stop_underlyings)`;
- `await api.unset_inhibition(vtherm_entity_id)`;
- `api.is_inhibition_started(vtherm_entity_id)`: `True` once the VTherm has
  restored its inhibition state at startup. Before that, both operations raise
  `InhibitionNotStartedError` (exported by `vtherm_api`) and change nothing.

The target is a VTherm climate entity implementing the core operations
`async_set_inhibition(bool)` and `async_unset_inhibition()`, and optionally
the boolean property `is_inhibition_started`. The API directly delegates to
those operations; it does not expose a Home Assistant service,
provider, factory, callback, status, policy, or source configuration.

An inhibition plugin owns its sources, delays, bypass, lifecycle, business
persistence, and `ACTIVE` / `INACTIVE` / `UNKNOWN` status. It calls
`set_inhibition` for `ACTIVE` and `UNKNOWN`, then calls `unset_inhibition` only
after it confirms `INACTIVE`. The core owns the effective `OFF` state, command
gate, entry stop, and exit reconciliation.
