import hashlib
import hmac
import importlib
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ORB_WEAVER_VAULT_ROOT", str(tmp_path / "vault_system"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'governor.db'}")
    monkeypatch.setenv("LOCAL_LLM_URL", "")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")
    monkeypatch.setenv("CALI_CRM_SYNC_ON_SIGNUP", "false")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_governor_test")
    backend_path = str((Path.cwd() / "backend").resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    for module_name in ("main", "app.orbs_governor", "app.core.config", "app.core.storage"):
        sys.modules.pop(module_name, None)
    main = importlib.import_module("main")
    return main, TestClient(main.app)


@pytest.fixture
def system(tmp_path, monkeypatch):
    return load_app(tmp_path, monkeypatch)


def signup(client, email):
    response = client.post("/api/auth/signup", json={
        "email": email,
        "password": "Governor!2026",
        "full_name": "Governor Customer",
        "phone": "555-0100",
        "address_line1": "1 Evidence Way",
        "city": "Austin",
        "state": "TX",
        "postal_code": "78701",
        "country": "US",
        "business_name": "Evidence Co",
    })
    assert response.status_code == 200, response.text
    body = response.json()
    return body["customer"], {"Authorization": f"Bearer {body['token']}"}


def create_project(client, headers, domain):
    response = client.post("/api/projects", headers=headers, json={"name": domain.split(".")[0].title(), "domain": domain})
    assert response.status_code == 200, response.text
    return response.json()


def write_preflight(main, project):
    target = main.client_root(project.domain) / "website_orb_context" / "site_preflight_report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"pages_scanned": 3, "generated_at": "2026-07-20T12:00:00Z", "warnings": []}), encoding="utf-8")


def complete_technical_evidence(main, project_id):
    with main.SessionLocal() as db:
        project = db.get(main.Project, int(project_id))
        write_preflight(main, project)
        crawl = main.CrawlJob(project_id=project.id, status="completed", pages_crawled=12, pages_found=12, config={})
        db.add(crawl)
        db.flush()
        db.add(main.AuditReport(
            project_id=project.id,
            crawl_job_id=crawl.id,
            overall_score=82,
            report_data={"summary": {"critical_count": 0}, "pointer_summary": {"stable": 8}},
        ))
        db.commit()


def action_payload(snapshot, action, inputs=None, confirmed=False):
    payload = {
        "project_id": snapshot["project_id"],
        "build_order_id": snapshot.get("build_order_id"),
        "action": action,
        "expected_stage": snapshot["current_stage"],
        "snapshot_version": snapshot["snapshot_version"],
        "inputs": inputs or {},
    }
    if confirmed:
        payload["confirmation_evidence"] = {
            "confirmed": True,
            "project_id": snapshot["project_id"],
            "action_name": action,
            "snapshot_version": snapshot["snapshot_version"],
            "confirmed_at": "2026-07-20T12:00:00Z",
            "method": "explicit_yes",
            "statement_hash": "evidence",
        }
    return payload


def submit(client, headers, snapshot, action, *, inputs=None, confirmed=False, key=None):
    return client.post(
        f"/api/projects/{snapshot['project_id']}/orbs-stage/actions",
        headers={**headers, "Idempotency-Key": key or f"key-{action}-{snapshot['snapshot_version']}"},
        json=action_payload(snapshot, action, inputs, confirmed),
    )


def test_technical_gates_expose_next_workflow_action_and_safe_welcome_navigation(system):
    main, client = system
    _customer, headers = signup(client, "gates@example.com")
    project = create_project(client, headers, "gates.example.com")

    snapshot = client.get(f"/api/projects/{project['id']}/orbs-stage", headers=headers).json()
    assert snapshot["current_stage"] == "preflight"
    assert [item["name"] for item in snapshot["allowed_actions"]] == [
        "run_preflight",
        "explore_orbs_packages",
        "open_dashboard",
        "visit_orb_marketplace",
    ]
    assert snapshot["next_recommended_action"] == "run_preflight"
    assert all(item["destination_verified"] for item in snapshot["allowed_actions"])

    with main.SessionLocal() as db:
        write_preflight(main, db.get(main.Project, int(project["id"])))
    snapshot = client.get(f"/api/projects/{project['id']}/orbs-stage", headers=headers).json()
    assert snapshot["current_stage"] == "crawl"
    assert [item["name"] for item in snapshot["allowed_actions"]] == ["run_crawl"]

    with main.SessionLocal() as db:
        crawl = main.CrawlJob(project_id=int(project["id"]), status="completed", pages_crawled=5, config={})
        db.add(crawl)
        db.commit()
    snapshot = client.get(f"/api/projects/{project['id']}/orbs-stage", headers=headers).json()
    assert snapshot["current_stage"] == "final_audit"
    assert [item["name"] for item in snapshot["allowed_actions"]] == ["run_final_audit"]

    with main.SessionLocal() as db:
        crawl = db.query(main.CrawlJob).filter(main.CrawlJob.project_id == int(project["id"])).first()
        db.add(main.AuditReport(project_id=int(project["id"]), crawl_job_id=crawl.id, overall_score=80, report_data={"summary": {}}))
        db.commit()
    snapshot = client.get(f"/api/projects/{project['id']}/orbs-stage", headers=headers).json()
    assert snapshot["current_stage"] == "orbs"
    assert [item["name"] for item in snapshot["allowed_actions"]] == ["review_orbs_integration"]


def test_stale_illegal_idempotent_and_cross_customer_actions_are_rejected(system):
    main, client = system
    _customer, headers = signup(client, "owner@example.com")
    project = create_project(client, headers, "owner.example.com")
    complete_technical_evidence(main, project["id"])
    snapshot = client.get(f"/api/projects/{project['id']}/orbs-stage", headers=headers).json()

    illegal = submit(client, headers, snapshot, "open_checkout", key="illegal")
    assert illegal.status_code == 409
    assert illegal.json()["code"] == "action_not_allowed"

    first = submit(client, headers, snapshot, "review_orbs_integration", key="same-action")
    assert first.status_code == 200
    assert first.json()["current_stage"] == "package_presentation_and_recommendation"
    repeated = submit(client, headers, snapshot, "review_orbs_integration", key="same-action")
    assert repeated.status_code == 200
    assert repeated.json() == first.json()
    conflict = submit(client, headers, first.json(), "start_final_closer_questionnaire", key="same-action")
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"

    stale = submit(client, headers, snapshot, "review_orbs_integration", key="stale-action")
    assert stale.status_code == 409
    assert stale.json()["code"] == "stale_snapshot"

    with main.SessionLocal() as db:
        from app.models.database import OrbsStageEvent
        count = db.query(OrbsStageEvent).filter(
            OrbsStageEvent.project_id == int(project["id"]),
            OrbsStageEvent.event_type == "transition_accepted",
        ).count()
        assert count == 1

    _other, other_headers = signup(client, "other@example.com")
    assert client.get(f"/api/projects/{project['id']}/orbs-stage", headers=other_headers).status_code == 404


def test_authoritative_sales_stages_reach_checkout_without_local_state(system):
    main, client = system
    _customer, headers = signup(client, "journey@example.com")
    project = create_project(client, headers, "journey.example.com")
    complete_technical_evidence(main, project["id"])
    with main.SessionLocal() as db:
        product = main.MarketplaceProduct(
            system_number="OW-ORBS-PREMIUM",
            title="Website ORBS Premium",
            slug="website-orbs-premium",
            description="Managed Website ORBS integration",
            price_cents=45000,
            currency="usd",
            category="website-orbs",
            tier="premium",
            status="active",
            visibility="public",
            approval_status="approved",
        )
        db.add(product)
        db.commit()
        product_id = str(product.id)

    snapshot = client.get(f"/api/projects/{project['id']}/orbs-stage", headers=headers).json()
    response = submit(client, headers, snapshot, "review_orbs_integration", key="journey-orbs")
    snapshot = response.json()
    assert snapshot["current_stage"] == "package_presentation_and_recommendation"

    snapshot = submit(client, headers, snapshot, "start_final_closer_questionnaire", key="journey-closer-start").json()
    snapshot = submit(client, headers, snapshot, "submit_final_closer_questionnaire", inputs={
        "business_outcome": "multi-department visitor guidance",
        "remaining_concern": "governance",
        "timing": "within 30 days",
        "support_expectation": "managed",
        "readiness": "ready to proceed",
    }, key="journey-closer-submit").json()
    recommendation = snapshot["approved_stage_evidence"]["package_recommendation"]
    assert recommendation["marketplace_product_id"] == product_id
    assert recommendation["final_closer_answers_applied"] is True

    snapshot = submit(client, headers, snapshot, "package_commitment", inputs={"marketplace_product_id": product_id}, confirmed=True, key="journey-package").json()
    snapshot = submit(client, headers, snapshot, "submit_build_configuration", inputs={
        "priority_routes": ["/", "/contact"],
        "installation_method": "managed",
        "support_level": "premium",
        "launch_timing": "within 30 days",
        "technical_choices": {"voice": True},
    }, key="journey-build").json()
    snapshot = submit(client, headers, snapshot, "approve_final_order", confirmed=True, key="journey-order").json()
    snapshot = submit(client, headers, snapshot, "submit_signature", inputs={
        "signer_name": "Governor Customer",
        "accepted_terms": True,
        "signature_hash": "signed-test-reference",
    }, confirmed=True, key="journey-signature").json()
    assert snapshot["current_stage"] == "checkout"
    with main.SessionLocal() as db:
        order = db.query(main.OrbsBuildOrder).filter(main.OrbsBuildOrder.project_id == int(project["id"])).one()
        assert order.final_order["recommendation_at_commitment"]["tier"] == "premium"
        assert order.final_order["final_closer_answers"]["support_expectation"] == "managed"


def test_safe_and_consequential_actions_have_independent_confirmation(system):
    main, client = system
    customer, headers = signup(client, "confirm@example.com")
    project = create_project(client, headers, "confirm.example.com")
    complete_technical_evidence(main, project["id"])
    with main.SessionLocal() as db:
        order = main.OrbsBuildOrder(
            project_id=int(project["id"]), customer_id=int(customer["id"]),
            current_stage="final_order_review", stage_status="ready", version=7,
            package_sku="OW-ORBS-1", package_tier="basic",
            final_order={"total_amount_cents": 10000}, build_configuration={"priority_routes": ["/"]},
        )
        db.add(order)
        db.commit()

    snapshot = client.get(f"/api/projects/{project['id']}/orbs-stage", headers=headers).json()
    actions = {item["name"]: item for item in snapshot["allowed_actions"]}
    assert actions["view_final_order"]["confirmation_required"] is False
    assert actions["approve_final_order"]["confirmation_required"] is True
    rejected = submit(client, headers, snapshot, "approve_final_order", key="missing-confirmation")
    assert rejected.status_code == 400
    assert rejected.json()["code"] == "confirmation_required"
    viewed = submit(client, headers, snapshot, "view_final_order", key="safe-view")
    assert viewed.status_code == 200
    assert viewed.json()["current_stage"] == "final_order_review"


def test_redirect_does_not_verify_payment_but_signed_webhook_does(system, monkeypatch):
    main, client = system
    customer, headers = signup(client, "payment@example.com")
    project = create_project(client, headers, "payment.example.com")
    complete_technical_evidence(main, project["id"])
    with main.SessionLocal() as db:
        order = main.OrbsBuildOrder(
            project_id=int(project["id"]), customer_id=int(customer["id"]), current_stage="checkout",
            stage_status="ready", version=11, package_sku="OW-ORBS-BASIC", package_tier="basic",
            final_order={
                "sku": "OW-ORBS-BASIC", "name": "Website ORBS Basic", "currency": "usd",
                "unit_amount_cents": 25000, "total_amount_cents": 25000,
            },
            signature={"signer_name": "Governor Customer", "signed_at": "2026-07-20T12:00:00Z"},
        )
        db.add(order)
        db.commit()

    async def fake_checkout(_order, _customer):
        return {"status": "checkout_created", "provider_order_id": "cs_governor", "checkout_url": "https://checkout.example/redirect"}

    monkeypatch.setattr(main, "_create_stripe_checkout", fake_checkout)
    snapshot = client.get(f"/api/projects/{project['id']}/orbs-stage", headers=headers).json()
    response = submit(client, headers, snapshot, "open_checkout", inputs={"provider": "stripe"}, confirmed=True, key="checkout")
    assert response.status_code == 200, response.text
    assert response.json()["current_stage"] == "checkout"
    with main.SessionLocal() as db:
        order = db.query(main.OrbsBuildOrder).filter(main.OrbsBuildOrder.project_id == int(project["id"])).one()
        checkout = db.get(main.CheckoutOrder, order.checkout_order_id)
        assert checkout.status == "checkout_created"
        assert checkout.payment_verified_at is None
        assert active_entitlement_count(db, order.id) == 0

    event = {
        "id": "evt_governor",
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_governor", "payment_status": "paid", "amount_total": 25000, "currency": "usd",
            "metadata": {"orb_weaver_order_id": str(checkout.id)},
        }},
    }
    raw = json.dumps(event, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(b"whsec_governor_test", timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    webhook = client.post("/api/webhooks/stripe", content=raw, headers={
        "Content-Type": "application/json", "Stripe-Signature": f"t={timestamp},v1={signature}",
    })
    assert webhook.status_code == 200, webhook.text
    assert webhook.json()["stage"] == "verified_payment"
    with main.SessionLocal() as db:
        order = db.query(main.OrbsBuildOrder).filter(main.OrbsBuildOrder.project_id == int(project["id"])).one()
        assert order.payment_status == "verified"
        assert active_entitlement_count(db, order.id) == 1


def active_entitlement_count(db, order_id):
    from app.models.database import OrbsEntitlement
    return db.query(OrbsEntitlement).filter(OrbsEntitlement.build_order_id == order_id, OrbsEntitlement.status == "active").count()


def test_pack_generation_requires_matching_entitlement_and_state_survives_new_session(system):
    main, client = system
    customer, headers = signup(client, "pack@example.com")
    project = create_project(client, headers, "pack.example.com")
    complete_technical_evidence(main, project["id"])
    with main.SessionLocal() as db:
        db.add(main.OrbsBuildOrder(
            project_id=int(project["id"]), customer_id=int(customer["id"]),
            current_stage="package_generation", stage_status="ready", version=15,
            package_sku="OW-ORBS-BASIC", package_tier="basic", payment_status="verified",
        ))
        db.commit()

    denied = client.post(f"/api/projects/{project['id']}/tpc-pack", headers=headers, json={"tier": "basic"})
    assert denied.status_code == 409
    assert denied.json()["code"] == "entitlement_required"

    first = client.get(f"/api/projects/{project['id']}/orbs-stage", headers=headers).json()
    with main.SessionLocal() as fresh_db:
        order = fresh_db.query(main.OrbsBuildOrder).filter(main.OrbsBuildOrder.project_id == int(project["id"])).one()
        assert order.current_stage == first["current_stage"] == "package_generation"
        assert str(order.version) == first["snapshot_version"]

    altered_wording = dict(first)
    altered_wording["allowed_actions"] = [{"name": "mark_website_orbs_live"}]
    authoritative = client.get(f"/api/projects/{project['id']}/orbs-stage", headers=headers).json()
    assert authoritative["current_stage"] == "package_generation"
    assert [item["name"] for item in authoritative["allowed_actions"]] == ["generate_entitled_orbpack"]
