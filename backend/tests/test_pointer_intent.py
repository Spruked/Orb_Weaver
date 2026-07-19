from app.orb.pointer_intent import resolve_pointer_intent


def pointer(target_id, route, meaning, aliases, confidence_class="VERIFIED"):
    return {
        "target_id": target_id,
        "page_route": route,
        "target_type": "button",
        "meaning": meaning,
        "direct_aliases": aliases,
        "intent_aliases": aliases,
        "status": "active",
        "confidence_class": confidence_class,
        "runtime_policy": {"may_point": confidence_class in {"VERIFIED", "STABLE"}},
    }


def test_natural_paraphrase_resolves_same_route_owner_target():
    records = [pointer("book-consult", "/", "button: Book a consultation", ["schedule a consult"])]
    matches = resolve_pointer_intent(records, "Where can I set up a conversation?", "https://example.test/")
    assert [match.record["target_id"] for match in matches] == ["book-consult"]
    assert matches[0].guidance_eligible is True


def test_wrong_route_never_returns_a_pointer():
    records = [pointer("book-consult", "/contact", "button: Book a consultation", ["schedule a consult"])]
    assert resolve_pointer_intent(records, "Can I schedule a consultation?", "https://example.test/pricing") == []


def test_similarly_named_competing_targets_are_rejected_as_ambiguous():
    records = [
        pointer("sales-consult", "/", "button: Book consultation", ["schedule a consult"]),
        pointer("support-consult", "/", "button: Book consultation", ["schedule a consult"]),
    ]
    assert resolve_pointer_intent(records, "Where can I schedule a consult?", "https://example.test/") == []


def test_low_confidence_semantic_match_remains_voice_only():
    records = [pointer("book-consult", "/", "button: Book a consultation", ["schedule a consult"], "UNCERTAIN")]
    matches = resolve_pointer_intent(records, "Where can I reserve a meeting?", "https://example.test/")
    assert len(matches) == 1
    assert matches[0].guidance_eligible is False


def test_owner_authority_disambiguates_an_unapproved_duplicate():
    records = [
        {
            **pointer("approved-beta", "/", "button: Join the Founding Beta", ["join the beta"], "VERIFIED"),
            "pointer_health": "OWNER_VERIFIED",
        },
        {
            **pointer("recovered-beta", "/", "button: Join the Founding Beta", ["join the beta"], "STABLE"),
            "pointer_health": "RECOVERED",
        },
    ]
    matches = resolve_pointer_intent(records, "How do I join the beta?", "https://example.test/")
    assert [match.record["target_id"] for match in matches] == ["approved-beta"]


def test_beta_paraphrases_resolve_to_owner_verified_target_without_exact_alias():
    records = [
        {
            **pointer("approved-beta", "/", "button: Join the Founding Beta", ["join the founding beta"], "VERIFIED"),
            "pointer_health": "OWNER_VERIFIED",
        },
        {
            **pointer("recovered-beta", "/", "button: Join the Founding Beta", ["join the founding beta"], "STABLE"),
            "pointer_health": "RECOVERED",
        },
    ]
    for transcript in (
        "How can I participate in the founding beta?",
        "Where is the beta program?",
        "How do I become a tester?",
    ):
        matches = resolve_pointer_intent(records, transcript, "https://example.test/")
        assert [match.record["target_id"] for match in matches] == ["approved-beta"]
