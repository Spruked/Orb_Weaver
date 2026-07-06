"""
Promotion/rescan rule — the guardrail that prevents one weird page
state (A/B test, cookie banner, logged-in variant, responsive layout)
from corrupting the authoritative map from visitor-session evidence.

This module is called ONLY by Package A's scan process. Package B
(runtime) never imports this — it only writes CandidateCorrection
records and never touches PlotRecord.status.

TODO(integration): wire `load_candidate_corrections` and
`save_pointer_plot_map` to your actual ORB context store (wherever Orb
Weaver already persists scan output). Session agreement is never
ground truth by itself: it can only flag a priority rescan. Only a
fresh Package A scan that independently re-derives the location may
write the authoritative PlotRecord.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from .pointer_plot_schema import CandidateCorrection, PlotRecord, PlotSource, PlotStatus

# Conservative default — flagged as an open decision in the doctrine doc.
# Raise or lower based on real traffic once this is live.
PROMOTION_THRESHOLD_SESSIONS = 3

# Repeated-failure escalation window: if the same target keeps failing
# live recovery within this window, stop attempting live recovery for
# it and flag needs_review instead of making every visitor wait.
STALE_HIT_WINDOW = timedelta(hours=24)
STALE_HIT_THRESHOLD = 3


def load_candidate_corrections(path: Path) -> list[CandidateCorrection]:
    """
    Storage interface for the candidate-correction queue. Package B may
    append to this queue; Package A is the only package allowed to
    evaluate it for promotion into the authoritative map.
    """
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("candidate_corrections", payload if isinstance(payload, list) else [])
    return [CandidateCorrection.parse_obj(row) for row in rows]


def save_candidate_corrections(path: Path, corrections: list[CandidateCorrection]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "orb_weaver.pointer_candidate_corrections.v1",
                "updated_at": datetime.utcnow().isoformat(),
                "candidate_corrections": [correction.dict() for correction in corrections],
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


def append_candidate_correction(path: Path, correction: CandidateCorrection) -> None:
    corrections = load_candidate_corrections(path)
    corrections.append(correction)
    save_candidate_corrections(path, corrections)


def save_pointer_plot_map(path: Path, records: list[PlotRecord]) -> None:
    """
    Writes the authoritative Package A map artifact. This is for scan/rescan
    output only; runtime recovery evidence must use CandidateCorrection.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "orb_weaver.pointer_plot_map.v1",
                "updated_at": datetime.utcnow().isoformat(),
                "record_count": len(records),
                "records": [record.dict() for record in records],
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


def group_corrections_by_target(
    corrections: list[CandidateCorrection],
) -> dict[str, list[CandidateCorrection]]:
    grouped: dict[str, list[CandidateCorrection]] = defaultdict(list)
    for c in corrections:
        grouped[c.target_id].append(c)
    return grouped


def flag_for_priority_rescan(
    target_id: str,
    corrections: list[CandidateCorrection],
    threshold: int = PROMOTION_THRESHOLD_SESSIONS,
) -> tuple[bool, str | None]:
    """
    Returns (needs_priority_rescan, candidate_locator).

    Visitor-session agreement is evidence, not authority. When the SAME
    correction (same new_locator) reaches `threshold`, Package A should
    prioritize a fresh scan/rescan for that target. This function must
    never be used to directly update the authoritative PlotRecord.
    """
    by_locator: dict[str, int] = defaultdict(int)
    for c in corrections:
        if c.target_id != target_id:
            continue
        by_locator[c.new_locator] += c.observed_count

    for locator, count in by_locator.items():
        if count >= threshold:
            return True, locator

    return False, None


def apply_scan_verified_promotion(record: PlotRecord, new_locator: str) -> PlotRecord:
    """
    Produces the updated PlotRecord after Package A's fresh scan/rescan
    independently verifies the candidate location. Session-threshold
    evidence alone must never call this function.
    """
    return record.copy(
        update={
            "semantic_locator": new_locator,
            "status": PlotStatus.ACTIVE,
            "source": PlotSource.LIVE_RECOVERY_PROMOTED,
            "last_verified_at": datetime.utcnow(),
        }
    )


def evaluate_stale_hits(
    target_id: str,
    stale_hit_timestamps: list[datetime],
    window: timedelta = STALE_HIT_WINDOW,
    threshold: int = STALE_HIT_THRESHOLD,
) -> bool:
    """
    Returns True if this target has failed live recovery often enough,
    recently enough, that Package B should stop attempting live
    recovery for it and fall straight to voice-only + needs_review.

    TODO(integration): stale_hit_timestamps should come from wherever
    Package B logs failed-recovery events for a target_id. This
    function is pure logic — wire the actual event log separately.
    """
    cutoff = datetime.utcnow() - window
    recent_hits = [ts for ts in stale_hit_timestamps if ts >= cutoff]
    return len(recent_hits) >= threshold


def mark_needs_review(record: PlotRecord) -> PlotRecord:
    return record.copy(update={"status": PlotStatus.NEEDS_REVIEW})
