"""Weaver's local vocabulary view of the shared agnostic lexical layer."""
from __future__ import annotations

from functools import lru_cache
import json

from manufacturing.templates.Website_Orb_Final.backend.skg.lexicon import compile_lexicon, resolve_utterance
from app.orb.nine_of_clubs import showcase_guidance_mode


@lru_cache(maxsize=4)
def _compile(snapshot: str) -> tuple[dict, dict]:
    source = json.loads(snapshot)
    nodes = {}
    for record in source["records"]:
        target = record.get("target_id")
        route = record.get("page_route") or record.get("route")
        if not target or not route or not record.get("meaning"):
            continue
        if str(record.get("pointer_health", "")).upper() in {"MISSING", "STALE", "INVALID", "BLOCKED"}:
            continue
        nid = f"pointer:{route}:{target}"
        nodes[nid] = {"id": nid, "kind": "pointer", "label": record["meaning"], "route": route,
                      "target_id": target, "witness_id": record.get("content_fingerprint")}
    for page in source["pages"]:
        route = page.get("route")
        if route and page.get("title"):
            nid = "route:" + route
            nodes[nid] = {"id": nid, "kind": "route", "label": page["title"], "route": route,
                          "witness_id": page.get("content_hash")}
    return compile_lexicon(nodes, source["lexical_index"], "orb-weaver-showcase"), nodes


def weaver_lexical_context(website_context: dict | None, page_capsule: dict | None, utterance: str) -> dict:
    if not showcase_guidance_mode(page_capsule):
        return {}
    context = website_context or {}
    # The server supplies this context from the active site's scan, not a
    # browser-provided alias bank or another customer's graph.
    if context.get("domain") not in {None, "orbweaver.spruked.com", "https://orbweaver.spruked.com", "localhost", "127.0.0.1"}:
        return {}
    snapshot = json.dumps({"records": (context.get("pointer_plot_map") or {}).get("records") or [],
                           "pages": context.get("page_knowledge") or context.get("pages") or [], "lexical_index": context.get("lexical_index") or {}},
                          sort_keys=True, ensure_ascii=False)
    lexicon, nodes = _compile(snapshot)
    match = resolve_utterance(lexicon, utterance)
    return {"schema": "orb_weaver.lexical_guidance.v1", "status": match["status"],
            "candidates": [{"node_id": nid, "label": nodes[nid]["label"][:160], "route": nodes[nid]["route"][:300],
                            "target_id": nodes[nid].get("target_id")} for nid in match["node_ids"][:4]],
            "candidate_count": len(match["node_ids"]), "authority": "advisory_only",
            "rule": "Aliases suggest meanings only. Ask to clarify ambiguous matches; preserve negation. A question is not a navigation request. Live validation and Governor authorization still apply."}
