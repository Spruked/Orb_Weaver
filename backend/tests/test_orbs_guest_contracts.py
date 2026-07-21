import importlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


SCHEMA_IDS = {
    "orb_weaver.orbs_stage_snapshot.v1",
    "orb_weaver.orbs_stage_action_request.v1",
    "orb_weaver.orbs_stage_action_result.v1",
    "orb_weaver.orbs_guest_session.v1",
    "orb_weaver.orbs_guest_merge_request.v1",
    "orb_weaver.orbs_guest_merge_result.v1",
}


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ORB_WEAVER_VAULT_ROOT", str(tmp_path / "vault_system"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'guest_contracts.db'}")
    monkeypatch.setenv("LOCAL_LLM_URL", "")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")
    monkeypatch.setenv("CALI_CRM_SYNC_ON_SIGNUP", "false")
    backend_path = str((Path.cwd() / "backend").resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    sys.modules.pop("main", None)
    for module_name in tuple(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)
    main = importlib.import_module("main")
    return main, TestClient(main.app)


def signup(client, email, guest_session_id=None):
    response = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "GuestMerge!2026",
            "full_name": "Guest Merge Customer",
            "phone": "555-0120",
            "address_line1": "1 Merge Way",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
            "country": "US",
            "guest_session_id": guest_session_id,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["customer"], {
        "Authorization": f"Bearer {response.json()['token']}"
    }


def create_guest(client):
    response = client.post(
        "/api/orbs/guest-sessions",
        json={
            "landing_intent": "Build a Website ORBS integration",
            "selected_tier_interest": "premium",
            "website_url": "https://guest-merge.example.com/",
            "original_cta_destination": "/orbs/start?tier=premium",
            "current_onboarding_step": "website",
            "completed_onboarding_steps": ["landing", "intent"],
            "non_sensitive_questionnaire_answers": {
                "primary_goal": "visitor guidance"
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_six_locked_contract_schema_files_are_present_and_versioned():
    schema_root = Path(__file__).resolve().parents[2] / "vault_system" / "schemas"
    discovered = set()
    for schema_id in SCHEMA_IDS:
        payload = json.loads((schema_root / f"{schema_id}.json").read_text(encoding="utf-8"))
        assert payload["$id"] == schema_id
        assert payload["additionalProperties"] is False
        discovered.add(payload["$id"])
    assert discovered == SCHEMA_IDS


def test_guest_merge_is_project_bound_idempotent_and_returns_fresh_snapshot(
    tmp_path, monkeypatch
):
    main, client = load_app(tmp_path, monkeypatch)
    guest = create_guest(client)
    customer, headers = signup(
        client, "guest-owner@example.com", guest["guest_session_id"]
    )
    request = {
        "schema": "orb_weaver.orbs_guest_merge_request.v1",
        "guest_session_id": guest["guest_session_id"],
        "idempotency_key": "guest-merge-owner-001",
        "project_display_name": "Guest Merge",
    }
    first = client.post(
        f"/api/orbs/guest-sessions/{guest['guest_session_id']}/merge",
        headers=headers,
        json=request,
    )
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["schema"] == "orb_weaver.orbs_guest_merge_result.v1"
    assert result["customer_id"] == str(customer["id"])
    assert result["original_cta_destination"] == "/orbs/start?tier=premium"
    assert result["fresh_snapshot"]["schema"] == "orb_weaver.orbs_stage_snapshot.v1"
    assert result["fresh_snapshot"]["customer_id"] == str(customer["id"])
    assert result["fresh_snapshot"]["current_stage"] == "preflight"
    assert result["fresh_snapshot"]["allowed_actions"][0]["name"] == "run_preflight"
    assert result["fresh_snapshot"]["allowed_actions"][0]["permitted_input_fields"] == []

    replay = client.post(
        f"/api/orbs/guest-sessions/{guest['guest_session_id']}/merge",
        headers=headers,
        json=request,
    )
    assert replay.status_code == 200
    assert replay.json() == result

    changed_key = client.post(
        f"/api/orbs/guest-sessions/{guest['guest_session_id']}/merge",
        headers=headers,
        json={**request, "idempotency_key": "guest-merge-owner-002"},
    )
    assert changed_key.status_code == 409
    assert changed_key.json()["code"] == "guest_session_consumed"

    with main.SessionLocal() as db:
        session = db.query(main.OrbsGuestSession).one()
        onboarding = db.query(main.OrbsOnboardingRecord).one()
        project = db.get(main.Project, int(result["project_id"]))
        assert session.consumed_by_customer_id == int(customer["id"])
        assert session.merged_project_id == project.id
        assert onboarding.project_id == project.id
        assert onboarding.transferred_progress["non_sensitive_questionnaire_answers"] == {
            "primary_goal": "visitor guidance"
        }
        assert project.customer_id == int(customer["id"])
        assert (
            db.query(main.Project)
            .filter(
                main.Project.customer_id == int(customer["id"]),
                main.Project.domain == "guest-merge.example.com",
            )
            .count()
            == 1
        )
        assert (
            db.query(main.Project)
            .filter(
                main.Project.customer_id == int(customer["id"]),
                main.Project.domain == "spruked.com",
            )
            .count()
            == 0
        )

    _other, other_headers = signup(client, "guest-other@example.com")
    denied = client.post(
        f"/api/orbs/guest-sessions/{guest['guest_session_id']}/merge",
        headers=other_headers,
        json={**request, "idempotency_key": "guest-merge-other-001"},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "guest_session_consumed"


def test_guest_session_rejects_sensitive_progress(tmp_path, monkeypatch):
    _main, client = load_app(tmp_path, monkeypatch)
    response = client.post(
        "/api/orbs/guest-sessions",
        json={
            "landing_intent": "Build an ORB",
            "website_url": "https://safe.example",
            "original_cta_destination": "/orbs/start",
            "non_sensitive_questionnaire_answers": {
                "payment_card": "must not be stored"
            },
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "sensitive_guest_data_rejected"


def test_basic_signup_fields_work_and_non_guest_keeps_legacy_project(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    response = client.post(
        "/api/auth/signup",
        json={
            "email": "basic-signup@example.com",
            "password": "BasicSignup!2026",
            "full_name": "Basic Signup",
            "business_name": "Basic Co",
        },
    )
    assert response.status_code == 200, response.text
    customer_id = int(response.json()["customer"]["id"])
    with main.SessionLocal() as db:
        projects = db.query(main.Project).filter(main.Project.customer_id == customer_id).all()
        assert [project.domain for project in projects] == ["spruked.com"]
