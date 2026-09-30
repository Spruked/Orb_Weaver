"""Calendar-free ISS timekeeping primitives.

Authoritative value is continuous SI nanoseconds from the immutable epoch.
All human-readable forms are pure display conversions.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import hashlib
import time
from typing import Any, Optional

ISS_EPOCH = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
ISS_EPOCH_LABEL = "2000-01-01 00:00:00.000000000 TAI"
ISS_REFERENCE_FRAME = "solar-system-barycentric"
ISS_SCALE_NAME = "Interplanetary Stardate Syncrometer Scale"
ISS_SCALE_DESIGNATION = "ISS"

NANOSECONDS_PER_SECOND = 1_000_000_000
AVERAGE_YEAR_NS = 31_556_952_000_000_000
TAI_UTC_OFFSET_S = 37
TAI_UTC_OFFSET_NS = TAI_UTC_OFFSET_S * NANOSECONDS_PER_SECOND


def _as_utc(dt: Optional[datetime] = None) -> datetime:
    """Return a timezone-aware UTC datetime."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_iss_time_ns(dt: Optional[datetime] = None) -> int:
    """Return continuous integer nanoseconds from the ISS epoch.

    The live path uses ``time.time_ns``. Explicit datetime values are limited
    to Python datetime's microsecond resolution.
    """
    if dt is None:
        utc_ns = time.time_ns()
        epoch_utc_ns = int(ISS_EPOCH.timestamp() * NANOSECONDS_PER_SECOND)
        return utc_ns + TAI_UTC_OFFSET_NS - epoch_utc_ns

    now = _as_utc(dt)
    delta: timedelta = now - ISS_EPOCH
    total_ns = (
        delta.days * 86_400 * NANOSECONDS_PER_SECOND
        + delta.seconds * NANOSECONDS_PER_SECOND
        + delta.microseconds * 1_000
    )
    return total_ns + TAI_UTC_OFFSET_NS


def get_stardate(dt: Optional[datetime] = None) -> float:
    """Display-only stardate = seconds since epoch, rounded to 9 decimals."""
    return round(get_iss_time_ns(dt) / NANOSECONDS_PER_SECOND, 9)


def format_iss_time(
    iss_time_ns: Optional[int] = None,
    precision: str = "milliseconds",
    mission_elapsed_ns: Optional[int] = None,
) -> str:
    """Format the authoritative nanosecond value for human display."""
    raw_ns = get_iss_time_ns() if iss_time_ns is None else int(iss_time_ns)
    sign = "-" if raw_ns < 0 else ""
    raw_ns = abs(raw_ns)
    years, remainder_ns = divmod(raw_ns, AVERAGE_YEAR_NS)
    fractional_thousand = (remainder_ns * 1000) // AVERAGE_YEAR_NS
    display_day_ns = (remainder_ns * 1461 * 86_400 * NANOSECONDS_PER_SECOND) // (4 * AVERAGE_YEAR_NS)
    display_day_ns %= 86_400 * NANOSECONDS_PER_SECOND
    hours, remainder = divmod(display_day_ns, 3_600 * NANOSECONDS_PER_SECOND)
    minutes, remainder = divmod(remainder, 60 * NANOSECONDS_PER_SECOND)
    seconds, nanoseconds = divmod(remainder, NANOSECONDS_PER_SECOND)

    if precision == "nanoseconds":
        subsecond = f".{nanoseconds:09d}"
    elif precision == "seconds":
        subsecond = ""
    else:
        subsecond = f".{nanoseconds // 1_000_000:03d}"

    display = f"{ISS_SCALE_DESIGNATION} {sign}{years:02d}.{fractional_thousand:03d} {hours:02d}:{minutes:02d}:{seconds:02d}{subsecond}"
    if mission_elapsed_ns is not None:
        met = max(0, int(mission_elapsed_ns))
        met_seconds, met_ns = divmod(met, NANOSECONDS_PER_SECOND)
        met_days, met_seconds = divmod(met_seconds, 86_400)
        met_hours, met_seconds = divmod(met_seconds, 3_600)
        met_minutes, met_seconds = divmod(met_seconds, 60)
        display += f"  |  MET {met_days:03d}/{met_hours:02d}:{met_minutes:02d}:{met_seconds:02d}"
        if precision == "nanoseconds":
            display += f".{met_ns:09d}"
        elif precision != "seconds":
            display += f".{met_ns // 1_000_000:03d}"
    return display


