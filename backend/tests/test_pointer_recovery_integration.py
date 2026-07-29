from app.orb import pointer_recovery


def test_normal_recovery_call_is_optimized_without_parallel_pipeline():
    assert getattr(pointer_recovery.reconcile_pointer_recovery, "_orb_pointer_optimizer_installed", False) is True

    baseline = {
        "records": [
            {
                "target_id": "join-beta",
                "page_route": "https://example.test/",
                "target_type": "button",
                "meaning": "button: Join Beta",
                "intent_aliases": ["Join Beta"],
                "direct_aliases": ["Join Beta", "open Join Beta"],
                "topic_aliases": ["information about website"],
                "content_fingerprint": "join-beta",
                "semantic_locator": "#join-beta",
                "confidence": 0.68,
                "confidence_class": "UNCERTAIN",
                "runtime_policy": {"may_point": False},
                "confidence_evidence": {"locator_method": "element_id"},
                "allowed_actions": ["point"],
                "status": "active",
            }
        ]
    }
    observations = []
    for viewport, size, x in (
        ("desktop", {"width": 1440, "height": 900}, 900),
        ("mobile", {"width": 390, "height": 844}, 120),
    ):
        for render_pass in (1, 2):
            observations.append(
                {
                    "render_id": f"/:{viewport}:{render_pass}",
                    "url": "https://example.test/",
                    "route": "/",
                    "viewport": viewport,
                    "viewport_size": size,
                    "candidates": [
                        {
                            "identity_key": f"/|button|button|join beta|",
                            "route": "/",
                            "accessible_name": "Join Beta",
                            "text": "Join Beta",
                            "text_fingerprint": "same",
                            "locator": "#join-beta",
                            "durable": True,
                            "rect": {"x": x, "y": 100, "width": 120, "height": 40},
                        }
                    ],
                }
            )

    recovered = pointer_recovery.reconcile_pointer_recovery(
        baseline,
        {
            "schema": "orb_weaver.pointer_browser_capture.v1",
            "generated_at": "2026-07-29T10:00:00+00:00",
            "observations": observations,
        },
    )

    record = recovered["records"][0]
    assert record["confidence_class"] == "STABLE"
    assert record["dom_mutability"] == "responsive"
    assert record["visual_recovery_hint"]["authority"] == "evidence_only"
    assert record["visual_recovery_hint"]["may_drive_pointer_action"] is False
    assert recovered["map_extensions"]["coordinate_policy"]["may_drive_pointer_action"] is False
