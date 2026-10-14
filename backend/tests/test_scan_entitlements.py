from app.orb.scan_entitlements import build_scan_execution_plan


def test_owner_preview_fails_closed_for_expensive_stages():
    plan = build_scan_execution_plan([])
    assert plan["source"] == "owner_preview"
    assert plan["dandy_allowed"] is False
    assert plan["competitor_analysis_allowed"] is False
    assert plan["ga4_allowed"] is False


def test_dandy_package_only_unlocks_dandy_work():
    plan = build_scan_execution_plan(["scan-dandy-advertising"])
    assert plan["dandy_allowed"] is True
    assert plan["competitor_analysis_allowed"] is False
    assert plan["ga4_allowed"] is False


def test_platinum_unlocks_external_ga4_and_competitors():
    plan = build_scan_execution_plan(["scan-platinum-intelligence"])
    assert plan["competitor_analysis_allowed"] is True
    assert plan["ga4_allowed"] is True
    assert "ga4" in plan["external_apis"]


def test_catalog_rules_are_overridable_without_client_granting_access():
    plan = build_scan_execution_plan(
        ["scan-dandy-advertising"],
        [{"sku": "scan-dandy-advertising", "entitlement_rules": {"capabilities": ["dandy_promo_pack", "campaign_briefs", "advertising_data", "show_production_briefs"], "external_apis": []}}],
        source="verified_project_purchase",
    )
    assert plan["source"] == "verified_project_purchase"
    assert "show_production_briefs" in plan["capabilities"]
