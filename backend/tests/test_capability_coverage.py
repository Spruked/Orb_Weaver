from app.crawler.capability_coverage import build_capability_coverage


def test_capability_rollup_is_mutually_exclusive_and_reconciles():
    coverage = build_capability_coverage(
        stages={
            "url_discovery": {"status": "COMPLETE"},
            "page_fetch": {"status": "COMPLETE"},
            "javascript_rendering": {"status": "BLOCKED"},
            "pointer_mapping": {"status": "COMPLETE"},
            "relationship_mapping": {"status": "COMPLETE"},
            "knowledge_chunking": {"status": "COMPLETE"},
        },
        stats={"depth_limit_hit": True, "authentication_wall_pages": 1},
        pages=[],
    )

    assert coverage["category_count"] == 22
    assert coverage["item_count"] == 161
    assert sum(coverage["status_counts"].values()) == coverage["category_count"]
    assert coverage["status"] == "partial"
    allowed_states = {"verified", "partial", "blocked", "requires_runtime_verification", "runtime_capability_not_crawl_verified", "not_run", "tracked"}
    assert all(isinstance(category["status"], str) and category["status"] in allowed_states for category in coverage["categories"])
    assert all("/" not in category["status"] for category in coverage["categories"])
    assert all(item["status"] == category["status"] for category in coverage["categories"] for item in category["item_evidence"])


def test_live_test_only_promotes_explicit_runtime_categories():
    coverage = build_capability_coverage(
        stages={},
        stats={},
        pages=[],
        runtime_evidence={"status": "COMPLETE", "verified_categories": ["13_voice_visitor_guidance"]},
    )
    statuses = {category["id"]: category["status"] for category in coverage["categories"]}
    assert statuses["13_voice_visitor_guidance"] == "verified"
    assert statuses["11_vault_intelligence"] == "runtime_capability_not_crawl_verified"
    assert statuses["14_orb_personality_physical_design"] == "runtime_capability_not_crawl_verified"


def test_runtime_evidence_distinguishes_not_run_from_incomplete():
    not_run = build_capability_coverage(stages={}, stats={}, pages=[])
    incomplete = build_capability_coverage(
        stages={},
        stats={},
        pages=[],
        runtime_evidence={"status": "FAILED", "verified_categories": []},
    )
    not_run_category = next(item for item in not_run["categories"] if item["id"] == "11_vault_intelligence")
    incomplete_category = next(item for item in incomplete["categories"] if item["id"] == "11_vault_intelligence")
    assert not_run_category["evidence"]["runtime_evidence_state"] == "not_run"
    assert incomplete_category["evidence"]["runtime_evidence_state"] == "incomplete"
    assert not_run_category["status"] == incomplete_category["status"] == "runtime_capability_not_crawl_verified"
