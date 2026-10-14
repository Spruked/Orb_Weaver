import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ORB_WEAVER_VAULT_ROOT", str(tmp_path / "vault_system"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'auth_test.db'}")
    monkeypatch.setenv("LOCAL_LLM_URL", "")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")
    backend_path = str((Path.cwd() / "backend").resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    sys.modules.pop("main", None)
    for module_name in tuple(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)
    main = importlib.import_module("main")
    return main, TestClient(main.app)


def test_login_rejects_wrong_password_and_restores_valid_session(tmp_path, monkeypatch):
    _main, client = load_app(tmp_path, monkeypatch)
    credentials = {"email": "auth-regression@example.com", "password": "AuthTest!2026"}
    signup = client.post(
        "/api/auth/signup",
        json={
            **credentials,
            "full_name": "Auth Regression",
            "business_name": "Auth Test",
            "country": "US",
        },
    )
    assert signup.status_code == 200, signup.text

    rejected = client.post(
        "/api/auth/login",
        json={"email": credentials["email"], "password": "wrong-password"},
    )
    assert rejected.status_code == 401
    assert rejected.json()["detail"] == "Invalid email or password"

    login = client.post("/api/auth/login", json=credentials)
    assert login.status_code == 200, login.text
    token = login.json()["token"]
    restored = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert restored.status_code == 200
    assert restored.json()["email"] == credentials["email"]
