from __future__ import annotations

from typing import Any, Dict


def apply_doctrine_gate(candidate: Dict[str, Any], route_record: Dict[str, Any]) -> Dict[str, Any]:
    boundaries = route_record.get("permitted_action_boundaries") or []
    action_class = candidate.get("fifth_mind", {}).get("candidate_action_class", "answer")
    requires_confirmation = any("confirm" in str(item).lower() for item in boundaries)
    blocked = action_class in {"site_modification", "desktop_tool"} and not any(
        "desktop" in str(item).lower() for item in boundaries
    )
    return {
        "allowed": not blocked,
        "action_class": "voice_only" if blocked else action_class,
        "requires_confirmation": requires_confirmation,
        "boundaries": boundaries,
    }

