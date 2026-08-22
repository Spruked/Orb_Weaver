from __future__ import annotations

import hashlib
import re
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import urlparse


NAVIGATION_SCHEMA = "orb_weaver.navigation_world.v1"
WORLD_STATE_SCHEMA = "orbot.world_state_seed.v1"


def build_navigation_world(
    pages: Iterable[Any],
    *,
    project_id: str = "",
    domain: str = "",
    pointer_map: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    page_list = [page for page in pages if page is not None]
    generated_at = datetime.now(timezone.utc).isoformat()
    resolved_domain = _domain(domain, page_list)

    page_by_route: Dict[str, Any] = {}
    for page in page_list:
        route = normalize_route(_get(page, "url", "/"))
        existing = page_by_route.get(route)
        if existing is None or _page_rank(page) > _page_rank(existing):
            page_by_route[route] = page

    pointer_records = _pointer_records(page_list, pointer_map)
    pointer_registry = _build_pointer_registry(pointer_records, pointer_map)
    entity_graph = _build_entity_graph(page_by_route)
    route_graph = _build_route_graph(page_by_route, entity_graph, pointer_registry)
    semantic_tiles = _build_semantic_tiles(page_by_route, route_graph, entity_graph, pointer_registry)

    version_hash = _version_hash(route_graph, entity_graph, pointer_registry, semantic_tiles)
    version = max(1, int(version_hash[:8], 16))
    pointer_version_hash = _pointer_version_hash(pointer_records)
    pointer_map_version = max(1, int(pointer_version_hash[:8], 16)) if pointer_records else 0
    snapshot_id = f"orbweb:{_slug(resolved_domain or 'site')}:{version_hash[:12]}"

    readiness = _guidance_readiness(pointer_registry, pointer_map)
    world_state_seed = {
        "schema": WORLD_STATE_SCHEMA,
        "snapshot_id": snapshot_id,
        "version": version,
        "captured_at": generated_at,
        "authority": "guidance",
        "route_id": "",
        "route_version": 0,
        "pointer_map_version": pointer_map_version,
        "components": [
            "route_graph",
            "localization_index",
            "entity_graph",
            "pointer_registry",
            "semantic_tiles",
        ],
        "forbidden_regions": [],
        "dangerous_capabilities": [],
        "system_load": "normal",
        "etag": f"{snapshot_id}:{version}",
        "extra": {
            "navigation_schema": NAVIGATION_SCHEMA,
            "navigation_world_version": version_hash,
            "pointer_map_revision": pointer_version_hash,
            "guidance_status": readiness["status"],
            "execution_rule": "planning_does_not_authorize_execution",
        },
    }

    world = {
        "schema": NAVIGATION_SCHEMA,
        "project_id": str(project_id or ""),
        "domain": resolved_domain,
        "generated_at": generated_at,
        "version": version_hash,
        "map_model": "topological_site_graph",
        "route_graph": route_graph,
        "localization_index": {
            route: {
                "node_id": node["node_id"],
                "route": route,
                "canonical_url": node.get("url", ""),
                "scanned": True,
            }
            for route, node in route_graph["nodes_by_route"].items()
        },
        "entity_graph": entity_graph,
        "pointer_registry": pointer_registry,
        "semantic_tiles": semantic_tiles,
        "guidance_readiness": readiness,
        "runtime_contract": {
            "localization": "current_url_to_route_node",
            "planning": "shortest_topological_path_over_scanned_routes",
            "semantic_context": "current_tile_plus_bounded_neighbors",
            "pointer_execution": "verified_or_stable_target_plus_live_dom_resolution",
            "authority": "orbot_core4_then_hard_admission_then_execution_permit",
            "hard_rule": "route_planning_and_pointer_lookup_never_authorize_execution",
        },
        "nats_worldstate_contract": {
            "binding_status": "transport_binding_deferred_to_runtime",
            "kv_bucket": "ORB_WORLD_STATE",
            "key_templates": {
                "current_route": "ws.{robot}.route.current",
                "navigation_map": "ws.{robot}.navigation.map",
                "pointer_revision": "ws.{robot}.pointer.revision",
                "semantic_tile": "ws.{robot}.semantic.tile.{node_id}",
            },
            "note": "Orb Weaver compiles state; runtime transport publishes only after deployment.",
        },
        "world_state_seed": world_state_seed,
        "summary": {
            "scanned_route_nodes": route_graph["node_count"],
            "frontier_routes": len(route_graph["frontier_nodes"]),
            "topological_edges": route_graph["edge_count"],
            "unique_entities": entity_graph["entity_count"],
            "entity_relationships": entity_graph["relationship_count"],
            "pointer_targets": pointer_registry["record_count"],
            "guidance_eligible_pointers": pointer_registry["eligible_count"],
            "route_locator_conflicts": pointer_registry["route_locator_conflict_count"],
            "semantic_tiles": len(semantic_tiles),
            "guidance_status": readiness["status"],
        },
    }
    return world


def navigation_world_summary(
    pages: Iterable[Any],
    *,
    project_id: str = "",
    domain: str = "",
    pointer_map: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    world = build_navigation_world(
        pages,
        project_id=project_id,
        domain=domain,
        pointer_map=pointer_map,
    )
    summary = dict(world["summary"])
    return {
        "schema": "orb_weaver.navigation_world_summary.v1",
        **summary,
        "navigation_world_version": world["version"],
        "world_etag": world["world_state_seed"]["etag"],
    }


def localize_route(world: Mapping[str, Any], url_or_route: str) -> Optional[Dict[str, Any]]:
    route = normalize_route(url_or_route)
    index = world.get("localization_index") or {}
    match = index.get(route)
    if isinstance(match, dict):
        return dict(match)
    return None


def plan_route_path(
    world: Mapping[str, Any],
    start: str,
    target: str,
) -> List[str]:
    graph = world.get("route_graph") or {}
    nodes_by_route = graph.get("nodes_by_route") or {}
    node_ids = {str(node.get("node_id")): route for route, node in nodes_by_route.items() if isinstance(node, dict)}

    start_route = _resolve_route_ref(start, nodes_by_route, node_ids)
    target_route = _resolve_route_ref(target, nodes_by_route, node_ids)
    if not start_route or not target_route:
        return []
    if start_route == target_route:
        return [start_route]

    adjacency = graph.get("adjacency") or {}
    queue = deque([(start_route, [start_route])])
    visited = {start_route}
    while queue:
        route, path = queue.popleft()
        for neighbor in adjacency.get(route, []):
            neighbor = normalize_route(neighbor)
            if neighbor not in nodes_by_route or neighbor in visited:
                continue
            if neighbor == target_route:
                return path + [neighbor]
            visited.add(neighbor)
            queue.append((neighbor, path + [neighbor]))
    return []


def semantic_tiles_for_route(
    world: Mapping[str, Any],
    route: str,
    *,
    neighbor_depth: int = 1,
) -> List[Dict[str, Any]]:
    normalized = normalize_route(route)
    tiles = world.get("semantic_tiles") or {}
    graph = world.get("route_graph") or {}
    adjacency = graph.get("undirected_adjacency") or {}
    if normalized not in tiles:
        return []

    depth_limit = max(0, int(neighbor_depth))
    queue = deque([(normalized, 0)])
    visited = {normalized}
    ordered: List[str] = []
    while queue:
        current, depth = queue.popleft()
        ordered.append(current)
        if depth >= depth_limit:
            continue
        for neighbor in adjacency.get(current, []):
            neighbor = normalize_route(neighbor)
            if neighbor in tiles and neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, depth + 1))
    return [dict(tiles[item]) for item in ordered if isinstance(tiles.get(item), dict)]


