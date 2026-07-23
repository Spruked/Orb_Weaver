import importlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ORB_WEAVER_VAULT_ROOT", str(tmp_path / "vault_system"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'orb_dock.db'}")
    monkeypatch.setenv("LOCAL_LLM_URL", "")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")
    monkeypatch.setenv("CALI_CRM_SYNC_ON_SIGNUP", "false")
    backend_path = str((Path.cwd() / "backend").resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    for module_name in (
        "main",
        "app.orb_dock",
        "app.models.database",
        "app.core.config",
        "app.core.storage",
    ):
        sys.modules.pop(module_name, None)
    main = importlib.import_module("main")
    return main, TestClient(main.app)


def signup(client, email):
    response = client.post("/api/auth/signup", json={
        "email": email,
        "password": "DockStation!2026",
        "full_name": "Dock Owner",
        "business_name": "Dock Station Test",
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    return {"Authorization": f"Bearer {payload['token']}"}


def create_project(client, headers, domain):
    response = client.post("/api/projects", headers=headers, json={"name": "Dock Project", "domain": domain})
    assert response.status_code == 200, response.text
    return response.json()


def write_site_world(main, domain):
    root = main.client_root(domain) / "website_orb_context"
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_context.json").write_text(json.dumps({
        "schema": "orb_weaver.site_world.v1",
        "domain": domain,
        "authority_flow": {"pages": [{"url": f"https://{domain}/appointments"}]},
        "visitor_tools": [{"id": "schedule_appointment", "keywords": ["appointment"], "spoken_output": "I can guide you to scheduling.", "suggested_route": "/appointments"}],
    }), encoding="utf-8")


def valid_configuration():
    return {
        "schema": "orb_weaver.orb_dock_configuration.v1",
        "appearance": {"skin_id": "pink_diamond"},
        "llm": {"provider": "runtime_default", "model": None},
        "business_objectives": [{
            "objective_id": "schedule",
            "name": "Schedule an appointment",
            "enabled": True,
            "completion_evidence": ["Verified appointment confirmation"],
            "required_fields": ["name", "contact"],
            "permitted_routes": ["/appointments"],
            "permitted_tools": ["schedule_appointment"],
            "escalation_route": "/appointments",
            "success_condition": "A verified appointment confirmation is returned.",
            "failure_condition": "The scheduling service does not confirm the appointment.",
        }],
        "additional_guide_rails": [{
            "guide_rail_id": "appointment_priority",
            "name": "Appointment priority",
            "enabled": True,
            "applies_when": "A visitor asks to schedule.",
            "orb_should": "Guide the visitor to the verified appointment workflow.",
            "orb_must_not": "Claim an appointment exists without confirmation.",
            "permitted_actions": ["Explain scheduling", "Open the verified scheduling route"],
            "required_evidence": ["Current appointment route", "Scheduling confirmation"],
            "escalate_when": "The scheduling service is unavailable.",
            "priority": "high",
            "effective_from": None,
            "effective_until": None,
            "owner_note": "Internal staffing note that must not reach the runtime.",
        }],
        "situational_guide_rails": [{
            "guide_rail_id": "appointment_page",
            "name": "Appointment page",
            "enabled": True,
            "conditions": {
                "current_pages": ["/appointments"],
                "visitor_types": [],
                "workflow_stages": [],
                "product_categories": [],
                "business_hours": [],
                "geographic_eligibility": [],
                "minimum_confidence": 0.8,
                "authentication_states": ["anonymous"],
                "active_promotions": [],
                "prior_history_terms": [],
            },
            "orb_should": "Explain the visible scheduling fields.",
            "orb_must_not": "Submit without visitor confirmation.",
            "permitted_actions": ["Point to verified scheduling fields"],
            "required_evidence": ["Current route and verified pointers"],
            "escalate_when": "A required field cannot be verified.",
            "priority": "medium",
            "owner_note": "Internal-only page note.",
        }],
    }


def test_dock_policy_compiles_publishes_and_strips_owner_notes(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    headers = signup(client, "dock-owner@example.com")
    project = create_project(client, headers, "dock.example.com")
    write_site_world(main, project["domain"])

    saved = client.put(
        f"/api/projects/{project['id']}/orb-dock",
        headers=headers,
        json=valid_configuration(),
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["compile"]["publishable"] is True

    published = client.post(f"/api/projects/{project['id']}/orb-dock/publish", headers=headers)
    assert published.status_code == 200, published.text
    assert published.json()["publication"]["version"] == 1

    with main.SessionLocal() as db:
        policy = db.query(main.OrbDockPolicy).filter(main.OrbDockPolicy.project_id == int(project["id"])).one()
        assert policy.compiled_policy["appearance"]["skin_id"] == "pink_diamond"
        assert policy.compiled_policy["enforcement"]["allowed_routes"] == ["/appointments"]
        assert policy.compiled_policy["enforcement"]["allowed_tools"] == ["schedule_appointment"]
        assert "owner_note" not in policy.compiled_policy["additional_guide_rails"][0]
        assert "owner_note" not in policy.compiled_policy["situational_guide_rails"][0]


def test_dock_rejects_unverified_routes_and_owner_doctrine_mutation(tmp_path, monkeypatch):
    _main, client = load_app(tmp_path, monkeypatch)
    headers = signup(client, "dock-guard@example.com")
    project = create_project(client, headers, "guard.example.com")
    configuration = valid_configuration()
    configuration["business_objectives"][0]["permitted_routes"] = ["/not-in-site-world"]

    saved = client.put(f"/api/projects/{project['id']}/orb-dock", headers=headers, json=configuration)
    assert saved.status_code == 200, saved.text
    assert saved.json()["compile"]["publishable"] is False
    assert any(item["code"] == "route_not_in_site_world" for item in saved.json()["compile"]["blockers"])
    blocked = client.post(f"/api/projects/{project['id']}/orb-dock/publish", headers=headers)
    assert blocked.status_code == 409

    configuration["locked_doctrine"] = []
    mutation = client.put(f"/api/projects/{project['id']}/orb-dock", headers=headers, json=configuration)
    assert mutation.status_code == 422
