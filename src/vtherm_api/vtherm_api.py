""" The API of Versatile Thermostat"""
from datetime import datetime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN

from .const import DOMAIN, VTHERM_API_NAME, NowClass
from .log_collector import get_vtherm_logger
from .plugin_climate import PluginClimate
from .ui_plugin import ERROR_ALREADY_REGISTERED, UiPlugin, build_ui_plugin
from .interfaces import (
    InterfaceFeatureManager,
    InterfaceFeatureManagerFactory,
    InterfacePropAlgorithmFactory,
    InterfaceThermostat,
)

_LOGGER = get_vtherm_logger(__name__)


class VThermAPI:  # pylint: disable=too-many-public-methods  # the public facade of the package, one method per operation
    """The VThermAPI
    This class is a singleton that provides access to the VTherm API instance through HA hass mecanism.
    It also provides a reference to the HA instance for use in the API implementation.
    """

    _hass: HomeAssistant = None

    def __init__(self) -> None:
        """Initialize the VThermAPI instance."""
        self._now: datetime = None
        self._prop_algorithm_registry: dict[str,
                                            InterfacePropAlgorithmFactory] = {}
        self._feature_manager_registry: dict[str,
                                             InterfaceFeatureManagerFactory] = {}
        # The order of insertion of the dict is the order of registration.
        self._ui_plugin_registry: dict[str, UiPlugin] = {}

    @classmethod
    def get_vtherm_api(cls, hass=None):
        """Get the eventual VTherm API class instance or
        instantiate it if it doesn't exists"""
        if hass is not None:
            cls._hass = hass

        if cls._hass is None:
            return None

        domain = cls._hass.data.get(DOMAIN)
        if not domain:
            cls._hass.data.setdefault(DOMAIN, {})

        ret = cls._hass.data.get(
            DOMAIN).get(VTHERM_API_NAME)
        if ret is None:
            ret = cls()
            cls._hass.data[DOMAIN][VTHERM_API_NAME] = ret
        return ret

    @classmethod
    def reset_vtherm_api(cls):
        """Reset the VTherm API instance and related data."""
        if cls._hass is None:
            return

        api = cls._hass.data.get(DOMAIN, {}).get(VTHERM_API_NAME)
        if api is not None:
            api._prop_algorithm_registry.clear()  # pylint: disable=protected-access
            api._feature_manager_registry.clear()  # pylint: disable=protected-access
            api._ui_plugin_registry.clear()  # pylint: disable=protected-access

        # Remove the API instance from hass.data
        if DOMAIN in cls._hass.data:
            cls._hass.data[DOMAIN].pop(
                VTHERM_API_NAME, None)
        cls._hass = None

    @property
    def hass(self):
        """Get the HomeAssistant object"""
        return type(self)._hass

    @property
    def name(self) -> str:
        """Get the name of the API"""
        return "VThermAPI"

    # For testing purpose
    def _set_now(self, now: datetime):
        """Set the now timestamp. This is only for tests purpose"""
        self._now = now

    @property
    def now(self) -> datetime:
        """Get now. The local datetime or the overloaded _set_now date"""
        return self._now if self._now is not None else NowClass.get_now(self._hass)

    def register_prop_algorithm(self, factory: InterfacePropAlgorithmFactory) -> None:
        """Register or replace a proportional algorithm factory."""
        name = factory.name.strip()
        if not name:
            raise ValueError(
                "The proportional algorithm factory name cannot be empty")

        self._prop_algorithm_registry[name] = factory

    def unregister_prop_algorithm(self, name: str) -> None:
        """Remove a proportional algorithm factory from the registry."""
        self._prop_algorithm_registry.pop(name, None)

    def get_prop_algorithm(self, name: str) -> InterfacePropAlgorithmFactory | None:
        """Return the registered proportional algorithm factory for a name."""
        return self._prop_algorithm_registry.get(name)

    def list_prop_algorithms(self) -> list[str]:
        """Return the registered proportional algorithm names in sorted order."""
        return sorted(self._prop_algorithm_registry)

    def register_feature_manager(self, factory: InterfaceFeatureManagerFactory) -> None:
        """Register or replace a feature manager factory."""
        name = factory.name.strip()
        if not name:
            raise ValueError(
                "The feature manager factory name cannot be empty")

        self._feature_manager_registry[name] = factory

    def unregister_feature_manager(self, name: str) -> None:
        """Remove a feature manager factory from the registry."""
        self._feature_manager_registry.pop(name, None)

    def get_feature_manager(self, name: str) -> InterfaceFeatureManagerFactory | None:
        """Return the registered feature manager factory for a name."""
        return self._feature_manager_registry.get(name)

    def list_feature_managers(self) -> list[str]:
        """Return the registered feature manager names in sorted order."""
        return sorted(self._feature_manager_registry)

    def get_feature_manager_factories(self) -> list[InterfaceFeatureManagerFactory]:
        """Return the registered feature manager factories.

        The core iterates over these factories when building a thermostat to
        instantiate one feature manager per eligible thermostat.
        """
        return [
            self._feature_manager_registry[name]
            for name in sorted(self._feature_manager_registry)
        ]

    def register_ui_plugin(  # pylint: disable=too-many-arguments  # the signature is fixed by the dashboard
        self,
        plugin_id: str,
        js_url: str,
        dashboard_version: str,
        *,
        requires: list[str] | tuple[str, ...] | None = None,
        load_after: list[str] | tuple[str, ...] | None = None,
        load_before: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        """Declare a UI plugin of the Versatile Thermostat dashboard.

        The registry is passive: it checks the structure of the declaration
        and the uniqueness of its identifier. It does not check the URL, the
        version constraint, the reserved identifiers ``core`` and ``core_*``
        nor the dependencies: the dashboard does, when it builds the list of
        plugins to load. Call it from the event loop, for example in
        ``async_setup_entry``.

        Registering again a declaration equal to the registered one does
        nothing, so ``async_setup_entry`` can run again (setup retry, several
        config entries) without unregistering first. The plugin keeps its
        place in the registration order.

        Raises:
            ValueError: A field is missing or has the wrong type, or a
                different plugin with the same identifier is already
                registered. Nothing is registered and the existing plugin is
                kept.
        """
        plugin = build_ui_plugin(
            plugin_id,
            js_url,
            dashboard_version,
            requires=requires,
            load_after=load_after,
            load_before=load_before,
        )
        registered = self._ui_plugin_registry.get(plugin.id)
        if registered == plugin:
            # Home Assistant can run async_setup_entry again without
            # async_unload_entry (setup retry, one call per config entry).
            _LOGGER.debug("%s - UI plugin %s already registered with the same declaration", self, plugin.id)
            return
        if registered is not None:
            raise ValueError(ERROR_ALREADY_REGISTERED.format(plugin_id=plugin.id))

        self._ui_plugin_registry[plugin.id] = plugin
        _LOGGER.debug("%s - UI plugin %s registered with %s", self, plugin.id, plugin.js_url)

    def unregister_ui_plugin(self, plugin_id: str) -> None:
        """Remove a UI plugin. An unknown identifier is ignored."""
        if not isinstance(plugin_id, str):
            return
        if self._ui_plugin_registry.pop(plugin_id.strip(), None) is not None:
            _LOGGER.debug("%s - UI plugin %s unregistered", self, plugin_id.strip())

    def get_ui_plugins(self) -> list[UiPlugin]:
        """Return the registered UI plugins, in registration order.

        The order is not a load order: a plugin that requires another one can
        come first. The returned list is a new list on each call.
        """
        return list(self._ui_plugin_registry.values())

    async def set_inhibition(
        self,
        vtherm_entity_id: str,
        stop_underlyings: bool,
    ) -> None:
        """Ask one VTherm core to enter inhibition.

        ``stop_underlyings`` only authorizes the unique entry stop. The core
        owns all other inhibition state, including command gating and the
        effective HVAC calculation.

        Raises ``InhibitionNotStartedError`` while the VTherm has not restored
        its inhibition state at startup (see ``is_inhibition_started``).
        """
        if not isinstance(stop_underlyings, bool):
            raise TypeError("stop_underlyings must be a bool")

        thermostat = self._get_inhibition_thermostat(vtherm_entity_id)
        await thermostat.async_set_inhibition(stop_underlyings)

    async def unset_inhibition(self, vtherm_entity_id: str) -> None:
        """Ask one VTherm core to reconcile and leave inhibition.

        Plugins must call this operation only after they have confirmed their
        own inactive state. The core keeps the command gate closed until its
        exit reconciliation finishes.

        Raises ``InhibitionNotStartedError`` while the VTherm has not restored
        its inhibition state at startup (see ``is_inhibition_started``).
        """
        thermostat = self._get_inhibition_thermostat(vtherm_entity_id)
        await thermostat.async_unset_inhibition()

    def is_inhibition_started(self, vtherm_entity_id: str) -> bool:
        """Return True once the targeted VTherm accepts the inhibition operations.

        A VTherm restores its inhibition state at the very beginning of its
        startup; before that, ``set_inhibition`` and ``unset_inhibition`` raise
        ``InhibitionNotStartedError``. A plugin checks this before calling and
        checks again later (for example at the VTherm's next state change).
        A core that does not expose this state accepts the operations at any
        time and is reported started. Raises like ``set_inhibition`` when the
        target is missing or does not support inhibition.
        """
        thermostat = self._get_inhibition_thermostat(vtherm_entity_id)
        return getattr(thermostat, "is_inhibition_started", True) is not False

    def _get_inhibition_thermostat(self, vtherm_entity_id: str):
        """Return the core implementing the minimal inhibition operations."""
        if not isinstance(vtherm_entity_id, str) or not vtherm_entity_id.strip():
            raise ValueError("vtherm_entity_id must be a non-empty entity ID")

        component: EntityComponent[ClimateEntity] | None = self._hass.data.get(
            CLIMATE_DOMAIN)
        if component is None:
            raise LookupError(
                f"No VTherm entity found for inhibition: {vtherm_entity_id}")

        for entity in component.entities:
            if getattr(entity, "entity_id", None) != vtherm_entity_id:
                continue
            if not all(
                callable(getattr(entity, method, None))
                for method in ("async_set_inhibition", "async_unset_inhibition")
            ):
                raise TypeError(
                    f"VTherm entity '{vtherm_entity_id}' does not support inhibition")
            return entity

        raise LookupError(
            f"No VTherm entity found for inhibition: {vtherm_entity_id}")

    def link_to_vtherm(self, vtherm, plugin_vtherm_entity_id: str):
        """Link the VTherm API to a specific VTherm entity."""
        # Implementation for linking to a VTherm entity
        # Find a vtherm instance of type PluginClimate in hass
        component: EntityComponent[ClimateEntity] = self._hass.data.get(
            CLIMATE_DOMAIN, None)
        if component:
            for entity in list(component.entities):
                try:
                    if entity.device_info and entity.device_info.get("model", None) == DOMAIN:
                        if plugin_vtherm_entity_id == entity.entity_id and isinstance(entity, InterfaceThermostat):
                            plugin_climate: PluginClimate = entity
                            _LOGGER.info(
                                "%s - We have found the linked PluginVTherm", self)
                            plugin_climate.link_to_vtherm(vtherm)
                            return
                except Exception as e:  # pylint: disable=broad-except
                    _LOGGER.error(
                        "Error searching/initializing entity %s: %s", entity.entity_id, e)

    def register_manager(self, manager: InterfaceFeatureManager):
        """Register a feature manager to the API."""
        # Implementation for registering a feature manager
        # Find all vtherm instance of type PluginClimate in hass and register the manager to them
        component: EntityComponent[ClimateEntity] = self._hass.data.get(
            CLIMATE_DOMAIN, None)
        if component:
            for entity in list(component.entities):
                try:
                    if entity.device_info and entity.device_info.get("model", None) == DOMAIN:
                        if isinstance(entity, InterfaceThermostat):
                            plugin_climate: PluginClimate = entity
                            plugin_climate.register_manager(manager)
                except Exception as e:  # pylint: disable=broad-except
                    _LOGGER.error(
                        "Error searching/initializing entity %s: %s", entity.entity_id, e)
