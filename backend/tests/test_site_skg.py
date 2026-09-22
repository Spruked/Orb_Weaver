from copy import deepcopy
import hashlib
import json

import pytest

from manufacturing.templates.Website_Orb_Final.backend.skg.graph import build_graph, validate_graph
from manufacturing.templates.Website_Orb_Final.backend.skg import lexicon
from manufacturing.website_orb.scan_evidence import scan_evidence
from manufacturing.templates.Website_Orb_Final.backend.skg.runtime import _read_graph


def sample_site(domain="sample.example"):
    def fact(key, route, kind, payload, **extra):
        return {"evidence_id": key, "evidence_type": kind, "source_url": f"https://{domain}{route}", "route": route,
                "content_hash": key + "-hash", "verified": True, "payload": payload, **extra}
    return {"site_id": domain, "domain": domain, "scan_id": "scan-1", "pages": [
        {"page_id": route, "url": f"https://{domain}{route}", "title": title, "content_hash": title}
        for route, title in [("/", "Welcome"), ("/services", "Services"), ("/book", "Reservations"), ("/island", "Archive")]
    ], "evidence": [
        fact("intro", "/", "page_text", {"heading": "Welcome", "text": "Book specialist consultations online."}),
        fact("link1", "/", "navigation_target", {"href": "/services", "label": "Services"}),
        fact("link2", "/services", "navigation_target", {"href": "/book", "label": "Reserve"}),
        fact("cycle", "/services", "navigation_target", {"href": "/", "label": "Home"}),
        fact("button", "/book", "form", {"label": "Reserve", "target_type": "button"}, pointer_target_id="reserve"),
    ], "lexical_index": {"canonical_terms": [{"term": "consultations", "count": 1}],
                          "aliases": {"nav: Reservations": ["make an appointment", "book a visit"]}},
        "site_goals": [{"goal_id": "appointment", "route": "/book", "label": "Book a consultation", "owner_approved": True}]}


def test_graph_has_witnessed_nodes_lexicon_and_emergent_precompiled_paths():
    source = sample_site()
    graph = build_graph(source)
    validate_graph(graph, source["site_id"], source["domain"])
    assert graph == build_graph(deepcopy(source))
    assert graph["route_index"]["/"]["journeys"]["appointment"] == {
        "status": "reachable", "next_route": "/services", "remaining_steps": 2}
    assert graph["route_index"]["/book"]["journeys"]["appointment"]["status"] == "arrived"
    assert graph["route_index"]["/island"]["journeys"]["appointment"]["status"] == "unreachable"
    match = lexicon.resolve_utterance(graph["lexicon"], "show me make an appointment")
    assert match["status"] == "matched"
    assert graph["nodes"][match["node_ids"][0]]["route"] == "/book"
    assert any(n["label"] == "consultations" for n in graph["nodes"].values())
    for edge in graph["edges"]:
        if edge["kind"] != "aliases":
            witness = graph["witnesses"][edge["witness_id"]]
            assert witness["content_hash"]
            assert witness["source_url"].startswith("https://sample.example")
    assert graph["destination_status"] == "suggested_needs_owner_approval"
    assert graph["authority"] == "advisory_only"


def test_empty_graph_and_no_approved_goal_do_not_invent_funnel():
    source = sample_site()
    source.update(pages=[], evidence=[], site_goals=[])
    graph = build_graph(source)
    assert graph["status"] == "empty"
    assert graph["destination"] is None
    assert graph["nodes"] == {}
    source = sample_site()
    source["site_goals"][0]["owner_approved"] = False
    graph = build_graph(source)
    assert graph["goals"] == []
    assert all(not value["journeys"] for value in graph["route_index"].values())


def test_excludes_foreign_unverified_and_broken_evidence_and_dangling_links():
    source = sample_site()
    source["pages"][1]["usable"] = False
    source["evidence"].extend([
        {**source["evidence"][0], "evidence_id": "foreign", "source_url": "https://other.example/", "payload": {"text": "FOREIGN"}},
        {**source["evidence"][0], "evidence_id": "guess", "verified": False, "payload": {"text": "GUESS"}},
    ])
    graph = build_graph(source)
    assert "/services" not in graph["route_index"]
    assert graph["route_index"]["/"]["journeys"]["appointment"]["status"] == "unreachable"
    assert all(n.get("text") not in {"FOREIGN", "GUESS"} for n in graph["nodes"].values())
    assert any(d["reason"] == "unresolved_link" for d in graph["diagnostics"])
    with pytest.raises(ValueError, match="another site"):
        validate_graph(graph, "other.example")
    broken = deepcopy(graph)
    broken["edges"][0]["target"] = "missing"
    with pytest.raises(ValueError, match="Dangling"):
        validate_graph(broken)


