"""UI plugins of the Versatile Thermostat dashboard.

A UI plugin is an integration that adds screens to the dashboard. It declares
itself in Python with ``VThermAPI.register_ui_plugin`` and ships a JavaScript
module that the dashboard loads.

The registry of ``VThermAPI`` is passive: it checks the structure of a
declaration and the uniqueness of its identifier, and keeps the declarations in
registration order. It does not sort the plugins and does not interpret their
dependencies, their URL or their version constraint; the dashboard does that
each time it builds the list of plugins to load.

This module does not import Home Assistant, so that a consumer can build a
:class:`UiPlugin` without it, for example in its tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FIELD_PLUGIN_ID = "plugin_id"
FIELD_JS_URL = "js_url"
FIELD_DASHBOARD_VERSION = "dashboard_version"
FIELD_REQUIRES = "requires"
FIELD_LOAD_AFTER = "load_after"
FIELD_LOAD_BEFORE = "load_before"

ERROR_REQUIRED_FIELD = "The UI plugin field '{name}' is required and must be a non-empty string"
ERROR_NOT_A_LIST = "The UI plugin field '{name}' must be a list of plugin identifiers"
ERROR_INVALID_ITEM = "The UI plugin field '{name}' must only contain non-empty strings, got {value!r}"
ERROR_ALREADY_REGISTERED = "A UI plugin with the identifier '{plugin_id}' is already registered"


@dataclass(frozen=True, slots=True)
class UiPlugin:
    """The declaration of a UI plugin of the dashboard.

    The constructor does not validate its arguments: ``register_ui_plugin``
    does, and builds the instances that ``get_ui_plugins`` returns.

    Attributes:
        id: Unique identifier of the plugin. ``core`` and ``core_*`` are
            reserved for the native plugins of the dashboard.
        js_url: URL of the JavaScript module of the plugin.
        dashboard_version: Versions of the dashboard that the plugin
            supports, for example ``">=1.0,<2.0"``.
        requires: Plugins that must be present for this one to load.
        load_after: Plugins to load before this one when they are present.
        load_before: Plugins to load after this one when they are present.
    """

    id: str
    js_url: str
    dashboard_version: str
    requires: tuple[str, ...] = ()
    load_after: tuple[str, ...] = ()
    load_before: tuple[str, ...] = ()


def _required_string(name: str, value: Any) -> str:
    """Return ``value`` if it is a string that is not blank, or raise ``ValueError``."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(ERROR_REQUIRED_FIELD.format(name=name))
    return value


def _identifiers(name: str, value: Any) -> tuple[str, ...]:
    """Return the stripped plugin identifiers of an optional list, or raise ``ValueError``.

    Only ``None``, a ``list`` or a ``tuple`` is accepted: a string is iterable
    and would be split into characters, and a set has no order.
    """
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError(ERROR_NOT_A_LIST.format(name=name))
    identifiers = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(ERROR_INVALID_ITEM.format(name=name, value=item))
        identifiers.append(item.strip())
    return tuple(identifiers)


def build_ui_plugin(  # pylint: disable=too-many-arguments  # the signature of register_ui_plugin, fixed by the dashboard
    plugin_id: Any,
    js_url: Any,
    dashboard_version: Any,
    *,
    requires: Any = None,
    load_after: Any = None,
    load_before: Any = None,
) -> UiPlugin:
    """Validate the arguments of ``register_ui_plugin`` and build the declaration.

    The identifier and the identifiers of the dependencies are stripped of
    their surrounding spaces. ``js_url`` and ``dashboard_version`` are kept as
    given: the dashboard interprets them and shows a faulty value as is.

    Raises:
        ValueError: A field is missing or has the wrong type. The message
            names the field.
    """
    return UiPlugin(
        id=_required_string(FIELD_PLUGIN_ID, plugin_id).strip(),
        js_url=_required_string(FIELD_JS_URL, js_url),
        dashboard_version=_required_string(FIELD_DASHBOARD_VERSION, dashboard_version),
        requires=_identifiers(FIELD_REQUIRES, requires),
        load_after=_identifiers(FIELD_LOAD_AFTER, load_after),
        load_before=_identifiers(FIELD_LOAD_BEFORE, load_before),
    )
