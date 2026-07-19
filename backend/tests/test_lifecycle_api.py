import importlib
import asyncio
import json
import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ORB_WEAVER_VAULT_ROOT", str(tmp_path / "vault_system"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'lifecycle_test.db'}")
    monkeypatch.setenv("LOCAL_LLM_URL", "")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")
    backend_path = str((Path.cwd() / "backend").resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    sys.modules.pop("main", None)
    sys.modules.pop("app.core.config", None)
    sys.modules.pop("app.core.storage", None)
    main = importlib.import_module("main")
    return main, TestClient(main.app)


def signup(client, email):
    response = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "LifecycleTest!2026",
            "full_name": "Lifecycle Test User",
            "phone": "555-0110",
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


def test_lifecycle_jobs_and_review_decisions_are_owner_scoped(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    owner_token = signup(client, "lifecycle-owner@example.com")
    other_token = signup(client, "lifecycle-other@example.com")
    project_response = client.post(
        "/api/projects",
        headers=auth(owner_token),
        json={"name": "Lifecycle", "domain": "example.test"},
    )
    project_id = int(project_response.json()["id"])

    with main.SessionLocal() as db:
        job = main.LifecycleJob(
            project_id=project_id,
            job_type="MAP_CRAWL",
            status="REVIEW_REQUIRED",
            phase="awaiting_map_approval",
        )
        db.add(job)
        db.flush()
        item = main.ReviewItem(
            lifecycle_job_id=job.id,
            severity="critical",
            category="map_approval",
            title="Approve map",
        )
        db.add(item)
        db.commit()
        job_id = job.id
        item_id = item.id

    listed = client.get(f"/api/projects/{project_id}/lifecycle-jobs", headers=auth(owner_token))
    assert listed.status_code == 200
    assert listed.json()[0]["job_type"] == "MAP_CRAWL"
    assert client.get(f"/api/lifecycle-jobs/{job_id}", headers=auth(other_token)).status_code == 404

    decision = client.post(
        f"/api/lifecycle-jobs/{job_id}/review-items/{item_id}/decision",
        headers=auth(owner_token),
        json={"decision": "approve", "notes": "Route inventory reviewed."},
    )
    assert decision.status_code == 200, decision.text
    payload = decision.json()
    assert payload["job"]["status"] == "APPROVED"
    assert payload["review_item"]["signature_hash"]
    assert payload["review_item"]["reviewer"] == "lifecycle-owner@example.com"


def test_owner_pointer_authority_is_signed_and_persisted_in_canonical_vault(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    owner_token = signup(client, "pointer-owner@example.com")
    other_token = signup(client, "pointer-other@example.com")
    project_id = int(client.post(
        "/api/projects",
        headers=auth(owner_token),
        json={"name": "Pointer Authority", "domain": "pointer.test"},
    ).json()["id"])
    pointer = {
        "target_id": "book-consult",
        "page_route": "https://pointer.test/",
        "target_type": "button",
        "meaning": "button: Book consultation",
        "intent_aliases": ["schedule a consult"],
        "direct_aliases": ["book consultation"],
        "topic_aliases": ["meeting"],
        "semantic_locator": "#book-consult",
        "content_fingerprint": "consult-fingerprint",
        "structural_context": {"tag": "button", "parent_locator": "main"},
        "allowed_actions": ["point"],
        "status": "active",
        "confidence": 0.62,
        "confidence_class": "UNCERTAIN",
        "runtime_policy": {"may_point": False},
        "pointer_health": "NEW",
    }
    context_root = main.client_root("pointer.test") / "website_orb_context"
    context_root.mkdir(parents=True, exist_ok=True)
    (context_root / "pointer_plot_map.json").write_text(json.dumps({
        "schema": "orb_weaver.pointer_plot_map.v1",
        "record_count": 1,
        "records": [pointer],
        "by_page": {"https://pointer.test/": ["book-consult"]},
    }), encoding="utf-8")

    with main.SessionLocal() as db:
        job = main.LifecycleJob(
            project_id=project_id,
            job_type="POINTER_RECOVERY",
            status="REVIEW_REQUIRED",
            phase="awaiting_pointer_visual_review",
        )
        db.add(job)
        db.flush()
        db.add(main.ReviewItem(
            lifecycle_job_id=job.id,
            severity="critical",
            category="pointer_recovery_visual_review",
            title="Review unresolved pointers",
            details={"pointers": [pointer]},
        ))
        db.commit()
        job_id = job.id

    denied = client.post(
        f"/api/lifecycle-jobs/{job_id}/pointers/book-consult/authority",
        headers=auth(other_token),
        json={"decision": "approve", "notes": "Not the owner."},
    )
    assert denied.status_code == 404

    response = client.post(
        f"/api/lifecycle-jobs/{job_id}/pointers/book-consult/authority",
        headers=auth(owner_token),
        json={"decision": "approve", "notes": "Verified against the current rendered page."},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["pointer"]["pointer_health"] == "OWNER_VERIFIED"
    assert payload["pointer"]["confidence_class"] == "VERIFIED"
    assert payload["pointer"]["runtime_policy"]["may_point"] is True
    assert payload["pointer"]["runtime_policy"]["may_click"] is False
    assert payload["signature_hash"]

    canonical = json.loads((context_root / "pointer_plot_map.json").read_text(encoding="utf-8"))
    authority = json.loads((context_root / "pointer_authority.json").read_text(encoding="utf-8"))
    assert canonical["records"][0]["pointer_health"] == "OWNER_VERIFIED"
    assert authority["decisions"][0]["target_id"] == "book-consult"
    assert authority["decisions"][0]["signature_hash"] == payload["signature_hash"]


def test_site_scan_requires_an_approved_map(tmp_path, monkeypatch):
    _main, client = load_app(tmp_path, monkeypatch)
    token = signup(client, "lifecycle-dependency@example.com")
    project = client.post(
        "/api/projects",
        headers=auth(token),
        json={"name": "Dependency", "domain": "dependency.test"},
    ).json()
    response = client.post(
        f"/api/projects/{project['id']}/lifecycle-jobs/site-scan",
        headers=auth(token),
        json={},
    )
    assert response.status_code == 409
    assert "approved Map Crawl" in response.json()["detail"]


def test_orb_scan_automatically_queues_exactly_one_pointer_recovery_pass(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    token = signup(client, "pointer-recovery@example.com")
    project_id = int(client.post(
        "/api/projects",
        headers=auth(token),
        json={"name": "Campaign", "domain": "campaign.orbweaver.spruked.com"},
    ).json()["id"])

    uncertain_pointer = {
        "target_id": "hero-cta",
        "page_route": "/",
        "target_type": "button",
        "meaning": "button: Request discussion",
        "semantic_locator": "main button:nth-of-type(1)",
        "content_fingerprint": "hero-cta",
        "confidence": 0.62,
        "confidence_class": "UNCERTAIN",
        "runtime_policy": {"may_point": False},
        "confidence_evidence": {"locator_method": "structural_css"},
        "allowed_actions": ["point"],
    }
    with main.SessionLocal() as db:
        crawl = main.CrawlJob(project_id=project_id, status="completed")
        db.add(crawl)
        db.flush()
        db.add(main.CrawledPage(
            crawl_job_id=crawl.id,
            url="https://campaign.orbweaver.spruked.com/",
            semantic_analysis={"pointer_plot_records": [uncertain_pointer]},
        ))
        site_scan = main.LifecycleJob(
            project_id=project_id,
            job_type="SITE_SCAN",
            status="COMPLETED",
            phase="site_scan_complete",
            result={"crawl_job_id": str(crawl.id)},
        )
        db.add(site_scan)
        db.flush()
        orb_scan = main.LifecycleJob(
            project_id=project_id,
            job_type="ORB_SCAN",
            status="PENDING",
            phase="queued",
            config={"source_job_id": site_scan.id},
        )
        db.add(orb_scan)
        db.commit()
        orb_scan_id = orb_scan.id

    def evidence_root(_domain, run_id):
        root = tmp_path / "evidence" / str(run_id)
        root.mkdir(parents=True, exist_ok=True)
        return root

    scheduled = []

    def capture_task(coroutine):
        scheduled.append(coroutine)
        coroutine.close()
        return None

    monkeypatch.setattr(main, "initialize_evidence_run", evidence_root)
    monkeypatch.setattr(main.asyncio, "create_task", capture_task)
    asyncio.run(main.run_lifecycle_job(orb_scan_id))

    with main.SessionLocal() as db:
        orb_scan = db.get(main.LifecycleJob, orb_scan_id)
        recovery_jobs = db.query(main.LifecycleJob).filter(
            main.LifecycleJob.project_id == project_id,
            main.LifecycleJob.job_type == "POINTER_RECOVERY",
        ).all()
        assert orb_scan.status == "POINTER_RECOVERY_REQUIRED"
        assert orb_scan.result["pointer_quality"]["stable_count"] == 0
        assert len(recovery_jobs) == 1
        assert recovery_jobs[0].status == "PENDING"
        assert recovery_jobs[0].config["routes"] == ["/", "/investor"]
        assert recovery_jobs[0].config["automatic_attempt"] == 1
        assert recovery_jobs[0].config["automatic_attempts_maximum"] == 1
        assert len(scheduled) == 1

    asyncio.run(main.run_lifecycle_job(orb_scan_id))
    with main.SessionLocal() as db:
        assert db.query(main.LifecycleJob).filter(
            main.LifecycleJob.project_id == project_id,
            main.LifecycleJob.job_type == "POINTER_RECOVERY",
        ).count() == 1


def test_evidence_manifest_detects_tampering_and_snapshots_absolute_sqlite(tmp_path, monkeypatch):
    backend_path = str((Path.cwd() / "backend").resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from app.lifecycle import evidence as evidence_module
    from app.lifecycle.evidence import (
        finalize_evidence_run,
        initialize_evidence_run,
        snapshot_sqlite_database,
        verify_evidence_run,
        write_json_artifact,
    )

    monkeypatch.setattr(evidence_module, "client_root", lambda _domain: tmp_path / "vault" / "clients" / "example.test")
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO evidence(value) VALUES ('preserved')")

    root = initialize_evidence_run("example.test", "run-1")
    write_json_artifact(root, "baseline/map/map.json", {"routes": ["/"]})
    snapshot = snapshot_sqlite_database(f"sqlite:///{source}", root)
    assert snapshot and snapshot.is_file()
    manifest = finalize_evidence_run(
        root,
        run_id="run-1",
        project_id="project-1",
        domain="example.test",
        job_type="MAP_CRAWL",
        status="COMPLETED",
        scan_contract={"max_pages": 1},
    )
    assert manifest["manifest_hash"]
    assert verify_evidence_run(root)["valid"] is True

    (root / "baseline/map/map.json").write_text('{"routes": []}\n', encoding="utf-8")
    assert verify_evidence_run(root)["valid"] is False
