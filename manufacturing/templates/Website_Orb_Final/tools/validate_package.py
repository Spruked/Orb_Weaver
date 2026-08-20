from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
COMPILED = ROOT / "compiled_orb"


REQUIRED_ROUTE_FIELDS = {
    "page_purpose",
    "summary",
    "target_tiering",
    "permitted_action_boundaries",
    "doctrine_conditions",
    "tpc_output_classes",
    "playbooks",
    "guiderails",
}


def main() -> None:
    required_files = [
        ROOT / "README.md",
        ROOT / "PACKAGE_MANIFEST.json",
        COMPILED / "site_world.json",
        COMPILED / "pointer_plot_map.json",
        COMPILED / "runtime_language.json",
        ROOT / "backend" / "app.py",
        ROOT / "frontend" / "src" / "WebsiteORB.tsx",
        ROOT / "backend" / "dock_adapter" / "dockstation_adapter.py",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required_files if not path.exists()]
    if missing:
        raise SystemExit(f"missing required files: {missing}")

    world = load_json(COMPILED / "site_world.json")
    if world.get("runtime_contract") != "precompiled_skg_lookup_only":
        raise SystemExit("site_world runtime_contract must be precompiled_skg_lookup_only")
    routes = world.get("routes")
    if not isinstance(routes, dict) or not routes:
        raise SystemExit("site_world routes missing")

    bad_routes = []
    for route, record in routes.items():
        if not isinstance(record, dict) or not REQUIRED_ROUTE_FIELDS.issubset(record):
            bad_routes.append(route)
    if bad_routes:
        raise SystemExit(f"routes missing precompiled fields: {bad_routes[:8]}")

    pointer_map = load_json(COMPILED / "pointer_plot_map.json")
    records = pointer_map.get("records", [])
    if not records:
        raise SystemExit("pointer map contains no records")

    print("package validation passed")
    print(f"routes={len(routes)} pointer_records={len(records)}")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"expected object json: {path}")
    return data


if __name__ == "__main__":
    main()

