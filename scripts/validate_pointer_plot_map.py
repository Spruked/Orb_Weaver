#!/usr/bin/env python3
"""Validate an Orb Weaver Pointer Plot Map against the live rendered site.

This command reuses Orb Weaver's existing Playwright recovery capture and
reconciliation pipeline. It does not grant click authority and it does not use
stored coordinates as action targets. Observed rectangles are retained only as
compact evidence for future localized recovery.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.orb.pointer_map_optimizer import optimize_pointer_map  # noqa: E402
from app.orb.pointer_recovery import (  # noqa: E402
    assess_pointer_quality,
    reconcile_pointer_recovery,
    run_pointer_recovery_capture,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate semantic locators using repeated desktop/mobile browser renders.",
    )
    parser.add_argument("--base-url", required=True, help="Canonical site origin, for example https://example.com")
    parser.add_argument("--map", required=True, dest="map_path", help="Authoritative or baseline pointer_plot_map.json")
    parser.add_argument(
        "--output-dir",
        help="Vault-backed output directory. Defaults to <map parent>/validation.",
    )
    parser.add_argument("--render-passes", type=int, default=2, help="Repeated renders per viewport; minimum 2")
    parser.add_argument(
        "--capture",
        help="Reuse an existing browser_capture.json instead of launching Chromium.",
    )
    parser.add_argument(
        "--publish",
        help="Optional explicit path for a validated pointer map. Existing files are replaced atomically.",
    )
    parser.add_argument(
        "--no-alias-compaction",
        action="store_true",
        help="Keep repeated topic aliases on every record.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    map_path = Path(args.map_path).expanduser().resolve()
    if not map_path.is_file():
        raise SystemExit(f"Pointer map not found: {map_path}")

    baseline = _read_json(map_path)
    records = [item for item in baseline.get("records") or [] if isinstance(item, dict)]
    if not records:
        raise SystemExit("Pointer map contains no records")

    base_url = _canonical_origin(args.base_url)
    routes = _routes(records)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else map_path.parent / "validation"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.capture:
        capture_path = Path(args.capture).expanduser().resolve()
        capture = _read_json(capture_path)
    else:
        capture_dir = output_dir / "browser_capture"
        capture = run_pointer_recovery_capture(
            base_url,
            routes,
            capture_dir,
            render_passes=max(2, int(args.render_passes)),
        )
        capture.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
        capture_path = capture_dir / "browser_capture.json"

    reconciled = reconcile_pointer_recovery(baseline, capture)
    if args.no_alias_compaction:
        validated = optimize_pointer_map(
            reconciled,
            capture,
            shared_alias_ratio=2.0,
            shared_alias_minimum=10**9,
        )
    else:
        validated = optimize_pointer_map(reconciled, capture)

    validated_path = output_dir / "pointer_plot_map.validated.json"
    report_path = output_dir / "pointer_validation_report.json"
    _write_json_atomic(validated_path, validated)

    report = build_validation_report(
        baseline,
        validated,
        capture,
        base_url=base_url,
        map_path=map_path,
        capture_path=capture_path,
        validated_path=validated_path,
    )
    _write_json_atomic(report_path, report)

    if args.publish:
        publish_path = Path(args.publish).expanduser().resolve()
        _write_json_atomic(publish_path, validated)
        report["published_path"] = str(publish_path)
        _write_json_atomic(report_path, report)

    print(json.dumps(report, indent=2))
    return 0 if report["status"] in {"POINTER_READY", "POINTER_RECOVERY_REQUIRED"} else 1


def build_validation_report(
    baseline: Dict[str, Any],
    validated: Dict[str, Any],
    capture: Dict[str, Any],
    *,
    base_url: str,
    map_path: Path,
    capture_path: Path,
    validated_path: Path,
) -> Dict[str, Any]:
    baseline_records = [item for item in baseline.get("records") or [] if isinstance(item, dict)]
    records = [item for item in validated.get("records") or [] if isinstance(item, dict)]
    quality = validated.get("quality") or assess_pointer_quality(validated)
    finding_classes = Counter(str(item.get("finding_class") or "UNKNOWN") for item in records)
    pointer_health = Counter(str(item.get("pointer_health") or "UNKNOWN") for item in records)
    mutability = Counter(str(item.get("dom_mutability") or "unknown") for item in records)
    locator_methods = Counter(
        str((item.get("confidence_evidence") or {}).get("locator_method") or "unknown")
        for item in records
    )
    with_geometry = sum(1 for item in records if item.get("visual_recovery_hint"))
    evidence_only_violations = [
        str(item.get("target_id") or "")
        for item in records
        if (item.get("visual_recovery_hint") or {}).get("may_drive_pointer_action") is not False
    ]

    status = str(quality.get("status") or "UNKNOWN")
    if evidence_only_violations:
        status = "INVALID_COORDINATE_AUTHORITY"

    return {
        "schema": "orb_weaver.pointer_validation_report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "base_url": base_url,
        "routes_checked": _routes(records),
        "baseline_record_count": len(baseline_records),
        "validated_record_count": len(records),
        "capture_schema": capture.get("schema"),
        "render_count": len(capture.get("observations") or []),
        "quality": quality,
        "finding_classes": dict(finding_classes),
        "pointer_health": dict(pointer_health),
        "dom_mutability": dict(mutability),
        "locator_methods": dict(locator_methods),
        "records_with_visual_recovery_evidence": with_geometry,
        "coordinate_policy": {
            "authority": "evidence_only",
            "may_drive_pointer_action": False,
            "violations": evidence_only_violations,
        },
        "alias_compaction": validated.get("optimization") or {},
        "files": {
            "input_map": str(map_path),
            "capture": str(capture_path),
            "validated_map": str(validated_path),
        },
    }


def _routes(records: Iterable[Dict[str, Any]]) -> List[str]:
    result = set()
    for record in records:
        value = str(record.get("page_route") or "/")
        parsed = urlparse(value if "://" in value else f"https://pointer.invalid{value if value.startswith('/') else '/' + value}")
        result.add((parsed.path or "/").rstrip("/") or "/")
    return sorted(result)


def _canonical_origin(value: str) -> str:
    raw = value.strip()
    parsed = urlparse(raw if raw.startswith(("http://", "https://")) else f"https://{raw}")
    if not parsed.netloc:
        raise SystemExit(f"Invalid base URL: {value}")
    return f"{parsed.scheme}://{parsed.netloc}"


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Unable to read JSON from {path}: {error}") from error
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected a JSON object in {path}")
    return payload


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
