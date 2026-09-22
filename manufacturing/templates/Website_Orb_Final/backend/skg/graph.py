"""Build-time semantic graph and validation shared by manufacturer and clone.

No host-site routes, fixed question counts, model calls, storage or executors.
Graph links describe evidence; they never grant navigation/click authority.
"""
from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import json
import math
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from .lexicon import compile_lexicon

SCHEMA = "orb_weaver.site_skg.v1"
COMPILER = "site-skg/1.0.0"
PRIVATE_CATEGORIES = {"admin", "private", "system"}


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def site_url(value: str, domain: str) -> str | None:
    """Keep query/fragment distinctions, reject foreign origins and credentials."""
    try:
        base = urlsplit("https://" + domain)
        parsed = urlsplit(urljoin("https://" + domain + "/", value))
        if parsed.scheme not in {"http", "https"} or parsed.netloc != base.netloc or parsed.username or parsed.password:
            return None
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, parsed.fragment))
    except (ValueError, TypeError):
        return None


def route_of(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit(("", "", parsed.path or "/", parsed.query, parsed.fragment))


def build_graph(document: dict) -> dict:
    """Compile canonical full-scan evidence, including explicitly verified facts.

    Page records witness route existence only. A content fact requires verified
    evidence. Goals require separate owner approval; centrality is advisory.
    """
    domain, site_id = document["domain"], str(document["site_id"])
    nodes, edges, witnesses = {}, {}, {}
    route_ids, records, diagnostics = {}, {}, []
    excluded_pages = {p["url"] for p in document.get("pages", [])
                      if p.get("route_category") in PRIVATE_CATEGORIES or p.get("usable") is False}
    canonical_terms = [term["term"] for term in (document.get("lexical_index") or {}).get("canonical_terms", [])
                       if isinstance(term, dict) and isinstance(term.get("term"), str)]

    def node(kind, key, label, url, **extra):
        nid = kind + ":" + digest([site_id, key])[:24]
        nodes.setdefault(nid, {"id": nid, "kind": kind, "label": label, "source_url": url,
                               "route": route_of(url) if url else None, **extra})
        return nid

    def witness(record, field, value, source_kind):
        wid = "witness:" + digest([record["source_url"], record["id"], field, value])[:24]
        witnesses[wid] = {"id": wid, "source_url": record["source_url"], "source_id": record["id"],
                          "source_kind": source_kind, "field": field, "text": value,
                          "content_hash": record["content_hash"]}
        return wid

    def edge(source, target, kind, wid):
        eid = "edge:" + digest([source, target, kind, wid])[:24]
        edges[eid] = {"id": eid, "source": source, "target": target, "kind": kind,
                      "weight": 1.0, "witness_id": wid}

    def add_route(url, label):
        rid = node("route", route_of(url), label or url, url)
        route_ids[url] = rid
        return rid

    for page in sorted(document.get("pages", []), key=lambda p: p["url"]):
        url = site_url(page["url"], domain)
        if not url or page.get("route_category") in PRIVATE_CATEGORIES or page.get("usable") is False:
            diagnostics.append({"source_id": page["page_id"], "reason": "excluded_route"})
            continue
        if not page.get("content_hash"):
            continue
        rid = add_route(url, page.get("title"))
        record = {"id": page["page_id"], "source_url": url, "content_hash": page["content_hash"]}
        nodes[rid]["witness_id"] = witness(record, "url", page["url"], "page")

    # Verified evidence can establish a route even for legacy sparse page lists.
    for item in sorted(document.get("evidence", []), key=lambda e: e["evidence_id"]):
        if item.get("verified") is not True or not item.get("content_hash"):
            continue
        url = site_url(item["source_url"], domain)
        if not url or item["source_url"] in excluded_pages:
            diagnostics.append({"source_id": item["evidence_id"], "reason": "excluded_evidence"})
            continue
        if item["evidence_type"] == "policy" and item["payload"].get("owner_approved") is not True:
            continue
        if item["evidence_id"] in records:
            raise ValueError("Duplicate scan evidence identity")
        rid = route_ids.get(url) or add_route(url, None)
        record = {"id": item["evidence_id"], "source_url": url, "content_hash": item["content_hash"]}
        records[item["evidence_id"]] = (item, record, rid)
        nodes[rid].setdefault("witness_id", witness(record, "source_url", item["source_url"], "evidence"))

    for item, record, rid in records.values():
        payload, url = item["payload"], record["source_url"]
        fields = [key for key in ("text", "answer", "description", "name", "title", "label", "heading")
                  if isinstance(payload.get(key), str) and payload[key].strip()]
        if item.get("pointer_target_id"):
            fields = [key for key in fields if key != "label"]
        for field in fields:
            text = payload[field]
            wid = witness(record, "payload." + field, text, "evidence")
            kind = "entity" if field == "name" else "concept"
            label = payload.get("name") or payload.get("title") or payload.get("heading") or text[:160]
            nid = node(kind, [url, item["evidence_id"], field], label, url, text=text, witness_id=wid)
            edge(rid, nid, "mentions", wid)
            # Canonical concepts must themselves be observed in this evidence.
            for term in (payload.get("concepts") or []) + canonical_terms:
                if isinstance(term, str) and term.strip() and re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I):
                    cid = node("concept", ["term", term.casefold()], term, None, witness_id=wid)
                    edge(nid, cid, "mentions", wid)
        target_id = item.get("pointer_target_id")
        if target_id:
            label = payload.get("label") or payload.get("name") or payload.get("title") or target_id
            wid = witness(record, "pointer_target_id", target_id, "evidence")
            pid = node("pointer", [url, target_id], label, url, target_id=target_id,
                       witness_id=wid, requires_live_validation=True)
            edge(rid, pid, "contains", wid)
            if item["evidence_type"] in {"navigation_target", "form"} or payload.get("target_type") in {"button", "form_field", "nav", "download"}:
                aid = node("action", [url, target_id], label, url, target_id=target_id,
                           witness_id=wid, authorization="proposal_only")
                edge(pid, aid, "presents", wid)
        href = payload.get("href")
        if item["evidence_type"] == "navigation_target" and isinstance(href, str):
            destination = site_url(urljoin(url, href), domain)
            if destination in route_ids:
                wid = witness(record, "payload.href", href, "evidence")
                edge(rid, route_ids[destination], "links_to", wid)
            else:
                diagnostics.append({"source_id": item["evidence_id"], "reason": "unresolved_link"})

    route_index = {route_of(url): {"node_id": rid, "node_ids": [], "edge_ids": [], "next_routes": [], "journeys": {}}
                   for url, rid in sorted(route_ids.items())}
    for nid, item in sorted(nodes.items()):
        if item.get("route") in route_index:
            route_index[item["route"]]["node_ids"].append(nid)
    inbound, reverse_links = defaultdict(set), defaultdict(set)
    for eid, item in sorted(edges.items()):
        source = nodes[item["source"]]
        if source.get("route") in route_index:
            route_index[source["route"]]["edge_ids"].append(eid)
        if item["kind"] == "links_to":
            target = nodes[item["target"]]
            inbound[item["target"]].add(item["source"])
            reverse_links[target["route"]].add(source["route"])
            route_index[source["route"]]["next_routes"].append(target["route"])
    goals = []
    for goal in document.get("site_goals", []):
        url = site_url(goal.get("route", ""), domain)
        if goal.get("owner_approved") is not True or url not in route_ids or not goal.get("goal_id") or not goal.get("label"):
            diagnostics.append({"source_id": str(goal.get("goal_id", "")), "reason": "goal_needs_owner_verification"})
            continue
        goal_id, destination = str(goal["goal_id"]), route_of(url)
        if any(g["goal_id"] == goal_id for g in goals):
            raise ValueError("Duplicate site goal id")
        goals.append({"goal_id": goal_id, "label": goal["label"], "destination": route_ids[url], "route": destination})
        # Precompile next hops once. No crawl, graph search, or global ranking
        # on runtime navigation. Cycles/disconnected components are explicit.
        found = {destination: {"status": "arrived", "next_route": None, "remaining_steps": 0}}
        queue = deque([destination])
        while queue:
            target = queue.popleft()
            for source in sorted(reverse_links[target]):
                if source not in found:
                    found[source] = {"status": "reachable", "next_route": target,
                                     "remaining_steps": found[target]["remaining_steps"] + 1}
                    queue.append(source)
        for route, context in route_index.items():
            context["journeys"][goal_id] = found.get(route, {"status": "unreachable", "next_route": None, "remaining_steps": None})
    for context in route_index.values():
        context["next_routes"] = sorted(set(context["next_routes"]))
    actionable_routes = {item["route"] for item in nodes.values() if item["kind"] == "action"}
    ranked_destinations = sorted({rid for rid in route_ids.values() if nodes[rid]["route"] in actionable_routes},
                                 key=lambda nid: (-len(inbound[nid]), nid))
    lexicon = compile_lexicon(nodes, document.get("lexical_index") or {}, site_id)
    nodes.update(lexicon.pop("nodes"))
    all_edges = list(edges.values()) + lexicon.pop("edges")
    graph = {"schema": SCHEMA, "compiler_version": COMPILER, "site_id": site_id, "domain": domain,
             "source_scan_id": str(document["scan_id"]), "source_fingerprint": digest(document),
             "nodes": nodes, "edges": all_edges, "witnesses": witnesses, "lexicon": lexicon,
             "entry_points": sorted(set(route_ids.values())), "route_index": route_index, "goals": goals,
             "destination": ranked_destinations[0] if ranked_destinations else None,
             "destination_status": "suggested_needs_owner_approval" if ranked_destinations else "unknown",
             "destination_candidates": ranked_destinations,
             "diagnostics": diagnostics, "status": "ready" if route_ids else "empty",
             "authority": "advisory_only"}
    validate_graph(graph)
    return graph