def _build_route_graph(
    page_by_route: Mapping[str, Any],
    entity_graph: Mapping[str, Any],
    pointer_registry: Mapping[str, Any],
) -> Dict[str, Any]:
    nodes_by_route: Dict[str, Dict[str, Any]] = {}
    route_entity_ids = entity_graph.get("by_route") or {}
    route_pointer_ids = pointer_registry.get("by_route") or {}

    for route, page in sorted(page_by_route.items()):
        url = str(_get(page, "url", "") or "")
        semantic = _mapping(_get(page, "semantic_analysis", {}))
        top_terms = _top_terms(semantic)
        nodes_by_route[route] = {
            "node_id": _route_node_id(route),
            "route": route,
            "url": url,
            "title": _get(page, "title"),
            "h1": _get(page, "h1"),
            "route_class": _route_classification(route),
            "crawl_depth": int(_get(page, "crawl_depth", 0) or 0),
            "status_code": _get(page, "status_code"),
            "indexable": bool(_get(page, "is_indexable", True)),
            "content_hash": _get(page, "content_hash"),
            "topics": top_terms[:20],
            "entity_ids": list(route_entity_ids.get(route, [])),
            "pointer_ids": list(route_pointer_ids.get(route, [])),
        }

    edges: List[Dict[str, Any]] = []
    seen_edges = set()
    frontier: Dict[str, Dict[str, Any]] = {}
    outgoing: Dict[str, set[str]] = defaultdict(set)
    incoming: Dict[str, set[str]] = defaultdict(set)

    for source_route, page in page_by_route.items():
        for link in _list(_get(page, "internal_link_targets", [])):
            if not isinstance(link, Mapping):
                continue
            target_url = str(link.get("url") or "")
            target_route = normalize_route(target_url)
            if target_route == source_route and not str(link.get("anchor") or "").strip():
                continue
            key = (source_route, target_route, str(link.get("anchor") or ""), str(link.get("discovery_zone") or "body"))
            if key in seen_edges:
                continue
            seen_edges.add(key)
            scanned = target_route in nodes_by_route
            edge = {
                "edge_id": _hash_id("edge", "|".join(key)),
                "source_node_id": _route_node_id(source_route),
                "target_node_id": _route_node_id(target_route),
                "source_route": source_route,
                "target_route": target_route,
                "relationship": "internal_link",
                "anchor_text": str(link.get("anchor") or "")[:160],
                "discovery_zone": str(link.get("discovery_zone") or "body"),
                "nofollow": bool(link.get("nofollow")),
                "target_scanned": scanned,
            }
            edges.append(edge)
            if scanned:
                outgoing[source_route].add(target_route)
                incoming[target_route].add(source_route)
            else:
                frontier[target_route] = {
                    "node_id": _route_node_id(target_route),
                    "route": target_route,
                    "url": target_url,
                    "scanned": False,
                    "status": "discovered_not_scanned",
                }

    adjacency = {
        route: sorted(outgoing.get(route, set()))
        for route in nodes_by_route
    }
    incoming_adjacency = {
        route: sorted(incoming.get(route, set()))
        for route in nodes_by_route
    }
    undirected_adjacency = {
        route: sorted(outgoing.get(route, set()) | incoming.get(route, set()))
        for route in nodes_by_route
    }
    return {
        "node_count": len(nodes_by_route),
        "edge_count": len(edges),
        "nodes": list(nodes_by_route.values()),
        "nodes_by_route": nodes_by_route,
        "edges": edges,
        "frontier_nodes": list(frontier.values()),
        "adjacency": adjacency,
        "incoming_adjacency": incoming_adjacency,
        "undirected_adjacency": undirected_adjacency,
    }


