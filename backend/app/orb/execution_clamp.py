from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import urlparse

logger = logging.getLogger("orb.execution_clamp")

SAFE_FALLBACK_ACTIONS: List[Dict[str, Any]] = [
    {"type": "move", "target": "safe-corner-top-right", "priority": 0},
    {"type": "speak", "text": "Hello. I am here if you need help.", "priority": 1},
]


@dataclass(frozen=True)
class ClampResult:
    allowed: bool
    node_id: str
    route_classification: str
    target_anchor: str
    semantic_actions: List[Dict[str, Any]]
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "node_id": self.node_id,
            "route_classification": self.route_classification,
            "target_anchor": self.target_anchor,
            "semantic_actions": self.semantic_actions,
            "reason": self.reason,
        }


def _path_from_url(current_url: str) -> str:
    parsed = urlparse((current_url or "").strip())
    if parsed.scheme or parsed.netloc:
        return parsed.path or "/"
    return current_url.split("?", 1)[0].strip() or "/"


def _iter_nodes(graph: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    raw_nodes = graph.get("operational_nodes") or graph.get("nodes") or graph.get("routes") or []
    if isinstance(raw_nodes, Mapping):
        for key, value in raw_nodes.items():
            if isinstance(value, Mapping):
                yield {"id": str(key), **value}
        return
    if isinstance(raw_nodes, list):
        for value in raw_nodes:
            if isinstance(value, Mapping):
                yield value


def _node_path_pattern(node: Mapping[str, Any]) -> Optional[str]:
    raw = node.get("url_pattern") or node.get("path_pattern") or node.get("url") or node.get("path")
    return str(raw).strip() if raw else None


def _route_matches(path: str, node: Mapping[str, Any]) -> bool:
    pattern = _node_path_pattern(node)
    if not pattern:
        return False
    if pattern.startswith(("http://", "https://")):
        pattern = urlparse(pattern).path or "/"
    return path == pattern or fnmatch.fnmatch(path, pattern)


def _state_matches(page_state_flags: Mapping[str, Any], node: Mapping[str, Any]) -> bool:
    required = node.get("page_state_flags") or node.get("state_flags") or node.get("requires") or {}
    if not isinstance(required, Mapping):
        return False
    for key, expected in required.items():
        if page_state_flags.get(str(key)) != expected:
            return False
    return True


def _safe_fallback(reason: str) -> ClampResult:
    logger.info("ORB execution clamped to fallback: %s", reason)
    return ClampResult(
        allowed=False,
        node_id="global_fallback",
        route_classification="unknown_or_needs_review",
        target_anchor="safe-corner-top-right",
        semantic_actions=list(SAFE_FALLBACK_ACTIONS),
        reason=reason,
    )


def clamp_orb_execution(
    current_url: str,
    page_state_flags: Mapping[str, Any],
    validated_topology_graph: Mapping[str, Any],
) -> Dict[str, Any]:
    if not isinstance(current_url, str) or not current_url.strip():
        return _safe_fallback("missing_current_url").to_dict()
    if not isinstance(page_state_flags, Mapping):
        return _safe_fallback("invalid_page_state_flags").to_dict()
    if not isinstance(validated_topology_graph, Mapping):
        return _safe_fallback("invalid_topology_graph").to_dict()

    path = _path_from_url(current_url)
    for node in _iter_nodes(validated_topology_graph):
        classification = str(node.get("classification") or node.get("route_classification") or "unknown_or_needs_review")
        if classification not in {"public_indexable", "public_nonindexable"}:
            continue
        if not _route_matches(path, node):
            continue
        if not _state_matches(page_state_flags, node):
            continue

        actions = node.get("semantic_actions") or node.get("actions") or []
        if not isinstance(actions, list) or not all(isinstance(item, Mapping) for item in actions):
            return _safe_fallback("matched_node_has_invalid_actions").to_dict()

        return ClampResult(
            allowed=True,
            node_id=str(node.get("id") or _node_path_pattern(node) or path),
            route_classification=classification,
            target_anchor=str(node.get("target_anchor") or node.get("anchor") or "safe-corner-top-right"),
            semantic_actions=[dict(item) for item in actions],
            reason="matched_operational_node",
        ).to_dict()

    return _safe_fallback("unmapped_or_unrecognized_page_state").to_dict()
