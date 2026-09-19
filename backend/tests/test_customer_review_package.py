import hashlib
import importlib
import io
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ORB_WEAVER_VAULT_ROOT", str(tmp_path / "vault_system"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'customer_review_package.db'}")
    monkeypatch.setenv("LOCAL_LLM_URL", "")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")
    monkeypatch.setenv("CALI_CRM_SYNC_ON_SIGNUP", "false")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "")
    backend_path = str((Path.cwd() / "backend").resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    for module_name in tuple(sys.modules):
        if module_name == "main" or module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)
    main = importlib.import_module("main")
    package = importlib.import_module("app.routers.customer_review_package")
    return main, package, TestClient(main.app)


def signup(client, email):
    response = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "ReviewPackage!2026",
            "full_name": "Review Package Customer",
            "business_name": "Review Package Co",
            "country": "US",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    return payload["customer"], {"Authorization": f"Bearer {payload['token']}"}


def create_project(client, headers, domain):
    response = client.post(
        "/api/projects",
        headers=headers,
        json={"name": domain.split(".")[0].title(), "domain": domain},
    )
    assert response.status_code == 200, response.text
    return response.json()


def grant_review_entitlement(
    main,
    customer_id,
    project_id,
    *,
    sku="OW-FULL-REVIEW-PACKAGE-1",
    price_cents=4900,
    order_currency="usd",
    line_currency="usd",
    quantity=1,
    verified=True,
    active=True,
):
    tier = "package_1" if sku == "OW-FULL-REVIEW-PACKAGE-1" else "package_2"
    with main.SessionLocal() as db:
        build_order = main.OrbsBuildOrder(
            project_id=int(project_id),
            customer_id=int(customer_id),
            current_stage="verified_payment" if verified else "checkout",
            stage_status="ready",
            version=1,
            package_sku=sku,
            package_tier=tier,
            payment_status="verified" if verified else "not_started",
            final_order={
                "sku": sku,
                "name": "Full Review Package",
                "currency": order_currency,
                "unit_amount_cents": price_cents,
                "total_amount_cents": price_cents * quantity,
            },
        )
        db.add(build_order)
        db.flush()
        checkout = main.CheckoutOrder(
            customer_id=int(customer_id),
            project_id=int(project_id),
            build_order_id=build_order.id,
            provider="stripe",
            status="paid" if verified else "checkout_created",
            amount_cents=price_cents * quantity,
            currency=order_currency,
            line_items=[{
                "sku": sku,
                "name": "Full Review Package",
                "unit_amount_cents": price_cents,
                "currency": line_currency,
                "quantity": quantity,
            }],
            payment_verified_at=datetime.utcnow() if verified else None,
        )
        db.add(checkout)
        db.flush()
        build_order.checkout_order_id = checkout.id
        grant = main.OrbsEntitlement(
            build_order_id=build_order.id,
            project_id=int(project_id),
            customer_id=int(customer_id),
            checkout_order_id=checkout.id,
            package_sku=sku,
            package_tier=tier,
            status="active" if active else "revoked",
        )
        db.add(grant)
        db.commit()
        return checkout.id


def add_generic_verified_order(main, customer_id, *, sku, price_cents):
    with main.SessionLocal() as db:
        db.add(main.CheckoutOrder(
            customer_id=int(customer_id),
            project_id=None,
            build_order_id=None,
            provider="stripe",
            status="paid",
            amount_cents=price_cents,
            currency="usd",
            line_items=[{
                "sku": sku,
                "name": "Generic cart item",
                "unit_amount_cents": price_cents,
                "currency": "usd",
                "quantity": 1,
            }],
            payment_verified_at=datetime.utcnow(),
        ))
        db.commit()


def add_completed_crawl(main, project_id, *, with_audit=True, url="https://review.example.test/"):
    with main.SessionLocal() as db:
        crawl = main.CrawlJob(
            project_id=int(project_id),
            status="completed",
            pages_crawled=1,
            pages_found=1,
            errors_count=0,
            config={},
        )
        db.add(crawl)
        db.flush()
        db.add(main.CrawledPage(
            crawl_job_id=crawl.id,
            url=url,
            title="Review Page",
            h1="Review",
            status_code=200,
            word_count=100,
        ))
        if with_audit:
            db.add(main.AuditReport(
                project_id=int(project_id),
                crawl_job_id=crawl.id,
                overall_score=92,
                issues_found=1,
                warnings_found=0,
                report_data={
                    "summary": {"total_issues": 1, "critical_count": 0, "warning_count": 0},
                    "scores": {"technical": 92},
                    "issues": {
                        "info": [{
                            "severity": "info",
                            "category": "content",
                            "title": "Example finding",
                            "description": "Example evidence",
                            "recommendation": "Keep monitoring",
                            "impact_score": 1,
                            "affected_urls": [url],
                        }]
                    },
                },
            ))
        db.commit()
        return crawl.id


def test_canonical_line_item_requires_sku_usd_price_and_positive_quantity(tmp_path, monkeypatch):
    _main, package, _client = load_app(tmp_path, monkeypatch)
    valid = {
        "sku": "OW-FULL-REVIEW-PACKAGE-1",
        "unit_amount_cents": 4900,
        "currency": "usd",
        "quantity": 1,
    }
    assert package._line_item_paid_tier(valid)["tier"] == "package_1"
    assert package._line_item_paid_tier({**valid, "sku": "orb-weaver-starter-audit"}) is None
    assert package._line_item_paid_tier({**valid, "currency": "eur"}) is None
    assert package._line_item_paid_tier({**valid, "unit_amount_cents": 9900}) is None
    assert package._line_item_paid_tier({**valid, "quantity": 0}) is None
    without_quantity = dict(valid)
    without_quantity.pop("quantity")
    assert package._line_item_paid_tier(without_quantity)["quantity"] == 1


