"""Permanent ORB identity and serial allocation.

Identity belongs to the ORB, not its current website deployment. Allocation is
idempotent for a build identity and records its ISS issuance envelope in the
canonical Vault.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from app.core import storage
from app.core.storage import require_vault_path
from app.core.timekeeping import event_timestamp


_LOCK = threading.Lock()


def _serial_registry() -> Path:
    return storage.VAULT_ROOT / "identity" / "orb_serial_registry.json"


def _safe_key(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._:-]+", "_", str(value).strip())
    if not normalized or len(normalized) > 180:
        raise ValueError("ORB identity key is invalid")
    return normalized


def _load_registry() -> dict[str, Any]:
    registry_path = _serial_registry()
    if not registry_path.exists():
        return {"schema": "orb_weaver.orb_identity_registry.v1", "next_sequence": 1, "identities": {}}
    return json.loads(registry_path.read_text(encoding="utf-8"))


def _write_registry(registry: dict[str, Any]) -> None:
    target = require_vault_path(_serial_registry(), "ORB identity registry")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(target)


def ensure_orb_identity(
    *,
    identity_key: str,
    site_id: str,
    domain: str,
    product_edition: str = "Website ORB",
    build_id: str = "",
) -> dict[str, Any]:
    """Allocate or return one permanent serial for an ORB build identity."""
    key = _safe_key(identity_key)
    with _LOCK:
        registry = _load_registry()
        existing = registry.setdefault("identities", {}).get(key)
        if existing:
            return existing
        timestamp = event_timestamp(source="orb_weaver.orb_identity")
        sequence = int(registry.get("next_sequence") or 1)
        serial = f"ORB-SN-{timestamp['local_display_time'][:4]}-{sequence:06d}"
        identity = {
            "schema": "orb_weaver.orb_identity.v1",
            "identity_key": key,
            "serial_number": serial,
            "product_edition": product_edition,
            "site_id": str(site_id),
            "domain": str(domain),
            "build_id": str(build_id),
            "identity_status": "ISSUED",
            "timestamp_envelope": timestamp,
            "timestamp_schema": "orb_weaver.iss_timestamp.v1",
            "lifecycle_rule": "serial_survives_owner_site_skin_persona_role_and_redeployment_changes",
            "certification_status": "PENDING_EXTERNAL_TRUEMARK_ISSUANCE",
        }
        registry["next_sequence"] = sequence + 1
        registry["identities"][key] = identity
        _write_registry(registry)
        return identity