def _build_entity_graph(page_by_route: Mapping[str, Any]) -> Dict[str, Any]:
    entities: Dict[str, Dict[str, Any]] = {}
    relationships: List[Dict[str, Any]] = []
    by_route: Dict[str, List[str]] = {}
    route_entity_sets: Dict[str, set[str]] = {}

    fields = {
        "named_entities": "entity",
        "people": "person",
        "organizations": "organization",
        "locations": "location",
        "product_names": "product",
        "schema_org_entities": "schema_type",
    }

    for route, page in sorted(page_by_route.items()):
        analysis = _mapping(_get(page, "entity_analysis", {}))
        current: set[str] = set()
        for field, entity_type in fields.items():
            for raw in _list(analysis.get(field)):
                name = _clean_entity(raw)
                if not name:
                    continue
                entity_id = _entity_id(name)
                current.add(entity_id)
                record = entities.setdefault(
                    entity_id,
                    {
                        "entity_id": entity_id,
                        "name": name,
                        "types": [],
                        "routes": [],
                    },
                )
                if entity_type not in record["types"]:
                    record["types"].append(entity_type)
                if route not in record["routes"]:
                    record["routes"].append(route)

        by_route[route] = sorted(current)
        route_entity_sets[route] = current
        for entity_id in sorted(current):
            relationships.append({
                "relationship_id": _hash_id("rel", f"{route}|mentions|{entity_id}"),
                "source_type": "route",
                "source_id": _route_node_id(route),
                "relationship": "mentions",
                "target_type": "entity",
                "target_id": entity_id,
                "route": route,
            })

    co_occurrence = set()
    for route, entity_ids in route_entity_sets.items():
        ordered = sorted(entity_ids)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                key = (left, right)
                if key in co_occurrence:
                    continue
                co_occurrence.add(key)
                relationships.append({
                    "relationship_id": _hash_id("rel", f"{left}|co_occurs|{right}"),
                    "source_type": "entity",
                    "source_id": left,
                    "relationship": "co_occurs_on_route",
                    "target_type": "entity",
                    "target_id": right,
                    "evidence_route": route,
                })

    for record in entities.values():
        record["types"].sort()
        record["routes"].sort()

    return {
        "entity_count": len(entities),
        "relationship_count": len(relationships),
        "entities": sorted(entities.values(), key=lambda item: (item["name"].lower(), item["entity_id"])),
        "entities_by_id": entities,
        "relationships": relationships,
        "by_route": by_route,
    }


