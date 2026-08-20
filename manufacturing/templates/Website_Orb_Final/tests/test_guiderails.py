import json

from Website_ORB.backend.config import SITE_WORLD_PATH


def test_site_world_declares_lookup_only_contract() -> None:
    world = json.loads(SITE_WORLD_PATH.read_text(encoding="utf-8"))
    assert world["runtime_contract"] == "precompiled_skg_lookup_only"
    for record in world["routes"].values():
        assert "cross_page_navigation_requires_explicit_confirmation" in record["permitted_action_boundaries"]
        assert "point_only_after_live_dom_resolution" in record["permitted_action_boundaries"]

