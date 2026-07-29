from app.orb.pointer_map_optimizer import optimize_pointer_map


def _record(target_id: str, route: str = "https://example.test/"):
    return {
        "target_id": target_id,
        "page_route": route,
        "target_type": "button",
        "meaning": f"button: {target_id}",
        "intent_aliases": [target_id],
        "direct_aliases": [target_id, f"open {target_id}"],
        "topic_aliases": ["information about website", f"where is {target_id}"],
        "content_fingerprint": target_id,
        "semantic_locator": f"#{target_id}",
        "confidence": 0.82,
        "confidence_class": "STABLE",
        "runtime_policy": {"may_point": True},
        "confidence_evidence": {"locator_method": "element_id"},
        "allowed_actions": ["point"],
        "status": "active",
    }


def _observation(render_id: str, viewport: str, target_id: str, *, x: float, text_fingerprint: str = "same"):
    sizes = {
        "desktop": {"width": 1440, "height": 900},
        "mobile": {"width": 390, "height": 844},
    }
    return {
        "render_id": render_id,
        "url": "https://example.test/",
        "route": "/",
        "viewport": viewport,
        "viewport_size": sizes[viewport],
        "candidates": [
            {
                "identity_key": f"/|button|button|{target_id}|",
                "route": "/",
                "accessible_name": target_id,
                "text": target_id,
                "text_fingerprint": text_fingerprint,
                "locator": f"#{target_id}",
                "durable": True,
                "rect": {"x": x, "y": 100, "width": 120, "height": 40},
            }
        ],
    }


def test_repeated_generic_topics_are_moved_to_page_level_table():
    pointer_map = {"schema": "orb_weaver.pointer_plot_map.v1", "records": [_record(f"target-{index}") for index in range(6)]}

    optimized = optimize_pointer_map(pointer_map)

    assert optimized["shared_topics_by_page"]["https://example.test/"] == ["information about website"]
    assert all("information about website" not in record["topic_aliases"] for record in optimized["records"])
    assert all(record["direct_aliases"] for record in optimized["records"])
    assert optimized["optimization"]["aliases_moved_from_records"] == 6


def test_geometry_is_evidence_only_and_never_action_authority():
    pointer_map = {"records": [_record("join-beta")]}
    capture = {
        "schema": "orb_weaver.pointer_browser_capture.v1",
        "generated_at": "2026-07-29T10:00:00+00:00",
        "observations": [
            _observation("/:desktop:1", "desktop", "join-beta", x=900),
            _observation("/:desktop:2", "desktop", "join-beta", x=902),
            _observation("/:mobile:1", "mobile", "join-beta", x=120),
            _observation("/:mobile:2", "mobile", "join-beta", x=122),
        ],
    }

    optimized = optimize_pointer_map(pointer_map, capture)
    record = optimized["records"][0]

    assert record["dom_mutability"] == "responsive"
    assert record["visual_recovery_hint"]["authority"] == "evidence_only"
    assert record["visual_recovery_hint"]["may_drive_pointer_action"] is False
    assert record["visual_recovery_hint"]["requires_live_dom_or_accessibility_verification"] is True
    assert set(record["visual_recovery_hint"]["observed_viewports"]) == {"desktop", "mobile"}
    assert optimized["map_extensions"]["coordinate_policy"]["may_drive_pointer_action"] is False


def test_content_change_marks_dynamic_without_changing_runtime_authority():
    record = _record("price")
    original_policy = dict(record["runtime_policy"])
    pointer_map = {"records": [record]}
    capture = {
        "observations": [
            _observation("/:desktop:1", "desktop", "price", x=300, text_fingerprint="price-one"),
            _observation("/:desktop:2", "desktop", "price", x=300, text_fingerprint="price-two"),
        ]
    }

    optimized = optimize_pointer_map(pointer_map, capture)
    updated = optimized["records"][0]

    assert updated["dom_mutability"] == "dynamic"
    assert updated["runtime_policy"] == original_policy
    assert updated["confidence"] == record["confidence"]


def test_single_render_is_deferred_js_not_static():
    pointer_map = {"records": [_record("late-button")]}
    capture = {
        "observations": [
            _observation("/:desktop:1", "desktop", "late-button", x=100),
        ]
    }

    optimized = optimize_pointer_map(pointer_map, capture)

    assert optimized["records"][0]["dom_mutability"] == "deferred_js"
