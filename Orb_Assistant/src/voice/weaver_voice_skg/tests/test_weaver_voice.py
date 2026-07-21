"""
test_weaver_voice.py
====================
Comprehensive test suite for the Weaver Voice & Personality SKG.

Tests cover:
  1. Tone evaluation across all 4 humor levels
  2. First-person enforcement
  3. Evidence-bound humor compliance
  4. Anti-decoration rule
  5. Intent routing (approved actions only)
  6. Prohibited pattern detection
  7. Full funnel traversal
  8. Handoff behavior

Run: python -m pytest tests/test_weaver_voice.py -v
"""

import pytest
import sys
import os

# Add logic path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "logic"))

from weaver_articulation import (
    WeaverArticulation, HumorLevel, InitiativeLevel,
    articulate, evaluate_tone, generate_response
)


@pytest.fixture
def weaver():
    """Fresh Weaver instance for each test."""
    root = os.path.join(os.path.dirname(__file__), "..")
    return WeaverArticulation(skg_root=root)


# ── 1. Tone Evaluation Tests ─────────────────────────────────

class TestToneEvaluation:
    """Verify stage-to-tone mapping is deterministic and correct."""

    def test_landing_page_is_full_personality(self, weaver):
        tone = weaver.evaluate_tone("landing_page", {"page_count": 42})
        assert tone.humor_level == HumorLevel.FULL
        assert tone.preset_name == "full_personality"
        assert tone.initiative == InitiativeLevel.HIGH
        assert tone.can_joke is True
        assert tone.can_initiate is True

    def test_preflight_setup_is_full_personality(self, weaver):
        tone = weaver.evaluate_tone("preflight_setup", {"url": "example.com"})
        assert tone.humor_level == HumorLevel.FULL
        assert tone.can_joke is True

    def test_audit_review_is_focused_warmth(self, weaver):
        tone = weaver.evaluate_tone("audit_review", {"score": 78})
        assert tone.humor_level == HumorLevel.FOCUSED
        assert tone.preset_name == "focused_warmth"
        assert tone.initiative == InitiativeLevel.MEDIUM

    def test_package_presentation_is_focused(self, weaver):
        tone = weaver.evaluate_tone("package_presentation", {"tier": "basic"})
        assert tone.humor_level == HumorLevel.FOCUSED

    def test_checkout_is_quiet_confidence(self, weaver):
        tone = weaver.evaluate_tone("checkout", {"amount": 299.99})
        assert tone.humor_level == HumorLevel.QUIET
        assert tone.preset_name == "quiet_confidence"
        assert tone.can_joke is False
        assert tone.can_initiate is False

    def test_signature_is_quiet(self, weaver):
        tone = weaver.evaluate_tone("signature", {})
        assert tone.humor_level == HumorLevel.QUIET

    def test_verified_payment_is_celebratory(self, weaver):
        tone = weaver.evaluate_tone("verified_payment", {"order_id": "ORD-123"})
        assert tone.humor_level == HumorLevel.CELEBRATORY
        assert tone.preset_name == "celebratory"

    def test_live_status_is_celebratory(self, weaver):
        tone = weaver.evaluate_tone("live_status", {"uptime_hours": 24})
        assert tone.humor_level == HumorLevel.CELEBRATORY

    def test_unknown_stage_defaults_to_focused(self, weaver):
        tone = weaver.evaluate_tone("nonexistent_stage", {})
        assert tone.humor_level == HumorLevel.FOCUSED


# ── 2. Evidence Gate Tests ───────────────────────────────────

class TestEvidenceGate:
    """Verify humor_requires_evidence governance flag."""

    def test_full_humor_downgrades_without_evidence(self, weaver):
        tone = weaver.evaluate_tone("landing_page", {})
        # No evidence → should downgrade from FULL to FOCUSED
        assert tone.humor_level == HumorLevel.FOCUSED
        assert tone.can_joke is False

    def test_full_humor_stays_with_evidence(self, weaver):
        tone = weaver.evaluate_tone("landing_page", {"page_count": 42, "broken_links": 3})
        assert tone.humor_level == HumorLevel.FULL
        assert tone.can_joke is True

    def test_celebratory_downgrades_without_evidence(self, weaver):
        tone = weaver.evaluate_tone("verified_payment", {})
        assert tone.humor_level == HumorLevel.FOCUSED

    def test_quiet_never_downgrades(self, weaver):
        # Quiet stages have no humor, so evidence gate is irrelevant
        tone = weaver.evaluate_tone("checkout", {})
        assert tone.humor_level == HumorLevel.QUIET


# ── 3. First-Person Enforcement Tests ────────────────────────

