import importlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def load_app(tmp_path, monkeypatch):
    vault_root = tmp_path / "vault_system"
    context_root = vault_root / "clients" / "campaign.orbweaver.spruked.com" / "website_orb_context"
    context_root.mkdir(parents=True)
    (context_root / "latest_context.json").write_text(
        json.dumps({"schema": "orb_weaver.site_world.v1", "site_name": "Campaign"}),
        encoding="utf-8",
    )
    (context_root / "pointer_plot_map.json").write_text(
        json.dumps(
            {
                "schema": "orb_weaver.pointer_plot_map.v1",
                "record_count": 1,
                "records": [
                    {
                        "target_id": "start",
                        "confidence": 0.95,
                        "confidence_class": "STABLE",
                        "runtime_policy": {"may_point": True},
                    }
                ],
                "by_page": {"/": ["start"]},
                "quality": {
                    "status": "POINTER_RECOVERY_REQUIRED",
                    "recovery_required": True,
                    "stable_count": 1,
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ORB_WEAVER_VAULT_ROOT", str(vault_root))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'orb_loader_test.db'}")
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


def test_bootstrap_blocks_unverified_pointer_context(tmp_path, monkeypatch):
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
    assert payload["status"] == "awaiting_scan"
    assert payload["site"]["domain"] == "demo.openai.chatgpt.site"
    assert payload["site"]["context_domain"] == "campaign.orbweaver.spruked.com"
    assert payload["pointer_map"]["record_count"] > 0
    assert payload["pointer_map"]["quality"]["status"] == "POINTER_RECOVERY_REQUIRED"
    assert payload["pointer_guidance"]["status"] == "NOT_STARTED"
    assert payload["pointer_guidance"]["safe_pointer_count"] == 1
    assert payload["deployment_preflight"] == {
        "passed": False,
        "blockers": ["POINTER_RECOVERY_REQUIRED", "RUNTIME_GUIDANCE_NOT_PROVEN"],
    }
    assert payload["orb_identity"]["skin_id"] == "orb_factory_default_v1"
    assert payload["orb_identity"]["asset_path"] == "/orb-skins/tuxorb.png"
    assert payload["orb_identity"]["asset_sha256"] == "f447043b007e9aba07c0c67e3b5749751f8db327b21b09f1a763eca359e73ca5"
    assert payload["orb_identity"]["owner_editable"] is False
    assert payload["orb_identity"]["immutable_default"] is True
    assert payload["orb_identity"]["fallback_enabled"] is True
    assert payload["page_capsule"]["current_url"] == "https://demo.openai.chatgpt.site/"
    assert payload["page_capsule"]["context_domain"] == "campaign.orbweaver.spruked.com"
    assert payload["observed_page"]["visible_controls"][0]["text"] == "Start"
    assert payload["installation"]["pointer_policy_enforced"] is True


def test_runtime_pointer_map_response_includes_project_and_crawl_provenance(tmp_path, monkeypatch):
    main, client = load_app(tmp_path, monkeypatch)
    with main.SessionLocal() as db:
        project = main.Project(name="Campaign", domain="campaign.orbweaver.spruked.com", customer_id=1)
        db.add(project)
        db.flush()
        crawl = main.CrawlJob(project_id=project.id, status="completed", pages_crawled=16, pages_found=25)
        db.add(crawl)
        db.commit()
        project_id = project.id
        crawl_id = crawl.id

    response = client.get("/api/orb/pointer-map?domain=campaign.orbweaver.spruked.com")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["project_id"] == str(project_id)
    assert payload["source_crawl_job_id"] == str(crawl_id)
    assert payload["domain"] == "campaign.orbweaver.spruked.com"


def test_uncertain_pointer_summary_blocks_runtime_guidance(tmp_path, monkeypatch):
    main, _client = load_app(tmp_path, monkeypatch)

    class Page:
        url = "https://campaign.orbweaver.spruked.com/"
        semantic_analysis = {
            "pointer_plot_records": [
                {
                    "target_id": f"target-{index}",
                    "page_route": "https://campaign.orbweaver.spruked.com/",
                    "semantic_locator": "a[href='/website-orb']",
                    "confidence_class": "UNCERTAIN",
                    "runtime_policy": {"may_point": False},
                }
                for index in range(12)
            ]
        }

    summary = main._pointer_summary_with_execution(
        main._pointer_summary_from_pages([Page()]),
        {"scan_stage_execution": {
            "pointer_mapping": {"status": "COMPLETE"},
            "pointer_verification": {"status": "COMPLETE"},
            "pointer_recovery": {"status": "BLOCKED"},
            "runtime_guidance": {"status": "BLOCKED", "output_count": 0},
        }},
    )
    assert summary["extraction_status"] == "COMPLETE"
    assert summary["status"] == "BLOCKED"
    assert summary["runtime_guidance_status"] == "BLOCKED"
    assert summary["pointer_recovery_status"] == "BLOCKED"
    assert summary["guidance_eligible_count"] == 0
    assert summary["quality"]["status"] == "POINTER_RECOVERY_REQUIRED"


def test_pointer_summary_uses_verified_quality_after_owner_review(tmp_path, monkeypatch):
    main, _client = load_app(tmp_path, monkeypatch)
    summary = main._pointer_summary_with_execution(
        {"record_count": 87, "quality": {"recovery_required": True}},
        {
            "verified_pointer_quality": {
                "status": "POINTER_READY",
                "recovery_required": False,
                "record_count": 10,
                "excluded_count": 77,
            },
            "scan_stage_execution": {
                "runtime_guidance": {"status": "COMPLETE", "output_count": 10},
            },
        },
    )

    assert summary["runtime_guidance_status"] == "COMPLETE"
    assert summary["guidance_eligible_count"] == 10
    assert summary["recovery_required"] is False
    assert summary["quality"]["status"] == "POINTER_READY"


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


def test_site_world_route_hint_resolves_without_model_invention(tmp_path, monkeypatch):
    main, _client = load_app(tmp_path, monkeypatch)
    context = {
        "site_name": "Vite",
        "domain": "vite.dev",
        "route_hints": {
            "Getting Started | Vite": "/guide",
            "Configuring Vite | Vite": "/config",
        },
    }

    result = main._lookup_site_route_hint(context, "Where does the Vite guide explain project configuration?")

    assert result["spoken_output"] == "You'll find Configuring Vite at /config."
    assert result["suggested_route"] == "/config"
    assert result["navigation"]["status"] == "verified"
    assert main._clean_spoken_output("Read [the guide](https://vite.dev/guide) **here**.") == "Read the guide here."


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


def test_runtime_blocks_stale_signup_route_suggestion(tmp_path, monkeypatch):
    main, _client = load_app(tmp_path, monkeypatch)
    website_context = {
        "domain": "campaign.orbweaver.spruked.com",
        "route_hints": {"login": "/login"},
        "visitor_tools": [
            {
                "id": "signup_guidance",
                "keywords": ["signup", "sign up", "create account"],
                "spoken_output": "Create an account from the signup page.",
                "suggested_route": "/signup",
            }
        ],
        "authority_flow": {"pages": [{"url": "https://campaign.orbweaver.spruked.com/login"}]},
    }

    result = main._lookup_domain_runtime_tool(website_context, "show me how to sign up for an account")

    assert result["suggested_route"] is None
    assert result["navigation"]["status"] == "blocked"
    assert result["navigation"]["route"] == "/signup"
    assert "will not move" in result["spoken_output"]


def test_runtime_allows_account_signup_guidance_to_existing_login_route(tmp_path, monkeypatch):
    main, _client = load_app(tmp_path, monkeypatch)
    website_context = {
        "domain": "campaign.orbweaver.spruked.com",
        "route_hints": {"login": "/login"},
        "visitor_tools": [
            {
                "id": "signup_guidance",
                "keywords": ["signup", "sign up", "create account", "account"],
                "spoken_output": "Create or log into an account from the login page.",
                "suggested_route": "/login",
            }
        ],
        "authority_flow": {"pages": [{"url": "https://campaign.orbweaver.spruked.com/login"}]},
    }

    result = main._lookup_domain_runtime_tool(website_context, "show me how to sign up for an account")

    assert result["suggested_route"] == "/login"
    assert result["navigation"]["status"] == "verified"
    assert result["navigation"]["may_navigate"] is True


def test_website_orb_text_response_includes_cco_runtime_trace(tmp_path, monkeypatch):
    _main, client = load_app(tmp_path, monkeypatch)
    context_path = (
        tmp_path
        / "vault_system"
        / "clients"
        / "campaign.orbweaver.spruked.com"
        / "website_orb_context"
        / "latest_context.json"
    )
    context_path.write_text(
        json.dumps(
            {
                "schema": "orb_weaver.site_world.v1",
                "site_name": "Campaign",
                "domain": "campaign.orbweaver.spruked.com",
                "site_summary": "A campaign site for Orb Weaver.",
                "route_hints": {"start": "/"},
                "authority_flow": {"pages": [{"url": "https://campaign.orbweaver.spruked.com/"}]},
                "visitor_tools": [
                    {
                        "id": "start_guidance",
                        "keywords": ["start", "begin"],
                        "spoken_output": "Use the Start control on this page.",
                        "suggested_route": "/",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/api/orb/website-text",
        headers={"Origin": "https://demo.openai.chatgpt.site"},
        json={
            "transcript": "How do I start?",
            "synthesize_tts": False,
            "target_url": "https://demo.openai.chatgpt.site/",
            "site_id": "orb-weaver-campaign",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["answer_state"] == "known"
    assert payload["learning_record_id"]
    trace = payload["cco_trace"]
    assert trace["schema"] == "orb_weaver.cco_runtime_trace.v1"
    assert trace["short_name"] == "CCO"
    assert trace["site_id"] == "orb-weaver-campaign"
    assert trace["domain"] == "campaign.orbweaver.spruked.com"
    assert trace["selected_strategy"] == "vault_compile"
    assert trace["task_profile"]["intent"]
    assert trace["evidence_package"]["context_tokens"] >= 0
    assert "retrieved.start_guidance" in trace["evidence_package"]["retrieved_fact_ids"]
    assert trace["correspondence_result"]["answer_state"] == "known"
    assert trace["correspondence_result"]["status"] == "supported"
    assert trace["articulation"]["llm_source"] == "orb-runtime-context"
    assert trace["write_back"]["posteriori_recorded"] is True
    assert trace["write_back"]["learning_record_id"] == payload["learning_record_id"]
