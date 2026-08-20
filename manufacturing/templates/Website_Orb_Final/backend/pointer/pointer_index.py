from __future__ import annotations

from typing import Any, Dict, List

from ..runtime.site_world import SiteWorld, normalize_route


def route_pointer_targets(world: SiteWorld, route: str, query: str = "", limit: int = 5) -> List[Dict[str, Any]]:
    normalized = normalize_route(route)
    records = list(world.pointer_by_route.get(normalized, []))
    if not records and normalized != "/":
        records = list(world.pointer_by_route.get("/", []))
    if query:
        records.sort(key=lambda record: _score_record(record, query), reverse=True)
    else:
        records.sort(key=lambda record: float(record.get("confidence") or 0), reverse=True)
    return records[:limit]


def _score_record(record: Dict[str, Any], query: str) -> float:
    text = " ".join(
        str(record.get(field, ""))
        for field in ("target_id", "meaning", "target_type", "semantic_locator")
    ).lower()
    aliases = record.get("direct_aliases") or record.get("intent_aliases") or []
    text += " " + " ".join(str(alias).lower() for alias in aliases)
    words = [part for part in query.lower().split() if len(part) > 2]
    keyword_score = sum(1 for word in words if word in text)
    return keyword_score + float(record.get("confidence") or 0)