def get_julian_date(dt: Optional[datetime] = None) -> float:
    """Return Julian Date for the supplied instant or current UTC."""
    now = _as_utc(dt)
    a = (14 - now.month) // 12
    y = now.year + 4800 - a
    m = now.month + 12 * a - 3
    jdn = now.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    fraction = (now.hour - 12) / 24 + now.minute / 1440 + now.second / 86400 + now.microsecond / 86_400_000_000
    return jdn + fraction


def format_timestamp(dt: Optional[datetime] = None, format_type: str = "iso") -> str:
    """Format a datetime for a derived display."""
    now = _as_utc(dt)
    formats = {
        "iso": now.isoformat(),
        "stardate": f"Stardate {get_stardate(now):.9f}",
        "julian": f"JD {get_julian_date(now):.6f}",
        "human": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    return formats.get(format_type, formats["iso"])


def current_timecodes() -> dict[str, Any]:
    """Return the complete current ISS time envelope."""
    now = _as_utc()
    iss_ns = get_iss_time_ns(now)
    return {
        "iss_time_ns": iss_ns,
        "scale_name": ISS_SCALE_NAME,
        "scale_designation": ISS_SCALE_DESIGNATION,
        "epoch": ISS_EPOCH_LABEL,
        "reference_frame": ISS_REFERENCE_FRAME,
        "iso_timestamp": now.isoformat(),
        "unix_timestamp_ns": int(now.timestamp() * NANOSECONDS_PER_SECOND),
        "stardate": get_stardate(now),
        "julian_date": get_julian_date(now),
        "unix_timestamp": int(now.timestamp()),
        "human_readable": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "tai_utc_offset_ns": TAI_UTC_OFFSET_NS,
        "anchor_hash": _generate_time_anchor_hash(now),
    }


def _generate_time_anchor_hash(dt: datetime) -> str:
    anchor = f"{get_iss_time_ns(dt)}-{get_julian_date(dt)}"
    return hashlib.sha256(anchor.encode()).hexdigest()[:16]


def canonical_timestamp(
    *,
    mission_epoch_ns: Optional[int] = None,
    proper_time_ns: Optional[int] = None,
    uncertainty_ns: Optional[int] = None,
    relativistic_correction_ns: Optional[int] = None,
    clock_id: str = "ISS-PRIMARY-ATOMIC-01",
    source: str = "ISS",
    reference_frame: Optional[str] = None,
    _timecodes: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build the canonical four-concept timestamp envelope."""
    timecodes = _timecodes or current_timecodes()
    mission_elapsed_ns = timecodes["iss_time_ns"] - mission_epoch_ns if mission_epoch_ns is not None else None
    return {
        "iss_time_ns": timecodes["iss_time_ns"],
        "scale_name": ISS_SCALE_NAME,
        "scale_designation": ISS_SCALE_DESIGNATION,
        "epoch": ISS_EPOCH_LABEL,
        "reference_frame": reference_frame or timecodes.get("reference_frame") or ISS_REFERENCE_FRAME,
        "clock_id": clock_id,
        "uncertainty_ns": uncertainty_ns,
        "proper_time_ns": proper_time_ns,
        "mission_elapsed_ns": mission_elapsed_ns,
        "relativistic_correction_ns": relativistic_correction_ns,
        "source": source,
        "local_display_time": timecodes["iso_timestamp"],
        "anchor_hash": timecodes.get("anchor_hash"),
        "epoch_timestamp_ns": timecodes["unix_timestamp_ns"],
        "standard_timestamp": timecodes["iso_timestamp"],
        "julian_timestamp": timecodes["julian_date"],
        "iss_timestamp": format_iss_time(timecodes["iss_time_ns"]),
        "stardate": timecodes["stardate"],
        "human_display": format_iss_time(timecodes["iss_time_ns"], precision="milliseconds", mission_elapsed_ns=mission_elapsed_ns),
        "human_display_precise": format_iss_time(timecodes["iss_time_ns"], precision="nanoseconds", mission_elapsed_ns=mission_elapsed_ns),
    }


def ensure_folder(folder_path: str) -> str:
    """Ensure a folder exists and return its absolute path."""
    folder_path = os.path.abspath(folder_path)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path
