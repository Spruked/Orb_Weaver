"""Canonical storage resolver for a manufactured Website ORB.

The package is intentionally fail-closed: cognition may not invent a
package-relative SKG vault when the installed canonical Vault is absent.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VAULT_ENV = "ORB_WEAVER_VAULT_ROOT"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
INJECTED_VAULT_ROOT = PACKAGE_ROOT / "runtime" / "vault_system"


def canonical_vault_root() -> Path:
    configured = os.environ.get(VAULT_ENV, "").strip()
    if not configured:
        raise RuntimeError(f"{VAULT_ENV} is required; manufactured cognition will not create a fallback vault")
    # The installed package may be relocated, but its internal canonical
    # location cannot be redirected through a symlink into a second store.
    for component in (PACKAGE_ROOT / "runtime", INJECTED_VAULT_ROOT):
        if component.is_symlink():
            raise RuntimeError("Manufactured runtime/vault_system must not be a symbolic link")
    root = Path(configured).expanduser().resolve()
    expected = INJECTED_VAULT_ROOT.resolve()
    if root != expected:
        raise RuntimeError(f"{VAULT_ENV} must reference the manufactured runtime/vault_system root: {expected}")
    manifest = root / "payload" / "payload_manifest.json"
    if not manifest.is_file():
        raise RuntimeError(f"Manufactured canonical Vault is incomplete: {manifest}")
    return root


def require_vault_path(path: Path, purpose: str) -> Path:
    root = canonical_vault_root()
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"{purpose} must remain inside the manufactured canonical Vault: {resolved}")
    return resolved


def skg_storage_paths() -> tuple[Path, Path]:
    root = canonical_vault_root()
    priori = require_vault_path(root / "payload" / "apriori", "SKG A Priori storage")
    posteriori = require_vault_path(root / "posteriori" / "orb_vault_skg", "SKG A Posteriori storage")
    priori.mkdir(parents=True, exist_ok=True)
    posteriori.mkdir(parents=True, exist_ok=True)
    return priori, posteriori


def record_skg_provenance(event: str, payload: dict[str, Any]) -> Path:
    """Append the SKG resolution lineage beside its knowledge and ledger."""
    root = canonical_vault_root()
    trace = require_vault_path(root / "audit" / "glyph_trace" / "skg_runtime.jsonl", "SKG glyph provenance")
    trace.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "orb_weaver.manufactured_skg_provenance.v1",
        "event": event,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
    with trace.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
    return trace


def record_runtime_audit(event: str, payload: dict[str, Any]) -> Path:
    """Append a minimal runtime-delivery audit record in the package Vault."""
    root = canonical_vault_root()
    trace = require_vault_path(root / "audit" / "glyph_trace" / "website_orb_runtime.jsonl", "Website ORB runtime audit")
    trace.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "orb_weaver.manufactured_runtime_audit.v1",
        "event": event,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    with trace.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return trace
