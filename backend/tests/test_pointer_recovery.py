from app.orb.pointer_recovery import (
    _candidate_matches_record,
    assess_pointer_quality,
    guidance_eligible_pointer_count,
    merge_canonical_pointer_authority,
    pointer_guidance_eligible,
    promote_owner_verified_pointer,
    reject_owner_pointer,
    reconcile_pointer_recovery,
)


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


def test_recovery_rejects_short_similarly_named_navigation_candidate():
    target = record("founding-beta", "UNCERTAIN", 'a[href="/founding-beta"]', "button: Join the Founding Beta")
    assert _candidate_matches_record(
        {"accessible_name": "Join the Founding Beta", "locator": 'a[href="/founding-beta"]'},
        target,
    ) is True
    assert _candidate_matches_record(
        {"accessible_name": "Beta", "locator": 'a[href="#beta"]'},
        target,
    ) is False


def test_owner_verification_grants_pointing_but_never_click_or_navigation():
    pointer_map = {"records": [record("consult", "UNCERTAIN", "#book-consult", "button: Book consultation")]}
    approved = promote_owner_verified_pointer(
        pointer_map,
        "consult",
        reviewer="owner@example.com",
        signature_hash="signed-decision",
        notes="Verified visually on desktop and mobile.",
        decided_at="2026-07-19T12:00:00+00:00",
    )
    pointer = approved["records"][0]
    assert pointer["pointer_health"] == "OWNER_VERIFIED"
    assert pointer["confidence_class"] == "VERIFIED"
    assert pointer["runtime_policy"]["may_point"] is True
    assert pointer["runtime_policy"]["may_click"] is False
    assert pointer["runtime_policy"]["may_navigate"] is False
    assert pointer["owner_authority"]["signature_hash"] == "signed-decision"


def test_owner_rejected_pointer_is_retained_but_excluded_from_runtime_quality():
    stable = [record(f"stable-{index}", "STABLE", f"#stable-{index}") for index in range(10)]
    rejected_candidate = record("unsafe", "UNCERTAIN", "main button:nth-of-type(8)")
    rejected = reject_owner_pointer(
        {"records": [*stable, rejected_candidate]},
        "unsafe",
        reviewer="owner@example.com",
        signature_hash="signed-rejection",
        notes="The target identity could not be verified.",
    )

    quality = rejected["quality"]
    rejected_pointer = next(item for item in rejected["records"] if item["target_id"] == "unsafe")
    assert rejected_pointer["owner_authority"]["state"] == "OWNER_REJECTED"
    assert rejected_pointer["owner_authority"]["signature_hash"] == "signed-rejection"
    assert len(rejected["records"]) == 11
    assert quality["total_record_count"] == 11
    assert quality["record_count"] == 10
    assert quality["excluded_count"] == 1
    assert quality["status"] == "POINTER_READY"


def test_rescan_retains_exact_owner_identity_and_demotes_stale_identity():
    original = record("consult", "STABLE", "#book-consult", "button: Book consultation")
    approved = promote_owner_verified_pointer(
        {"records": [original]},
        "consult",
        reviewer="owner@example.com",
        signature_hash="signed-decision",
    )
    retained = merge_canonical_pointer_authority(approved, {"records": [dict(original)]})
    assert retained["records"][0]["pointer_health"] == "OWNER_VERIFIED"
    assert retained["authority_reconciliation"]["retained_count"] == 1

    replacement = record("consult-v2", "UNCERTAIN", "#book-consult-v2", "button: Book consultation")
    demoted = merge_canonical_pointer_authority(approved, {"records": [replacement]})
    stale = next(item for item in demoted["records"] if item["target_id"] == "consult")
    assert stale["pointer_health"] == "DEPRECATED"
    assert stale["status"] == "inactive"
    assert stale["runtime_policy"]["may_point"] is False
    assert stale["finding_subreason"] == "owner_verified_identity_not_confirmed_by_rescan"


