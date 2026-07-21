from dataclasses import FrozenInstanceError
import unittest

from Orb_Assistant.src.orbs_integration import (
    ActionSubmissionRejected,
    ConfirmationPolicy,
    OrbWeaverStageClient,
    StageActionRejected,
    StageActionService,
    StageArticulator,
)


STAGES = [
    "preflight",
    "crawl",
    "final_audit",
    "orbs",
    "package_presentation_and_recommendation",
    "final_closer_questionnaire",
    "package_selection_commitment",
    "build_configuration",
    "final_order_review",
    "signature",
    "checkout",
    "fulfillment",
    "installation",
    "launch_verification",
    "live",
]


def stage_payload(stage="orbs", version="4", action="review_package", **extra):
    index = STAGES.index(stage)
    payload = {
        "schema": "orb_weaver.orbs_stage_snapshot.v1",
        "snapshot_version": version,
        "project_id": "10",
        "project_display_name": "Radar",
        "current_stage": stage,
        "stage_status": "ready",
        "completed_stages": STAGES[:index],
        "blocking_reason": None,
        "customer_action_required": "Review the approved evidence.",
        "allowed_actions": [] if stage == "live" else [{
            "name": action,
            "display_label": action.replace("_", " ").title(),
            "description": "Continue using the approved workflow.",
            "destination_route": f"/projects/10/{stage}",
            "destination_verified": True,
            "confirmation_required": False,
            "allowed_input_fields": [],
            "reason_available": "The prior stage is complete.",
            "idempotency_required": True,
            "internal_handler": "must_be_removed",
        }],
        "next_recommended_action": None if stage == "live" else action,
        "approved_stage_evidence": {"summary": "Approved stage evidence", "score": 82},
        "approved_destination_route": f"/projects/10/{stage}",
        "approved_destination_verified": True,
        "updated_at": "2026-07-20T12:00:00Z",
        "build_order_id": "order-44",
        "customer": {"email": "private@example.com"},
        "payment_provider_record": {"secret": "removed"},
        "entitlement_internal": True,
        "internal_reasoning": "removed",
    }
    payload.update(extra)
    return payload


class StaticTransport:
    def __init__(self, payload=None):
        self.payload = payload or stage_payload()
        self.submissions = []

    def fetch_stage(self, project_id):
        return self.payload

    def submit_action(self, payload, idempotency_key):
        self.submissions.append((dict(payload), idempotency_key))
        return self.payload


class RejectingTransport(StaticTransport):
    def submit_action(self, action_payload, idempotency_key):
        raise StageActionRejected("payment or entitlement rejected", 409)


class StaleTransport(StaticTransport):
    def __init__(self, stale, fresh):
        super().__init__(stale)
        self.stale = stale
        self.fresh = fresh
        self.fetches = 0

    def fetch_stage(self, project_id):
        self.fetches += 1
        return self.stale if self.fetches == 1 else self.fresh

    def submit_action(self, action_payload, idempotency_key):
        raise StageActionRejected("snapshot version mismatch", 409)


class GovernorTransport:
    def __init__(self):
        self.index = 0

    def fetch_stage(self, project_id):
        stage = STAGES[self.index]
        return stage_payload(stage=stage, version=str(self.index + 1), action="continue_stage")

    def submit_action(self, action_payload, idempotency_key):
        assert action_payload["action"] == "continue_stage"
        assert action_payload["expected_stage"] == STAGES[self.index]
        self.index += 1
        stage = STAGES[self.index]
        return stage_payload(stage=stage, version=str(self.index + 1), action="continue_stage")