def _build_pointer_registry(
    records: List[Dict[str, Any]],
    pointer_map: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    by_route: Dict[str, List[str]] = defaultdict(list)
    pois: Dict[str, Dict[str, Any]] = {}
    route_locator_groups: Dict[tuple[str, str], List[str]] = defaultdict(list)
    classes: Dict[str, int] = defaultdict(int)
    eligible = 0

    for record in records:
        target_id = str(record.get("target_id") or "")
        if not target_id:
            continue
        route = normalize_route(record.get("page_route") or record.get("page_url") or "/")
        locator = str(record.get("semantic_locator") or "")
        confidence_class = str(record.get("confidence_class") or "UNCERTAIN").upper()
        may_point = bool(_mapping(record.get("runtime_policy")).get("may_point"))
        is_eligible = _pointer_guidance_eligible(record)
        classes[confidence_class] += 1
        eligible += int(is_eligible)
        by_route[route].append(target_id)
        if locator:
            route_locator_groups[(route, locator)].append(target_id)

        pois[target_id] = {
            "target_id": target_id,
            "route": route,
            "target_type": record.get("target_type"),
            "meaning": record.get("meaning"),
            "semantic_locator": locator,
            "content_fingerprint": record.get("content_fingerprint"),
            "structural_context": record.get("structural_context") or {},
            "anchor_strategy": record.get("anchor_strategy"),
            "confidence": float(record.get("confidence") or 0),
            "confidence_class": confidence_class,
            "may_point": may_point,
            "guidance_eligible": is_eligible,
            "must_verify_live_dom": True,
            "allowed_actions": record.get("allowed_actions") or [],
            "pointer_health": record.get("pointer_health"),
            "finding_class": record.get("finding_class"),
        }

    conflicts: List[Dict[str, Any]] = []
    for (route, locator), target_ids in sorted(route_locator_groups.items()):
        unique_ids = sorted(set(target_ids))
        if len(unique_ids) <= 1:
            continue
        conflicts.append({
            "conflict_id": _hash_id("ptrconf", f"{route}|{locator}|{'|'.join(unique_ids)}"),
            "route": route,
            "semantic_locator": locator,
            "target_ids": unique_ids,
            "reason": "multiple_target_ids_share_route_and_locator",
            "execution_policy": "block_locator_until_identity_resolved",
        })

    source_quality = _mapping((pointer_map or {}).get("quality"))
    return {
        "source_schema": (pointer_map or {}).get("schema") if pointer_map else "embedded_page_pointer_records",
        "source_artifact": "pointer_plot_map.json",
        "record_count": len(pois),
        "eligible_count": eligible,
        "confidence_classes": dict(sorted(classes.items())),
        "route_locator_conflict_count": len(conflicts),
        "route_locator_conflicts": conflicts,
        "source_quality": source_quality,
        "pois": pois,
        "by_route": {route: sorted(set(ids)) for route, ids in sorted(by_route.items())},
        "execution_policy": "never_point_from_compiled_locator_without_live_dom_identity_resolution",
    }


def _build_semantic_tiles(
    page_by_route: Mapping[str, Any],
    route_graph: Mapping[str, Any],
    entity_graph: Mapping[str, Any],
    pointer_registry: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    tiles: Dict[str, Dict[str, Any]] = {}
    neighbors = route_graph.get("undirected_adjacency") or {}
    by_route_entities = entity_graph.get("by_route") or {}
    by_route_pointers = pointer_registry.get("by_route") or {}
    pois = pointer_registry.get("pois") or {}

    for route, page in sorted(page_by_route.items()):
        semantic = _mapping(_get(page, "semantic_analysis", {}))
        pointer_ids = list(by_route_pointers.get(route, []))
        eligible_pointer_ids = [
            pointer_id
            for pointer_id in pointer_ids
            if _mapping(pois.get(pointer_id)).get("guidance_eligible") is True
        ]
        excerpt = re.sub(r"\s+", " ", str(semantic.get("content_excerpt") or "")).strip()[:1200]
        tile_payload = {
            "route": route,
            "node_id": _route_node_id(route),
            "title": _get(page, "title"),
            "h1": _get(page, "h1"),
            "topics": _top_terms(semantic)[:24],
            "entity_ids": list(by_route_entities.get(route, [])),
            "pointer_ids": pointer_ids,
            "eligible_pointer_ids": eligible_pointer_ids,
            "neighbor_routes": list(neighbors.get(route, [])),
            "content_excerpt": excerpt,
            "semantic_depth": semantic.get("semantic_depth"),
        }
        tile_payload["tile_version"] = _hash_id(
            "tile",
            f"{route}|{_get(page, 'content_hash', '')}|{'|'.join(pointer_ids)}|{'|'.join(tile_payload['entity_ids'])}",
        )
        tiles[route] = tile_payload
    return tiles


def _guidance_readiness(
    pointer_registry: Mapping[str, Any],
    pointer_map: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    record_count = int(pointer_registry.get("record_count") or 0)
    eligible_count = int(pointer_registry.get("eligible_count") or 0)
    conflicts = int(pointer_registry.get("route_locator_conflict_count") or 0)
    source_quality = _mapping((pointer_map or {}).get("quality"))
    recovery_required = bool(source_quality.get("recovery_required"))

    blockers: List[str] = []
    if record_count == 0:
        blockers.append("NO_POINTER_TARGETS")
    if eligible_count == 0:
        blockers.append("NO_GUIDANCE_ELIGIBLE_POINTERS")
    if conflicts:
        blockers.append("ROUTE_LOCATOR_CONFLICTS")
    if recovery_required:
        blockers.append("POINTER_RECOVERY_REQUIRED")

    if record_count == 0 or eligible_count == 0 or recovery_required:
        status = "BLOCKED"
    elif conflicts:
        status = "DEGRADED"
    else:
        status = "READY"

    route_status: Dict[str, Dict[str, Any]] = {}
    pois = pointer_registry.get("pois") or {}
    conflicts_by_route = defaultdict(int)
    for conflict in pointer_registry.get("route_locator_conflicts") or []:
        if isinstance(conflict, Mapping):
            conflicts_by_route[normalize_route(conflict.get("route"))] += 1
    for route, target_ids in (pointer_registry.get("by_route") or {}).items():
        safe = sum(1 for target_id in target_ids if _mapping(pois.get(target_id)).get("guidance_eligible") is True)
        route_status[route] = {
            "pointer_count": len(target_ids),
            "eligible_count": safe,
            "conflict_count": conflicts_by_route.get(route, 0),
            "status": "ELIGIBLE" if safe and not conflicts_by_route.get(route) else "REVIEW_REQUIRED",
        }

    return {
        "status": status,
        "blockers": blockers,
        "route_status": route_status,
        "planning_available": True,
        "pointer_execution_available": status == "READY",
        "execution_policy": "existing_pointer_recovery_and_live_dom_verification_remain_authoritative",
    }


def _pointer_records(
    page_list: List[Any],
    pointer_map: Optional[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    if pointer_map and isinstance(pointer_map.get("records"), list):
        return [dict(record) for record in pointer_map.get("records", []) if isinstance(record, Mapping)]
    records: List[Dict[str, Any]] = []
    seen = set()
    for page in page_list:
        semantic = _mapping(_get(page, "semantic_analysis", {}))
        for record in _list(semantic.get("pointer_plot_records")):
            if not isinstance(record, Mapping):
                continue
            target_id = str(record.get("target_id") or "")
            dedupe = target_id or repr(sorted(record.items()))
            if dedupe in seen:
                continue
            seen.add(dedupe)
            records.append(dict(record))
    return records


def _pointer_guidance_eligible(record: Mapping[str, Any]) -> bool:
    if record.get("status") not in (None, "active"):
        return False
    if str(record.get("confidence_class") or "") not in {"VERIFIED", "STABLE"}:
        return False
    if _mapping(record.get("runtime_policy")).get("may_point") is not True:
        return False
    if str(record.get("pointer_health") or "") in {"OWNER_REJECTED", "DEPRECATED", "REMOVED"}:
        return False
    if record.get("finding_subreason") == "owner_rejected_pointer_identity":
        return False
    return True


def _version_hash(*objects: Mapping[str, Any]) -> str:
    parts: List[str] = []
    route_graph = objects[0]
    for node in route_graph.get("nodes") or []:
        parts.append(
            f"n:{node.get('route')}:{node.get('content_hash')}:{node.get('status_code')}"
        )
    for edge in route_graph.get("edges") or []:
        parts.append(
            f"e:{edge.get('source_route')}:{edge.get('target_route')}:{edge.get('anchor_text')}"
        )
    entity_graph = objects[1]
    for entity in entity_graph.get("entities") or []:
        parts.append(f"x:{entity.get('entity_id')}:{','.join(entity.get('routes') or [])}")
    pointer_registry = objects[2]
    for target_id, poi in sorted((pointer_registry.get("pois") or {}).items()):
        parts.append(
            f"p:{target_id}:{poi.get('route')}:{poi.get('semantic_locator')}:{poi.get('confidence_class')}"
        )
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _pointer_version_hash(records: List[Dict[str, Any]]) -> str:
    parts = [
        f"{record.get('target_id')}|{normalize_route(record.get('page_route') or '/')}|"
        f"{record.get('semantic_locator')}|{record.get('content_fingerprint')}|{record.get('confidence_class')}"
        for record in records
    ]
    return hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest()


def normalize_route(value: Any) -> str:
    raw = str(value or "/").strip()
    if raw.startswith(("http://", "https://")):
        parsed = urlparse(raw)
        raw = parsed.path or "/"
    if not raw.startswith("/"):
        raw = f"/{raw}"
    raw = raw.split("#", 1)[0].split("?", 1)[0]
    raw = re.sub(r"/{2,}", "/", raw)
    return raw.rstrip("/") or "/"


def _resolve_route_ref(
    value: str,
    nodes_by_route: Mapping[str, Any],
    node_ids: Mapping[str, str],
) -> Optional[str]:
    raw = str(value or "")
    if raw in node_ids:
        return node_ids[raw]
    route = normalize_route(raw)
    return route if route in nodes_by_route else None


def _route_node_id(route: str) -> str:
    return _hash_id("route", normalize_route(route))


def _entity_id(name: str) -> str:
    return _hash_id("entity", _normalize_entity(name))


def _hash_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]}"


def _route_classification(route: str) -> str:
    path = normalize_route(route).lower()
    if path.endswith("/sitemap.xml") or path.endswith("/robots.txt"):
        return "system"
    if path == "/admin" or path.startswith("/admin/"):
        return "admin"
    if path == "/cart" or path.startswith("/cart/") or path == "/checkout" or path.startswith("/checkout/"):
        return "transactional"
    if path in {"/dashboard", "/account"} or path.startswith("/dashboard/") or path.startswith("/account/"):
        return "private"
    if path in {"/login", "/signup", "/artifacts"} or path.startswith("/login/") or path.startswith("/signup/"):
        return "utility"
    return "public_content"


def _top_terms(semantic: Mapping[str, Any]) -> List[str]:
    terms: List[str] = []
    seen = set()
    for item in _list(semantic.get("top_terms")):
        value = item.get("term") if isinstance(item, Mapping) else item
        text = str(value or "").strip()
        lowered = text.lower()
        if text and lowered not in seen:
            terms.append(text)
            seen.add(lowered)
    return terms


def _domain(domain: str, pages: List[Any]) -> str:
    supplied = str(domain or "").strip().lower()
    if supplied:
        parsed = urlparse(supplied if "://" in supplied else f"https://{supplied}")
        return parsed.netloc or supplied
    for page in pages:
        url = str(_get(page, "url", "") or "")
        parsed = urlparse(url)
        if parsed.netloc:
            return parsed.netloc.lower()
    return ""


def _page_rank(page: Any) -> tuple[int, int, int]:
    return (
        int(_get(page, "status_code", 0) == 200),
        int(bool(_get(page, "is_indexable", False))),
        int(_get(page, "word_count", 0) or 0),
    )


def _clean_entity(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:200]


def _normalize_entity(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:64] or "site"


def _get(obj: Any, field: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(field, default)
    return getattr(obj, field, default)


def _mapping(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, (list, tuple, set)) else []
