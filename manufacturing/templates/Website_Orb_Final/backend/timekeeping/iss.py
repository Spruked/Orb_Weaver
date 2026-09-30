"""Self-contained ISS timestamp adapter for installed Website ORBs."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
ISS_ROOT = PACKAGE_ROOT / "backend" / "vendor" / "interplanetary_stardate_syncrometer"
if str(ISS_ROOT) not in sys.path:
    sys.path.insert(0, str(ISS_ROOT))

from iss_module import canonical_timestamp  # noqa: E402


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def event_timestamp(
    *,
    source: str = "website_orb_runtime",
    reference_frame: str = "solar-system-barycentric",
    clock_id: str = "ISS-PRIMARY-ATOMIC-01",
    uncertainty_ns: Optional[int] = None,
    proper_time_ns: Optional[int] = None,
    relativistic_correction_ns: Optional[int] = None,
) -> dict[str, Any]:
    return canonical_timestamp(
        source=source,
        reference_frame=reference_frame,
        clock_id=clock_id,
        uncertainty_ns=uncertainty_ns,
        proper_time_ns=proper_time_ns,
        relativistic_correction_ns=relativistic_correction_ns,
    )


def stamp_record(record: dict[str, Any], *, source: str = "website_orb_runtime") -> dict[str, Any]:
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
        "iss_anchor_hash": envelope.get("anchor_hash"),
        "timestamp_envelope": envelope,
        "timestamp_schema": "orb_weaver.iss_timestamp.v1",
    }