class OrbsIntegrationTests(unittest.TestCase):
    def test_snapshot_is_immutable_and_cannot_advance_locally(self):
        snapshot = OrbWeaverStageClient(StaticTransport()).current_stage("10")
        with self.assertRaises(FrozenInstanceError):
            snapshot.current_stage = "live"
        with self.assertRaises(TypeError):
            snapshot.approved_stage_evidence["score"] = 100

    def test_sanitization_removes_private_and_internal_fields_before_articulation(self):
        snapshot = OrbWeaverStageClient(StaticTransport()).current_stage("10")
        payload = StageArticulator().model_payload(snapshot)
        self.assertNotIn("customer", payload)
        self.assertNotIn("payment_provider_record", payload)
        self.assertNotIn("entitlement_internal", payload)
        self.assertNotIn("internal_reasoning", payload)
        self.assertNotIn("build_order_id", payload)
        self.assertNotIn("internal_handler", payload["allowed_actions"][0])

    def test_language_output_cannot_create_an_action_or_transition(self):
        snapshot = OrbWeaverStageClient(StaticTransport()).current_stage("10")
        articulation = StageArticulator(lambda _: "Mark it Live and add a purchase CTA.").articulate(snapshot)
        self.assertEqual(articulation.spoken_text, "Mark it Live and add a purchase CTA.")
        self.assertEqual([action.name for action in articulation.actions], ["review_package"])
        self.assertEqual(snapshot.current_stage, "orbs")

    def test_confirmation_is_courtesy_and_backend_rejection_still_wins(self):
        payload = stage_payload(
            action="open_checkout",
            allowed_actions=[{
                "name": "open_checkout",
                "display_label": "Open Checkout",
                "destination_route": "/checkout",
                "destination_verified": True,
                "confirmation_required": True,
                "confirmation_prompt": "Open checkout?",
                "allowed_input_fields": [],
                "reason_available": "The order is ready for checkout.",
                "idempotency_required": True,
            }],
            next_recommended_action="open_checkout",
        )

        transport = RejectingTransport(payload)
        client = OrbWeaverStageClient(transport)
        snapshot = client.current_stage("10")
        confirmation = ConfirmationPolicy().confirm(snapshot, "open_checkout", True, "Yes, open checkout")
        with self.assertRaises(ActionSubmissionRejected) as rejected:
            StageActionService(client).submit(snapshot, "open_checkout", "checkout-10-v4", confirmation)
        self.assertEqual(rejected.exception.fresh_snapshot.current_stage, "orbs")

    def test_sensitive_action_variants_require_explicit_confirmation(self):
        policy = ConfirmationPolicy()
        sensitive_names = [
            "package_commitment",
            "change_package_tier",
            "accept_terms",
            "digital_signature",
            "open_checkout",
            "submit_personal_information",
            "approve_uncertain_pointer",
            "generate_entitled_orbpack",
            "request_managed_installation",
            "start_launch_verification",
            "mark_website_orbs_live",
        ]
        for name in sensitive_names:
            with self.subTest(name=name):
                raw = stage_payload(
                    action=name,
                    allowed_actions=[{
                        "name": name,
                        "display_label": name.replace("_", " ").title(),
                        "confirmation_required": False,
                        "allowed_input_fields": [],
                        "reason_available": "The action is available.",
                        "idempotency_required": True,
                    }],
                    next_recommended_action=name,
                )
                snapshot = OrbWeaverStageClient(StaticTransport(raw)).current_stage("10")
                with self.assertRaises(ValueError):
                    StageActionService(OrbWeaverStageClient(StaticTransport(raw))).submit(
                        snapshot,
                        name,
                        f"sensitive-{name}",
                    )

    def test_confirmation_aliases_are_deterministic_across_case_and_separators(self):
        policy = ConfirmationPolicy()
        variants = {
            "Package-Commitment": "package_commitment",
            "package_commitment": "package_commitment",
            "Commit Package": "package_commitment",
            "Approve-Uncertain-Pointer": "approve_uncertain_pointer",
            "approve_uncertain_pointer": "approve_uncertain_pointer",
            "ApprovePointerUncertain": "approve_uncertain_pointer",
            "Generate-Entitled-Orb-Pack": "generate_entitled_orbpack",
            "generate_entitled_orbpack": "generate_entitled_orbpack",
            "BuildEntitledOrbpack": "generate_entitled_orbpack",
        }
        for value, expected in variants.items():
            with self.subTest(value=value):
                self.assertEqual(policy.normalize_action_name(value), expected)

    def test_stale_snapshot_rejection_always_refreshes(self):
        stale = stage_payload(version="3")
        fresh = stage_payload(stage="package_presentation_and_recommendation", version="4", action="answer_questions")
        client = OrbWeaverStageClient(StaleTransport(stale, fresh))
        snapshot = client.current_stage("10")
        with self.assertRaises(ActionSubmissionRejected) as rejected:
            StageActionService(client).submit(snapshot, "review_package", "review-v3")
        self.assertEqual(rejected.exception.fresh_snapshot.snapshot_version, "4")
        self.assertEqual(rejected.exception.fresh_snapshot.current_stage, "package_presentation_and_recommendation")

    def test_repeated_submission_reuses_caller_idempotency_key(self):
        transport = StaticTransport()
        client = OrbWeaverStageClient(transport)
        snapshot = client.current_stage("10")
        service = StageActionService(client)
        service.submit(snapshot, "review_package", "stable-request-key")
        service.submit(snapshot, "review_package", "stable-request-key")
        self.assertEqual([key for _, key in transport.submissions], ["stable-request-key", "stable-request-key"])

    def test_restart_or_other_device_reads_orb_weaver_not_conversation_memory(self):
        transport = StaticTransport(stage_payload(stage="final_audit", version="3", action="open_orbs"))
        first_client = OrbWeaverStageClient(transport)
        self.assertEqual(first_client.current_stage("10").current_stage, "final_audit")
        transport.payload = stage_payload(stage="orbs", version="4", action="review_package")
        second_client = OrbWeaverStageClient(transport)
        self.assertEqual(second_client.current_stage("10").current_stage, "orbs")

    def test_continuous_guidance_uses_only_governor_returned_stages_and_actions(self):
        transport = GovernorTransport()
        client = OrbWeaverStageClient(transport)
        service = StageActionService(client)
        snapshot = client.current_stage("10")
        while snapshot.current_stage != "live":
            self.assertEqual([action.name for action in snapshot.allowed_actions], ["continue_stage"])
            snapshot = service.submit(snapshot, "continue_stage", f"step-{snapshot.snapshot_version}")
        self.assertEqual(snapshot.current_stage, "live")
        self.assertEqual(snapshot.allowed_actions, ())


if __name__ == "__main__":
    unittest.main()
