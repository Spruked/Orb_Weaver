#!/usr/bin/env python3
"""
Run a local Orb Weaver crawl against a target site and write the ORB-facing
pointer map plus topological navigation/world-state artifacts into the client
substrate folder.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.crawler.engine import OrbWeaverCrawler  # noqa: E402
from app.orb.navigation_world import build_navigation_world  # noqa: E402
from app.orb.pointer_plot import pointer_plot_map_from_pages  # noqa: E402
from vault_system.paths import client_root  # noqa: E402


def _safe_pack_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip().lower())
    return cleaned.strip("._-") or "unknown_site"


def _domain_from_url(value: str) -> str:
    parsed = urlparse(value if value.startswith(("http://", "https://")) else f"https://{value}")
    return parsed.netloc or _safe_pack_name(value)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _duplicate_target_ids(records: List[Dict[str, Any]]) -> List[str]:
    counts = Counter(str(record.get("target_id")) for record in records if record.get("target_id"))
    return sorted(target_id for target_id, count in counts.items() if count > 1)


async def run(args: argparse.Namespace) -> Dict[str, Any]:
    crawler = OrbWeaverCrawler(
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        delay=args.delay,
        tier="authenticated",
    )
    pages = await crawler.crawl(args.url)
    pointer_map = pointer_plot_map_from_pages(pages)

    domain = args.domain or _domain_from_url(args.url)
    site_vault = client_root(domain)
    context_dir = site_vault / "website_orb_context"
    current_dir = site_vault / "current"
    pointer_path = context_dir / "pointer_plot_map.json"
    existing_pointer_map = _read_json(pointer_path)
    existing_count = int(existing_pointer_map.get("record_count") or 0)
    extracted_records = pointer_map.get("records") or []
    preserve_existing = bool(existing_count and not extracted_records and not args.allow_empty)

    if preserve_existing:
        pointer_map = existing_pointer_map

    records = pointer_map.get("records") or []
    duplicates = _duplicate_target_ids(records)
    navigation_world = build_navigation_world(
        pages,
        domain=domain,
        pointer_map=pointer_map,
    )
    navigation_summary = navigation_world.get("summary") or {}
    crawler_stats = {
        **crawler.get_crawl_stats(),
        "topological_route_nodes": int(navigation_summary.get("scanned_route_nodes") or 0),
        "topological_edges": int(navigation_summary.get("topological_edges") or 0),
        "unique_entities": int(navigation_summary.get("unique_entities") or 0),
        "entity_relationships": int(navigation_summary.get("entity_relationships") or 0),
        "pointer_targets": int(navigation_summary.get("pointer_targets") or 0),
        "guidance_eligible_pointers": int(navigation_summary.get("guidance_eligible_pointers") or 0),
        "pointer_route_locator_conflicts": int(navigation_summary.get("route_locator_conflicts") or 0),
        "semantic_tiles": int(navigation_summary.get("semantic_tiles") or 0),
        "navigation_guidance_status": navigation_summary.get("guidance_status"),
        "navigation_world_version": navigation_world.get("version"),
        "orbot_world_etag": (navigation_world.get("world_state_seed") or {}).get("etag"),
    }

    summary = {
        "schema": "orb_weaver.self_scan_summary.v2",
        "url": args.url,
        "domain": domain,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pages_scanned": len(pages),
        "crawler_stats": crawler_stats,
        "pointer_record_count": int(pointer_map.get("record_count") or len(records)),
        "routes_with_pointers": len(pointer_map.get("by_page") or {}),
        "duplicate_target_ids": duplicates,
        "preserved_existing_pointer_map": preserve_existing,
        "existing_pointer_record_count": existing_count,
        "navigation_world": navigation_summary,
        "world_state_seed": {
            "schema": (navigation_world.get("world_state_seed") or {}).get("schema"),
            "etag": (navigation_world.get("world_state_seed") or {}).get("etag"),
            "pointer_map_version": (navigation_world.get("world_state_seed") or {}).get("pointer_map_version"),
        },
        "status": "passed" if records and not duplicates else "needs_review",
    }
    if preserve_existing:
        summary["status"] = "render_failed_preserved_existing_map"

    semantic_tiles = {
        "schema": "orb_weaver.semantic_tiles.v1",
        "navigation_world_version": navigation_world.get("version"),
        "tiles": navigation_world.get("semantic_tiles") or {},
    }

    _write_json(pointer_path, pointer_map)
    _write_json(context_dir / "navigation_world.json", navigation_world)
    _write_json(context_dir / "semantic_tiles.json", semantic_tiles)
    _write_json(context_dir / "orbot_world_state_seed.json", navigation_world["world_state_seed"])
    _write_json(context_dir / "self_scan_summary.json", summary)
    _write_json(
        current_dir / "latest_self_scan.json",
        {
            "summary": summary,
            "pointer_plot_map": pointer_map,
            "navigation_world": navigation_world,
            "orbot_world_state_seed": navigation_world["world_state_seed"],
        },
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Self-scan a site and write Orb Weaver pointer, navigation, and Orbot WorldState artifacts."
    )
    parser.add_argument("--url", default="https://orbweaver.spruked.com")
    parser.add_argument("--domain", default="")
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--delay", type=float, default=0.1)
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow this run to overwrite an existing pointer map with zero records.",
    )
    args = parser.parse_args()

    summary = asyncio.run(run(args))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