def test_rescan_retains_exact_owner_rejection_and_keeps_it_excluded():
    original = record(
        "unsafe",
        "UNCERTAIN",
        "#unsafe-action",
        "button: Unsafe action",
    )
    rejected = reject_owner_pointer(
        {"records": [original]},
        "unsafe",
        reviewer="owner@example.com",
        signature_hash="signed-rejection",
        notes="Owner rejected this exact pointer identity.",
        decided_at="2026-08-14T10:00:00+00:00",
    )

    retained = merge_canonical_pointer_authority(
        rejected,
        {"records": [dict(original)]},
        reconciled_at="2026-08-14T10:05:00+00:00",
    )

    pointer = retained["records"][0]
    assert pointer["pointer_health"] == "OWNER_REJECTED"
    assert pointer["confidence_class"] == "BLOCKED"
    assert pointer["finding_class"] == "BLOCKED"
    assert pointer["finding_subreason"] == "owner_rejected_pointer_identity"
    assert pointer["runtime_policy"]["may_point"] is False
    assert pointer["owner_authority"]["state"] == "OWNER_REJECTED"
    assert pointer["owner_authority"]["signature_hash"] == "signed-rejection"
    assert retained["quality"]["excluded_count"] == 1
    assert retained["authority_reconciliation"]["previous_owner_rejected_count"] == 1
    assert retained["authority_reconciliation"]["retained_rejected_count"] == 1
    assert retained["authority_reconciliation"]["demoted_count"] == 0


def test_guidance_requires_explicit_target_permission_and_safe_state():
    explicit = record("explicit", "STABLE", "#explicit")
    assert pointer_guidance_eligible(explicit) is True
    missing_permission = record("missing", "STABLE", "#missing")
    missing_permission["runtime_policy"] = {}
    assert pointer_guidance_eligible(missing_permission) is False
    uncertain = record("uncertain-guidance", "UNCERTAIN", "#uncertain")
    uncertain["runtime_policy"] = {"may_point": True}
    assert pointer_guidance_eligible(uncertain) is False
    rejected = record("rejected-guidance", "STABLE", "#rejected")
    rejected["pointer_health"] = "OWNER_REJECTED"
    rejected["finding_subreason"] = "owner_rejected_pointer_identity"
    assert pointer_guidance_eligible(rejected) is False
    assert guidance_eligible_pointer_count({"records": [explicit, missing_permission, uncertain, rejected]}) == 1


def test_pointer_quality_ignores_semantic_reference_records():
    references = [
        {
            **record(f"reference-{index}", "UNCERTAIN", f"main p:nth-of-type({index + 1})", meaning="paragraph: Helpful explanatory text"),
            "target_type": "paragraph",
            "pointer_class": "semantic_reference",
            "runtime_policy": {"may_point": False},
        }
        for index in range(40)
    ]
    guidance = record("guidance", "STABLE", "#start")
    guidance["pointer_class"] = "live_guidance"
    quality = assess_pointer_quality({"records": [guidance, *references]}, thresholds={"minimum_stable_pointers": 1})
    assert quality["record_count"] == 1
    assert quality["guidance_record_count"] == 1
    assert quality["reference_record_count"] == 40
    assert quality["stable_ratio"] == 1.0
    assert quality["recovery_required"] is False


def test_no_guidance_targets_do_not_trigger_recovery():
    references = [
        {
            **record(f"reference-{index}", "UNCERTAIN", f"main p:nth-of-type({index + 1})", meaning="faq answer: General context"),
            "target_type": "faq_answer",
            "pointer_class": "semantic_reference",
            "runtime_policy": {"may_point": False},
        }
        for index in range(5)
    ]
    quality = assess_pointer_quality({"records": references})
    assert quality["status"] == "NO_GUIDANCE_TARGETS"
    assert quality["recovery_required"] is False
    assert quality["reference_record_count"] == 5
    assert guidance_eligible_pointer_count({"records": references}) == 0
