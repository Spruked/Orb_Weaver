import tempfile
import unittest
from pathlib import Path

from memory_core import AIMSMemorySystem, AuthorityClass, EntryType, OutcomeSignal, Relation
from memory_core.skg import EdgeState


class WebsiteOrbMemoryFoundationTests(unittest.TestCase):
    def test_full_session_has_selected_context_but_not_silent_eviction(self):
        with tempfile.TemporaryDirectory() as directory:
            system = AIMSMemorySystem(Path(directory))
            system.start_session("visit-1")
            for number in range(40):
                system.remember_session_event("visit-1", "message", {"text": f"turn {number}"})
            system.remember_session_event("visit-1", "goal", {"text": "find account billing"}, relevance=1.0)
            context = system.session_context("visit-1", "billing account", limit=5)
            self.assertEqual(context["session"]["event_count"], 41)
            self.assertEqual(len(context["context"]), 5)
            self.assertTrue(any(item["kind"] == "goal" for item in context["context"]))

    def test_only_explicit_outcome_package_becomes_durable_and_retrievable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = AIMSMemorySystem(root)
            system.start_session("visit-1")
            raw_secret = "raw transcript must never become durable"
            system.remember_session_event("visit-1", "message", {"text": raw_secret})
            system.finalize_session_outcome("visit-1", {
                "goals": ["complete checkout"], "completed_actions": ["opened checkout"],
                "outcome": "visitor completed purchase", "unapproved": raw_secret,
            }, visitor_key="visitor-hash")
            ledger = system.long_term.ledger_path.read_text(encoding="utf-8")
            self.assertNotIn(raw_secret, ledger)
            prior = system.retrieve_prior_session_outcomes("visitor-hash", "checkout")
            self.assertEqual(prior[0]["outcome_package"]["goals"], ["complete checkout"])
            self.assertNotIn("visitor_key", prior[0]["outcome_package"])

    def test_authority_and_outcome_signal_are_bounded_and_private_snapshot_is_allowlisted(self):
        with tempfile.TemporaryDirectory() as directory:
            system = AIMSMemorySystem(Path(directory))
            protected = system.assert_apriori("Never expose private memory", authority_class=AuthorityClass.INVARIANT)
            system.vault.challenge(protected.atom_id, 0.9)
            self.assertEqual(system.vault.get(protected.atom_id).confidence, 1.0)
            self.assertIsNone(system.vault.retire(protected.atom_id))
            receipt = system.retrieve("private memory")
            signal = system.record_outcome_signal(OutcomeSignal(
                session_id="visit-1", cognitive_event_id="turn-1", outcome="successful",
                quality=1.0, confidence=1.0, retrieval_id=receipt["retrieval_id"],
                result="verified", visitor_response="completed",
            ))
            self.assertTrue(signal["material"])
            snapshot = system.maintenance_snapshot()
            rendered = str(snapshot)
            self.assertIn("outcomes", snapshot)
            self.assertNotIn("Never expose private memory", rendered)
            self.assertNotIn("results", snapshot)

    def test_material_outcomes_drive_derived_edge_lifecycle_not_vault_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            system = AIMSMemorySystem(Path(directory))
            prior = system.assert_apriori("installation guidance")
            source = system.commit(EntryType.OBSERVATION, {"event": "installation flow"})
            learned = system.derive_aposteriori("installation goes to preflight", [source], initial_confidence=0.7)
            for _ in range(3):
                system.vault.reinforce(learned.atom_id, 0.01)
            system.indexes.upsert(learned)
            edge = system.link(learned.atom_id, prior.atom_id, Relation.SUPPORTS, weight=0.9)
            receipt = system.retrieve("installation guidance")
            for number in range(9):
                system.record_outcome_signal(OutcomeSignal(
                    session_id="visit", cognitive_event_id=f"turn-{number}", outcome="failed",
                    quality=1.0, confidence=1.0, retrieval_id=receipt["retrieval_id"], evidence_ids=[source.entry_id],
                ))
            self.assertIn(system.skg.edge(edge.edge_id).state, {EdgeState.RETIRED, EdgeState.PRUNED})
            self.assertIsNotNone(system.vault.get(learned.atom_id))


if __name__ == "__main__":
    unittest.main()
