"""Bounded vocabulary hints shared by Weaver and manufactured site SKGs.

Alias collisions remain ambiguous. Language matching never authorizes actions.
Generated aliases are vocabulary evidence, not quotes from a site's body text.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import re
import unicodedata

MAX_ALIASES_PER_NODE = 24
MAX_ALIAS_NODES = 4000
MAX_PHRASE_CHARS = 240
PREFIXES = ("where do i ", "information about ", "tell me about ", "take me to ", "where is ",
            "where's ", "where are ", "show me ", "go to ", "jump to ", "info about ",
            "how do i ", "how to ", "i want to ", "i need to ", "find ", "show ", "open ", "locate ")
KINDS = {"button": {"action", "pointer"}, "nav": {"route", "pointer"},
         "heading": {"concept", "entity", "pointer"}, "paragraph": {"concept", "pointer"},
         "section": {"concept", "route", "pointer"}, "form field": {"action", "pointer"}}


def normalize(phrase: str) -> str:
    text = unicodedata.normalize("NFKC", phrase).casefold().replace("’", "'").strip()
    text = re.sub(r"\s+", " ", text)
    while True:
        prefix = next((prefix for prefix in PREFIXES if text.startswith(prefix)), None)
        if not prefix:
            break
        text = text[len(prefix):].strip()
    # Only a leading article is optional. Internal words, negation and product
    # distinctions stay intact ("don't open X" must never collapse to "X").
    text = re.sub(r"^(?:a|an|the)\s+", "", text)
    return text.rstrip("?.!").strip()


def _id(parts) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]


def compile_lexicon(nodes: dict, lexical_index: dict, site_id: str) -> dict:
    by_label = defaultdict(list)
    for nid, node in sorted(nodes.items()):
        kind, separator, label = node.get("label", "").partition(":")
        label = label if separator and kind.strip().casefold() in KINDS else node.get("label", "")
        if node["kind"] != "alias" and normalize(label):
            by_label[normalize(label)].append(nid)
    index, alias_nodes, alias_edges = {}, {}, {}
    per_node = defaultdict(set)
    report = {"alias_keys_seen": 0, "unmatched_keys": 0, "ambiguous_keys": 0,
              "alias_phrases_seen": 0, "alias_nodes_added": 0, "alias_edges_added": 0, "cap_reached": False}

    def reconcile(targets):
        # An action and its physical pointer are two graph views of the same
        # route-scoped target, not two competing meanings. Other collisions
        # (including equal labels on different routes) must remain explicit.
        grouped = {}
        order = {"action": 0, "pointer": 1}
        for nid in sorted(targets, key=lambda value: (order.get(nodes[value]["kind"], 2), value)):
            target = nodes[nid].get("target_id")
            key = (nodes[nid].get("route"), target) if target else ("node", nid)
            grouped.setdefault(key, nid)
        return sorted(grouped.values())

    def add(phrase, targets, key):
        norm = normalize(phrase)
        if not norm or len(norm) > MAX_PHRASE_CHARS:
            return
        if norm not in index and len(index) >= MAX_ALIAS_NODES:
            report["cap_reached"] = True
            return
        for nid in reconcile(targets):
            if norm not in per_node[nid] and len(per_node[nid]) >= MAX_ALIASES_PER_NODE:
                report["cap_reached"] = True
                continue
            per_node[nid].add(norm)
            index.setdefault(norm, set()).add(nid)
            aid = "alias:" + _id([site_id, norm])
            alias_nodes.setdefault(aid, {"id": aid, "kind": "alias", "label": norm,
                                         "source_url": None, "route": None})
            eid = "edge:" + _id([aid, nid])
            alias_edges.setdefault(eid, {"id": eid, "source": aid, "target": nid, "kind": "aliases", "weight": 0.6,
                                         "lexical_witness": {"key": key, "phrase": phrase, "source_kind": "lexical_index",
                                                             "target_witness_id": nodes[nid].get("witness_id")}})

    # Canonical labels participate in the SAME bounded index as aliases.
    for label, targets in sorted(by_label.items()):
        add(label, targets, "canonical_label")
    aliases = lexical_index.get("aliases") or {}
    for raw_key, phrases in sorted(aliases.items()):
        report["alias_keys_seen"] += 1
        kind, separator, label = raw_key.partition(":")
        typed = bool(separator and kind.strip().casefold() in KINDS)
        targets = by_label.get(normalize(label if typed else raw_key), [])
        if typed:
            targets = [nid for nid in targets if nodes[nid]["kind"] in KINDS[kind.strip().casefold()]]
        targets = reconcile(targets)
        if not targets:
            report["unmatched_keys"] += 1
            continue
        if len(targets) > 1:
            report["ambiguous_keys"] += 1
        if not isinstance(phrases, list):
            continue
        for phrase in sorted({p for p in phrases if isinstance(p, str)}):
            report["alias_phrases_seen"] += 1
            add(phrase, targets, raw_key)
    resolved_index = {key: reconcile(value) for key, value in sorted(index.items())}
    resolved_edges = [edge for edge in alias_edges.values()
                      if edge["target"] in resolved_index[alias_nodes[edge["source"]]["label"]]]
    report["alias_nodes_added"], report["alias_edges_added"] = len(alias_nodes), len(resolved_edges)
    return {"schema": "orb_weaver.lexicon.v1", "site_id": site_id,
            "index": resolved_index,
            "nodes": alias_nodes, "edges": resolved_edges, "report": report}


def resolve_utterance(lexicon: dict, utterance: str) -> dict:
    norm = normalize(utterance)
    targets = lexicon.get("index", {}).get(norm, []) if norm else []
    return {"status": "matched" if len(targets) == 1 else "ambiguous" if targets else "unmatched",
            "normalized_phrase": norm, "node_ids": list(targets), "authority": "advisory_only"}


def aliases_for_node(lexicon: dict, node_id: str, limit: int = 8) -> list[str]:
    return [phrase for phrase, targets in lexicon.get("index", {}).items() if node_id in targets][:max(0, limit)]
