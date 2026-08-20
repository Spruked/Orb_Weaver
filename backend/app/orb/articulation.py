from __future__ import annotations

import re
from typing import Any, Dict


DOCTRINE_VERSION = "orb-weaver-articulation/1.0.0"
FACTUAL_LANES = {"control", "catalog", "apriori", "posteriori", "site_world"}


def _clean_speech(value: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", str(value or ""))
    text = re.sub(r"[`*_#]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def articulate(resolution: Dict[str, Any], profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
    factual_answer = _clean_speech(str(resolution.get("answer") or ""))
    lane = str(resolution.get("source_lane") or "unknown")
    if not factual_answer:
        factual_answer = "I do not have enough verified information to answer that yet."
    spoken = factual_answer
    checksum_failures = []
    if lane in FACTUAL_LANES and spoken != factual_answer:
        checksum_failures.append("factual_meaning_changed")
        spoken = factual_answer
    if resolution.get("verification_state") == "pending" and "verified" in spoken.lower():
        checksum_failures.append("pending_state_overstated")
        spoken = factual_answer
    return {
        "spoken_text": spoken,
        "trace": {
            "schema": "orb_weaver.articulation_trace.v1",
            "doctrine_version": DOCTRINE_VERSION,
            "source_lane": lane,
            "mode": "deterministic_fact_preservation" if lane in FACTUAL_LANES else "bounded_generated_expression",
            "factual_answer_hash": resolution.get("answer_hash"),
            "profile": (profile or {}).get("voice_profile") or "website_orb_default",
            "checksum": {"passed": not checksum_failures, "failures": checksum_failures},
        },
    }
