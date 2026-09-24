"""Master capability checklist and evidence-backed coverage reporting."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from bs4 import BeautifulSoup

MASTER_NAME = "Orb Weaver — Master Capability List.html"


def _master_path() -> Path | None:
    candidates = [Path("/app") / MASTER_NAME, Path(__file__).resolve().parents[3] / MASTER_NAME]
    return next((path for path in candidates if path.is_file()), None)


def load_master_capabilities() -> List[Dict[str, Any]]:
    path = _master_path()
    if not path:
        return []
    try:
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    except (OSError, UnicodeError):
        return []
    categories: List[Dict[str, Any]] = []
    for heading in soup.find_all("h2"):
        title = heading.get_text(" ", strip=True)
        if title.lower().startswith(("owner-priority", "orb-priority", "crawl completion", "six authoritative", "future /")):
            continue
        paragraph = heading.find_next_sibling("p")
        if not paragraph:
            continue
        items = [
            re.sub(r"\s+", " ", item).strip(" ·—")
            for item in re.split(r"\s+·\s+", paragraph.get_text(" ", strip=True))
            if item.strip(" ·—")
        ]
        categories.append({
            "id": re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_"),
            "title": title,
            "items": items,
        })
    return categories


RUNTIME_CATEGORY_PREFIXES = (
    "11_vault", "12_tpc", "13_voice", "14_orb_personality", "15_manufacturing",
    "16_dock", "17_live_test", "18_release", "19_marketplace", "22_manufacturing",
)


def _status_for_category(
    category_id: str,
    stages: Mapping[str, Any],
    stats: Mapping[str, Any],
    pages: Sequence[Any],
    runtime_evidence: Mapping[str, Any],
) -> str:
    def stage(name: str) -> str:
        return str((stages.get(name) or {}).get("status") or "NOT_STARTED").upper()

    if category_id.startswith("1_discovery"):
        return "verified" if (
            stage("url_discovery") == "COMPLETE"
            and stage("page_fetch") == "COMPLETE"
            and not stats.get("depth_limit_hit")
            and not stats.get("authentication_wall_pages")
        ) else "partial"
    if category_id.startswith("2_rendering"):
        if stage("javascript_rendering") != "COMPLETE":
            return "blocked"
        diagnostics = stats.get("render_diagnostics") or {}
        return "partial" if any(int(diagnostics.get(key) or 0) for key in (
            "pages_with_console_errors", "pages_with_page_errors", "failed_request_count", "failed_response_count"
        )) else "verified"
    if category_id.startswith("3_content"):
        return "verified" if all(stage(name) == "COMPLETE" for name in ("page_content_scan", "semantic_indexing", "schema_extraction")) else "partial"
    if category_id.startswith("4_design"):
        return "partial"
    if category_id.startswith("5_commerce"):
        catalog = stats.get("commercial_catalog") or {}
        if stage("commercial_catalog_extraction") != "COMPLETE":
            return "partial" if catalog else "not_run"
        return "verified" if int(catalog.get("entry_count") or 0) > 0 else "partial"
    if category_id.startswith("6_interface"):
        return "partial" if stage("pointer_mapping") == "COMPLETE" else "blocked"
    if category_id.startswith("7_lidar"):
        return "requires_runtime_verification" if stage("pointer_mapping") == "COMPLETE" else "blocked"
    if category_id.startswith("8_selective"):
        return "verified" if stage("pointer_verification") == "COMPLETE" and stage("pointer_recovery") == "COMPLETE" else "blocked"
    if category_id.startswith("9_tesseract"):
        measured = sum(1 for page in pages if (page.semantic_analysis or {}).get("tesseract_weave"))
        return "partial" if measured == len(pages) and pages else "partial" if measured else "not_run"
    if category_id.startswith("10_site_world"):
        return "verified" if stage("relationship_mapping") == "COMPLETE" and stage("knowledge_chunking") == "COMPLETE" else "partial"
    if category_id.startswith(RUNTIME_CATEGORY_PREFIXES):
        verified_categories = set(runtime_evidence.get("verified_categories") or [])
        if str(category_id) in verified_categories and str(runtime_evidence.get("status") or "").upper() == "COMPLETE":
            return "verified"
        return "runtime_capability_not_crawl_verified"
    if category_id.startswith("20_lifecycle"):
        return "verified" if stats.get("historical") else "partial"
    if category_id.startswith("21_auditing"):
        return "partial" if stage("source_validation") == "COMPLETE" else "partial"
    return "tracked"


def build_capability_coverage(
    *,
    stages: Mapping[str, Any],
    stats: Mapping[str, Any],
    pages: Sequence[Any],
    runtime_evidence: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    runtime_evidence = runtime_evidence or {}
    categories = []
    counts: Dict[str, int] = {}
    for category in load_master_capabilities():
        status = _status_for_category(category["id"], stages, stats, pages, runtime_evidence)
        counts[status] = counts.get(status, 0) + 1
        categories.append({
            **category,
            "status": status,
            "item_evidence": [
                {"label": item, "status": status, "stage_ids": sorted(stages.keys())}
                for item in category["items"]
            ],
            "evidence": {"stage_ids": sorted(stages.keys()), "runtime_evidence": runtime_evidence},
        })
    unresolved = sum(value for key, value in counts.items() if key != "verified")
    return {
        "schema": "orb_weaver.capability_coverage.v1",
        "source": MASTER_NAME,
        "status": "complete" if categories and unresolved == 0 else "partial",
        "category_count": len(categories),
        "item_count": sum(len(category["items"]) for category in categories),
        "status_counts": counts,
        "runtime_evidence": runtime_evidence,
        "runtime_promotion_rule": "Live Test must persist status COMPLETE and explicitly list verified category IDs before runtime-only categories can become verified.",
        "categories": categories,
    }
