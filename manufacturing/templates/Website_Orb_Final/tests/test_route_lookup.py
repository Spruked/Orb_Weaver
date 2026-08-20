from Website_ORB.backend.config import POINTER_MAP_PATH, RUNTIME_LANGUAGE_PATH, SITE_WORLD_PATH, TOOL_CACHE_PATH
from Website_ORB.backend.runtime.route_lookup import lookup_route
from Website_ORB.backend.runtime.site_world import SiteWorld


def test_route_lookup_home() -> None:
    world = SiteWorld.load(SITE_WORLD_PATH, POINTER_MAP_PATH, RUNTIME_LANGUAGE_PATH, TOOL_CACHE_PATH)
    matched, record = lookup_route(world, "/")
    assert matched == "/"
    assert record["target_tiering"]["full_route_scoped_targets"]


def test_route_lookup_falls_back_to_home() -> None:
    world = SiteWorld.load(SITE_WORLD_PATH, POINTER_MAP_PATH, RUNTIME_LANGUAGE_PATH, TOOL_CACHE_PATH)
    matched, record = lookup_route(world, "/not-a-real-route")
    assert matched == "/"
    assert record["summary"]

