from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict


MANUFACTURING_SCHEMA = "orb_weaver.customer_dock_station_manifest.v1"
SOURCE_MANIFEST_KEYS = ("name", "repository", "commit")


def load_template_manifest(template_root: Path) -> Dict[str, Any]:
    manifest_path = template_root / "manifest.template.json"
    with manifest_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_manifest_hash(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def public_template_source(template_manifest: Dict[str, Any]) -> Dict[str, Any]:
    source = template_manifest.get("source", {})
    return {key: source[key] for key in SOURCE_MANIFEST_KEYS if key in source}


def customer_manifest(
    *,
    template_manifest: Dict[str, Any],
    customer_id: str,
    deployment_id: str,
    template_tree_hash: str,
) -> Dict[str, Any]:
    generated_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    manifest: Dict[str, Any] = {
        "schema": MANUFACTURING_SCHEMA,
        "customer_id": customer_id,
        "deployment_id": deployment_id,
        "generated_at": generated_at,
        "delivery_unit": "customer_dock_station_with_installed_orb",
        "manufacturing_pass": {
            "manufacturing_structure": True,
            "blank_template": True,
            "delivery_ready": False,
        },
        "template": {
            "template_id": template_manifest.get("template_id"),
            "template_version": template_manifest.get("template_version"),
            "source": public_template_source(template_manifest),
            "tree_hash": template_tree_hash,
        },
        "paths": {
            "dock_station": ".",
            "dock_station_app": "app",
            "orb_template": "app/orb/template",
            "deployment_manifest": "deployment/manifest.json",
            "verification_report": "reports/verification-report.json",
        },
    }
    manifest["manifest_hash"] = stable_manifest_hash(manifest)
    return manifest
