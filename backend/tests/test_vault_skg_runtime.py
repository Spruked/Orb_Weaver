from __future__ import annotations

from datetime import datetime

import pytest

from app.orb.turn_resolver import CanonicalTurnResolver
from app.orb.vault_skg_adapter import VaultSKGAdapter, materialize_site_apriori


def _adapter(tmp_path):
    priori = tmp_path / "A_Priori_Vault"
    posteriori = tmp_path / "A_Posteriori_Vault"
    materialize_site_apriori(
        priori,
        {
            "catalog": {"entries": []},
            "qa": {
                "entries": [
                    {
                        "qa_id": "weaver-purpose",
                        "question": "What does Weaver do?",
                        "aliases": ["Explain Weaver"],
                        "answer": "Weaver understands the site and guides visitors.",
                        "intent": "GENERAL",
                    }
                ]
            },
            "ontology": {"nodes": [], "edges": []},
            "policies": {"rules": []},
        },
    )
    return VaultSKGAdapter(priori, posteriori), priori, posteriori


def test_apriori_resolves_directly_and_new_learning_stays_candidate(tmp_path):
    adapter, _, _ = _adapter(tmp_path)

    known = adapter.lookup("apriori", "What does Weaver do?")
    assert known and known["source"] == "a_priori_qa"

    learned = adapter.report_outcome(
        query="What is your cheapest ORB?",
        resolution_source="catalog",
        answer="Basic is the lowest-priced ORB.",
        success=True,
    )
    assert learned["experience_id"].startswith("exp_")
    assert learned["candidate_state"] == "CANDIDATE"
    assert adapter.lookup("posteriori", "What is your cheapest ORB?") is None


def test_orb_name_does_not_trigger_comparison_intent(tmp_path):
    adapter, _, _ = _adapter(tmp_path)
    learned = adapter.report_outcome(
        query="What does ORB Weaver do?",
        resolution_source="site_world",
        answer="Weaver guides visitors.",
        success=True,
    )
    assert learned["intent"] == "GENERAL"


def test_verified_alias_promotes_persists_and_improves_later_query(tmp_path):
    adapter, priori, posteriori = _adapter(tmp_path)
    aliases = [
        "What is your cheapest ORB?",
        "Cheapest website ORB",
        "Which ORB costs least?",
        "What is your cheapest ORB?",
    ]

    result = None
    for query in aliases:
        result = adapter.report_outcome(
            query=query,
            resolution_source="catalog",
            answer="Basic is the lowest-priced ORB.",
            success=True,
        )

    assert result and result["candidate_state"] == "PROMOTED"
    reloaded = VaultSKGAdapter(priori, posteriori)
    match = reloaded.lookup("posteriori", "Cheapest website ORB")
    assert match and match["answer"] == "Basic is the lowest-priced ORB."
    assert match["evidence_ids"][0].startswith("kn_")


@pytest.mark.asyncio
async def test_authoritative_apriori_wins_over_contradictory_posteriori(tmp_path):
    adapter, _, _ = _adapter(tmp_path)
    for _ in range(4):
        adapter.report_outcome(
            query="What does Weaver do?",
            resolution_source="local_model",
            answer="An untrusted contradictory answer.",
            success=True,
        )

    resolver = CanonicalTurnResolver(vault_skg_lookup=adapter.lookup)
    result = await resolver.resolve(
        "What does Weaver do?",
        domain="example.test",
        apriori={
            "qa": {
                "entries": [
                    {
                        "qa_id": "authoritative-purpose",
                        "question": "What does Weaver do?",
                        "answer": "The authoritative answer.",
                        "source_evidence_ids": ["owner-approved-purpose"],
                    }
                ]
            }
        },
    )

    assert result["source_lane"] == "apriori"
    assert result["spoken_output"] == "The authoritative answer."
    assert result["evidence_ids"] == ["owner-approved-purpose"]


def test_pruning_uses_usefulness_and_validity_not_age_alone(tmp_path):
    adapter, _, _ = _adapter(tmp_path)
    posteriori = adapter.coordinator.posteriori
    adapter.report_outcome(
        query="A useful remembered phrase",
        resolution_source="catalog",
        answer="A verified useful answer.",
        success=True,
    )
    node = next(iter(posteriori.exp_cog.candidate_queue.values()))
    node.created_at = type(node.created_at)(
        iso="2000-01-01T00:00:00",
        unix=datetime(2000, 1, 1).timestamp(),
        crawl_version="old",
    )
    node.access_count = 20
    node.success_streak = 20
    node.confidence.value = 0.8

    action, details = posteriori.prune_logic.evaluate_for_pruning(node)
    assert action == "retain"
    assert details is None
