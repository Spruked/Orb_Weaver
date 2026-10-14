import json
import tempfile
import unittest
from pathlib import Path

from app.orb import aims_memory
from memory_core import EntryType


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
        # Routine visitor turns are session-only; durable outcome retention is
        # reserved for the explicit verified-outcome path.
        self.assertEqual(aims_memory._aims().retrieval_ledger.outcome_statistics()["total"], 0)

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

    def test_authenticated_prior_outcome_is_not_retrieved_across_visitor_sessions(self):
        session = "b" * 24
        context = aims_memory.context_for_turn("checkout", session, "customer-42")
        system = aims_memory._aims()
        system.finalize_session_outcome(
            context["session_id"], {"goals": ["complete checkout"], "outcome": "completed"},
            visitor_key=aims_memory._visitor_key("customer-42"),
        )
        returned = aims_memory.context_for_turn("checkout again", "c" * 24, "customer-42")
        self.assertEqual(returned["prior_session_outcomes"], [])

    def test_authenticated_scoped_outcome_survives_bridge_restart(self):
        site = "www.example.test"
        context = aims_memory.context_for_turn(
            "checkout", "e" * 24, "customer-42", "https://www.example.test/shop",
        )
        aims_memory._aims().finalize_session_outcome(
            context["session_id"], {"goals": ["complete checkout"], "outcome": "completed"},
            visitor_key=aims_memory._visitor_key("customer-42"), site_scope=site,
        )
        aims_memory._system = None
        returned = aims_memory.context_for_turn(
            "checkout", "f" * 24, "customer-42", "https://www.example.test/shop",
        )
        self.assertEqual(returned["prior_session_outcomes"][0]["outcome_package"]["goals"], ["complete checkout"])
        isolated = aims_memory.context_for_turn(
            "checkout", "g" * 24, "customer-42", "https://other.example.test/shop",
        )
        self.assertEqual(isolated["prior_session_outcomes"], [])

    def test_indexed_posterior_recall_is_scoped_bounded_and_advisory(self):
        context = aims_memory.context_for_turn(
            "billing", "h" * 24, None, "https://www.example.test/billing",
        )
        system = aims_memory._aims()
        source = system.commit(
            EntryType.OBSERVATION,
            {"event": "verified billing evidence"},
        )
        atom = system.derive_aposteriori(
            "billing guidance is verified", [source],
            metadata={"site_scope": "www.example.test"}, initial_confidence=0.7,
        )
        for _ in range(3):
            system.vault.reinforce(atom.atom_id, 0.01)
        system.indexes.upsert(atom)
        recalled = aims_memory.context_for_turn(
            "billing", "i" * 24, None, "https://www.example.test/billing",
        )
        self.assertEqual(recalled["indexed_evidence"][0]["statement"], "billing guidance is verified")
        self.assertEqual(recalled["indexed_evidence"][0]["authority"], "advisory_evidence_only")
        other = aims_memory.context_for_turn(
            "billing", "j" * 24, None, "https://other.example.test/billing",
        )
        self.assertEqual(other["indexed_evidence"], [])
        self.assertLessEqual(
            len(json.dumps(recalled["indexed_evidence"]).encode()),
            aims_memory.AIMS_RECALL_MAX_BYTES,
        )


if __name__ == "__main__":
    unittest.main()
