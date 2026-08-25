"""Broader commercial-offering ontology layered over the deterministic catalog.

The legacy compiler is intentionally preserved for exact Product/Service/schema
facts. This adapter adds non-ecommerce offerings such as SaaS role packages,
AI employees and service headings without inventing prices, SKUs or availability.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Sequence, Tuple


AI_ROLE_RE = re.compile(
    r"\bAI\s+(?:Executive\s+Assistant|Sales\s+Representative|Customer\s+Support\s+Specialist|"
    r"Marketing\s+Associate|Recruiter|Project\s+Manager|Researcher|Employee|Assistant|Agent|Specialist)\b",
    re.I,
)
SERVICE_RE = re.compile(
    r"\b(?:roof(?:ing)?\s+(?:repair|replacement|inspection|installation|maintenance)|"
    r"repair|replacement|inspection|installation|maintenance|implementation|consulting|training|"
    r"managed\s+service|professional\s+service|support\s+service|design\s+service)\b",
    re.I,
)
PLAN_RE = re.compile(r"\b(?:starter|basic|standard|professional|pro|business|enterprise|premium|platinum)\s+(?:plan|package|tier)\b", re.I)
GENERIC_HEADINGS = {
    "services", "our services", "features", "our features", "solutions", "products", "pricing",
    "what we do", "how it works", "use cases", "resources", "about", "contact",
}


def _entry_id(kind: str, name: str, url: str) -> str:
    seed = f"v2|{kind.lower()}|{name.lower()}|{url.lower()}"
    return "catalog_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _headings(page: Any) -> List[str]:
    values: List[str] = []
    for value in [getattr(page, "h1", None), *(getattr(page, "h2_tags", None) or [])]:
        if value:
            values.append(re.sub(r"\s+", " ", str(value)).strip())
    semantic = getattr(page, "semantic_analysis", None) or {}
    for record in semantic.get("pointer_plot_records") or []:
        if not isinstance(record, dict) or record.get("target_type") != "heading":
            continue
        meaning = str(record.get("meaning") or "")
        value = meaning.split(":", 1)[1].strip() if ":" in meaning else meaning.strip()
        if value:
            values.append(value)
    return list(dict.fromkeys(values))


def _candidate_entries(page: Any) -> Iterable[Dict[str, Any]]:
    url = str(getattr(page, "url", "") or "")
    for heading in _headings(page):
        cleaned = heading.strip(" -–—:|")
        if not cleaned or len(cleaned) > 140 or cleaned.lower() in GENERIC_HEADINGS:
            continue

        role = AI_ROLE_RE.search(cleaned)
        if role:
            name = role.group(0)
            yield {
                "catalog_id": _entry_id("SoftwareApplication", name, url),
                "kind": "SoftwareApplication",
                "offering_type": "ai_agent",
                "name": name,
                "description": None,
                "sku": None,
                "gtin": None,
                "brand": None,
                "category": "AI Employee / Agent",
                "url": url,
                "source_page": url,
                "offers": [],
                "availability": None,
                "variants": [],
                "specifications": {},
                "schema_types": [],
                "evidence": ["visible_heading"],
                "confidence": 0.82,
            }
            continue

        if PLAN_RE.search(cleaned):
            yield {
                "catalog_id": _entry_id("Product", cleaned, url),
                "kind": "Product",
                "offering_type": "subscription_plan",
                "name": cleaned,
                "description": None,
                "sku": None,
                "gtin": None,
                "brand": None,
                "category": "Subscription Plan",
                "url": url,
                "source_page": url,
                "offers": [],
                "availability": None,
                "variants": [],
                "specifications": {},
                "schema_types": [],
                "evidence": ["visible_heading"],
                "confidence": 0.76,
            }
            continue

        if SERVICE_RE.search(cleaned):
            yield {
                "catalog_id": _entry_id("Service", cleaned, url),
                "kind": "Service",
                "offering_type": "service",
                "name": cleaned,
                "description": None,
                "sku": None,
                "gtin": None,
                "brand": None,
                "category": "Service",
                "url": url,
                "source_page": url,
                "offers": [],
                "availability": None,
                "variants": [],
                "specifications": {},
                "schema_types": [],
                "evidence": ["visible_heading"],
                "confidence": 0.74,
            }


def _identity(entry: Dict[str, Any]) -> Tuple[str, str]:
    return (str(entry.get("name") or "").strip().lower(), str(entry.get("source_page") or entry.get("url") or "").strip().lower())


def install_catalog_v2(compiler_module) -> None:
    if getattr(compiler_module, "_orb_catalog_v2_installed", False):
        return

    original_compile = compiler_module.compile_commercial_catalog

    def enhanced_compile(pages: Sequence[Any]) -> Dict[str, Any]:
        result = original_compile(pages)
        entries = [dict(item) for item in result.get("entries") or []]
        existing_names = {str(item.get("name") or "").strip().lower() for item in entries}

        for page in pages:
            for candidate in _candidate_entries(page):
                name_key = str(candidate.get("name") or "").strip().lower()
                if not name_key or name_key in existing_names:
                    continue
                entries.append(candidate)
                existing_names.add(name_key)

        # Preserve legacy exact counters while expanding the business ontology.
        for entry in entries:
            if not entry.get("offering_type"):
                kind = str(entry.get("kind") or "").lower()
                if kind == "service":
                    entry["offering_type"] = "service"
                elif kind == "softwareapplication":
                    entry["offering_type"] = "software_platform"
                else:
                    entry["offering_type"] = "product"

        type_counts = Counter(str(entry.get("offering_type") or "unknown") for entry in entries)
        result["schema"] = "orb_weaver.commercial_catalog.v2"
        result["entries"] = sorted(entries, key=lambda item: (str(item.get("offering_type")), str(item.get("name"))))
        result["entry_count"] = len(entries)
        result["product_count"] = sum(1 for item in entries if str(item.get("kind") or "").lower() != "service")
        result["service_count"] = sum(1 for item in entries if str(item.get("kind") or "").lower() == "service")
        result["offering_type_counts"] = dict(type_counts)
        result["commercial_model"] = {
            "software_or_ai_agent_business": bool(type_counts.get("ai_agent") or type_counts.get("software_platform")),
            "service_business": bool(type_counts.get("service")),
            "subscription_business": bool(type_counts.get("subscription_plan")),
            "evidence_state": "OBSERVED" if entries else "UNKNOWN",
            "note": "No price, SKU, availability or plan term is invented when source evidence is absent.",
        }
        return result

    compiler_module.compile_commercial_catalog = enhanced_compile
    compiler_module._orb_catalog_v2_installed = True


__all__ = ["install_catalog_v2"]
