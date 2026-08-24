#!/usr/bin/env python3
"""Classify legacy Vault files without inventing their provenance.

Dry-run is the default. ``--apply`` writes suspended legacy trace records;
those records make the migration auditable but do not make legacy knowledge
eligible for active A Priori/A Posteriori use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.orb.vault_glyph_trace import record_vault_object  # noqa: E402


ROOT = Path(__file__).resolve().parents[1] / "vault_system"
SKIP_NAMES = {"README.md", "__init__.py", "vault_integrity_report.json"}


def legacy_id(relative: str, path: Path) -> str:
    identity = f"{relative}|{path.stat().st_size}|{path.stat().st_mtime_ns}"
    return "LEGACY-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]


def existing_ids() -> set[str]:
    ledger = ROOT / "audit" / "glyph_trace" / "objects.jsonl"
    if not ledger.exists():
        return set()
    result = set()
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line).get("vault_object_id")
            if value:
                result.add(str(value))
        except json.JSONDecodeError:
            pass
    return result


def candidates() -> list[tuple[str, Path, str]]:
    traced = existing_ids()
    result = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file()):
        relative = path.relative_to(ROOT).as_posix()
        if path.name in SKIP_NAMES or "/__pycache__/" in f"/{relative}" or relative.startswith("audit/glyph_trace/"):
            continue
        object_id = legacy_id(relative, path)
        if relative in traced or path.name in traced or path.stem in traced or object_id in traced:
            continue
        result.append((relative, path, object_id))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write suspended legacy Glyph Trace records")
    args = parser.parse_args()
    items = candidates()
    print(json.dumps({"mode": "apply" if args.apply else "dry_run", "candidate_count": len(items), "status": "ready"}, indent=2))
    if not args.apply:
        for relative, _path, object_id in items[:20]:
            print(f"{object_id} {relative}")
        return
    for relative, path, object_id in items:
        record_vault_object(
            object_id=object_id,
            object_type="legacy_vault_object",
            vault_partition=relative.split("/", 1)[0],
            content={"path": relative, "size_bytes": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns},
            source_ids=[relative],
            source_hashes=[f"deferred:size={path.stat().st_size}"],
            lifecycle_state="LEGACY_UNTRACED",
            verification_state="LEGACY_UNTRACED",
            actor_type="vault_legacy_migration",
            event_type="MIGRATED_LEGACY",
            event_reason="historical_provenance_not_proven",
            provenance_confidence="unknown",
            runtime_eligibility="suspended",
        )
    print(json.dumps({"migrated_count": len(items), "runtime_eligibility": "suspended"}, indent=2))


if __name__ == "__main__":
    main()