def validate_graph(graph: dict, site_id: str | None = None, domain: str | None = None) -> None:
    if graph.get("schema") != SCHEMA or graph.get("authority") != "advisory_only":
        raise ValueError("Invalid site SKG contract")
    if not graph.get("site_id") or not graph.get("domain") or not graph.get("source_fingerprint"):
        raise ValueError("Missing site SKG provenance")
    if (site_id is not None and graph["site_id"] != site_id) or (domain is not None and graph["domain"] != domain):
        raise ValueError("Site SKG belongs to another site")
    nodes, witnesses = graph["nodes"], graph["witnesses"]
    for nid, item in nodes.items():
        if item["id"] != nid or not isinstance(item.get("label"), str) or not item["label"].strip():
            raise ValueError("Invalid SKG node identity or label")
        if item["kind"] == "alias":
            continue
        if item["id"] != nid or item.get("witness_id") not in witnesses:
            raise ValueError("Unwitnessed SKG node")
        if item.get("source_url") and not site_url(item["source_url"], graph["domain"]):
            raise ValueError("Foreign SKG node")
    for item in witnesses.values():
        if not item.get("text") or not item.get("content_hash") or not site_url(item["source_url"], graph["domain"]):
            raise ValueError("Invalid SKG witness")
    for item in graph["edges"]:
        if not math.isfinite(item["weight"]) or item["weight"] <= 0:
            raise ValueError("Invalid SKG edge weight")
        if item["kind"] == "aliases":
            if item["source"] not in nodes or item["target"] not in nodes or item["lexical_witness"]["target_witness_id"] not in witnesses:
                raise ValueError("Dangling SKG alias")
            continue
        if item["source"] not in nodes or item["target"] not in nodes or item["witness_id"] not in witnesses or item["weight"] <= 0:
            raise ValueError("Dangling or invalid SKG edge")
    for route, context in graph["route_index"].items():
        if context["node_id"] not in nodes or nodes[context["node_id"]]["route"] != route:
            raise ValueError("Invalid SKG route index")
        if any(nid not in nodes for nid in context["node_ids"]) or any(target not in graph["route_index"] for target in context["next_routes"]):
            raise ValueError("Dangling SKG route context")
        for goal_id, journey in context["journeys"].items():
            if journey["status"] == "reachable" and journey["next_route"] not in context["next_routes"]:
                raise ValueError("Unwitnessed SKG journey hop")
            if journey["status"] == "reachable":
                following = graph["route_index"][journey["next_route"]]["journeys"][goal_id]
                if following["status"] not in {"reachable", "arrived"} or journey["remaining_steps"] != following["remaining_steps"] + 1:
                    raise ValueError("Non-convergent SKG journey")
    if graph["lexicon"]["site_id"] != graph["site_id"]:
        raise ValueError("Foreign SKG lexicon")
    for phrase, targets in graph["lexicon"]["index"].items():
        if not phrase or not targets or any(nid not in nodes or nodes[nid]["kind"] == "alias" for nid in targets):
            raise ValueError("Invalid SKG lexical index")
