#!/usr/bin/env python3
"""Read-only file-level audit for the canonical Orb Weaver Vault.

This deliberately reports missing history instead of inventing provenance.
Database rows and external stores are reported as audit scope gaps for a
later adapter-backed migration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[1]
VAULT_ROOT = REPO_ROOT / "vault_system"
LEDGER = VAULT_ROOT / "audit" / "glyph_trace" / "objects.jsonl"
SKIP_NAMES = {"vault_integrity_report.json", "README.md", "__init__.py"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_traces() -> Dict[str, Dict[str, Any]]:
    traces: Dict[str, Dict[str, Any]] = {}
    if not LEDGER.is_file():
        return traces
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        object_id = str(record.get("vault_object_id") or "")
        if object_id:
            traces[object_id] = record
    return traces


def metadata(path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                result = payload
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            result = {}
    return result


def audit(*, full_hash: bool = False) -> Dict[str, Any]:
    traces = load_traces()
    findings = []
    counts = Counter()
    objects = []
    for path in sorted(p for p in VAULT_ROOT.rglob("*") if p.is_file()):
        relative = path.relative_to(VAULT_ROOT).as_posix()
        if path.name in SKIP_NAMES or "/__pycache__/" in f"/{relative}" or relative.startswith("audit/glyph_trace/"):
            continue
        size = path.stat().st_size
        large = size > 10 * 1024 * 1024
        digest = sha256(path) if full_hash or not large else f"deferred:size={size}"
        data = metadata(path) if full_hash or not large else {}
        trace = traces.get(relative) or traces.get(path.name) or traces.get(path.stem)
        if trace and trace.get("verification_state") == "LEGACY_UNTRACED":
            classification = "legacy_untraced"
        elif trace:
            classification = "provable_historical" if trace.get("verification_state") == "VERIFIED" else "partially_reconstructable"
        else:
            has_provenance = bool(data.get("source") or data.get("provenance") or data.get("source_ids"))
            classification = "partially_reconstructable" if has_provenance else "legacy_untraced"
        counts[classification] += 1
        missing = []
        for field in ("schema_version", "source_provenance", "verification_state", "glyph_trace_id", "lifecycle_state", "producer", "consumer", "retention_policy"):
            present = bool((trace or {}).get(field))
            if field == "schema_version":
                present = present or bool(data.get("schema") or data.get("schema_version"))
            if field == "source_provenance":
                present = present or bool(data.get("source") or data.get("provenance") or data.get("source_ids"))
            if field == "verification_state":
                present = present or bool(data.get("verification_state") or data.get("status"))
            if not present:
                missing.append(field)
        if classification == "legacy_untraced":
            findings.append({"finding": "UNTRACED_OBJECT", "path": relative, "action": "reverify_or_migrate", "missing": missing})
        elif missing:
            findings.append({"finding": "INCOMPLETE_TRACE", "path": relative, "action": "complete_lineage", "missing": missing})
        if large and not full_hash:
            findings.append({"finding": "LARGE_OBJECT_HASH_DEFERRED", "path": relative, "action": "run_with_full_hash", "size_bytes": size})
        objects.append({"path": relative, "sha256": digest, "classification": classification, "missing": missing})

    database_inventory = {}
    for database in sorted(VAULT_ROOT.rglob("*.db")):
        tables = {}
        try:
            with sqlite3.connect(database) as connection:
                names = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
                for (name,) in names:
                    tables[name] = int(connection.execute(f'SELECT COUNT(*) FROM "{name.replace(chr(34), chr(34) * 2)}"').fetchone()[0])
        except sqlite3.Error as exc:
            tables = {"_audit_error": str(exc)}
        database_inventory[str(database.relative_to(VAULT_ROOT))] = tables
    return {
        "schema": "orb_weaver.vault_integrity_report.v1",
        "vault_root": str(VAULT_ROOT),
        "vault_audit_status": "migration_required" if findings else "pass",
        "new_runtime_trace_coverage": "enforced",
        "historical_vault_trace_coverage": "partial" if findings else "complete",
        "scope": "file_level; database rows and external stores require adapter-backed audit",
        "counts": dict(counts),
        "object_count": len(objects),
        "finding_count": len(findings),
        "database_inventory": database_inventory,
        "findings": findings,
        "objects": objects,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    parser.add_argument("--full-hash", action="store_true", help="hash large files too; may be slow")
    args = parser.parse_args()
    report = audit(full_hash=args.full_hash)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(json.dumps({key: value for key, value in report.items() if key not in {"findings", "objects"}}, indent=2))
        for finding in report["findings"][:25]:
            print(f"{finding['finding']}: {finding['path']}")
        if len(report["findings"]) > 25:
            print(f"... {len(report['findings']) - 25} more findings; use --json for the full report")


if __name__ == "__main__":
    main()
