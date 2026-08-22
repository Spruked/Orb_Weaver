from types import SimpleNamespace

from app.orb.navigation_world import (
    build_navigation_world,
    localize_route,
    plan_route_path,
    semantic_tiles_for_route,
)


def page(route, links=(), entities=(), terms=(), pointers=(), depth=0):
    url = "https://example.com" + ("" if route == "/" else route)
    return SimpleNamespace(
        url=url,
        title=route.strip("/") or "Home",
        h1=route.strip("/").title() or "Home",
        status_code=200,
        is_indexable=True,
        crawl_depth=depth,
        word_count=300,
        content_hash=f"hash-{route}",
        internal_link_targets=[
            {
                "url": "https://example.com" + ("" if target == "/" else target),
                "anchor": target.strip("/") or "Home",
                "nofollow": False,
                "discovery_zone": "body",
            }
            for target in links
        ],
        entity_analysis={
            "named_entities": list(entities),
            "people": [],
            "organizations": [],
            "locations": [],
            "product_names": [],
            "schema_org_entities": [],
        },
        semantic_analysis={
            "top_terms": [{"term": term, "count": 2} for term in terms],
            "content_excerpt": f"Information about {', '.join(terms)}",
            "semantic_depth": "moderate",
            "pointer_plot_records": list(pointers),
        },
    )


def pointer(target_id, route, locator, klass="STABLE", may_point=True):
    return {
        "target_id": target_id,
        "page_route": "https://example.com" + ("" if route == "/" else route),
        "target_type": "button",
        "meaning": f"button {target_id}",
        "semantic_locator": locator,
        "content_fingerprint": f"fp-{target_id}",
        "confidence": 0.88 if klass == "STABLE" else 0.62,
        "confidence_class": klass,
        "runtime_policy": {"may_point": may_point},
        "status": "active",
        "pointer_health": "RECOVERED" if klass == "STABLE" else "NEW",
        "allowed_actions": ["point"],
    }


def test_builds_topological_graph_and_shortest_path():
    p_home = pointer("home-price", "/", "a[href='/pricing']")
    p_price = pointer("price-contact", "/pricing", "a[href='/contact']")
    p_contact = pointer("contact-form", "/contact", "form#contact")
    pages = [
        page("/", links=("/pricing", "/contact"), entities=("Orb Weaver",), terms=("robotics",), pointers=(p_home,)),
        page("/pricing", links=("/contact",), entities=("Orb Weaver", "Pro Plan"), terms=("pricing",), pointers=(p_price,), depth=1),
        page("/contact", entities=("Orb Weaver",), terms=("support",), pointers=(p_contact,), depth=1),
    ]
    world = build_navigation_world(pages, domain="example.com")
    assert world["summary"]["scanned_route_nodes"] == 3
    assert world["summary"]["topological_edges"] == 3
    assert plan_route_path(world, "/", "/contact") == ["/", "/contact"]
    assert plan_route_path(world, "/pricing", "/contact") == ["/pricing", "/contact"]


def test_localizes_current_url_and_builds_semantic_tiles():
    pages = [
        page("/", links=("/pricing",), terms=("robotics",)),
        page("/pricing", links=("/contact",), terms=("pricing",)),
        page("/contact", terms=("support",)),
    ]
    world = build_navigation_world(pages, domain="example.com")
    localized = localize_route(world, "https://example.com/pricing?ref=visitor")
    assert localized["route"] == "/pricing"
    assert localized["node_id"].startswith("route_")
    routes = [tile["route"] for tile in semantic_tiles_for_route(world, "/pricing", neighbor_depth=1)]
    assert routes[0] == "/pricing"
    assert set(routes) == {"/", "/pricing", "/contact"}


def test_entity_graph_deduplicates_entities():
    pages = [
        page("/", entities=("Orb Weaver",)),
        page("/pricing", entities=("Orb Weaver", "Pro Plan")),
    ]
    world = build_navigation_world(pages, domain="example.com")
    names = {entity["name"] for entity in world["entity_graph"]["entities"]}
    assert names == {"Orb Weaver", "Pro Plan"}
    assert world["summary"]["unique_entities"] == 2


