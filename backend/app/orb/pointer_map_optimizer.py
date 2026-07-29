from __future__ import annotations

import copy
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import median
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from app.orb.pointer_recovery import _candidate_matches_record


DOM_MUTABILITY_VALUES = {
    "static",
    "responsive",
    "dynamic",
    "deferred_js",
    "conditional",
    "unknown",
}


def optimize_pointer_map(
    pointer_map: Dict[str, Any],
    capture: Optional[Dict[str, Any]] = None,
    *,
    shared_alias_ratio: float = 0.70,
    shared_alias_minimum: int = 5,
) -> Dict[str, Any]:
    """Return a backwards-compatible, enriched Pointer Plot Map.

    The optimizer intentionally does not grant new pointer authority. It:

    * classifies DOM mutability from repeated browser observations;
    * stores compact viewport/rectangle observations as evidence-only hints;
    * moves only highly repeated generic topic aliases to a page-level table;
    * leaves direct aliases, locators, confidence, runtime policy, and allowed
      actions unchanged.

    Existing runtimes that ignore the added map-level fields continue to work.
    """

    optimized = copy.deepcopy(pointer_map)
    records = [item for item in optimized.get("records") or [] if isinstance(item, dict)]
    before_bytes = _json_size(pointer_map)

    observations = [
        item
        for item in (capture or {}).get("observations") or []
        if isinstance(item, dict)
    ]
    if observations:
        _enrich_from_capture(records, observations, capture or {})

    shared_topics_by_page, moved_alias_count = _compact_repeated_topic_aliases(
        records,
        shared_alias_ratio=shared_alias_ratio,
        shared_alias_minimum=shared_alias_minimum,
    )

    optimized["records"] = records
    optimized["record_count"] = len(records)
    optimized["by_page"] = _by_page(records)
    if shared_topics_by_page:
        optimized["shared_topics_by_page"] = shared_topics_by_page

    mutability_counts = Counter(
        str(record.get("dom_mutability") or "unknown") for record in records
    )
    optimized["map_extensions"] = {
        **(optimized.get("map_extensions") or {}),
        "schema": "orb_weaver.pointer_plot_extensions.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coordinate_policy": {
            "authority": "evidence_only",
            "may_drive_pointer_action": False,
            "statement": (
                "Observed rectangles may accelerate visual recovery, but live DOM or "
                "accessibility verification remains required before pointing or action."
            ),
        },
        "dom_mutability_values": sorted(DOM_MUTABILITY_VALUES),
        "dom_mutability_counts": dict(mutability_counts),
        "shared_topic_alias_count": sum(len(values) for values in shared_topics_by_page.values()),
        "aliases_moved_from_records": moved_alias_count,
        "source_capture_schema": (capture or {}).get("schema"),
    }

    after_bytes = _json_size(optimized)
    optimized["optimization"] = {
        "schema": "orb_weaver.pointer_map_optimization.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "before_bytes": before_bytes,
        "after_bytes": after_bytes,
        "bytes_saved_before_extension_metadata": max(0, before_bytes - after_bytes),
        "aliases_moved_from_records": moved_alias_count,
        "backwards_compatible": True,
    }
    return optimized


def _enrich_from_capture(
    records: List[Dict[str, Any]],
    observations: List[Dict[str, Any]],
    capture: Dict[str, Any],
) -> None:
    observations_by_route: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    candidates_by_route: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for observation in observations:
        route = _route(observation.get("route") or observation.get("url"))
        observations_by_route[route].append(observation)
        for candidate in observation.get("candidates") or []:
            if not isinstance(candidate, dict):
                continue
            candidates_by_route[route].append({
                **candidate,
                "_render_id": str(observation.get("render_id") or ""),
                "_viewport": str(observation.get("viewport") or "unknown"),
                "_viewport_size": observation.get("viewport_size") or {},
            })

    for record in records:
        route = _route(record.get("page_route"))
        candidates = [
            candidate
            for candidate in candidates_by_route.get(route, [])
            if _candidate_matches_record(candidate, record)
        ]
        route_observations = observations_by_route.get(route, [])
        record["dom_mutability"] = _classify_dom_mutability(candidates, route_observations)
        if candidates:
            record["visual_recovery_hint"] = _visual_recovery_hint(
                candidates,
                capture_generated_at=str(capture.get("generated_at") or ""),
            )


def _classify_dom_mutability(
    candidates: List[Dict[str, Any]],
    route_observations: List[Dict[str, Any]],
) -> str:
    if not candidates:
        return "unknown"

    render_ids = {str(item.get("_render_id") or "") for item in candidates}
    route_render_ids = {
        str(item.get("render_id") or "") for item in route_observations
    }
    viewports = {str(item.get("_viewport") or "unknown") for item in candidates}
    locators = {str(item.get("locator") or "") for item in candidates if item.get("locator")}
    fingerprints = {
        str(item.get("text_fingerprint") or "")
        for item in candidates
        if item.get("text_fingerprint")
    }

    if len(render_ids) == 1:
        return "deferred_js"
    if route_render_ids and render_ids != route_render_ids:
        return "conditional"
    if len(locators) > 1 or len(fingerprints) > 1:
        return "dynamic"
    if len(viewports) > 1 and _geometry_changes_by_viewport(candidates):
        return "responsive"
    return "static"


