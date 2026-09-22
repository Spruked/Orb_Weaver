"""Read-only, manifest-bound site SKG lookup. No runtime graph compilation."""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json

from ..storage import canonical_vault_root, require_vault_path
from .graph import validate_graph
from .lexicon import resolve_utterance


@lru_cache(maxsize=1)
def _read_graph(path: str, expected_hash: str, site_id: str, domain: str, scan_id: str) -> dict:
    from pathlib import Path
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError("Site SKG hash mismatch")
    graph = json.loads(raw)
    validate_graph(graph, site_id, domain)
    if graph["status"] != "ready" or graph["source_scan_id"] != scan_id:
        raise ValueError("Site SKG empty or stale")
    return graph


def load_site_graph() -> dict:
    root = canonical_vault_root()
    try:
        manifest_path = require_vault_path(root / "payload" / "payload_manifest.json", "SKG manifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        path = require_vault_path(root / "payload" / "apriori" / "site_skg.json", "required site SKG")
        return _read_graph(str(path), manifest["artifacts"]["apriori/site_skg.json"]["sha256"],
                           str(manifest["site_id"]), manifest["domain"], str(manifest["source"]["scan_id"]))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("Required site SKG is missing, invalid or belongs to another build; remanufacture from approved evidence") from exc


def site_guidance_context(route: str, message: str = "") -> dict:
    graph = load_site_graph()
    context = graph["route_index"].get(route)
    match = resolve_utterance(graph["lexicon"], message)
    # Bounded response surface; full graph remains resident, not in the prompt.
    candidates = [{"node_id": nid, "label": graph["nodes"][nid]["label"],
                   "route": graph["nodes"][nid].get("route"),
                   "excerpt": (graph["nodes"][nid].get("text") or "")[:600],
                   "target_id": graph["nodes"][nid].get("target_id")}
                  for nid in match["node_ids"][:8]]
    return {"schema": "orb_weaver.site_skg.context.v1", "site_id": graph["site_id"],
            "source_fingerprint": graph["source_fingerprint"], "authority": "advisory_only",
            "route_status": "known" if context else "unknown", "lexical_status": match["status"],
            "matched_candidates": candidates, "candidate_count": len(match["node_ids"]),
            "next_routes": (context or {}).get("next_routes", [])[:8],
            "journeys": dict(list((context or {}).get("journeys", {}).items())[:8]),
            "action_rule": "Visitor intent, live DOM validation and Governor authorization remain required. Ambiguous aliases require clarification."}