def test_route_locator_conflict_quarantines_only_conflicting_targets():
    safe = pointer("safe-home", "/", "button#safe")
    first = pointer("a", "/pricing", "button.buy")
    second = pointer("b", "/pricing", "button.buy")
    pages = [
        page("/", links=("/pricing",), pointers=(safe,)),
        page("/pricing", pointers=(first, second)),
    ]
    pointer_map = {
        "schema": "orb_weaver.pointer_plot_map.v1",
        "records": [safe, first, second],
        "quality": {"recovery_required": False},
    }
    world = build_navigation_world(pages, domain="example.com", pointer_map=pointer_map)

    assert world["pointer_registry"]["route_locator_conflict_count"] == 1
    assert world["pointer_registry"]["conflicted_target_ids"] == ["a", "b"]

    assert world["pointer_registry"]["pois"]["a"]["guidance_eligible"] is False
    assert world["pointer_registry"]["pois"]["b"]["guidance_eligible"] is False

    assert world["semantic_tiles"]["/pricing"]["eligible_pointer_ids"] == []
    assert world["guidance_readiness"]["route_status"]["/pricing"]["status"] == "NO_ELIGIBLE_TARGET"

    assert world["semantic_tiles"]["/"]["eligible_pointer_ids"] == ["safe-home"]
    assert world["guidance_readiness"]["route_status"]["/"]["status"] == "ELIGIBLE"

    assert world["guidance_readiness"]["status"] == "DEGRADED"
    assert world["guidance_readiness"]["pointer_execution_available"] is True
    assert world["guidance_readiness"]["pointer_execution_scope"] == "route_target"


def test_pointer_recovery_blocks_map_readiness_not_verified_target_guidance():
    stable = pointer("safe", "/", "button#safe")
    pointer_map = {
        "schema": "orb_weaver.pointer_plot_map.v1",
        "records": [stable],
        "quality": {"recovery_required": True, "status": "POINTER_RECOVERY_REQUIRED"},
    }
    world = build_navigation_world(
        [page("/", pointers=(stable,))],
        domain="example.com",
        pointer_map=pointer_map,
    )

    # Deployment/map health remains blocked.
    assert world["guidance_readiness"]["status"] == "BLOCKED"
    assert world["guidance_readiness"]["map_recovery_required"] is True
    assert "POINTER_RECOVERY_REQUIRED" in world["guidance_readiness"]["blockers"]

    # Exact verified target guidance remains available.
    assert world["guidance_readiness"]["route_status"]["/"]["status"] == "ELIGIBLE"
    assert world["semantic_tiles"]["/"]["eligible_pointer_ids"] == ["safe"]
    assert world["guidance_readiness"]["pointer_execution_available"] is True
    assert world["guidance_readiness"]["target_scoped_authority"] is True


def test_world_state_seed_matches_orbot_contract_shape():
    pages = [page("/", terms=("robotics",))]
    world = build_navigation_world(pages, domain="example.com")
    seed = world["world_state_seed"]
    assert seed["authority"] == "guidance"
    assert seed["etag"] == f"{seed['snapshot_id']}:{seed['version']}"
    assert "pointer_registry" in seed["components"]
    assert world["nats_worldstate_contract"]["binding_status"] == "transport_binding_deferred_to_runtime"


def test_scanned_route_with_no_topological_path_returns_empty_path():
    pages = [
        page("/", links=("/pricing",)),
        page("/pricing"),
        page("/isolated"),
    ]
    world = build_navigation_world(pages, domain="example.com")
    assert localize_route(world, "/isolated")["route"] == "/isolated"
    assert plan_route_path(world, "/", "/isolated") == []
    assert plan_route_path(world, "/isolated", "/pricing") == []


def test_discovered_frontier_node_never_localizes_or_becomes_plannable():
    world = build_navigation_world(
        [page("/", links=("/ghost",), terms=("home",))],
        domain="example.com",
    )
    frontier = world["route_graph"]["frontier_nodes"]
    assert len(frontier) == 1
    assert frontier[0]["route"] == "/ghost"
    assert frontier[0]["scanned"] is False
    assert frontier[0]["status"] == "discovered_not_scanned"
    assert localize_route(world, "/ghost") is None
    assert plan_route_path(world, "/", "/ghost") == []


def test_route_with_zero_valid_pointer_targets_does_not_inherit_home_target():
    home = pointer("home-safe", "/", "button#home")
    pricing_uncertain = pointer(
        "pricing-uncertain",
        "/pricing",
        "button#pricing",
        klass="UNCERTAIN",
        may_point=False,
    )
    world = build_navigation_world(
        [
            page("/", links=("/pricing",), pointers=(home,)),
            page("/pricing", pointers=(pricing_uncertain,)),
        ],
        domain="example.com",
    )
    assert world["semantic_tiles"]["/"]["eligible_pointer_ids"] == ["home-safe"]
    assert world["semantic_tiles"]["/pricing"]["eligible_pointer_ids"] == []
    assert world["pointer_registry"]["by_route"]["/pricing"] == ["pricing-uncertain"]
    assert "home-safe" not in world["pointer_registry"]["by_route"]["/pricing"]