def test_generic_cart_order_cannot_unlock_project_package_and_ownership_isolated(tmp_path, monkeypatch):
    main, _package, client = load_app(tmp_path, monkeypatch)
    owner, owner_headers = signup(client, "review-owner@example.com")
    other, other_headers = signup(client, "review-other@example.com")
    project = create_project(client, owner_headers, "review-owner.example.test")

    add_generic_verified_order(
        main,
        owner["id"],
        sku="OW-FULL-REVIEW-PACKAGE-1",
        price_cents=4900,
    )
    status = client.get(f"/api/projects/{project['id']}/customer-review-package", headers=owner_headers)
    assert status.status_code == 200, status.text
    assert status.json()["eligible"] is False

    wrong_owner = client.get(f"/api/projects/{project['id']}/customer-review-package", headers=other_headers)
    assert wrong_owner.status_code == 404
    assert other["id"] != owner["id"]


def test_entitlement_rejects_wrong_currency_and_unverified_payment(tmp_path, monkeypatch):
    main, _package, client = load_app(tmp_path, monkeypatch)
    customer, headers = signup(client, "review-currency@example.com")
    project = create_project(client, headers, "review-currency.example.test")

    grant_review_entitlement(
        main,
        customer["id"],
        project["id"],
        order_currency="eur",
        line_currency="eur",
    )
    response = client.get(f"/api/projects/{project['id']}/customer-review-package", headers=headers)
    assert response.status_code == 200
    assert response.json()["eligible"] is False

    with main.SessionLocal() as db:
        db.query(main.OrbsEntitlement).delete()
        db.query(main.CheckoutOrder).delete()
        db.query(main.OrbsBuildOrder).delete()
        db.commit()
    grant_review_entitlement(main, customer["id"], project["id"], verified=False)
    response = client.get(f"/api/projects/{project['id']}/customer-review-package", headers=headers)
    assert response.json()["eligible"] is False


def test_latest_completed_crawl_requires_its_own_audit(tmp_path, monkeypatch):
    main, _package, client = load_app(tmp_path, monkeypatch)
    customer, headers = signup(client, "review-lineage@example.com")
    project = create_project(client, headers, "review-lineage.example.test")
    grant_review_entitlement(main, customer["id"], project["id"])

    old_crawl_id = add_completed_crawl(main, project["id"], with_audit=True, url="https://review-lineage.example.test/old")
    new_crawl_id = add_completed_crawl(main, project["id"], with_audit=False, url="https://review-lineage.example.test/new")
    assert new_crawl_id > old_crawl_id

    response = client.get(f"/api/projects/{project['id']}/customer-review-package", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["eligible"] is True
    assert payload["ready"] is False
    assert payload["reason"] == "completed_audit_required"
    assert payload["crawl_id"] == str(new_crawl_id)


def test_successful_download_has_exact_files_hashes_and_reuses_cached_package(tmp_path, monkeypatch):
    main, package, client = load_app(tmp_path, monkeypatch)
    customer, headers = signup(client, "review-ready@example.com")
    project = create_project(client, headers, "review-ready.example.test")
    grant_review_entitlement(main, customer["id"], project["id"])
    crawl_id = add_completed_crawl(main, project["id"], with_audit=True, url="https://review-ready.example.test/")

    first = client.get(f"/api/projects/{project['id']}/customer-review-package", headers=headers)
    assert first.status_code == 200, first.text
    first_payload = first.json()
    assert first_payload["eligible"] is True
    assert first_payload["ready"] is True
    assert first_payload["cached"] is False
    assert first_payload["crawl_id"] == str(crawl_id)

    second = client.get(f"/api/projects/{project['id']}/customer-review-package", headers=headers)
    assert second.status_code == 200, second.text
    assert second.json()["cached"] is True

    download = client.get(f"/api/projects/{project['id']}/customer-review-package/download", headers=headers)
    assert download.status_code == 200, download.text
    assert download.headers["content-type"].startswith("application/zip")

    with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
        assert set(archive.namelist()) == set(package.PACKAGE_FILES)
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["source"]["crawl_id"] == str(crawl_id)
        assert manifest["entitlement"]["sku"] == "OW-FULL-REVIEW-PACKAGE-1"
        manifest_names = {entry["name"] for entry in manifest["files"]}
        assert manifest_names == set(package.PACKAGE_FILES) - {"manifest.json"}
        for entry in manifest["files"]:
            payload = archive.read(entry["name"])
            assert hashlib.sha256(payload).hexdigest() == entry["sha256"]
            assert len(payload) == entry["bytes"]


def test_router_preserves_pointer_lidar_urls_and_mounts_review_package_api(tmp_path, monkeypatch):
    _main, _package, _client = load_app(tmp_path, monkeypatch)
    from app.routers.orb_telemetry import router

    paths = {getattr(route, "path", "") for route in router.routes}
    assert "/ws/orb-pointer" in paths
    assert "/ws/lidar-2d-mapping" in paths
    assert "/api/projects/{project_id}/customer-review-package" in paths
    assert "/api/projects/{project_id}/customer-review-package/download" in paths
