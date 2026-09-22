from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple


def classify_intent(message: str, route_record: Dict[str, Any]) -> Tuple[str, float]:
    semantic = route_record.get("semantic_guidance") or {}
    if semantic.get("lexical_status") == "ambiguous":
        return "clarify_site_topic", 0.5
    if semantic.get("lexical_status") == "matched":
        return "site_guidance", 1.0
    return "general_site_help", 0.1


def _keyword_score(text: str, keywords: Iterable[str]) -> float:
    hits = 0
    total = 0
    for keyword in keywords:
        key = str(keyword).lower().strip()
        if not key:
            continue
        total += 1
        if key in text:
            hits += 1
    return hits / max(total, 1)
