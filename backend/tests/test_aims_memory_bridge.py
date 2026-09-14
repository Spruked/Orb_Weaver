import tempfile
import unittest
from pathlib import Path

from app.orb import aims_memory


class AimsMemoryBridgeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous_root = aims_memory.RUNTIME_ROOT
        aims_memory.RUNTIME_ROOT = Path(self.directory.name)
        aims_memory._system = None

    def tearDown(self):
        aims_memory._system = None
        aims_memory.RUNTIME_ROOT = self.previous_root
        self.directory.cleanup()

    def test_turn_context_is_selected_not_full_and_result_is_observed(self):
        session = "a" * 24
        for turn in range(16):
            context = aims_memory.context_for_turn(
                f"tour turn {turn}", session, None, "https://example.test/", {"phase": "understanding"},
            )
        self.assertEqual(context["provider"], "aims")
        self.assertEqual(type(aims_memory._aims().skg_trio.prior.backend).__name__, "GraphQLiteSKGBackend")
        self.assertEqual(context["full_session_event_count"], 48)
        self.assertLessEqual(len(context["relevant_session_context"]), 12)
        aims_memory.record_turn_result(context, "Here is the next verified stop.")
        active = aims_memory._aims().session_context(context["session_id"], "verified")
        self.assertGreater(active["session"]["event_count"], 48)
        self.assertEqual(aims_memory._aims().retrieval_ledger.outcome_statistics()["total"], 1)

    def test_agency_context_retrieval_does_not_manufacture_visitor_messages(self):
        session = "d" * 24
        context = aims_memory.context_for_turn("I want to see guidance", session, None)
        system = aims_memory._aims()
        before = system.session_context(context["session_id"], "guidance")["session"]["event_count"]

        selected = aims_memory.context_for_agency("Current governed tour objective", session, None)
        after_context = system.session_context(context["session_id"], "guidance")

        self.assertEqual(selected["session_id"], context["session_id"])
        self.assertEqual(after_context["session"]["event_count"], before)
        texts = [event.payload.get("text") for event in system.sessions[context["session_id"]].events()]
        self.assertNotIn("Current governed tour objective", texts)
        self.assertIn("I want to see guidance", texts)

    def test_authenticated_prior_outcome_is_pseudonymous_and_retrieved(self):
        session = "b" * 24
        context = aims_memory.context_for_turn("checkout", session, "customer-42")
        system = aims_memory._aims()
        system.finalize_session_outcome(
            context["session_id"], {"goals": ["complete checkout"], "outcome": "completed"},
            visitor_key=aims_memory._visitor_key("customer-42"),
        )
        returned = aims_memory.context_for_turn("checkout again", "c" * 24, "customer-42")
        self.assertEqual(returned["prior_session_outcomes"][0]["outcome_package"]["outcome"], "completed")


if __name__ == "__main__":
    unittest.main()
