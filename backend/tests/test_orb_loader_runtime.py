import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'orb_loader_test.db'}")
    monkeypatch.setenv("LOCAL_LLM_URL", "")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")
    backend_path = str((Path.cwd() / "backend").resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    sys.modules.pop("main", None)
    sys.modules.pop("app.core.config", None)
    main = importlib.import_module("main")
    return main, TestClient(main.app)


def page_context(url="https://demo.openai.chatgpt.site/"):
    return {
        "url": url,
        "host": "demo.openai.chatgpt.site",
        "pathname": "/",
        "title": "Campaign",
        "viewport": {"width": 1200, "height": 800},
        "visible_controls": [{"tag": "button", "text": "Start"}],
        "captured_at": "2026-07-18T12:00:00Z",
    }


def test_bootstrap_accepts_registered_chatgpt_site_and_reports_page(tmp_path, monkeypatch):
    _main, client = load_app(tmp_path, monkeypatch)
    response = client.post(
        "/api/orb/bootstrap",
        headers={"Origin": "https://demo.openai.chatgpt.site"},
        json={
            "site_id": "orb-weaver-campaign",
            "target_url": "https://demo.openai.chatgpt.site/",
            "loader_version": "1",
            "page_context": page_context(),
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["schema"] == "orb_weaver.loader_bootstrap.v1"
    assert payload["status"] == "ready"
    assert payload["site"]["domain"] == "demo.openai.chatgpt.site"
    assert payload["site"]["context_domain"] == "campaign.orbweaver.spruked.com"
    assert payload["pointer_map"]["record_count"] > 0
    assert payload["pointer_map"]["quality"]["status"] == "POINTER_RECOVERY_REQUIRED"
    assert payload["pointer_guidance"]["status"] == "recovery_required"
    assert payload["pointer_guidance"]["safe_pointer_count"] == 1
    assert payload["deployment_preflight"] == {"passed": False, "blockers": ["POINTER_RECOVERY_REQUIRED"]}
    assert payload["orb_identity"]["skin_id"] == "orb_factory_default_v1"
    assert payload["orb_identity"]["owner_editable"] is False
    assert payload["orb_identity"]["immutable_default"] is True
    assert payload["orb_identity"]["fallback_enabled"] is True
    assert payload["page_capsule"]["current_url"] == "https://demo.openai.chatgpt.site/"
    assert payload["page_capsule"]["context_domain"] == "campaign.orbweaver.spruked.com"
    assert payload["observed_page"]["visible_controls"][0]["text"] == "Start"
    assert payload["installation"]["pointer_policy_enforced"] is True


def test_bootstrap_rejects_unapproved_origin(tmp_path, monkeypatch):
    _main, client = load_app(tmp_path, monkeypatch)
    response = client.post(
        "/api/orb/bootstrap",
        headers={"Origin": "https://attacker.example"},
        json={
            "site_id": "orb-weaver-campaign",
            "target_url": "https://attacker.example/",
            "loader_version": "1",
            "page_context": {**page_context("https://attacker.example/"), "host": "attacker.example"},
        },
    )
    assert response.status_code == 403


def test_site_id_maps_runtime_questions_to_the_canonical_scan(tmp_path, monkeypatch):
    main, _client = load_app(tmp_path, monkeypatch)
    mapped = main._orb_context_target_url(
        "https://demo.openai.chatgpt.site/pricing?plan=pro",
        "orb-weaver-campaign",
        "https://demo.openai.chatgpt.site",
    )
    assert mapped == "https://campaign.orbweaver.spruked.com/pricing?plan=pro"


def test_orb_websocket_is_origin_checked_and_route_aware(tmp_path, monkeypatch):
    _main, client = load_app(tmp_path, monkeypatch)
    with client.websocket_connect(
        "/ws/orb?site_id=orb-weaver-campaign&loader_version=1",
        headers={"origin": "https://demo.openai.chatgpt.site"},
    ) as socket:
        connected = socket.receive_json()
        assert connected["type"] == "orb.connected"
        socket.send_json({"type": "orb.route", "target_url": "https://demo.openai.chatgpt.site/about"})
        route = socket.receive_json()
        assert route == {
            "type": "orb.route.ack",
            "target_url": "https://demo.openai.chatgpt.site/about",
            "route": "/about",
        }
