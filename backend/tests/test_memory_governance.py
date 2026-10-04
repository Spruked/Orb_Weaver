import pytest

from app.orb.memory_governance import (
    CONSENT_VERSION,
    RETENTION_POLICY_VERSION,
    MemoryCandidate,
    MemoryPolicyRejection,
    authorize_account_memory,
)
from app.models.database import Customer, OrbUserMemory, get_engine, get_session_maker, init_db
from main import OrbMemoryUpsert, _orb_memory_summary, _upsert_orb_memory


def test_explicit_account_candidate_is_authorized_and_versioned():
    authorization = authorize_account_memory(MemoryCandidate(
        memory_type="preferred_name",
        value="Aster",
        source="explicit_user_preference",
        account_id="42",
        consent_version=CONSENT_VERSION,
    ))

    assert authorization.account_id == "42"
    assert authorization.memory_type == "preferred_name"
    assert authorization.retention_policy_version == RETENTION_POLICY_VERSION


@pytest.mark.parametrize("candidate", [
    MemoryCandidate("health", "secret", "explicit_user_preference", "42", CONSENT_VERSION),
    MemoryCandidate("preferred_name", "Aster", "model_inference", "42", CONSENT_VERSION, True),
    MemoryCandidate("preferred_name", "Aster", "explicit_user_preference", "42", "old"),
])
def test_unallowlisted_inferred_or_stale_candidates_fail_closed(candidate):
    with pytest.raises(MemoryPolicyRejection):
        authorize_account_memory(candidate)


def test_memory_write_derives_source_and_read_excludes_legacy_rows(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'memory.db'}")
    init_db(engine)
    db = get_session_maker(engine)()
    customer = Customer(
        email="policy-boundary@example.com",
        password_hash="test",
        business_name="Policy Boundary",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    saved = _upsert_orb_memory(customer, OrbMemoryUpsert(
        category="preferred_name",
        key="address_me_as",
        value="Aster",
        source="forged_client_source",
    ), db)
    assert saved.source == "account_user_action"
    assert _orb_memory_summary(customer, db)["items"][0]["source"] == "account_user_action"

    legacy = OrbUserMemory(
        customer_id=customer.id,
        account_id=str(customer.id),
        category="preferred_name",
        memory_type="preferred_name",
        key="legacy_name",
        value="Legacy",
        source="legacy_client_source",
        consent_version=None,
        retention_policy_version=None,
    )
    db.add(legacy)
    db.commit()
    assert [item["key"] for item in _orb_memory_summary(customer, db)["items"]] == ["address_me_as"]


def test_expired_anonymous_context_is_swept():
    from main import _anonymous_orb_contexts, _prune_anonymous_orb_contexts

    _anonymous_orb_contexts["expired-session"] = {
        "summary": "should disappear", "turns": [], "expires_at": 0,
    }
    _prune_anonymous_orb_contexts(now=1)
    assert "expired-session" not in _anonymous_orb_contexts
