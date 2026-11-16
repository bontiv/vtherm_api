"""Tests for the registry of the UI plugins of the dashboard exposed by VThermAPI."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.vtherm_api.const import DOMAIN
from src.vtherm_api.ui_plugin import UiPlugin, build_ui_plugin
from src.vtherm_api.vtherm_api import VThermAPI


@pytest.fixture(name="hass")
def hass_fixture():
    """Return a minimal Home Assistant-like object, as the tests of the dashboard do."""
    VThermAPI.reset_vtherm_api()
    hass = SimpleNamespace(data={DOMAIN: {}}, config=SimpleNamespace(time_zone="UTC"))
    yield hass
    VThermAPI.reset_vtherm_api()


@pytest.fixture(name="api")
def api_fixture(hass) -> VThermAPI:
    """Return the VThermAPI of the minimal Home Assistant-like object."""
    return VThermAPI.get_vtherm_api(hass)


class FakeFactory:
    """A factory of feature manager or of proportional algorithm, reduced to its name."""

    def __init__(self, name: str) -> None:
        self.name = name


# --- UiPlugin ---------------------------------------------------------------------------------------------------------------------------


def test_ui_plugin_is_built_by_keyword_like_the_dashboard_tests() -> None:
    """The construction copied from the tests of the dashboard keeps the six values as given."""
    plugin = UiPlugin(
        id="a",
        js_url="/a/ui.js",
        dashboard_version=">=1.0",
        requires=tuple(["core"]),
        load_after=tuple(()),
        load_before=tuple(()),
    )

    assert (plugin.id, plugin.js_url, plugin.dashboard_version) == ("a", "/a/ui.js", ">=1.0")
    assert (plugin.requires, plugin.load_after, plugin.load_before) == (("core",), (), ())


def test_ui_plugin_dependencies_default_to_empty_tuples() -> None:
    plugin = UiPlugin(id="a", js_url="/a/ui.js", dashboard_version=">=1.0")

    assert (plugin.requires, plugin.load_after, plugin.load_before) == ((), (), ())


def test_ui_plugin_compares_by_value() -> None:
    assert UiPlugin(id="a", js_url="/a.js", dashboard_version="==1.0") == UiPlugin(id="a", js_url="/a.js", dashboard_version="==1.0")
    assert UiPlugin(id="a", js_url="/a.js", dashboard_version="==1.0") != UiPlugin(id="a", js_url="/b.js", dashboard_version="==1.0")


def test_ui_plugin_is_immutable() -> None:
    plugin = UiPlugin(id="a", js_url="/a.js", dashboard_version="==1.0")

    with pytest.raises(FrozenInstanceError):
        plugin.js_url = "/b.js"  # type: ignore[misc]

    assert plugin.js_url == "/a.js"


# --- Validation of a declaration ----------------------------------------------------------------------------------------------------------


def test_build_strips_the_identifiers_and_keeps_the_url_and_the_constraint() -> None:
    plugin = build_ui_plugin("  my_plugin  ", " /my.js ", " >=1.0 ", requires=[" core "], load_after=("core_tpi",))

    assert plugin == UiPlugin(id="my_plugin", js_url=" /my.js ", dashboard_version=" >=1.0 ", requires=("core",), load_after=("core_tpi",))


@pytest.mark.parametrize(
    ("arguments", "field"),
    [
        (("  ", "/a.js", ">=1.0"), "plugin_id"),
        ((None, "/a.js", ">=1.0"), "plugin_id"),
        (("a", None, ">=1.0"), "js_url"),
        (("a", "", ">=1.0"), "js_url"),
        (("a", "/a.js", 1), "dashboard_version"),
        (("a", "/a.js", "   "), "dashboard_version"),
    ],
)
def test_build_refuses_a_missing_required_field(arguments, field: str) -> None:
    with pytest.raises(ValueError) as err:
        build_ui_plugin(*arguments)

    assert str(err.value) == f"The UI plugin field '{field}' is required and must be a non-empty string"


@pytest.mark.parametrize("field", ["requires", "load_after", "load_before"])
@pytest.mark.parametrize("value", ["core", {"core"}, {"core": 1}, 3])
def test_build_refuses_dependencies_that_are_not_a_list(field: str, value) -> None:
    with pytest.raises(ValueError) as err:
        build_ui_plugin("a", "/a.js", ">=1.0", **{field: value})

    assert str(err.value) == f"The UI plugin field '{field}' must be a list of plugin identifiers"


@pytest.mark.parametrize("field", ["requires", "load_after", "load_before"])
@pytest.mark.parametrize(("item", "shown"), [("", "''"), ("  ", "'  '"), (3, "3"), (None, "None")])
def test_build_refuses_a_dependency_that_is_not_a_non_empty_string(field: str, item, shown: str) -> None:
    with pytest.raises(ValueError) as err:
        build_ui_plugin("a", "/a.js", ">=1.0", **{field: ["core", item]})

    assert str(err.value) == f"The UI plugin field '{field}' must only contain non-empty strings, got {shown}"


def test_build_accepts_a_tuple_and_none() -> None:
    plugin = build_ui_plugin("a", "/a.js", ">=1.0", requires=None, load_before=("other",))

    assert (plugin.requires, plugin.load_before) == ((), ("other",))


# --- Registration -------------------------------------------------------------------------------------------------------------------------


def test_register_a_valid_plugin(api: VThermAPI) -> None:
    api.register_ui_plugin("my_plugin", "/my_plugin_static/my-plugin.js", ">=1.0,<2.0", requires=["core"], load_after=["core_tpi"])

    assert api.get_ui_plugins() == [
        UiPlugin(
            id="my_plugin",
            js_url="/my_plugin_static/my-plugin.js",
            dashboard_version=">=1.0,<2.0",
            requires=("core",),
            load_after=("core_tpi",),
            load_before=(),
        )
    ]


def test_register_strips_the_identifier(api: VThermAPI) -> None:
    api.register_ui_plugin("  my_plugin  ", "/my.js", ">=1.0")

    assert [plugin.id for plugin in api.get_ui_plugins()] == ["my_plugin"]


def test_register_without_dependencies(api: VThermAPI) -> None:
    api.register_ui_plugin("a", "/a.js", ">=1.0")

    (plugin,) = api.get_ui_plugins()
    assert (plugin.requires, plugin.load_after, plugin.load_before) == ((), (), ())


@pytest.mark.parametrize(
    ("arguments", "keywords"),
    [
        (("  ", "/a.js", ">=1.0"), {}),
        (("a", None, ">=1.0"), {}),
        (("a", "/a.js", 1), {}),
        (("a", "/a.js", ">=1.0"), {"requires": "core"}),
        (("a", "/a.js", ">=1.0"), {"load_after": ["core", ""]}),
        (("a", "/a.js", ">=1.0"), {"load_before": [None]}),
    ],
)
def test_an_invalid_registration_registers_nothing(api: VThermAPI, arguments, keywords) -> None:
    with pytest.raises(ValueError):
        api.register_ui_plugin(*arguments, **keywords)

    assert api.get_ui_plugins() == []


def test_a_duplicate_identifier_is_refused_and_the_first_plugin_is_kept(api: VThermAPI) -> None:
    api.register_ui_plugin("a", "/first.js", ">=1.0")

    with pytest.raises(ValueError) as err:
        api.register_ui_plugin("a", "/second.js", ">=1.0")

    assert str(err.value) == "A UI plugin with the identifier 'a' is already registered"
    assert [plugin.js_url for plugin in api.get_ui_plugins()] == ["/first.js"]


def test_a_duplicate_is_detected_after_stripping(api: VThermAPI) -> None:
    api.register_ui_plugin("a", "/a.js", ">=1.0")

    with pytest.raises(ValueError, match="identifier 'a' is already registered"):
        api.register_ui_plugin(" a ", "/other.js", ">=1.0")


@pytest.mark.parametrize(
    "keywords",
    [
        {"dashboard_version": ">=2.0"},
        {"requires": ["core"]},
        {"load_after": ["core"]},
        {"load_before": ["core"]},
    ],
)
def test_a_duplicate_with_any_different_field_is_refused(api: VThermAPI, keywords) -> None:
    api.register_ui_plugin("a", "/a.js", ">=1.0")
    arguments = {"plugin_id": "a", "js_url": "/a.js", "dashboard_version": ">=1.0", **keywords}

    with pytest.raises(ValueError, match="identifier 'a' is already registered"):
        api.register_ui_plugin(**arguments)

    assert api.get_ui_plugins() == [UiPlugin(id="a", js_url="/a.js", dashboard_version=">=1.0")]


def test_the_same_declaration_registered_again_is_accepted_and_keeps_its_place(api: VThermAPI) -> None:
    """Home Assistant can run async_setup_entry again without async_unload_entry: setup retry, several config entries."""
    api.register_ui_plugin("a", "/a.js", ">=1.0", requires=["core"])
    api.register_ui_plugin("b", "/b.js", ">=1.0")

    api.register_ui_plugin(" a ", "/a.js", ">=1.0", requires=(" core ",))

    assert [plugin.id for plugin in api.get_ui_plugins()] == ["a", "b"]


@pytest.mark.asyncio
async def test_the_documented_example_survives_a_setup_retry(hass) -> None:
    namespace: dict = {}
    exec(compile(_documented_example(), str(API_REFERENCE), "exec"), namespace)  # pylint: disable=exec-used

    assert await namespace["async_setup_entry"](hass, None)
    assert await namespace["async_setup_entry"](hass, None)

    assert [plugin.id for plugin in VThermAPI.get_vtherm_api(hass).get_ui_plugins()] == ["my_plugin"]


def test_the_registry_is_passive(api: VThermAPI) -> None:
    """Reserved identifiers, external URL, unsupported constraint and absent dependency are the business of the dashboard."""
    api.register_ui_plugin("core_custom", "/core_custom.js", ">=1.0")
    api.register_ui_plugin("external", "https://autre-hote/plugin.js", "^1.0")
    api.register_ui_plugin("orphan", "/orphan.js", ">=1.0", requires=["absent"])
    api.register_ui_plugin("loop_a", "/loop_a.js", ">=1.0", requires=["loop_b"])
    api.register_ui_plugin("loop_b", "/loop_b.js", ">=1.0", requires=["loop_a"])

    plugins = {plugin.id: plugin for plugin in api.get_ui_plugins()}
    assert set(plugins) == {"core_custom", "external", "orphan", "loop_a", "loop_b"}
    assert (plugins["external"].js_url, plugins["external"].dashboard_version) == ("https://autre-hote/plugin.js", "^1.0")


# --- Removal ----------------------------------------------------------------------------------------------------------------------------


def test_unregister_an_existing_plugin(api: VThermAPI) -> None:
    api.register_ui_plugin("a", "/a.js", ">=1.0")
    api.register_ui_plugin("b", "/b.js", ">=1.0")

    api.unregister_ui_plugin(" a ")

    assert [plugin.id for plugin in api.get_ui_plugins()] == ["b"]


@pytest.mark.parametrize("plugin_id", ["unknown", "", None, 3])
def test_unregister_an_unknown_plugin_changes_nothing(api: VThermAPI, plugin_id) -> None:
    api.register_ui_plugin("a", "/a.js", ">=1.0")

    api.unregister_ui_plugin(plugin_id)

    assert [plugin.id for plugin in api.get_ui_plugins()] == ["a"]


def test_register_again_after_a_reload(api: VThermAPI) -> None:
    """The dashboard withdraws and registers its native plugins again at each reload, with a new URL."""
    api.register_ui_plugin("core", "/vtherm_dashboard/plugins/core.js?v=0.1.0", "==0.1.0")

    api.unregister_ui_plugin("core")
    api.register_ui_plugin("core", "/vtherm_dashboard/plugins/core.js?v=0.2.0", "==0.2.0")

    assert [plugin.js_url for plugin in api.get_ui_plugins()] == ["/vtherm_dashboard/plugins/core.js?v=0.2.0"]


# --- Reading ----------------------------------------------------------------------------------------------------------------------------


def test_no_plugin(api: VThermAPI) -> None:
    assert api.get_ui_plugins() == []


def test_the_registry_does_not_sort(api: VThermAPI) -> None:
    api.register_ui_plugin("b", "/b.js", ">=1.0", requires=["a"])
    api.register_ui_plugin("a", "/a.js", ">=1.0")

    assert [plugin.id for plugin in api.get_ui_plugins()] == ["b", "a"]


def test_a_plugin_registered_again_goes_last(api: VThermAPI) -> None:
    for plugin_id in ("a", "b", "c"):
        api.register_ui_plugin(plugin_id, f"/{plugin_id}.js", ">=1.0")

    api.unregister_ui_plugin("b")
    api.register_ui_plugin("b", "/b.js", ">=1.0")

    assert [plugin.id for plugin in api.get_ui_plugins()] == ["a", "c", "b"]


def test_the_returned_list_is_a_copy(api: VThermAPI) -> None:
    api.register_ui_plugin("a", "/a.js", ">=1.0")

    api.get_ui_plugins().clear()

    assert [plugin.id for plugin in api.get_ui_plugins()] == ["a"]


# --- Separation of the registries ---------------------------------------------------------------------------------------------------------


def test_other_registries_are_not_listed(api: VThermAPI) -> None:
    api.register_feature_manager(FakeFactory("manager"))
    api.register_prop_algorithm(FakeFactory("algorithm"))

    assert api.get_ui_plugins() == []


def test_the_same_name_in_two_registries(api: VThermAPI) -> None:
    api.register_feature_manager(FakeFactory("x"))
    api.register_ui_plugin("x", "/x.js", ">=1.0")

    api.unregister_ui_plugin("x")

    assert api.get_ui_plugins() == []
    assert api.list_feature_managers() == ["x"]


# --- Reset ------------------------------------------------------------------------------------------------------------------------------


def test_reset_gives_an_empty_registry(hass, api: VThermAPI) -> None:
    api.register_ui_plugin("a", "/a.js", ">=1.0")

    VThermAPI.reset_vtherm_api()

    assert VThermAPI.get_vtherm_api(hass).get_ui_plugins() == []


def test_reset_empties_an_instance_kept_by_a_consumer(api: VThermAPI) -> None:
    api.register_ui_plugin("a", "/a.js", ">=1.0")

    VThermAPI.reset_vtherm_api()

    assert api.get_ui_plugins() == []


# --- Documentation ----------------------------------------------------------------------------------------------------------------------

API_REFERENCE = Path(__file__).resolve().parent.parent / "documentation" / "en" / "api-reference.md"


def _documented_example() -> str:
    """Return the code of the example of the UI plugin registry in the API reference, importing the package under test."""
    text = API_REFERENCE.read_text(encoding="utf-8")
    block = text.split("<!-- example: ui-plugin-registry -->", 1)[1].split("```python", 1)[1].split("```", 1)[0]
    return block.replace("from vtherm_api import", "from src.vtherm_api import")


@pytest.mark.asyncio
async def test_the_documented_example_runs(hass) -> None:
    namespace: dict = {}
    exec(compile(_documented_example(), str(API_REFERENCE), "exec"), namespace)  # pylint: disable=exec-used

    assert await namespace["async_setup_entry"](hass, None)
    (plugin,) = VThermAPI.get_vtherm_api(hass).get_ui_plugins()
    assert (plugin.id, plugin.requires, plugin.load_after) == ("my_plugin", ("core",), ("core_tpi",))

    assert await namespace["async_unload_entry"](hass, None)
    assert VThermAPI.get_vtherm_api(hass).get_ui_plugins() == []


@pytest.mark.parametrize(
    "message",
    [
        "The UI plugin field '<name>' is required and must be a non-empty string",
        "The UI plugin field '<name>' must be a list of plugin identifiers",
        "The UI plugin field '<name>' must only contain non-empty strings, got <value>",
        "A UI plugin with the identifier '<id>' is already registered",
    ],
)
def test_the_api_reference_lists_every_error_message(message: str) -> None:
    assert f"`{message}`" in API_REFERENCE.read_text(encoding="utf-8")