class TestFirstPersonEnforcement:
    """Verify first_person_mandatory governance flag."""

    def test_third_person_detected_and_corrected(self, weaver):
        text = "The system will scan your website now."
        corrected, compliant = weaver._enforce_first_person(text)
        assert compliant is False
        assert "I will" in corrected
        assert "The system will" not in corrected

    def test_report_indicates_detected(self, weaver):
        text = "The report indicates 42 broken links."
        corrected, compliant = weaver._enforce_first_person(text)
        assert "I found" in corrected or "I" in corrected

    def test_mixed_case_third_person_is_detected(self, weaver):
        text = "The ORB will handle that. It Will proceed without delay."
        corrected, compliant = weaver._enforce_first_person(text)
        assert compliant is False
        assert "I will" in corrected or "I" in corrected
        assert "The ORB will" not in corrected
        assert "It Will" not in corrected

    def test_users_may_proceed_detected(self, weaver):
        text = "Users may proceed to the next step."
        corrected, compliant = weaver._enforce_first_person(text)
        assert "you can" in corrected.lower() or "I" in corrected

    def test_already_first_person_is_compliant(self, weaver):
        text = "I'll scan your site and show you what I find."
        corrected, compliant = weaver._enforce_first_person(text)
        assert compliant is True
        assert corrected == text

    def test_missing_first_person_gets_prepended(self, weaver):
        text = "Scanning your website now."
        corrected, compliant = weaver._enforce_first_person(text)
        assert compliant is False
        assert corrected.startswith("I want to help with this.")


# ── 4. Anti-Decoration Tests ─────────────────────────────────

class TestAntiDecoration:
    """Verify anti-decoration rule with 2500ms stabilization threshold."""

    def test_within_stabilization_window_is_compliant(self, weaver):
        import time
        stable_at = time.time()  # Just stabilized
        result = weaver._check_anti_decoration(stable_at, False, "landing_page")
        assert result is True

    def test_after_threshold_without_action_is_noncompliant(self, weaver):
        import time
        stable_at = time.time() - 4.0  # 4 seconds ago
        weaver.last_screen_stable_at = stable_at
        result = weaver._check_anti_decoration(stable_at, False, "landing_page")
        # Should be non-compliant because Weaver hasn't spoken or handed off
        assert result is False

    def test_visitor_input_active_is_compliant(self, weaver):
        import time
        stable_at = time.time() - 10.0  # Long past threshold
        result = weaver._check_anti_decoration(stable_at, True, "landing_page")
        assert result is True  # User speaking → Weaver correctly silent

    def test_handoff_marks_compliant(self, weaver):
        import time
        stable_at = time.time() - 4.0
        weaver.mark_screen_stable("landing_page")
        weaver.mark_handoff()
        result = weaver._check_anti_decoration(stable_at, False, "landing_page")
        assert result is True


# ── 5. Intent Routing Tests ──────────────────────────────────

