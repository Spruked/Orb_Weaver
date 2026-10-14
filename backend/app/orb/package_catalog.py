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
        "sku": "scan-full-intelligence",
        "name": "Full Website Intelligence Scan",
        "category": "scan",
        "description": "The complete scan foundation for a customer Website ORB and decision-ready reporting.",
        "features": [
            "Full website crawl and scan evidence",
            "SEO audit and prioritized recommendations",
            "Commercial catalog, products, services, and pricing evidence",
            "Dandy promotional/ad-data pack with owner approval boundary",
            "Site World, runtime context, and report files",
            "Spatial mapping and verified pointer readiness assessment",
        ],
        "price_cents": None,
        "currency": "usd",
        "pricing_status": "tbd",
        "purchasable": False,
        "active": True,
        "sort_order": 10,
    },
    {
        "sku": "scan-seo",
        "name": "SEO Scan",
        "category": "scan",
        "description": "A focused search, content, technical, performance, accessibility, and security scan.",
        "features": [
            "Technical SEO and indexability findings",
            "Content, headings, links, metadata, and structured-data review",
            "Performance, accessibility, mobile, and security signals",
            "Prioritized report and exportable recommendations",
        ],
        "price_cents": None,
        "currency": "usd",
        "pricing_status": "tbd",
        "purchasable": False,
        "active": True,
        "sort_order": 20,
    },
    {
        "sku": "scan-dandy-ad-data",
        "name": "Dandy Ad Data Scan",
        "category": "scan",
        "description": "Source-grounded promotional intelligence extracted from public commercial website evidence.",
        "features": [
            "Candidate claims, offers, prices, and proof points",
            "Target-customer signals and promotional angles",
            "Listener URLs and draft 15/30/60-second ad reads",
            "Risk flags and explicit owner-approval workflow",
        ],
        "price_cents": None,
        "currency": "usd",
        "pricing_status": "tbd",
        "purchasable": False,
        "active": True,
        "sort_order": 30,
    },
    {
        "sku": "scan-spatial-mapping",
        "name": "Spatial Mapping Scan",
        "category": "scan",
        "description": "A runtime-readiness scan for spatial movement, verified destinations, and Point/Ping guidance.",
        "features": [
            "Pointer Plot Map and target identity evidence",
            "Live DOM verification and recovery readiness",
            "Route, target, geometry, and protected-area signals",
            "Guidance eligibility and unresolved-target reporting",
        ],
        "price_cents": None,
        "currency": "usd",
        "pricing_status": "tbd",
        "purchasable": False,
        "active": True,
        "sort_order": 40,
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
        "sort_order": 50,
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
        "sort_order": 60,
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
        "sort_order": 70,
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
        merged = []
        for item in packages:
            if not isinstance(item, dict) or not item.get("sku"):
                continue
            merged.append(_normalized_package({**defaults.get(item["sku"], {}), **item}))
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
            for field in ("price_cents", "currency", "purchasable", "active", "sort_order"):
                if field in updates:
                    package[field] = updates[field]
            break
    else:
        raise KeyError(sku)
    return save_catalog(vault_root, packages)
