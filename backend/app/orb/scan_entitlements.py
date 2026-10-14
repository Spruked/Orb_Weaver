"""Server-side entitlement planning for scan execution.

The browser may request a scan, but it cannot grant itself expensive stages.
This module resolves only verified, project-bound purchases and turns them into
an immutable execution plan stored with the crawl evidence.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping


PACKAGE_RULES: dict[str, dict[str, Any]] = {
    "scan-basic-intelligence": {
        "capabilities": ["baseline_scan", "foundational_seo", "baseline_spatial"],
        "external_apis": [],
    },
    "scan-enhanced-intelligence": {
        "capabilities": [
            "baseline_scan", "foundational_seo", "baseline_spatial", "semantic_analysis",
            "journey_analysis", "conversion_analysis", "product_intelligence",
            "accessibility_analysis", "responsive_analysis", "expanded_spatial",
        ],
        "external_apis": [],
    },
    "scan-platinum-intelligence": {
        "capabilities": [
            "baseline_scan", "foundational_seo", "baseline_spatial", "semantic_analysis",
            "journey_analysis", "conversion_analysis", "product_intelligence",
            "accessibility_analysis", "responsive_analysis", "expanded_spatial",
            "advanced_spatial", "workflow_analysis", "commercial_opportunities",
            "verification_evidence", "comprehensive_recommendations", "competitor_analysis",
            "ga4_analytics",
        ],
        "external_apis": ["ga4"],
    },
    "scan-seo-intelligence": {
        "capabilities": ["foundational_seo", "seo_intelligence", "competitor_analysis"],
        "external_apis": [],
    },
    "scan-dandy-advertising": {
        "capabilities": ["dandy_promo_pack", "campaign_briefs", "show_production_briefs", "advertising_data"],
        "external_apis": [],
    },
    "orb-basic-website-visitor": {
        "capabilities": ["baseline_scan", "baseline_spatial", "orb_runtime_basic"],
        "external_apis": [],
    },
    "orb-enhanced-website-intelligence": {
        "capabilities": [
            "baseline_scan", "baseline_spatial", "semantic_analysis", "journey_analysis",
            "conversion_analysis", "product_intelligence", "expanded_spatial", "orb_runtime_enhanced",
        ],
        "external_apis": [],
    },
    "orb-platinum-premium-dock-station": {
        "capabilities": [
            "baseline_scan", "baseline_spatial", "semantic_analysis", "journey_analysis",
            "conversion_analysis", "product_intelligence", "accessibility_analysis",
            "responsive_analysis", "expanded_spatial", "advanced_spatial", "workflow_analysis",
            "commercial_opportunities", "verification_evidence", "comprehensive_recommendations",
            "orb_runtime_platinum", "premium_dock_station",
        ],
        "external_apis": [],
    },
}


def package_rules(sku: str, catalog: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Return catalog overrides when present, with safe SKU defaults."""
    rules = dict(PACKAGE_RULES.get(sku, {}))
    for item in catalog:
        if item.get("sku") != sku:
            continue
        configured = item.get("entitlement_rules")
        if isinstance(configured, Mapping):
            rules.update(configured)
        break
    return rules


def build_scan_execution_plan(
    package_skus: Iterable[str],
    catalog: Iterable[Mapping[str, Any]] = (),
    *,
    source: str = "owner_preview",
) -> dict[str, Any]:
    """Merge purchased package rules and fail closed for costly work."""
    skus = sorted({str(sku) for sku in package_skus if str(sku) in PACKAGE_RULES})
    capabilities = {"baseline_scan", "foundational_seo", "baseline_spatial"} if not skus else set()
    external_apis: set[str] = set()
    for sku in skus:
        rules = package_rules(sku, catalog)
        capabilities.update(str(value) for value in rules.get("capabilities", []))
        external_apis.update(str(value) for value in rules.get("external_apis", []))
    return {
        "schema": "orb_weaver.scan_execution_entitlement.v1",
        "source": source,
        "purchased_package_skus": skus,
        "capabilities": sorted(capabilities),
        "external_apis": sorted(external_apis),
        "dandy_allowed": "dandy_promo_pack" in capabilities,
        "competitor_analysis_allowed": "competitor_analysis" in capabilities,
        "ga4_allowed": "ga4" in external_apis or "ga4_analytics" in capabilities,
    }


def capability_allowed(plan: Mapping[str, Any] | None, capability: str) -> bool:
    return capability in set((plan or {}).get("capabilities") or [])

