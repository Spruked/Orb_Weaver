import json
import sys
from pathlib import Path


BACKEND_PATH = str((Path.cwd() / "backend").resolve())
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)


def test_unknown_interaction_creates_sanitized_site_stump(tmp_path, monkeypatch):
    from app.core import storage
    from app.orb import site_learning

    vault_root = tmp_path / "vault_system"
    monkeypatch.setattr(storage, "VAULT_ROOT", vault_root)
    monkeypatch.setattr(storage, "CLIENTS_ROOT", vault_root / "clients")
    monkeypatch.setattr(site_learning, "client_root", lambda domain: vault_root / "clients" / domain)
    monkeypatch.setattr(site_learning, "require_vault_path", lambda path, purpose="persistent data": Path(path).resolve())

    record_id = site_learning.record_interaction(
        domain="Example.Test",
        transcript="Can you call me at 555-123-4567 about whether installation is included?",
        spoken_output="I do not have enough evidence on this site to answer that.",
        answer_state="unknown",
        llm_source="local-fallback",
        target_url="https://example.test/pricing",
        route="/pricing",
        retrieval_failure="no_authoritative_site_evidence",
    )

    root = vault_root / "clients" / "example.test" / "website_orb_learning"
    interactions = (root / "posteriori" / "interactions.jsonl").read_text(encoding="utf-8").splitlines()
    assert record_id
    assert len(interactions) == 1
    record = json.loads(interactions[0])
    assert record["privacy"]["raw_conversation_stored"] is False
    assert "[redacted]" in record["visitor_wording_sanitized"]
    assert "555-123-4567" not in record["visitor_wording_sanitized"]

    ledger = json.loads((root / "stump_ledger" / "stump-ledger.json").read_text(encoding="utf-8"))
    assert ledger["entries"][0]["frequency"] == 1
    assert ledger["entries"][0]["status"] == "owner_review_needed"


def test_verified_case_lookup_is_site_scoped(tmp_path, monkeypatch):
    from app.core import storage
    from app.orb import site_learning

    vault_root = tmp_path / "vault_system"
    monkeypatch.setattr(storage, "VAULT_ROOT", vault_root)
    monkeypatch.setattr(storage, "CLIENTS_ROOT", vault_root / "clients")
    monkeypatch.setattr(site_learning, "client_root", lambda domain: vault_root / "clients" / domain)
    monkeypatch.setattr(site_learning, "require_vault_path", lambda path, purpose="persistent data": Path(path).resolve())
    root = site_learning.site_learning_root("example.test")
    (root / "verified_cases.json").write_text(
        json.dumps(
            {
                "schema": site_learning.VERIFIED_CASES_SCHEMA,
                "cases": [
                    {
                        "case_id": "case_installation_included",
                        "normalized_intent": "installation included",
                        "phrases": ["is installation included", "does install come with it"],
                        "approved_answer": "Installation details are listed on the services page.",
                        "supporting_evidence": ["owner_resolution_1"],
                        "scope": {"routes": ["/pricing"]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    match = site_learning.lookup_verified_case("example.test", "Is installation included?", "/pricing")
    assert match
    assert match["llm_source"] == "verified-posteriori-case"
    assert match["case_id"] == "case_installation_included"

    assert site_learning.lookup_verified_case("other.test", "Is installation included?", "/pricing") is None
    assert site_learning.lookup_verified_case("example.test", "Is installation included?", "/contact") is None