class TestIntentRouting:
    """Verify intent-to-action mapping and governor validation."""

    def test_approved_action_routes_cleanly(self, weaver):
        context = {
            "stage_id": "landing_page",
            "screen_stable_at": __import__('time').time(),
            "visitor_input_active": False,
            "evidence": {"page_count": 42},
            "visitor_statement": "Scan my website",
            "allowed_actions": ["start_preflight", "explore_packages", "login"],
            "recommended_action": "start_preflight",
            "situation_description": "Visitor wants preflight scan"
        }
        response = weaver.articulate(context)
        assert response.recommended_action == "start_preflight"
        assert "start_preflight" in response.text.lower() or "scan" in response.text.lower()
        assert response.first_person_compliant is True

    def test_unapproved_action_gets_constrained_fallback(self, weaver):
        context = {
            "stage_id": "landing_page",
            "screen_stable_at": __import__('time').time(),
            "visitor_input_active": False,
            "evidence": {},
            "visitor_statement": "I want to access the admin panel",
            "allowed_actions": ["start_preflight", "explore_packages"],
            "recommended_action": "open_admin_panel",  # NOT in allowed_actions
            "situation_description": "Visitor requests unauthorized action"
        }
        response = weaver.articulate(context)
        assert "not available" in response.text.lower() or "next available" in response.text.lower()
        assert response.first_person_compliant is True

    def test_ambiguous_input_asks_clarifying_question(self, weaver):
        context = {
            "stage_id": "landing_page",
            "screen_stable_at": __import__('time').time(),
            "visitor_input_active": False,
            "evidence": {},
            "visitor_statement": "hmmmmm",
            "allowed_actions": ["start_preflight", "explore_packages"],
            "recommended_action": None,
            "situation_description": "Ambiguous visitor input"
        }
        response = weaver.articulate(context)
        assert "tell me a bit more" in response.text.lower() or "what you're looking for" in response.text.lower()

    def test_raw_visitor_statement_requires_verified_intent(self, weaver, monkeypatch):
        def fail(*args, **kwargs):
            raise AssertionError("_normalize_intent should not be called")

        monkeypatch.setattr(weaver, "_normalize_intent", fail)

        context = {
            "stage_id": "landing_page",
            "screen_stable_at": __import__('time').time(),
            "visitor_input_active": False,
            "evidence": {},
            "visitor_statement": "scan my site",
            "allowed_actions": ["start_preflight"],
            "recommended_action": "start_preflight",
            "situation_description": "Visitor requests routing"
        }

        response = weaver.articulate(context)
        assert response.recommended_action is None
        assert "deferred" in response.text.lower() or "verified" in response.text.lower()

    def test_invalid_intent_result_is_rejected(self, weaver):
        context = {
            "stage_id": "landing_page",
            "screen_stable_at": __import__('time').time(),
            "visitor_input_active": False,
            "evidence": {},
            "visitor_statement": "scan my site",
            "intent_result": {"source": "guest", "status": "raw"},
            "allowed_actions": ["start_preflight"],
            "recommended_action": "start_preflight",
            "situation_description": "Visitor requests routing"
        }

        response = weaver.articulate(context)
        assert response.recommended_action is None
        assert "deferred" in response.text.lower() or "verified" in response.text.lower()

    def test_shared_state_does_not_leak_between_requests(self, weaver):
        weaver.mark_handoff()

        stale_context = {
            "stage_id": "checkout",
            "screen_stable_at": __import__('time').time() - 5.0,
            "visitor_input_active": False,
            "evidence": {},
            "visitor_statement": "",
            "allowed_actions": ["continue"],
            "recommended_action": "continue",
            "situation_description": "Stale screen"
        }

        response = weaver.articulate(stale_context)
        assert response.anti_decoration_compliant is False


# ── 6. Prohibited Pattern Tests ──────────────────────────────

class TestProhibitedPatterns:
    """Verify prohibited pattern detection across all tone levels."""

    def test_visitor_mockery_detected(self, weaver):
        text = "Your website is a disaster and you should be embarrassed."
        tone = weaver.evaluate_tone("audit_review", {"score": 30})
        prohibited = weaver._detect_prohibited_patterns(text, tone)
        assert len(prohibited) > 0
        assert any("disaster" in p.lower() for p in prohibited)

    def test_generic_motivational_quote_detected_in_full(self, weaver):
        text = "Believe you can and you're halfway there. Now let me scan your site."
        tone = weaver.evaluate_tone("landing_page", {"page_count": 10})
        prohibited = weaver._detect_prohibited_patterns(text, tone)
        # Generic motivational quotes are prohibited in full personality
        assert any("motivational" in p.lower() for p in prohibited)

    def test_humor_in_quiet_stage_detected(self, weaver):
        text = "Your checkout is broken. Well, that's... a lot of broken code. I've seen worse."
        tone = weaver.evaluate_tone("checkout", {"amount": 99.99})
        prohibited = weaver._detect_prohibited_patterns(text, tone)
        # Any humor in quiet stage is prohibited
        assert len(prohibited) > 0


# ── 7. Full Funnel Traversal Test ────────────────────────────

