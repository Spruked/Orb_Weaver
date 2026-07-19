import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ORB_WEAVER_VAULT_ROOT", str(tmp_path / "vault_system"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'orb_memory_test.db'}")
    monkeypatch.setenv("LOCAL_LLM_URL", "")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")
    backend_path = str((Path.cwd() / "backend").resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    sys.modules.pop("main", None)
    sys.modules.pop("app.core.config", None)
    sys.modules.pop("app.core.storage", None)
    main = importlib.import_module("main")
    monkeypatch.setattr(main, "_orb_cognitive_pulse", lambda transcript: {"cognitive_mode": "TEST", "glow_intensity": 0.5})
    return main, TestClient(main.app)


def signup(client, email):
    response = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "OrbMemoryTest!2026",
            "full_name": "Memory Test User",
            "phone": "555-0100",
            "address_line1": "100 Orbit Way",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
            "country": "US",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_orb_memory_is_scoped_to_authenticated_user(tmp_path, monkeypatch):
    _main, client = load_app(tmp_path, monkeypatch)
    token_a = signup(client, "orb-memory-a@example.com")
    token_b = signup(client, "orb-memory-b@example.com")

    created = client.post(
        "/api/orb/memory",
        headers=auth(token_a),
        json={
            "category": "preferred_name",
            "key": "address_me_as",
            "value": "Bryan",
            "source": "explicit_user_preference",
            "confidence": 1.0,
        },
    )
    assert created.status_code == 200, created.text
    memory_id = created.json()["id"]

    memory_a = client.get("/api/orb/memory", headers=auth(token_a))
    memory_b = client.get("/api/orb/memory", headers=auth(token_b))
    assert memory_a.status_code == 200
    assert memory_b.status_code == 200
    assert [item["value"] for item in memory_a.json()["items"]] == ["Bryan"]
    assert memory_b.json()["items"] == []

    cross_delete = client.delete(f"/api/orb/memory/{memory_id}", headers=auth(token_b))
    assert cross_delete.status_code == 404

    own_delete = client.delete(f"/api/orb/memory/{memory_id}", headers=auth(token_a))
    assert own_delete.status_code == 200
    assert client.get("/api/orb/memory", headers=auth(token_a)).json()["items"] == []


def test_orb_request_receives_only_current_users_memory(tmp_path, monkeypatch):
    _main, client = load_app(tmp_path, monkeypatch)
    token_a = signup(client, "orb-context-a@example.com")
    token_b = signup(client, "orb-context-b@example.com")

    client.post(
        "/api/orb/memory",
        headers=auth(token_a),
        json={
            "category": "preferred_name",
            "key": "address_me_as",
            "value": "Aster",
            "source": "explicit_user_preference",
        },
    )
    client.post(
        "/api/orb/memory",
        headers=auth(token_b),
        json={
            "category": "preferred_name",
            "key": "address_me_as",
            "value": "Beacon",
            "source": "explicit_user_preference",
        },
    )

    response_a = client.post(
        "/api/orb/website-text",
        headers=auth(token_a),
        json={"transcript": "Do you remember who I am?"},
    )
    response_b = client.post(
        "/api/orb/website-text",
        headers=auth(token_b),
        json={"transcript": "Do you remember who I am?"},
    )
    anonymous = client.post("/api/orb/website-text", json={"transcript": "Do you remember who I am?"})

    assert response_a.status_code == 200, response_a.text
    assert response_b.status_code == 200, response_b.text
    assert anonymous.status_code == 200, anonymous.text

    values_a = [item["value"] for item in response_a.json()["memory_context"]["items"]]
    values_b = [item["value"] for item in response_b.json()["memory_context"]["items"]]
    assert values_a == ["Aster"]
    assert values_b == ["Beacon"]
    assert response_a.json()["memory_context"]["user_id"] != response_b.json()["memory_context"]["user_id"]
    assert response_a.json()["spoken_output"] == "I remember that you prefer to be addressed as Aster."
    assert response_b.json()["spoken_output"] == "I remember that you prefer to be addressed as Beacon."
    assert anonymous.json()["memory_context"]["scope"] == "anonymous_session"
    assert anonymous.json()["memory_context"]["items"] == []
