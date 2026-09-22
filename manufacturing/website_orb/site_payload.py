"""Fresh, site-bound manufacturing inputs and derived semantic indexes."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from manufacturing.templates.Website_Orb_Final.backend.skg.graph import digest, site_url, route_of


def validate_site_inputs(document: dict, source_context: dict, site_config: dict) -> list[str]:
    errors = []
    for section, field, expected in (("storage", "single_vault", True),
                                     ("behavior", "live_target_verification_required", True),
                                     ("behavior", "browser_speech_synthesis", False)):
        if field in site_config.get(section, {}) and site_config[section][field] is not expected:
            errors.append(f"site_config:{section}.{field}:immutable_runtime_boundary")
    for key in ("site_id", "domain"):
        if key in site_config and str(site_config[key]) != str(document[key]):
            errors.append(f"site_config:{key}:cannot_replace_scan_identity")
    for item in document.get("pages", []):
        if not site_url(item["url"], document["domain"]):
            errors.append("evidence:foreign_page_origin")
    for item in document.get("evidence", []):
        if not site_url(item["source_url"], document["domain"]):
            errors.append("evidence:foreign_fact_origin")
        elif route_of(item["source_url"]) != item["route"]:
            errors.append("evidence:fact_route_mismatch")
    # Legacy unbound 'latest_context' is not a valid input to a selected scan.
    if source_context:
        for key, expected in (("site_id", str(document["site_id"])), ("domain", document["domain"]), ("source_scan_id", str(document["scan_id"]))):
            if str(source_context.get(key, "")) != expected:
                errors.append(f"source_context:{key}:does_not_match_selected_scan")
    base_url = site_config.get("base_url", "https://" + document["domain"])
    if not site_url(base_url, document["domain"]) or urlsplit(base_url).path not in {"", "/"}:
        errors.append("site_config:invalid_base_url")
    for origin in site_config.get("allowed_origins", [base_url.rstrip("/")]):
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            errors.append("site_config:invalid_explicit_origin")
    return sorted(set(errors))


def compile_site_intelligence(document: dict, graph: dict) -> dict:
    header = {"site_id": str(document["site_id"]), "domain": document["domain"],
              "source_scan_id": str(document["scan_id"]), "source_fingerprint": graph["source_fingerprint"]}
    chunks, postings = [], {}
    for item in document.get("evidence", []):
        if item.get("verified") is not True or item["route"] not in graph["route_index"]:
            continue
        payload = item["payload"]
        text = payload.get("text") or payload.get("answer") or payload.get("description")
        if not isinstance(text, str) or not text.strip():
            continue
        if item["evidence_type"] == "policy" and payload.get("owner_approved") is not True:
            continue
        cid = "chunk:" + digest([item["evidence_id"], item["content_hash"]])[:24]
        chunks.append({"chunk_id": cid, "source_url": item["source_url"], "route": item["route"],
                       "text": text, "heading": payload.get("heading") or payload.get("title"),
                       "source_evidence_ids": [item["evidence_id"]], "content_hash": item["content_hash"]})
        for word in sorted(set(re.findall(r"\w+", text.casefold()))):
            postings.setdefault(word, []).append(cid)
    lex = document.get("lexical_index") or {}
    return {
        "lexical_index": {**header, "schema": "orb_weaver.site_lexical_index.v1",
                          "canonical_terms": lex.get("canonical_terms") or [], "aliases": lex.get("aliases") or {},
                          "compiled_report": graph["lexicon"]["report"]},
        "knowledge_chunks": {**header, "schema": "orb_weaver.site_knowledge_chunks.v1", "chunks": chunks},
        "retrieval_index": {**header, "schema": "orb_weaver.site_retrieval_index.v1", "postings": postings},
    }
