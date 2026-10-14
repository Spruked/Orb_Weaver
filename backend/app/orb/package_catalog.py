"""Authoritative customer scan and Website ORB package catalog.

Prices intentionally start as ``None``.  An unpriced package is displayed as
TBD and cannot be added to checkout until an administrator sets a price and
explicitly enables purchase.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.core.storage import require_vault_path


PACKAGE_CATALOG_SCHEMA = "orb_weaver.customer_package_catalog.v1"
CATALOG_FILENAME = "orb_package_catalog.json"


DEFAULT_PACKAGE_CATALOG: list[dict[str, Any]] = [
    {
        "sku": "scan-basic-intelligence",
        "name": "Basic Website Intelligence Scan",
        "category": "scan",
        "tier": "basic",
        "description": "Website discovery, crawl inventory, content, navigation, basic technical health, foundational SEO findings, and baseline spatial mapping.",
        "features": [
            "Website discovery and crawl inventory",
            "Content, navigation, and basic technical health",
            "Foundational SEO findings",
            "Baseline spatial mapping",
            "Downloadable report and evidence files",
        ],
        "price_cents": None,
        "currency": "usd",
        "pricing_status": "tbd",
        "purchasable": False,
        "active": True,
        "sort_order": 10,
    },
    {
        "sku": "scan-enhanced-intelligence",
        "name": "Enhanced Website Intelligence Scan",
        "category": "scan",
        "tier": "enhanced",
        "description": "Everything in Basic, plus deeper semantic analysis, customer journeys, conversion paths, product intelligence, accessibility, responsive layouts, and expanded spatial analysis.",
        "features": [
            "Everything in Basic",
            "Deeper semantic and product intelligence",
            "Customer journeys and conversion paths",
            "Accessibility and responsive-layout analysis",
            "Expanded spatial analysis and downloadable data",
        ],
        "price_cents": None,
        "currency": "usd",
        "pricing_status": "tbd",
        "purchasable": False,
        "active": True,
        "sort_order": 20,
    },
    {
        "sku": "scan-platinum-intelligence",
        "name": "Platinum Website Intelligence Scan",
        "category": "scan",
        "tier": "platinum",
        "description": "Everything in Enhanced, plus the complete applicable website intelligence dataset, advanced spatial mapping, workflow analysis, commercial opportunities, verification evidence, and comprehensive recommendations.",
        "features": [
            "Everything in Enhanced",
            "Complete applicable Master Capability List scan dataset",
            "Advanced spatial mapping and verification evidence",
            "Workflow analysis and commercial opportunities",
            "Comprehensive recommendations and downloadable data",
        ],
        "price_cents": None,
        "currency": "usd",
        "pricing_status": "tbd",
        "purchasable": False,
        "active": True,
        "sort_order": 30,
    },
    {
        "sku": "scan-seo-intelligence",
        "name": "SEO Intelligence Package",
        "category": "specialized",
        "description": "A dedicated technical SEO, search visibility, structured-data, indexing, content-opportunity, keyword, and competitive analysis package where supported.",
        "features": [
            "Technical SEO and indexability findings",
            "Structured data, metadata, and content opportunities",
            "Keyword and competitive analysis where supported",
            "Downloadable SEO report and evidence files",
        ],
        "price_cents": None,
        "currency": "usd",
        "pricing_status": "tbd",
        "purchasable": False,
        "active": True,
        "sort_order": 40,
    },
    {
        "sku": "scan-dandy-advertising",
        "name": "Dandy Advertising Intelligence Package",
        "category": "specialized",
        "description": "Advertising readiness, campaign landing pages, messaging consistency, conversion tracking, creative opportunities, and available connected advertising data.",
        "features": [
            "Site Prominence, Commercial Opportunity, and Campaign Readiness",
            "Traceable claims, offers, proof points, and audience signals",
            "Campaign briefs and Dandy Show production briefs",
            "Draft ad reads, listener URLs, risk flags, and owner approval",
        ],
        "price_cents": None,
        "currency": "usd",
        "pricing_status": "tbd",
        "purchasable": False,
        "active": True,
        "sort_order": 50,
    },
    {
        "sku": "orb-basic-website-visitor",
        "name": "Basic Website Visitor ORB",
        "category": "orb",
        "tier": "basic",
        "description": "A website-native visitor guide built from approved public site evidence and verified visitor pathways.",
        "features": [
            "Voice-first visitor interaction",
            "Site-specific context and approved guidance",
            "Basic verified navigation and Point/Ping targets",
            "Installable Website ORB package",
        ],
        "price_cents": None,
        "currency": "usd",
        "pricing_status": "tbd",
        "purchasable": False,
        "active": True,
        "sort_order": 60,
    },
    {
        "sku": "orb-enhanced-website-intelligence",
        "name": "Enhanced Website Intelligence ORB",
        "category": "orb",
        "tier": "enhanced",
        "description": "A richer installable Website ORB with deeper scan intelligence, spatial guidance, and learning-loop context.",
        "features": [
            "Everything in Basic Website Visitor ORB",
            "Full intelligence scan artifacts and report context",
            "Expanded commercial, SEO, Dandy, and spatial evidence",
            "Learning-loop and verified-outcome runtime context",
        ],
        "price_cents": None,
        "currency": "usd",
        "pricing_status": "tbd",
        "purchasable": False,
        "active": True,
        "sort_order": 70,
    },
    {
        "sku": "orb-platinum-premium-dock-station",
        "name": "Platinum Website ORB w/Premium Dock Station",
        "category": "orb",
        "tier": "platinum",
        "description": "The full Website ORB delivery with Premium Dock Station owner controls and deployment support.",
        "features": [
            "Everything in Enhanced Website Intelligence ORB",
            "Premium Dock Station configuration and owner policy controls",
            "Expanded deployment, maintenance, and verification workflow",
            "Installable ORB and Dock Station release package",
        ],
        "price_cents": None,
        "currency": "usd",
        "pricing_status": "tbd",
        "purchasable": False,
        "active": True,
        "sort_order": 80,
    },
]


def catalog_path(vault_root: Path) -> Path:
    return require_vault_path(Path(vault_root) / "marketing" / CATALOG_FILENAME, "customer package catalog")


def _normalized_package(package: dict[str, Any]) -> dict[str, Any]:
    item = deepcopy(package)
    price = item.get("price_cents")
    item["price_cents"] = int(price) if price is not None else None
    item["currency"] = str(item.get("currency") or "usd").lower()
    item["pricing_status"] = "set" if item["price_cents"] is not None else "tbd"
    item["purchasable"] = bool(item.get("purchasable")) and item["price_cents"] is not None and item["pricing_status"] == "set"
    item["features"] = [str(value) for value in item.get("features") or []]
    item["category"] = str(item.get("category") or "upgrade")
    item["product_group"] = str(item.get("product_group") or item["category"])
    item["included_capabilities"] = [str(value) for value in item.get("included_capabilities") or item["features"]]
    item["entitlement_rules"] = item.get("entitlement_rules") if isinstance(item.get("entitlement_rules"), dict) else {}
    item["fulfillment"] = item.get("fulfillment") if isinstance(item.get("fulfillment"), dict) else {}
    return item


def load_catalog(vault_root: Path) -> list[dict[str, Any]]:
    path = catalog_path(vault_root)
    if not path.is_file():
        return [_normalized_package(item) for item in DEFAULT_PACKAGE_CATALOG]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        packages = payload.get("packages") if isinstance(payload, dict) else None
        if not isinstance(packages, list):
            raise ValueError("catalog packages must be a list")
        defaults = {item["sku"]: item for item in DEFAULT_PACKAGE_CATALOG}
        persisted = {}
        for item in packages:
            if not isinstance(item, dict) or not item.get("sku"):
                continue
            persisted[item["sku"]] = item
        merged = [_normalized_package({**item, **persisted.get(item["sku"], {})}) for item in DEFAULT_PACKAGE_CATALOG]
        known = set(defaults)
        merged.extend(
            _normalized_package(item)
            for sku, item in persisted.items()
            if sku not in known and item.get("category") in {"upgrade", "service"}
        )
        return merged or [_normalized_package(item) for item in DEFAULT_PACKAGE_CATALOG]
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return [_normalized_package(item) for item in DEFAULT_PACKAGE_CATALOG]


def save_catalog(vault_root: Path, packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = catalog_path(vault_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = [_normalized_package(item) for item in packages]
    path.write_text(json.dumps({"schema": PACKAGE_CATALOG_SCHEMA, "packages": normalized}, indent=2) + "\n", encoding="utf-8")
    return normalized


def update_package(vault_root: Path, sku: str, updates: dict[str, Any]) -> list[dict[str, Any]]:
    packages = load_catalog(vault_root)
    for package in packages:
        if package["sku"] == sku:
            for field in ("price_cents", "currency", "purchasable", "active", "sort_order", "features", "included_capabilities", "entitlement_rules", "fulfillment"):
                if field in updates:
                    package[field] = updates[field]
            break
    else:
        raise KeyError(sku)
    return save_catalog(vault_root, packages)