def test_lexicon_collisions_negation_unicode_and_caps(monkeypatch):
    nodes = {key: {"kind": "action", "label": "Continue", "route": route, "witness_id": key}
             for key, route in [("one", "/one"), ("two", "/two")]}
    compiled = lexicon.compile_lexicon(nodes, {"aliases": {"button: Continue": ["move ahead"]}}, "site")
    assert lexicon.resolve_utterance(compiled, "show me the Continue")["node_ids"] == ["one", "two"]
    assert lexicon.resolve_utterance(compiled, "move ahead")["status"] == "ambiguous"
    assert lexicon.resolve_utterance(compiled, "don't open Continue")["status"] == "unmatched"
    assert lexicon.resolve_utterance(compiled, "Continue or cancel")["status"] == "unmatched"
    assert lexicon.normalize("Where’s the CAFÉ?") == "café"
    assert lexicon.normalize("where do I start") == "start"
    monkeypatch.setattr(lexicon, "MAX_ALIAS_NODES", 3)
    monkeypatch.setattr(lexicon, "MAX_ALIASES_PER_NODE", 2)
    capped = lexicon.compile_lexicon(nodes, {"aliases": {"button: Continue": [f"phrase {i}" for i in range(100)]}}, "site")
    assert len(capped["index"]) <= 3
    assert len(capped["edges"]) <= 4
    assert capped["report"]["cap_reached"]


def test_lexicon_reconciles_action_and_pointer_but_not_different_routes():
    nodes = {"action": {"kind": "action", "label": "Continue", "target_id": "next", "route": "/", "witness_id": "a"},
             "pointer": {"kind": "pointer", "label": "Continue", "target_id": "next", "route": "/", "witness_id": "p"}}
    compiled = lexicon.compile_lexicon(nodes, {"aliases": {"button: Continue": ["move ahead"]}}, "site")
    assert lexicon.resolve_utterance(compiled, "move ahead")["status"] == "matched"
    assert lexicon.resolve_utterance(compiled, "Continue")["status"] == "matched"


def test_normalizer_supplies_real_scan_content_and_lexical_bank():
    pages = [{"id": 1, "url": "https://sample.example/", "title": "Home", "h1": "Home",
              "status_code": 200, "content_hash": "observed-hash",
              "semantic_analysis": {"content_excerpt": "Actual observed site text."},
              "internal_link_targets": [{"url": "/book", "anchor": "Reserve"}]}]
    document = scan_evidence(site_id="sample", domain="sample.example", scan_id="fresh", captured_at="now",
                             pages=pages, lexical_index={"aliases": {}}, unresolved_urls=[])
    assert document["evidence"][0]["payload"]["text"] == "Actual observed site text."
    assert document["evidence"][1]["payload"]["href"] == "/book"
    assert build_graph(document)["source_scan_id"] == "fresh"
    blocked = scan_evidence(site_id="sample", domain="sample.example", scan_id="fresh", captured_at="now",
                           pages=pages, lexical_index={}, unresolved_urls=[pages[0]["url"]])
    assert blocked["evidence"] == []
    assert build_graph(blocked)["status"] == "empty"


def test_required_graph_loader_rejects_tampering_foreign_site_and_old_scan(tmp_path):
    graph = build_graph(sample_site())
    path = tmp_path / "site_skg.json"
    raw = json.dumps(graph).encode()
    path.write_bytes(raw)
    expected = hashlib.sha256(raw).hexdigest()
    assert _read_graph(str(path), expected, "sample.example", "sample.example", "scan-1")["status"] == "ready"
    with pytest.raises(ValueError, match="another site"):
        _read_graph(str(path), expected, "different-site", "sample.example", "scan-1")
    with pytest.raises(ValueError, match="stale"):
        _read_graph(str(path), expected, "sample.example", "sample.example", "scan-2")
    with pytest.raises(ValueError, match="hash mismatch"):
        _read_graph(str(path), "incorrect-checksum", "sample.example", "sample.example", "scan-1")
