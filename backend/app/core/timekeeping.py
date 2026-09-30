"""Orb Weaver's canonical timestamp adapter.

The Interplanetary Stardate Syncrometer (ISS) is the authoritative ordering
clock for Vault events. Existing ISO fields remain for compatibility, while
new audit records carry the complete ISS envelope and anchor hash.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
ISS_ROOT = REPO_ROOT / "vault_system" / "Interplanetary_Stardate_Syncrometer"
if str(ISS_ROOT) not in sys.path:
    sys.path.insert(0, str(ISS_ROOT))

from iss_module import canonical_timestamp  # noqa: E402


def utc_now() -> datetime:
    """Return an aware UTC datetime for legacy database/API compatibility."""
    return datetime.now(timezone.utc)


def event_timestamp(
    *,
    source: str = "orb_weaver",
    reference_frame: str = "solar-system-barycentric",
    clock_id: str = "ISS-PRIMARY-ATOMIC-01",
    uncertainty_ns: Optional[int] = None,
    proper_time_ns: Optional[int] = None,
    relativistic_correction_ns: Optional[int] = None,
) -> dict[str, Any]:
    """Return the canonical ISS envelope for a persisted or tracked event."""
    return canonical_timestamp(
        source=source,
        reference_frame=reference_frame,
        clock_id=clock_id,
        uncertainty_ns=uncertainty_ns,
        proper_time_ns=proper_time_ns,
        relativistic_correction_ns=relativistic_correction_ns,
    )


def stamp_record(record: dict[str, Any], *, source: str = "orb_weaver") -> dict[str, Any]:
    """Attach canonical ISS fields without removing existing record fields."""
    envelope = event_timestamp(source=source)
    return {
        **record,
        "timestamp": envelope["standard_timestamp"],
        "recorded_at": record.get("recorded_at", envelope["standard_timestamp"]),
        "created_at": record.get("created_at", envelope["standard_timestamp"]),
        "updated_at": envelope["standard_timestamp"],
        "iss_time_ns": envelope["iss_time_ns"],
        "epoch_timestamp_ns": envelope["epoch_timestamp_ns"],
        "standard_timestamp": envelope["standard_timestamp"],
        "julian_timestamp": envelope["julian_timestamp"],
        "iss_timestamp": envelope["iss_timestamp"],
        "iss_stardate": envelope["stardate"],
        "local_display_time": envelope["local_display_time"],
        "proper_time_ns": envelope["proper_time_ns"],
        "mission_elapsed_ns": envelope["mission_elapsed_ns"],
        "relativistic_correction_ns": envelope["relativistic_correction_ns"],
        "iss_reference_frame": envelope["reference_frame"],
        "iss_clock_id": envelope["clock_id"],
        "iss_scale_name": envelope["scale_name"],
        "iss_anchor_hash": _anchor_hash(envelope),
        "timestamp_envelope": envelope,
        "timestamp_schema": "orb_weaver.iss_timestamp.v1",
    }


def _anchor_hash(envelope: dict[str, Any]) -> str:
    return str(envelope.get("anchor_hash") or "")
