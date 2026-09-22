"""Normalize stored scan observations without inventing settled business facts."""
from __future__ import annotations

from manufacturing.templates.Website_Orb_Final.backend.skg.graph import digest, route_of


def scan_evidence(*, site_id: str, domain: str, scan_id: str, captured_at: str,
                  pages: list[dict], lexical_index: dict, unresolved_urls: list[str]) -> dict:
    normalized, evidence = [], []
    for page in pages:
        url = page["url"]
        semantic = page.get("semantic_analysis") or {}
        content_hash = page.get("content_hash")
        page_id = str(page.get("id") or digest([url, content_hash])[:24])
        category = semantic.get("route_classification") or "unknown"
        if category not in {"public_content", "admin", "transactional", "utility", "system", "private", "unknown"}:
            category = "unknown"
        usable = bool(content_hash and page.get("status_code") == 200 and url not in unresolved_urls)
        normalized.append({"page_id": page_id, "url": url, "route": route_of(url),
                           "title": page.get("title"), "content_hash": content_hash or digest([url, page.get("title")]),
                           "route_category": category, "usable": usable})
        if not usable or category in {"admin", "private", "system"}:
            continue

        def add(kind, key, payload, pointer=None):
            item = {"evidence_id": page_id + ":" + key, "evidence_type": kind,
                    "source_url": url, "route": route_of(url), "content_hash": content_hash,
                    "captured_at": captured_at, "verified": True, "payload": payload}
            if pointer:
                item.update({"pointer_target_id": pointer["target_id"], "selector": pointer.get("semantic_locator")})
            evidence.append(item)

        text = semantic.get("content_excerpt")
        if isinstance(text, str) and text.strip():
            add("page_text", "text", {"text": text, "title": page.get("title"), "heading": page.get("h1")})
        for index, block in enumerate(page.get("schema_markup") or []):
            if not isinstance(block, dict):
                continue
            entries = [block, *(block.get("@graph") or [])]
            for offset, entity in enumerate(entries):
                if isinstance(entity, dict) and isinstance(entity.get("name"), str) and entity["name"].strip():
                    kind = str(entity.get("@type") or "")
                    payload = {"name": entity["name"]}
                    if isinstance(entity.get("description"), str):
                        payload["description"] = entity["description"]
                    offers = entity.get("offers") or {}
                    if isinstance(offers, dict) and offers.get("price") is not None:
                        payload["price"] = {"display_text": str(offers["price"]), "currency": offers.get("priceCurrency")}
                        payload["availability"] = offers.get("availability")
                    payload["sku"] = entity.get("sku")
                    add({"Product": "product", "Service": "service"}.get(kind, "structured_data"), f"schema:{index}:{offset}", payload)
                if isinstance(entity, dict) and entity.get("@type") == "FAQPage":
                    for qindex, question in enumerate(entity.get("mainEntity") or []):
                        if not isinstance(question, dict):
                            continue
                        answer = question.get("acceptedAnswer") or {}
                        if isinstance(answer, dict) and question.get("name") and answer.get("text"):
                            add("faq", f"faq:{index}:{offset}:{qindex}", {"question": question["name"], "answer": answer["text"]})
        for index, link in enumerate(page.get("internal_link_targets") or []):
            if isinstance(link, dict) and link.get("url"):
                add("navigation_target", f"link:{index}", {"href": link["url"], "label": link.get("anchor") or link["url"]})
        for index, pointer in enumerate(semantic.get("pointer_plot_records") or []):
            if not isinstance(pointer, dict) or not pointer.get("target_id") or not pointer.get("meaning"):
                continue
            if str(pointer.get("pointer_health", "")).upper() in {"STALE", "MISSING", "INVALID", "BLOCKED"}:
                continue
            add("other", f"pointer:{index}", {
                "label": pointer["meaning"], "target_type": pointer.get("target_type"),
                "structural_context": pointer.get("structural_context") or {},
                "anchor_strategy": pointer.get("anchor_strategy") or "element_center",
                "aliases": sorted({str(alias) for field in ("direct_aliases", "intent_aliases", "topic_aliases")
                                   for alias in pointer.get(field, []) if isinstance(alias, str)}),
            }, pointer)
            evidence[-1]["confidence"] = float(pointer.get("confidence", 0.55))
    return {"schema": "orb_weaver.full_scan_evidence.v1", "site_id": site_id, "domain": domain,
            "scan_id": scan_id, "captured_at": captured_at, "scanner_version": "orb-weaver-crawl-normalizer/1.1.0",
            "pages": normalized, "evidence": evidence, "lexical_index": lexical_index}
