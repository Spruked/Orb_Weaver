"""Canonical append-only Vault Glyph Trace ledger.

Geometric glyphs identify semantic content; Glyph Trace IDs identify custody
and lifecycle.  They are intentionally separate identities.
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from app.core.storage import AUDIT_ROOT, require_vault_path


LEDGER_ROOT = AUDIT_ROOT / "glyph_trace"
OBJECTS_LEDGER = LEDGER_ROOT / "objects.jsonl"
EVENTS_LEDGER = LEDGER_ROOT / "events.jsonl"
_LOCK = threading.Lock()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, default=str, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _append(path: Path, payload: Dict[str, Any]) -> None:
    path = require_vault_path(path, "Vault Glyph Trace ledger")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=True) + "\n")


def record_vault_object(
    *,
    object_id: str,
    object_type: str,
    vault_partition: str,
    content: Any,
    governance_trace_id: Optional[str] = None,
    source_ids: Optional[Iterable[str]] = None,
    source_hashes: Optional[Iterable[str]] = None,
    lifecycle_state: str = "ACTIVE",
    verification_state: str = "UNVERIFIED",
    actor_type: str = "website_orb_runtime",
    event_type: str = "CREATED",
    event_reason: str = "runtime_object_created",
    provenance_confidence: str = "verified",
    runtime_eligibility: str = "active",
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    content_hash = _hash(content)
    trace_id = f"GT-VLT-{uuid.uuid4().hex}"
    event_id = f"GTE-{uuid.uuid4().hex}"
    record = {
        "glyph_trace_id": trace_id,
        "vault_object_id": object_id,
        "object_type": object_type,
        "vault_partition": vault_partition,
        "created_at": now,
        "updated_at": now,
        "actor_type": actor_type,
        "actor_id": "orb_weaver",
        "origin_session_id": None,
        "origin_turn_id": None,
        "governance_trace_id": governance_trace_id,
        "source_ids": list(source_ids or []),
        "source_hashes": list(source_hashes or []),
        "content_hash": content_hash,
        "schema_version": "orb_weaver.glyph_trace.v1",
        "geometric_glyph_id": f"GG-{content_hash[:24]}",
        "skg_node_ids": [],
        "related_trace_ids": [],
        "epistemic_state": "site_scoped" if vault_partition == "site_world" else "runtime_record",
        "verification_state": verification_state,
        "provenance_confidence": provenance_confidence,
        "runtime_eligibility": runtime_eligibility,
        "confidence_state": "known" if verification_state == "VERIFIED" else "unverified",
        "contradiction_state": "none",
        "lifecycle_state": lifecycle_state,
        "promotion_state": "not_applicable",
        "pruning_state": "retained",
        "previous_version_id": None,
        "supersedes_id": None,
        "superseded_by_id": None,
        "created_event_id": event_id,
        "last_event_id": event_id,
        "integrity_algorithm": "sha256",
        "integrity_verified_at": now,
    }
    event = {
        "event_id": event_id,
        "glyph_trace_id": trace_id,
        "timestamp": now,
        "event_type": event_type,
        "actor": actor_type,
        "session_id": None,
        "turn_id": None,
        "governance_trace_id": governance_trace_id,
        "before_hash": None,
        "after_hash": content_hash,
        "evidence_refs": list(source_ids or []),
        "reason": event_reason,
        "result": "recorded",
    }
    with _LOCK:
        _append(OBJECTS_LEDGER, record)
        _append(EVENTS_LEDGER, event)
    return record
