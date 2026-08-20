from Website_ORB.backend.config import POINTER_MAP_PATH, RUNTIME_LANGUAGE_PATH, SITE_WORLD_PATH, TOOL_CACHE_PATH
from Website_ORB.backend.pointer.pointer_index import route_pointer_targets
from Website_ORB.backend.runtime.site_world import SiteWorld


def test_pointer_targets_are_indexed_by_route() -> None:
    world = SiteWorld.load(SITE_WORLD_PATH, POINTER_MAP_PATH, RUNTIME_LANGUAGE_PATH, TOOL_CACHE_PATH)
    targets = route_pointer_targets(world, "/", "preflight", limit=5)
    assert targets
    assert all("target_id" in target for target in targets)

