import asyncio
import importlib
import json
import sys
from io import BytesIO
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from PIL import Image


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


class FakeProviderResponse:
    def __init__(self, body, status_code=200):
        self._body = body
        self.status_code = status_code
        self.request = httpx.Request("GET", "http://provider.test")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("provider error", request=self.request, response=self)

    def json(self):
        return self._body


class FakeProviderClient:
    calls = []
    response_factory = None

    def __init__(self, *args, **kwargs):
        del args, kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        del args

    async def get(self, url):
        self.calls.append(url)
        return self.response_factory(url)


def test_dock_provider_discovery_uses_protocol_specific_endpoints(tmp_path, monkeypatch):
    main, _client = load_app(tmp_path, monkeypatch)
    main.settings.OLLAMA_BASE_URL = "http://127.0.0.1:11434"
    main.settings.OPENAI_COMPATIBLE_BASE_URL = "http://127.0.0.1:16520"
    FakeProviderClient.calls = []
    FakeProviderClient.response_factory = staticmethod(lambda url: FakeProviderResponse(
        {"models": [{"name": "qwen2.5:3b", "size": 123}]} if url.endswith("/api/tags")
        else {"data": [{"id": "gateway-model"}]}
    ))
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeProviderClient)

    ollama = asyncio.run(main._inspect_dock_provider("ollama_local"))
    gateway = asyncio.run(main._inspect_dock_provider("openai_compatible"))

    assert ollama["status"] == "available", ollama
    assert ollama["protocol"] == "native_ollama"
    assert ollama["models"][0]["name"] == "qwen2.5:3b"
    assert gateway["status"] == "available"
    assert gateway["protocol"] == "openai_compatible"
    assert gateway["models"][0]["name"] == "gateway-model"
    assert FakeProviderClient.calls == [
        "http://127.0.0.1:11434/api/tags",
        "http://127.0.0.1:16520/v1/models",
    ]


def test_dock_ollama_404_is_provider_misconfiguration(tmp_path, monkeypatch):
    main, _client = load_app(tmp_path, monkeypatch)
    main.settings.OLLAMA_BASE_URL = "http://127.0.0.1:16520"
    FakeProviderClient.response_factory = staticmethod(lambda _url: FakeProviderResponse({}, status_code=404))
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeProviderClient)

    result = asyncio.run(main._inspect_dock_provider("ollama_local"))

    assert result["status"] == "provider_misconfigured", result
    assert "protocol" in result["message"]


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


def test_dock_classifies_owner_preferences_without_weakening_standard_behavior(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    headers = signup(client, "dock-preferences@example.com")
    project = create_project(client, headers, "preferences.example.com")
    configuration = valid_configuration()
    configuration["behavior"] = {
        "must_follow_rules": ["Use a friendly greeting", "Always guarantee payment is secure"],
        "must_not_rules": ["Send an email to every visitor"],
        "prohibited_tone": ["sarcastic"],
    }

    saved = client.put(f"/api/projects/{project['id']}/orb-dock", headers=headers, json=configuration)
    assert saved.status_code == 200, saved.text
    payload = saved.json()
    review = {item["text"]: item for item in payload["compile"]["preference_review"]}
    assert review["Use a friendly greeting"]["status"] == "compatible"
    assert review["Always guarantee payment is secure"]["status"] == "conflict"
    assert review["Send an email to every visitor"]["status"] == "unsupported"
    assert review["sarcastic"]["status"] == "redundant"
    assert payload["compile"]["publishable"] is False
    assert payload["compile"]["preference_review"]

    compiled = main.compile_configuration(
        main.DockConfiguration.model_validate(configuration),
        None,
        project_id=str(project["id"]),
        domain=project["domain"],
        next_version=1,
    )["compiled_policy"]
    assert compiled["behavior"]["standard_behavior"]["verification"]
    assert "Use a friendly greeting" in compiled["behavior"]["owner_preferences"]
    assert "Always guarantee payment is secure" not in compiled["behavior"]["owner_preferences"]


def test_custom_orb_skin_is_normalized_and_selected_with_public_fallback_asset(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    headers = signup(client, "dock-skin@example.com")
    project = create_project(client, headers, "skin.example.com")
    image = Image.new("RGBA", (1600, 800), (20, 120, 180, 220))
    payload = BytesIO()
    image.save(payload, format="WEBP")
    payload.seek(0)

    uploaded = client.post(
        f"/api/projects/{project['id']}/orb-dock/custom-skin",
        headers=headers,
        files={"image": ("my-orb.webp", payload, "image/webp")},
    )
    assert uploaded.status_code == 200, uploaded.text
    response = uploaded.json()
    appearance = response["configuration"]["appearance"]
    assert appearance["skin_id"].startswith("custom_orb_")
    assert appearance["custom_skin_asset_path"].endswith(f"/{appearance['skin_id']}.png")
    assert appearance["custom_skin_file_size"] < 12 * 1024 * 1024
    custom = next(item for item in response["skins"] if item["skin_id"] == appearance["skin_id"])
    assert custom["custom"] is True

    asset = client.get(appearance["custom_skin_asset_path"])
    assert asset.status_code == 200
    with Image.open(BytesIO(asset.content)) as normalized:
        assert normalized.size == (1024, 1024)
        assert normalized.format == "PNG"

    reset = client.put(
        f"/api/projects/{project['id']}/orb-dock",
        headers=headers,
        json={**response["configuration"], "appearance": {"skin_id": "orb_factory_default_v1"}},
    )
    assert reset.status_code == 200, reset.text
    assert reset.json()["compile"]["publishable"] is True
