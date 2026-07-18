from app.orb.pointer_recovery import assess_pointer_quality, reconcile_pointer_recovery


def record(target_id, confidence_class, locator, meaning="button: Request discussion", route="/"):
    return {
        "target_id": target_id,
        "page_route": route,
        "target_type": "button",
        "meaning": meaning,
        "semantic_locator": locator,
        "content_fingerprint": target_id,
        "confidence": 0.82 if confidence_class == "STABLE" else 0.62,
        "confidence_class": confidence_class,
        "runtime_policy": {"may_point": confidence_class in {"VERIFIED", "STABLE"}},
        "confidence_evidence": {"locator_method": "element_id" if locator.startswith("#") else "structural_css"},
        "allowed_actions": ["point"],
    }


def test_campaign_scale_quality_requires_pointer_recovery():
    pointer_map = {"records": [record("stable", "STABLE", "#stable")] + [
        record(f"uncertain-{index}", "UNCERTAIN", f"main button:nth-of-type({index + 1})")
        for index in range(136)
    ]}
    quality = assess_pointer_quality(pointer_map)
    assert quality["status"] == "POINTER_RECOVERY_REQUIRED"
    assert quality["stable_count"] == 1
    assert quality["uncertain_count"] == 136
    assert quality["stable_ratio"] == round(1 / 137, 4)
    assert "stable_ratio_below_threshold" in quality["triggers"]
    assert "stable_pointer_floor_not_met" in quality["triggers"]
    assert quality["thresholds"]["maximum_automatic_recovery_attempts"] == 1


def test_absolute_stable_floor_blocks_small_pointer_maps():
    pointer_map = {"records": [record(f"stable-{index}", "STABLE", f"#stable-{index}") for index in range(9)]}
    quality = assess_pointer_quality(pointer_map)
    assert quality["stable_ratio"] == 1.0
    assert quality["recovery_required"] is True
    assert quality["triggers"] == ["stable_pointer_floor_not_met"]


def test_recovery_promotes_durable_identity_and_keeps_dynamic_content_distinct():
    baseline = {"records": [record("price", "UNCERTAIN", "#price", "button: Price $499")]}
    capture = {
        "observations": [
            {
                "render_id": "root:desktop:1",
                "url": "https://example.test/",
                "route": "/",
                "viewport": "desktop",
                "candidates": [{
                    "identity_key": "/|button|button|price|",
                    "route": "/",
                    "accessible_name": "Price $499",
                    "locator": "#price",
                    "durable": True,
                    "text_fingerprint": "version-one",
                }],
            },
            {
                "render_id": "root:desktop:2",
                "url": "https://example.test/",
                "route": "/",
                "viewport": "desktop",
                "candidates": [{
                    "identity_key": "/|button|button|price|",
                    "route": "/",
                    "accessible_name": "Price $479",
                    "locator": "#price",
                    "durable": True,
                    "text_fingerprint": "version-two",
                }],
            },
        ]
    }
    recovered = reconcile_pointer_recovery(baseline, capture)
    pointer = recovered["records"][0]
    assert pointer["confidence_class"] == "STABLE"
    assert pointer["runtime_policy"]["may_point"] is True
    assert pointer["finding_class"] == "DYNAMIC"
    assert pointer["finding_subreason"] == "content_changed_identity_stable"
    assert pointer["pointer_health"] == "RECOVERED"
    assert recovered["recovery"]["automatic_attempts_used"] == 1


def test_unresolved_pointer_uses_existing_taxonomy_with_reason_subclassification():
    baseline = {"records": [record("unstable", "UNCERTAIN", "main button:nth-of-type(4)")]}
    recovered = reconcile_pointer_recovery(baseline, {"observations": []})
    pointer = recovered["records"][0]
    assert pointer["finding_class"] == "UNVERIFIED"
    assert pointer["finding_subreason"] == "selector_not_durable"
    assert "selector_not_durable" in pointer["uncertainty_reasons"]
    assert "element_not_visible" in pointer["uncertainty_reasons"]
    assert pointer["runtime_policy"]["may_point"] is False


def test_duplicate_targets_use_conflict_finding_class():
    duplicated = [
        record("duplicate-a", "UNCERTAIN", "main button:nth-of-type(1)"),
        record("duplicate-b", "UNCERTAIN", "main button:nth-of-type(1)"),
    ]
    recovered = reconcile_pointer_recovery({"records": duplicated}, {"observations": []})
    assert {pointer["finding_class"] for pointer in recovered["records"]} == {"CONFLICT"}
    assert all(pointer["finding_subreason"] == "selector_not_durable" for pointer in recovered["records"])