class TestFullFunnelTraversal:
    """Simulate a complete customer journey through all stages."""

    def test_complete_funnel_journey(self, weaver):
        import time

        journey = [
            ("landing_page", {"page_count": 42}, "Visitor arrives"),
            ("preflight_setup", {"url": "example.com"}, "Starting preflight"),
            ("preflight_progress", {"pages_scanned": 150, "total_pages": 640}, "Scanning in progress"),
            ("crawl_progress", {"routes_found": 202, "pointers_mapped": 6531}, "Crawl running"),
            ("audit_review", {"seo_score": 78, "content_score": 45, "critical_issues": 2}, "Audit complete"),
            ("package_presentation", {"recommended_tier": "enhanced"}, "Presenting packages"),
            ("final_closer_questionnaire", {"questions_remaining": 3}, "Questionnaire"),
            ("package_commitment", {"tier": "enhanced", "price": 499}, "Committing"),
            ("build_configuration", {"config_steps": 5}, "Configuring build"),
            ("final_order_review", {"total": 499}, "Reviewing order"),
            ("signature", {"agreement_id": "AGR-001"}, "Signing agreement"),
            ("checkout", {"amount": 499}, "Processing payment"),
            ("verified_payment", {"order_id": "ORD-001", "amount": 499}, "Payment confirmed"),
            ("successful_installation", {"install_time": "2.3s"}, "Installed"),
            ("live_status", {"uptime_hours": 0, "visitor_count": 1}, "Now live"),
        ]

        for stage_id, evidence, situation in journey:
            context = {
                "stage_id": stage_id,
                "screen_stable_at": time.time(),
                "visitor_input_active": False,
                "evidence": evidence,
                "visitor_statement": "",
                "allowed_actions": ["continue", "proceed", "confirm"],
                "recommended_action": "continue",
                "situation_description": situation
            }

            response = weaver.articulate(context)

            # Universal checks
            assert response.first_person_compliant is True, f"First-person failed at {stage_id}"
            assert len(response.prohibited_patterns_detected) == 0, f"Prohibited patterns at {stage_id}: {response.prohibited_patterns_detected}"
            assert response.stage_id == stage_id

            # Stage-specific checks
            if stage_id in ["checkout", "signature", "package_commitment"]:
                assert response.humor_level == HumorLevel.QUIET, f"Should be quiet at {stage_id}"
                assert "joke" not in response.text.lower() or "funny" not in response.text.lower()

            if stage_id in ["landing_page", "preflight_setup"]:
                # With evidence, should be full
                if evidence:
                    assert response.humor_level == HumorLevel.FULL, f"Should be full at {stage_id}"


# ── 8. Handoff Behavior Tests ────────────────────────────────

class TestHandoffBehavior:
    """Verify Weaver hands off control correctly."""

    def test_active_input_triggers_handoff(self, weaver):
        import time
        context = {
            "stage_id": "landing_page",
            "screen_stable_at": time.time(),
            "visitor_input_active": True,  # KEY: user is typing
            "evidence": {"page_count": 42},
            "visitor_statement": "",
            "allowed_actions": ["start_preflight"],
            "recommended_action": None,
            "situation_description": "User typing"
        }
        response = weaver.articulate(context)
        assert response.handoff_triggered is True
        assert "stay close" in response.text.lower() or "explore at your own pace" in response.text.lower()

    def test_explicit_handoff_phrase_variety(self, weaver):
        weaver.mark_screen_stable("audit_review")
        weaver.mark_handoff()
        assert weaver.control_handed_off is True

    def test_re_entry_after_handoff(self, weaver):
        weaver.mark_screen_stable("landing_page")
        weaver.mark_handoff()
        # Later, user clicks something → Weaver re-engages
        weaver.mark_screen_stable("preflight_setup")
        assert weaver.control_handed_off is False  # Reset on new screen


# ── 9. Bit Structure Tests ───────────────────────────────────

class TestBitStructure:
    """Verify setup → punchline → sincere pivot template."""

    def test_evidence_bound_humor_has_all_three_parts(self, weaver):
        preset = weaver.presets["full_personality"]
        bit = preset["bit_examples"][0]
        assert "setup" in bit
        assert "punchline" in bit
        assert "sincere_pivot" in bit
        # Setup must reference evidence
        assert "{" in bit["setup"]  # Has evidence placeholder

    def test_joke_without_evidence_gets_flagged(self, weaver):
        text = "Your site is like a maze. A corn maze with good SEO. But it's fixable!"
        tone = weaver.evaluate_tone("landing_page", {})  # No evidence
        # Without evidence, tone downgrades to focused
        assert tone.humor_level == HumorLevel.FOCUSED
        # In focused mode, jokes are prohibited
        prohibited = weaver._detect_prohibited_patterns(text, tone)
        assert len(prohibited) > 0


# ── 10. Integration Tests ────────────────────────────────────

class TestIntegration:
    """Test module-level convenience functions."""

    def test_articulate_entry_point(self):
        import time
        context = {
            "stage_id": "landing_page",
            "screen_stable_at": time.time(),
            "visitor_input_active": False,
            "evidence": {"page_count": 100},
            "visitor_statement": "",
            "allowed_actions": ["start_preflight"],
            "recommended_action": "start_preflight",
            "situation_description": "Landing page entry"
        }
        response = articulate(context)
        assert response.text != ""
        assert response.first_person_compliant is True

    def test_evaluate_tone_entry_point(self):
        tone = evaluate_tone("audit_review", {"score": 85})
        assert tone.humor_level == HumorLevel.FOCUSED

    def test_generate_response_entry_point(self):
        envelope = {
            "stage_id": "celebratory",
            "evidence": {"uptime_hours": 24},
            "situation": "Launch complete"
        }
        text = generate_response(envelope)
        assert "I" in text
        assert text != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
