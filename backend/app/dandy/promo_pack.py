"""Deterministic promotional intelligence extracted from a completed crawl.

This module deliberately does not invent marketing claims. Every approved claim,
offer, price, and listener URL carries a source page so Dandy can review the
evidence before putting a client into sponsor inventory.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from app.route_policy import is_sensitive_route


DANDY_PACK_SCHEMA = "orb_weaver.dandy_promo_pack.v1"
DANDY_APPROVED_SCHEMA = "orb_weaver.dandy_approved_promo_payload.v1"
_RISKY_CLAIM = re.compile(
    r"\b(best|#1|number one|guarantee(?:d)?|cure|instant|never|always|proven|"
    r"award[- ]winning|revolutionary|world[- ]class|risk[- ]free|no risk)\b",
    re.IGNORECASE,
)
_PRICE = re.compile(r"(?:\$\s?\d[\d,]*(?:\.\d{1,2})?|\b\d[\d,]*(?:\.\d{1,2})?\s?(?:usd|dollars)\b)", re.IGNORECASE)
_CTA = re.compile(r"\b(contact|book|schedule|shop|buy|get started|start|demo|learn more|visit|apply|request|call|join)\b", re.IGNORECASE)
_AUDIENCE = re.compile(r"\b(?:designed|made|built|ideal|great)\s+for\s+([^.!?]{3,100})", re.IGNORECASE)


def _clean(value: Any, limit: int = 320) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n|:-")
    return text[:limit].rstrip()


def _unique(values: Sequence[str], limit: int = 12) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean(value)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def _page_text(page: Mapping[str, Any]) -> list[str]:
    values = [page.get("title"), page.get("h1"), page.get("meta_description")]
    values.extend(page.get("h2_tags") or [])
    semantic = page.get("semantic_analysis") or {}
    for key in ("summary", "description", "text", "content", "snippet"):
        values.append(semantic.get(key))
    return _unique([_clean(value) for value in values if value], limit=18)


def _schema_objects(page: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    objects = page.get("schema_markup") or []
    if isinstance(objects, Mapping):
        objects = [objects]
    return [item for item in objects if isinstance(item, Mapping)]


def _schema_type(item: Mapping[str, Any]) -> str:
    raw = item.get("@type") or item.get("type") or ""
    if isinstance(raw, list):
        return " ".join(str(value) for value in raw)
    return str(raw)


def _first_business_name(pages: Sequence[Mapping[str, Any]], domain: str) -> tuple[str, str | None]:
    for preferred in (r"organization|localbusiness|brand",):
        for page in pages:
            for item in _schema_objects(page):
                if re.search(preferred, _schema_type(item), re.IGNORECASE):
                    name = _clean(item.get("name"), 160)
                    if name:
                        return name, page.get("url")
    for page in pages:
        for value in (page.get("title"), page.get("h1")):
            name = _clean(value, 160)
            if name:
                return re.split(r"\s+[|–—-]\s+", name)[0].strip(), page.get("url")
    for page in pages:
        for item in _schema_objects(page):
            if re.search(r"product|service", _schema_type(item), re.IGNORECASE):
                name = _clean(item.get("name"), 160)
                if name:
                    return name, page.get("url")
    return urlparse(domain if "://" in domain else f"https://{domain}").hostname or domain, None


def _offers(pages: Sequence[Mapping[str, Any]], catalog: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    offers: list[dict[str, Any]] = []
    for page in pages:
        for item in _schema_objects(page):
            item_type = _schema_type(item)
            if not re.search(r"product|service|offer", item_type, re.IGNORECASE):
                continue
            offer = item.get("offers") if isinstance(item.get("offers"), Mapping) else {}
            name = _clean(item.get("name"), 180)
            description = _clean(item.get("description"), 320)
            price = _clean(offer.get("price") or item.get("price"), 80)
            if name:
                offers.append({"name": name, "description": description, "price": price or None, "url": page.get("url"), "source": "schema"})
    for item in (catalog or {}).get("entries", []) if isinstance((catalog or {}).get("entries"), list) else []:
        if not isinstance(item, Mapping):
            continue
        name = _clean(item.get("name") or item.get("title"), 180)
        if name:
            offers.append({"name": name, "description": _clean(item.get("description"), 320), "price": _clean(item.get("price"), 80) or None, "url": item.get("url") or item.get("source_url"), "source": "commercial_catalog"})
    return offers[:20]


def _public_prices(pages: Sequence[Mapping[str, Any]], offers: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    prices = [{"price": offer.get("price"), "url": offer.get("url"), "source": offer.get("source")} for offer in offers if offer.get("price")]
    for page in pages:
        for text in _page_text(page):
            for match in _PRICE.findall(text):
                prices.append({"price": match, "url": page.get("url"), "source": "page_text"})
    seen: set[tuple[str, str]] = set()
    result = []
    for row in prices:
        key = (_clean(row.get("price")), _clean(row.get("url")))
        if key[0] and key not in seen:
            seen.add(key)
            result.append({"price": key[0], "source_url": key[1], "evidence_type": row.get("source")})
    return result[:20]


def _claims(pages: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    approved: list[dict[str, Any]] = []
    risky: list[dict[str, Any]] = []
    for page in pages:
        for text in _page_text(page):
            if len(text) < 18 or text.endswith("?"):
                continue
            target = risky if _RISKY_CLAIM.search(text) else approved
            row = {"claim": text, "source_url": page.get("url"), "evidence_type": "page_text"}
            if target is risky:
                row["reason"] = "Contains promotional or absolute language requiring owner review."
            target.append(row)
    return approved[:20], risky[:20]


def _target_customers(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    audiences: list[dict[str, Any]] = []
    for page in pages:
        for item in _schema_objects(page):
            audience = item.get("audience")
            if isinstance(audience, Mapping):
                label = _clean(audience.get("audienceType") or audience.get("name"), 160)
                if label:
                    audiences.append({"segment": label, "source_url": page.get("url"), "evidence_type": "schema"})
        for text in _page_text(page):
            match = _AUDIENCE.search(text)
            if match:
                audiences.append({"segment": _clean(match.group(1), 160), "source_url": page.get("url"), "evidence_type": "page_text"})
    seen: set[tuple[str, str]] = set()
    result = []
    for row in audiences:
        key = (_clean(row["segment"]).casefold(), _clean(row["source_url"]))
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result[:12]


def build_dandy_promo_pack(
    pages: Sequence[Mapping[str, Any]],
    *,
    domain: str,
    crawl_job_id: int | str | None = None,
    catalog: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a source-grounded Dandy sponsor/promotional pack from crawl pages."""
    page_rows = [
        page for page in pages
        if isinstance(page, Mapping) and page.get("url") and not is_sensitive_route(str(page.get("url")))
    ]
    business_name, business_source = _first_business_name(page_rows, domain)
    offers = _offers(page_rows, catalog)
    catalog_quality = (catalog or {}).get("data_quality") if isinstance(catalog, Mapping) else None
    catalog_quality_status = str((catalog_quality or {}).get("status") or "not_available")
    quality_blocked = catalog_quality_status in {"contaminated", "insufficient", "partial"}
    candidate_claims, risky_claims = _claims(page_rows)
    target_customer = _target_customers(page_rows)
    prices = _public_prices(page_rows, offers)
    listener_urls = _unique([str(page.get("url")) for page in page_rows], limit=30)
    cta_urls = [str(page.get("url")) for page in page_rows if _CTA.search(" ".join(_page_text(page)))]
    cta_url = cta_urls[0] if cta_urls else (listener_urls[0] if listener_urls else None)
    cta_label = "Visit the website" if cta_url else None
    if cta_url:
        for page in page_rows:
            if page.get("url") == cta_url:
                cta_label = next((text for text in _page_text(page) if _CTA.search(text)), cta_label)
                break

    proof_points = candidate_claims[:8]
    differentiators = _unique([row["claim"] for row in candidate_claims if len(row["claim"]) > 40], limit=8)
    what_they_sell = _unique([offer["name"] for offer in offers] + [row["claim"] for row in candidate_claims[:4]], limit=8)
    promo_angles = []
    for offer in offers[:5]:
        promo_angles.append({"angle": f"Spotlight {offer['name']}", "evidence": [offer.get("url")], "approval": "source_grounded"})
    for claim in candidate_claims[:5]:
        promo_angles.append({"angle": claim["claim"], "evidence": [claim.get("source_url")], "approval": "source_grounded"})
    promo_angles = promo_angles[:10]
    offer_line = offers[0]["name"] if offers else (what_they_sell[0] if what_they_sell else "the business")
    claim_line = candidate_claims[0]["claim"] if candidate_claims else f"Learn more about {business_name}."
    destination = cta_url or domain
    ad_reads = {
        "15s": f"Looking for {offer_line}? {business_name} offers {claim_line} Visit {destination} to learn more.",
        "30s": f"This episode is supported by {business_name}. Discover {offer_line}. {claim_line} Visit {destination} for details.",
        "60s": f"Today’s sponsor is {business_name}. Their site highlights {offer_line}. {claim_line} Explore the source and current details at {destination}.",
    }
    offers = [{"offer_id": f"offer_{index:03d}", **offer} for index, offer in enumerate(offers, 1)]
    candidate_claims = [{"claim_id": f"claim_{index:03d}", **claim} for index, claim in enumerate(candidate_claims, 1)]
    risky_claims = [{"claim_id": f"risky_{index:03d}", **claim} for index, claim in enumerate(risky_claims, 1)]
    return {
        "schema": DANDY_PACK_SCHEMA,
        "status": "blocked_quality" if quality_blocked else ("complete" if page_rows else "empty"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {"crawl_job_id": str(crawl_job_id) if crawl_job_id is not None else None, "domain": domain, "page_count": len(page_rows)},
        "business": {"name": business_name, "name_source_url": business_source, "what_they_sell": what_they_sell},
        "offers": offers,
        "catalog_quality": catalog_quality or {"status": "not_available"},
        "pricing_public": prices,
        "proof_points": proof_points,
        "differentiators": differentiators,
        "target_customer": target_customer,
        "promo_angles": promo_angles,
        "cta": {"label": cta_label, "url": cta_url, "approval": "source_grounded" if cta_url else "missing"},
        "candidate_claims": candidate_claims,
        "risky_claims": risky_claims,
        "suggested_ad_reads": ad_reads,
        "sponsor_read_talking_points": _unique([offer["name"] for offer in offers] + differentiators, limit=12),
        "listener_urls": listener_urls,
        "owner_approval": {
            "status": "pending",
            "owner_approved": False,
            "approved_at": None,
            "approved_by": None,
            "approved_claim_ids": [],
            "approved_offer_ids": [],
            "approved_ad_read_ids": [],
            "rule": "Generated source-grounded content is draft material. Explicit owner authorization is required before Dandy production insertion. Catalog quality must be usable before production consideration.",
        },
    }


def build_approved_dandy_payload(pack: Mapping[str, Any]) -> dict[str, Any]:
    """Return only owner-authorized material; fail closed for draft packs."""
    approval = pack.get("owner_approval") if isinstance(pack.get("owner_approval"), Mapping) else {}
    if approval.get("status") != "approved" or approval.get("owner_approved") is not True:
        raise ValueError("Dandy pack has not received explicit owner approval")
    if pack.get("status") == "blocked_quality":
        raise ValueError("Dandy pack is blocked by commercial catalog data quality")

    claim_ids = set(str(value) for value in approval.get("approved_claim_ids") or [])
    offer_ids = set(str(value) for value in approval.get("approved_offer_ids") or [])
    ad_read_ids = set(str(value) for value in approval.get("approved_ad_read_ids") or [])
    claims = [row for row in pack.get("candidate_claims") or [] if row.get("claim_id") in claim_ids]
    offers = [row for row in pack.get("offers") or [] if row.get("offer_id") in offer_ids]
    reads = {
        key: value
        for key, value in (pack.get("suggested_ad_reads") or {}).items()
        if f"ad_read_{key}" in ad_read_ids
    }
    return {
        "schema": DANDY_APPROVED_SCHEMA,
        "source_pack_schema": pack.get("schema"),
        "source": pack.get("source") or {},
        "business": pack.get("business") or {},
        "offers": offers,
        "claims": claims,
        "ad_reads": reads,
        "cta": pack.get("cta") or {},
        "listener_urls": pack.get("listener_urls") or [],
        "owner_approval": {
            "status": "approved",
            "approved_at": approval.get("approved_at"),
            "approved_by": approval.get("approved_by"),
            "approved_claim_ids": sorted(claim_ids),
            "approved_offer_ids": sorted(offer_ids),
            "approved_ad_read_ids": sorted(ad_read_ids),
        },
    }