def _geometry_changes_by_viewport(candidates: List[Dict[str, Any]]) -> bool:
    centers: Dict[str, List[tuple[float, float]]] = defaultdict(list)
    for item in candidates:
        rect = item.get("rect") or {}
        try:
            x = float(rect.get("x") or 0.0)
            y = float(rect.get("y") or 0.0)
            width = float(rect.get("width") or 0.0)
            height = float(rect.get("height") or 0.0)
        except (TypeError, ValueError):
            continue
        centers[str(item.get("_viewport") or "unknown")].append(
            (x + width / 2.0, y + height / 2.0)
        )
    if len(centers) < 2:
        return False
    viewport_centers = [
        (median(point[0] for point in points), median(point[1] for point in points))
        for points in centers.values()
        if points
    ]
    if len(viewport_centers) < 2:
        return False
    first = viewport_centers[0]
    return any(abs(x - first[0]) > 12 or abs(y - first[1]) > 12 for x, y in viewport_centers[1:])


def _visual_recovery_hint(
    candidates: List[Dict[str, Any]],
    *,
    capture_generated_at: str,
) -> Dict[str, Any]:
    by_viewport: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        if isinstance(item.get("rect"), dict):
            by_viewport[str(item.get("_viewport") or "unknown")].append(item)

    observed_viewports: Dict[str, Any] = {}
    for viewport, items in sorted(by_viewport.items()):
        rects = [item.get("rect") or {} for item in items]
        compact_rect = {
            key: round(median(_number(rect.get(key)) for rect in rects), 2)
            for key in ("x", "y", "width", "height")
        }
        viewport_sizes = [
            item.get("_viewport_size") or {}
            for item in items
            if isinstance(item.get("_viewport_size"), dict)
        ]
        viewport_size = viewport_sizes[0] if viewport_sizes else {}
        observed_viewports[viewport] = {
            "viewport_size": {
                "width": int(_number(viewport_size.get("width"))),
                "height": int(_number(viewport_size.get("height"))),
            },
            "median_document_rect": compact_rect,
            "observation_count": len(items),
            "render_ids": sorted({str(item.get("_render_id") or "") for item in items}),
        }

    return {
        "authority": "evidence_only",
        "may_drive_pointer_action": False,
        "coordinate_space": "document_css_pixels",
        "requires_live_dom_or_accessibility_verification": True,
        "captured_at": capture_generated_at or datetime.now(timezone.utc).isoformat(),
        "observed_viewports": observed_viewports,
    }


def _compact_repeated_topic_aliases(
    records: List[Dict[str, Any]],
    *,
    shared_alias_ratio: float,
    shared_alias_minimum: int,
) -> tuple[Dict[str, List[str]], int]:
    records_by_page: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        records_by_page[str(record.get("page_route") or "")].append(record)

    shared_topics_by_page: Dict[str, List[str]] = {}
    moved = 0
    for page_route, page_records in records_by_page.items():
        counts: Counter[str] = Counter()
        display_value: Dict[str, str] = {}
        for record in page_records:
            for alias in record.get("topic_aliases") or []:
                normalized = _normalize(alias)
                if not normalized:
                    continue
                counts[normalized] += 1
                display_value.setdefault(normalized, str(alias).strip())

        threshold = max(
            shared_alias_minimum,
            int(math.ceil(max(1, len(page_records)) * shared_alias_ratio)),
        )
        shared_keys = {alias for alias, count in counts.items() if count >= threshold}
        if not shared_keys:
            continue

        shared_topics_by_page[page_route] = sorted(display_value[key] for key in shared_keys)
        for record in page_records:
            original = list(record.get("topic_aliases") or [])
            compacted = [alias for alias in original if _normalize(alias) not in shared_keys]
            moved += len(original) - len(compacted)
            record["topic_aliases"] = compacted

    return shared_topics_by_page, moved


def _by_page(records: Iterable[Dict[str, Any]]) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = defaultdict(list)
    for record in records:
        target_id = str(record.get("target_id") or "")
        if target_id:
            result[str(record.get("page_route") or "")].append(target_id)
    return dict(result)


def _route(value: Any) -> str:
    raw = str(value or "/")
    parsed = urlparse(raw if "://" in raw else f"https://pointer.invalid{raw if raw.startswith('/') else '/' + raw}")
    return (parsed.path or "/").rstrip("/") or "/"


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _number(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _json_size(value: Dict[str, Any]) -> int:
    return len(json.dumps(value, separators=(",", ":"), default=str).encode("utf-8"))
