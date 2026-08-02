import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ORB_WEAVER_VAULT_ROOT", str(tmp_path / "vault_system"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'checkout_providers.db'}")
    monkeypatch.setenv("LOCAL_LLM_URL", "")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")
    monkeypatch.setenv("CALI_CRM_SYNC_ON_SIGNUP", "false")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "")
    monkeypatch.setenv("SQUARE_ACCESS_TOKEN", "")
    monkeypatch.setenv("SQUARE_LOCATION_ID", "")
    backend_path = str((Path.cwd() / "backend").resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    for module_name in tuple(sys.modules):
        if module_name == "main" or module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)
    main = importlib.import_module("main")
    return main, TestClient(main.app)


def signup(client):
    response = client.post(
        "/api/auth/signup",
        json={
            "email": "checkout-square@example.com",
            "password": "Checkout!2026",
            "full_name": "Checkout Customer",
            "phone": "555-0199",
            "address_line1": "10 Cart Way",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
            "country": "US",
            "business_name": "Checkout Co",
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_cart_checkout_accepts_square_provider_and_dispatches(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    headers = signup(client)

    async def fake_square(order, customer):
        assert order.provider == "square"
        assert order.amount_cents == 9900
        assert customer.email == "checkout-square@example.com"
        return {
            "status": "checkout_created",
            "provider_order_id": "square-link-id",
            "checkout_url": "https://squareup.com/pay/example",
        }

    monkeypatch.setattr(main, "_create_square_checkout", fake_square)

    cart = client.post(
        "/api/cart/items",
        headers=headers,
        json={"sku": "orb-weaver-starter-audit", "quantity": 1},
    )
    assert cart.status_code == 200, cart.text

    response = client.post("/api/cart/checkout", headers=headers, json={"provider": "square"})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["provider"] == "square"
    assert payload["status"] == "checkout_created"
    assert payload["provider_order_id"] == "square-link-id"
    assert payload["checkout_url"] == "https://squareup.com/pay/example"


def test_square_checkout_reports_missing_configuration(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    headers = signup(client)
    assert client.post(
        "/api/cart/items",
        headers=headers,
        json={"sku": "orb-weaver-starter-audit", "quantity": 1},
    ).status_code == 200

    response = client.post("/api/cart/checkout", headers=headers, json={"provider": "square"})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["provider"] == "square"
    assert payload["status"] == "provider_not_configured"
    assert "SQUARE_ACCESS_TOKEN" in payload["error"]


def test_cart_checkout_accepts_venmo_provider_and_uses_paypal_venmo_source(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    headers = signup(client)

    async def fake_paypal(order, payment_source="paypal"):
        assert order.provider == "venmo"
        assert payment_source == "venmo"
        return {
            "status": "checkout_created",
            "provider_order_id": "venmo-paypal-order",
            "checkout_url": "https://www.paypal.com/checkoutnow?token=venmo-paypal-order",
        }

    monkeypatch.setattr(main, "_create_paypal_checkout", fake_paypal)

    assert client.post(
        "/api/cart/items",
        headers=headers,
        json={"sku": "orb-weaver-starter-audit", "quantity": 1},
    ).status_code == 200

    response = client.post("/api/cart/checkout", headers=headers, json={"provider": "venmo"})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["provider"] == "venmo"
    assert payload["status"] == "checkout_created"
    assert payload["provider_order_id"] == "venmo-paypal-order"
