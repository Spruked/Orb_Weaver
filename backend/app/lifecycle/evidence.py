from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from app.core.config import settings
from app.core.storage import client_root


EVIDENCE_DIRECTORIES = (
    "baseline/map",
    "baseline/site",
    "baseline/orb",
    "baseline/databases",
    "verification/map",
    "verification/site",
    "verification/orb",
    "verification/databases",
    "reconciliation",
    "review",
    "preflight",
    "sentinel",
    "failure_diagnostics",
    "reports",
    "exports",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
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


def initialize_evidence_run(domain: str, run_id: int | str) -> Path:
    root = client_root(domain) / "runs" / str(run_id)
    for relative in EVIDENCE_DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)
    return root


def write_json_artifact(root: Path, relative_path: str, payload: Any) -> Path:
    target = (root / relative_path).resolve()
    if root.resolve() not in target.parents:
        raise ValueError("Evidence artifact path must remain inside the run root")
    _write_json_atomic(target, payload)
    return target


def write_failure_diagnostic(
    root: Path,
    *,
    stage: str,
    category: str,
    url: Optional[str] = None,
    error: Optional[str] = None,
    http_status: Optional[int] = None,
    attempts: int = 1,
    timing_ms: Optional[float] = None,
    retry: Optional[Dict[str, Any]] = None,
    browser_render_status: Optional[str] = None,
    impact: str = "stage_incomplete",
    evidence: Optional[Dict[str, Any]] = None,
    recommended_action: Optional[str] = None,
) -> Path:
    diagnostics_dir = root / "failure_diagnostics"
    existing = sorted(diagnostics_dir.glob("diagnostic_*.json"))
    identifier = len(existing) + 1
    return write_json_artifact(
        root,
        f"failure_diagnostics/diagnostic_{identifier:04d}.json",
        {
            "schema": "orb_weaver.failure_diagnostic.v1",
            "recorded_at": _utc_now(),
            "stage": stage,
            "url": url,
            "category": category,
            "http_status": http_status,
            "attempts": attempts,
            "timing_ms": timing_ms,
            "retry": retry or {"eligible": False, "attempted": False},
            "browser_render_status": browser_render_status,
            "impact": impact,
            "evidence": {**(evidence or {}), **({"error": error[:2000]} if error else {})},
            "recommended_action": recommended_action or "Inspect the stage evidence and retry within the scan contract.",
        },
    )


def _sqlite_path(database_url: str) -> Optional[Path]:
    if database_url in {"sqlite:///:memory:", "sqlite+pysqlite:///:memory:"}:
        return None
    for prefix in ("sqlite+pysqlite:///", "sqlite:///"):
        if database_url.startswith(prefix):
            raw_path = database_url[len(prefix):].split("?", 1)[0]
            return Path("/" + raw_path.lstrip("/")) if database_url.startswith(prefix + "/") else Path(raw_path)
    return None


def snapshot_sqlite_database(database_url: str, root: Path, *, verification: bool = False) -> Optional[Path]:
    source = _sqlite_path(database_url)
    if not source or not source.is_file():
        return None
    relative_dir = "verification/databases" if verification else "baseline/databases"
    destination = root / relative_dir / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as destination_connection:
        source_connection.backup(destination_connection)
    schema_path = destination.with_suffix(destination.suffix + ".schema.json")
    with sqlite3.connect(destination) as connection:
        rows = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name"
        ).fetchall()
    _write_json_atomic(
        schema_path,
        {
            "schema": "orb_weaver.database_snapshot.v1",
            "created_at": _utc_now(),
            "source_name": source.name,
            "snapshot_name": destination.name,
            "objects": [
                {"type": row[0], "name": row[1], "table": row[2], "sql": row[3]}
                for row in rows
            ],
        },
    )
    return destination


def _artifact_files(root: Path) -> Iterable[Path]:
    excluded = {"manifest.json", "checksums.json"}
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.name not in excluded
    )


def finalize_evidence_run(
    root: Path,
    *,
    run_id: int | str,
    project_id: int | str,
    domain: str,
    job_type: str,
    status: str,
    scan_contract: Dict[str, Any],
    previous_run_id: Optional[int | str] = None,
    previous_manifest_hash: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    write_json_artifact(root, "scan_contract.json", scan_contract)
    checksums = {
        path.relative_to(root).as_posix(): {
            "sha256": _sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in _artifact_files(root)
    }
    evidence_root_hash = _sha256_bytes(
        "\n".join(f"{name}:{entry['sha256']}" for name, entry in sorted(checksums.items())).encode("utf-8")
    )
    checksum_payload = {
        "schema": "orb_weaver.checksums.v1",
        "generated_at": _utc_now(),
        "evidence_root_hash": evidence_root_hash,
        "files": checksums,
    }
    _write_json_atomic(root / "checksums.json", checksum_payload)

    manifest = {
        "schema": "orb_weaver.run_manifest.v1",
        "run_id": str(run_id),
        "project_id": str(project_id),
        "domain": domain,
        "job_type": job_type,
        "status": status,
        "generated_at": _utc_now(),
        "previous_run_id": str(previous_run_id) if previous_run_id is not None else None,
        "previous_manifest_hash": previous_manifest_hash,
        "evidence_root_hash": evidence_root_hash,
        "artifact_count": len(checksums),
        "software": {
            "orb_weaver_version": settings.VERSION,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "metadata": metadata or {},
    }
    manifest_hash = _sha256_bytes(_canonical_json_bytes(manifest))
    manifest["manifest_hash"] = manifest_hash
    _write_json_atomic(root / "manifest.json", manifest)
    return manifest


def verify_evidence_run(root: Path) -> Dict[str, Any]:
    manifest_path = root / "manifest.json"
    checksums_path = root / "checksums.json"
    if not manifest_path.is_file() or not checksums_path.is_file():
        return {"valid": False, "reason": "manifest_or_checksums_missing", "files": {}}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
    expected_manifest_hash = manifest.pop("manifest_hash", None)
    actual_manifest_hash = _sha256_bytes(_canonical_json_bytes(manifest))
    manifest["manifest_hash"] = expected_manifest_hash
    file_results: Dict[str, Any] = {}
    for relative, expected in (checksums.get("files") or {}).items():
        path = root / relative
        actual = _sha256_file(path) if path.is_file() else None
        file_results[relative] = {
            "valid": actual == expected.get("sha256"),
            "expected": expected.get("sha256"),
            "actual": actual,
        }
    evidence_root_hash = _sha256_bytes(
        "\n".join(
            f"{name}:{entry.get('sha256')}"
            for name, entry in sorted((checksums.get("files") or {}).items())
        ).encode("utf-8")
    )
    valid = (
        expected_manifest_hash == actual_manifest_hash
        and evidence_root_hash == checksums.get("evidence_root_hash")
        and all(result["valid"] for result in file_results.values())
    )
    return {
        "valid": valid,
        "manifest_hash_valid": expected_manifest_hash == actual_manifest_hash,
        "evidence_root_hash_valid": evidence_root_hash == checksums.get("evidence_root_hash"),
        "manifest": manifest,
        "files": file_results,
    }
