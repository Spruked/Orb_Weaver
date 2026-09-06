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
    for module_name in tuple(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)
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


def test_orphaned_crawl_is_reconciled_and_history_uses_lightweight_rows(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    token = signup(client, "crawl-lease@example.com")
    project_response = client.post(
        "/api/projects",
        headers=auth(token),
        json={"name": "Lease Test", "domain": "lease.example.test"},
    )
    project_id = int(project_response.json()["id"])

    with main.SessionLocal() as db:
        crawl = main.CrawlJob(
            project_id=project_id,
            status="running",
            start_time=main.datetime.utcnow() - main.timedelta(hours=2),
            heartbeat_at=main.datetime.utcnow() - main.timedelta(hours=2),
            worker_id="dead-worker",
            config={"max_pages": 500},
        )
        db.add(crawl)
        db.flush()
        for index in range(25):
            db.add(main.CrawledPage(crawl_job_id=crawl.id, url=f"https://lease.example.test/{index}"))
        db.commit()

    assert main._reconcile_orphaned_crawl_jobs() == 1

    response = client.get("/api/crawl-jobs", headers=auth(token))
    assert response.status_code == 200
    row = response.json()[0]
    assert row["status"] == "failed"
    assert row["error"] == "Crawl worker was interrupted by a backend restart."
    assert "pages" not in row
    assert "assembly_status" not in row
    assert "pointer_summary" not in row

    workspace = client.get("/api/account/workspace-summary", headers=auth(token))
    assert workspace.status_code == 200
    assert workspace.json()["latest_crawl"]["id"] == row["id"]


def test_combined_dashboard_uses_latest_completed_crawl_for_summary(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    token = signup(client, "combined-dashboard@example.com")
    project_response = client.post(
        "/api/projects",
        headers=auth(token),
        json={"name": "Dashboard", "domain": "dashboard.example.test"},
    )
    assert project_response.status_code == 200, project_response.text
    project_id = int(project_response.json()["id"])

    with main.SessionLocal() as db:
        crawl = main.CrawlJob(
            project_id=project_id,
            status="completed",
            pages_crawled=3,
            pages_found=5,
            config={"stats": {"pages_crawled": 3, "custom_dashboard_marker": 1}},
        )
        db.add(crawl)
        db.commit()

    response = client.get(f"/api/combined/{project_id}/dashboard", headers=auth(token))
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["latest_crawl"]["status"] == "completed"
    assert payload["crawl_summary"]["custom_dashboard_marker"] == 1

    with main.SessionLocal() as db:
        db.add(main.CrawlJob(project_id=project_id, status="running", pages_crawled=1, config={}))
        db.commit()
    payload = client.get(f"/api/combined/{project_id}/dashboard", headers=auth(token)).json()
    assert payload["latest_crawl"]["status"] == "completed"
    assert payload["current_crawl"]["status"] == "running"
    assert payload["current_crawl"]["pages_crawled"] == 1
    assert payload["current_crawl"]["stats"]["lidar_weave"]["status"] == "not_scanned"


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
        crawl = main.CrawlJob(
            project_id=project_id,
            status="completed",
            config={"scan_stage_execution": {}},
        )
        db.add(crawl)
        db.flush()
        job = main.LifecycleJob(
            project_id=project_id,
            job_type="POINTER_RECOVERY",
            status="REVIEW_REQUIRED",
            phase="awaiting_pointer_visual_review",
            result={"crawl_job_id": str(crawl.id)},
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
        crawl_id = crawl.id

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

    with main.SessionLocal() as db:
        baseline = db.get(main.CrawlJob, crawl_id)
        execution = (baseline.config or {})["scan_stage_execution"]
        assert execution["runtime_guidance"]["status"] == "COMPLETE"
        assert execution["runtime_guidance"]["output_count"] == 1
        assert (baseline.config or {})["verified_pointer_quality"]["recovery_required"] is True


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


def test_active_crawl_and_linked_lifecycle_can_be_cancelled_by_owner(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    owner_token = signup(client, "cancel-owner@example.com")
    other_token = signup(client, "cancel-other@example.com")
    project_id = int(client.post(
        "/api/projects",
        headers=auth(owner_token),
        json={"name": "Cancelable", "domain": "cancelable.test"},
    ).json()["id"])

    with main.SessionLocal() as db:
        crawl = main.CrawlJob(project_id=project_id, status="running", pages_crawled=12, pages_found=20)
        db.add(crawl)
        db.flush()
        lifecycle = main.LifecycleJob(
            project_id=project_id,
            job_type="MAP_CRAWL",
            status="RUNNING",
            phase="crawling_pages",
            result={"crawl_job_id": str(crawl.id)},
        )
        db.add(lifecycle)
        db.commit()
        crawl_id = crawl.id
        lifecycle_id = lifecycle.id

    assert client.post(f"/api/crawl-jobs/{crawl_id}/cancel", headers=auth(other_token)).status_code == 404
    response = client.post(f"/api/crawl-jobs/{crawl_id}/cancel", headers=auth(owner_token))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancel_requested"

    with main.SessionLocal() as db:
        assert db.get(main.CrawlJob, crawl_id).status == "cancel_requested"
        assert db.get(main.LifecycleJob, lifecycle_id).status == "CANCEL_REQUESTED"


def test_pending_lifecycle_cancel_is_immediate(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    token = signup(client, "cancel-pending@example.com")
    project_id = int(client.post(
        "/api/projects",
        headers=auth(token),
        json={"name": "Pending Cancel", "domain": "pending-cancel.test"},
    ).json()["id"])
    with main.SessionLocal() as db:
        job = main.LifecycleJob(project_id=project_id, job_type="MAP_CRAWL", status="PENDING", phase="queued")
        db.add(job)
        db.commit()
        job_id = job.id

    response = client.post(f"/api/lifecycle-jobs/{job_id}/cancel", headers=auth(token))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["phase"] == "cancelled_by_user"


def test_site_scan_preserves_completed_phase_and_progress(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    token = signup(client, "site-scan-evidence@example.com")
    project_id = int(client.post(
        "/api/projects",
        headers=auth(token),
        json={"name": "Site Scan Evidence", "domain": "site-scan-evidence.test"},
    ).json()["id"])

    with main.SessionLocal() as db:
        crawl = main.CrawlJob(project_id=project_id, status="completed", pages_crawled=2, pages_found=2)
        db.add(crawl)
        db.flush()
        db.add_all([
            main.CrawledPage(crawl_job_id=crawl.id, url="https://site-scan-evidence.test/"),
            main.CrawledPage(crawl_job_id=crawl.id, url="https://site-scan-evidence.test/about"),
        ])
        map_job = main.LifecycleJob(
            project_id=project_id,
            job_type="MAP_CRAWL",
            status="APPROVED",
            phase="approved",
            result={"crawl_job_id": str(crawl.id)},
        )
        db.add(map_job)
        db.flush()
        site_job = main.LifecycleJob(
            project_id=project_id,
            job_type="SITE_SCAN",
            status="PENDING",
            phase="queued",
            config={"source_job_id": map_job.id},
        )
        db.add(site_job)
        db.commit()
        site_job_id = site_job.id

    asyncio.run(main.run_lifecycle_job(site_job_id))

    with main.SessionLocal() as db:
        completed = db.get(main.LifecycleJob, site_job_id)
        assert completed.status == "COMPLETED"
        assert completed.phase == "site_scan_complete"
        assert completed.progress_current == 2
        assert completed.progress_total == 2


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
        root = tmp_path / "vault_system" / "evidence" / str(run_id)
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
    from app.core import storage

    test_vault = tmp_path / "vault"
    monkeypatch.setattr(storage, "VAULT_ROOT", test_vault)
    monkeypatch.setattr(evidence_module, "client_root", lambda _domain: test_vault / "clients" / "example.test")
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


def test_ordinary_crawl_preserves_owner_approval_and_rejection_everywhere(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.orb.pointer_recovery import promote_owner_verified_pointer, reject_owner_pointer

    main, _client = load_app(tmp_path, monkeypatch)

    def pointer(target_id, locator, meaning):
        return {
            "target_id": target_id,
            "page_route": "/",
            "target_type": "button",
            "meaning": meaning,
            "semantic_locator": locator,
            "content_fingerprint": f"{target_id}-fingerprint",
            "structural_context": {"tag": "button", "parent_locator": "main"},
            "allowed_actions": ["point"],
            "status": "active",
            "confidence": 0.62,
            "confidence_class": "UNCERTAIN",
            "runtime_policy": {"may_point": False},
            "pointer_health": "NEW",
        }

    approved_candidate = pointer("approved-target", "#approved", "button: Approved target")
    rejected_candidate = pointer("rejected-target", "#rejected", "button: Rejected target")

    canonical = promote_owner_verified_pointer(
        {"records": [approved_candidate, rejected_candidate]},
        "approved-target",
        reviewer="owner@example.com",
        signature_hash="signed-approval",
    )
    canonical = reject_owner_pointer(
        canonical,
        "rejected-target",
        reviewer="owner@example.com",
        signature_hash="signed-rejection",
    )

    root = main.client_root("authority.test")
    for directory in (
        "current",
        "history",
        "website_orb_context",
        "crm_context",
        "mail_context",
        "dandy_sponsor_pack",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)

    (root / "website_orb_context" / "pointer_plot_map.json").write_text(
        json.dumps(canonical),
        encoding="utf-8",
    )

    candidate_map = {
        "schema": "orb_weaver.pointer_plot_map.v1",
        "record_count": 2,
        "records": [dict(approved_candidate), dict(rejected_candidate)],
        "by_page": {"/": ["approved-target", "rejected-target"]},
    }
    payload = {
        "schema": "orb_weaver.client_crawl.v1",
        "crawl": {"id": "77", "stats": {}},
        "pointer_plot_map": candidate_map,
        "website_orb_context": {"pointer_plot_map": candidate_map},
    }

    monkeypatch.setattr(main, "_ensure_client_pack", lambda _project: root)
    monkeypatch.setattr(main, "_client_index_path", lambda _project: root / "index.sqlite")
    monkeypatch.setattr(main, "_init_client_index", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main, "_index_pack_meta", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main, "_index_crawl_pack", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main, "_append_jsonl", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main, "_global_intelligence_root", lambda: root)
    monkeypatch.setattr(main, "_global_crawl_pattern", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(main, "_client_crawl_pack", lambda *_args, **_kwargs: payload)

    project = SimpleNamespace(
        id=1,
        domain="authority.test",
        name="Authority Test",
        customer_id=None,
        ga4_property_id=None,
    )
    crawl_job = SimpleNamespace(id=77, config={})
    db = SimpleNamespace(commit=lambda: None)

    main.preserve_client_crawl_intelligence(project, crawl_job, [], db)

    for artifact_path in (
        root / "website_orb_context" / "pointer_plot_map.json",
        root / "website_orb_context" / "latest_context.json",
        root / "current" / "latest_crawl.json",
        root / "history" / "crawl_77.json",
    ):
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        pointer_map = (
            artifact
            if artifact_path.name == "pointer_plot_map.json"
            else artifact.get("pointer_plot_map")
            or artifact["website_orb_context"]["pointer_plot_map"]
        )
        records = {item["target_id"]: item for item in pointer_map["records"]}

        assert records["approved-target"]["pointer_health"] == "OWNER_VERIFIED"
        assert records["approved-target"]["runtime_policy"]["may_point"] is True
        assert records["rejected-target"]["pointer_health"] == "OWNER_REJECTED"
        assert records["rejected-target"]["runtime_policy"]["may_point"] is False
        assert records["rejected-target"]["finding_subreason"] == "owner_rejected_pointer_identity"
