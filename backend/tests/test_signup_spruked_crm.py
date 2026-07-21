import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ORB_WEAVER_VAULT_ROOT", str(tmp_path / "vault_system"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'signup_test.db'}")
    monkeypatch.setenv("LOCAL_LLM_URL", "")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")
    monkeypatch.setenv("CALI_CRM_URL", "http://localhost:21010/")
    monkeypatch.setenv("CALI_CRM_SYNC_ON_SIGNUP", "false")
    backend_path = str((Path.cwd() / "backend").resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    sys.modules.pop("main", None)
    sys.modules.pop("app.core.config", None)
    sys.modules.pop("app.core.storage", None)
    main = importlib.import_module("main")
    return main, TestClient(main.app)


def signup_payload(email="spruked-signup@example.com"):
    return {
        "email": email,
        "password": "SprukedSignup!2026",
        "full_name": "Spruked Admin",
        "phone": "555-21010",
        "address_line1": "21010 CRM Way",
        "city": "Austin",
        "state": "TX",
        "postal_code": "78701",
        "country": "US",
        "business_name": "Spruked",
    }


def test_signup_creates_first_admin_spruked_project_and_cali_crm_import(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)

    response = client.post("/api/auth/signup", json=signup_payload())

    assert response.status_code == 200, response.text
    customer = response.json()["customer"]
    assert customer["is_admin"] is True

    with main.SessionLocal() as db:
        project = db.query(main.Project).filter(main.Project.customer_id == int(customer["id"])).first()
        assert project.domain == "spruked.com"
        assert project.name == "Spruked"

    imports = list((tmp_path / "vault_system" / "integrations" / "cali_crm" / "imports" / "pending").glob("*.json"))
    assert len(imports) == 1
    assert "orb_weaver_signup_customer" in imports[0].name


def test_later_signup_gets_spruked_project_without_admin(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    assert client.post("/api/auth/signup", json=signup_payload("first@example.com")).status_code == 200

    response = client.post("/api/auth/signup", json=signup_payload("second@example.com"))

    assert response.status_code == 200, response.text
    customer = response.json()["customer"]
    assert customer["is_admin"] is False
    with main.SessionLocal() as db:
        project = db.query(main.Project).filter(main.Project.customer_id == int(customer["id"])).first()
        assert project.domain == "spruked.com"
