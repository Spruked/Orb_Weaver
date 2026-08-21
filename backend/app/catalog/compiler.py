"""Deterministic commercial catalog extraction for Website ORB builds.

The catalog is intentionally separate from semantic retrieval and the a-priori /
a-posteriori vaults.  It compiles direct business facts that should be answerable
without an LLM: products, services, SKUs/models, prices, availability, variants,
specifications, and their canonical source URLs.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import hashlib
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urljoin


COMMERCIAL_SCHEMA_TYPES = {
    "product",
    "productgroup",
    "individualproduct",
    "service",
    "offer",
    "aggregateoffer",
    "menuitem",
    "course",
    "softwareapplication",
    "vehicle",
}

AVAILABILITY_MAP = {
    "instock": "in_stock",
    "outofstock": "out_of_stock",
    "preorder": "preorder",
    "presale": "presale",
    "backorder": "backorder",
    "discontinued": "discontinued",
    "limitedavailability": "limited",
    "onlineonly": "online_only",
    "instoreonly": "in_store_only",
    "soldout": "sold_out",
}


def _text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, str):
        cleaned = re.sub(r"\s+", " ", value).strip()
        return cleaned or None
    return None


def _list(value: Any) -> List[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _schema_types(node: Mapping[str, Any]) -> List[str]:
    raw = node.get("@type")
    values = raw if isinstance(raw, list) else [raw]
    return [str(item).strip() for item in values if item]


def _walk_json(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        graph = value.get("@graph")
        if graph is not None:
            yield from _walk_json(graph)
        for key, child in value.items():
            if key == "@graph":
                continue
            if isinstance(child, (Mapping, list)):
                yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _normalize_url(raw: Any, page_url: str) -> Optional[str]:
    value = _text(raw)
    if not value:
        return None
    try:
        return urljoin(page_url, value)
    except Exception:
        return value


def _money(raw: Any) -> Optional[str]:
    value = _text(raw)
    if not value:
        return None
    cleaned = value.replace(",", "").replace("$", "").strip()
    try:
        number = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
        if not match:
            return value
        try:
            number = Decimal(match.group(0))
        except InvalidOperation:
            return value
    normalized = format(number.normalize(), "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def _availability(raw: Any) -> Optional[str]:
    value = _text(raw)
    if not value:
        return None
    token = re.sub(r"[^a-z]", "", value.rsplit("/", 1)[-1].lower())
    return AVAILABILITY_MAP.get(token, value.rsplit("/", 1)[-1].lower())


def _specifications(node: Mapping[str, Any]) -> Dict[str, str]:
    specs: Dict[str, str] = {}
    skip = {
        "@context", "@type", "@id", "name", "description", "url", "image",
        "sku", "mpn", "gtin", "gtin8", "gtin12", "gtin13", "gtin14",
        "brand", "category", "offers", "hasVariant", "isVariantOf", "model",
    }
    for key, raw in node.items():
        if key in skip or key.startswith("@"):
            continue
        if isinstance(raw, (str, int, float, bool)):
            value = _text(raw)
            if value and len(value) <= 240:
                specs[str(key)] = value
        elif isinstance(raw, Mapping) and str(raw.get("@type") or "").lower() == "propertyvalue":
            label = _text(raw.get("name")) or str(key)
            value = _text(raw.get("value"))
            if value:
                specs[label] = value
    for prop in _list(node.get("additionalProperty")):
        if not isinstance(prop, Mapping):
            continue
        label = _text(prop.get("name") or prop.get("propertyID"))
        value = _text(prop.get("value"))
        if label and value:
            specs[label] = value
    return specs


def _brand(node: Mapping[str, Any]) -> Optional[str]:
    raw = node.get("brand")
    if isinstance(raw, Mapping):
        return _text(raw.get("name"))
    return _text(raw)


def _category(node: Mapping[str, Any]) -> Optional[str]:
    raw = node.get("category")
    if isinstance(raw, Mapping):
        return _text(raw.get("name"))
    return _text(raw)


def _offers(node: Mapping[str, Any], page_url: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in _list(node.get("offers")):
        if not isinstance(raw, Mapping):
            continue
        offer_type = (_schema_types(raw) or ["Offer"])[0]
        currency = _text(raw.get("priceCurrency"))
        price = _money(raw.get("price"))
        low = _money(raw.get("lowPrice"))
        high = _money(raw.get("highPrice"))
        if not price and low and high and low == high:
            price = low
        rows.append({
            "type": offer_type,
            "price": price,
            "low_price": low,
            "high_price": high,
            "currency": currency,
            "availability": _availability(raw.get("availability")),
            "url": _normalize_url(raw.get("url"), page_url),
            "seller": _text((raw.get("seller") or {}).get("name")) if isinstance(raw.get("seller"), Mapping) else _text(raw.get("seller")),
            "valid_from": _text(raw.get("validFrom")),
            "price_valid_until": _text(raw.get("priceValidUntil")),
        })
    return [row for row in rows if any(value is not None for key, value in row.items() if key != "type")]


def _entry_id(kind: str, name: str, sku: Optional[str], url: str) -> str:
    seed = "|".join([kind.lower(), name.lower(), (sku or "").lower(), url.lower()])
    return "catalog_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _entry_from_schema(node: Mapping[str, Any], page_url: str) -> Optional[Dict[str, Any]]:
    types = _schema_types(node)
    lowered = {item.lower() for item in types}
    if not lowered.intersection(COMMERCIAL_SCHEMA_TYPES):
        return None
    # Offers are attached to their parent product/service when possible. A bare
    # Offer still becomes an entry only when it carries its own commercial name.
    name = _text(node.get("name"))
    if not name:
        item = node.get("itemOffered")
        if isinstance(item, Mapping):
            name = _text(item.get("name"))
    if not name:
        return None

    primary_type = next((item for item in types if item.lower() in COMMERCIAL_SCHEMA_TYPES), types[0] if types else "CommercialItem")
    item_url = _normalize_url(node.get("url") or node.get("@id"), page_url) or page_url
    sku = _text(node.get("sku") or node.get("mpn") or node.get("model"))
    gtin = next((_text(node.get(key)) for key in ("gtin", "gtin14", "gtin13", "gtin12", "gtin8") if _text(node.get(key))), None)
    offers = _offers(node, page_url)
    variants: List[Dict[str, Any]] = []
    for raw in _list(node.get("hasVariant")):
        if not isinstance(raw, Mapping):
            continue
        variants.append({
            "name": _text(raw.get("name")),
            "sku": _text(raw.get("sku") or raw.get("mpn") or raw.get("model")),
            "url": _normalize_url(raw.get("url") or raw.get("@id"), page_url),
            "offers": _offers(raw, page_url),
            "specifications": _specifications(raw),
        })

    return {
        "catalog_id": _entry_id(primary_type, name, sku, item_url),
        "kind": primary_type,
        "name": name,
        "description": _text(node.get("description")),
        "sku": sku,
        "gtin": gtin,
        "brand": _brand(node),
        "category": _category(node),
        "url": item_url,
        "source_page": page_url,
        "offers": offers,
        "availability": next((offer.get("availability") for offer in offers if offer.get("availability")), None),
        "variants": variants,
        "specifications": _specifications(node),
        "schema_types": types,
        "evidence": ["json_ld"],
        "confidence": 0.98,
    }


def _schema_payloads(page: Any) -> Iterable[Any]:
    for wrapper in getattr(page, "schema_markup", None) or []:
        if isinstance(wrapper, Mapping) and wrapper.get("type") == "json-ld":
            yield wrapper.get("data")
        elif isinstance(wrapper, Mapping):
            yield wrapper


def _fallback_product_entries(page: Any) -> Iterable[Dict[str, Any]]:
    entity_analysis = getattr(page, "entity_analysis", None) or {}
    for raw_name in entity_analysis.get("product_names") or []:
        name = _text(raw_name)
        if not name:
            continue
        url = str(getattr(page, "url", "") or "")
        yield {
            "catalog_id": _entry_id("Product", name, None, url),
            "kind": "Product",
            "name": name,
            "description": None,
            "sku": None,
            "gtin": None,
            "brand": None,
            "category": None,
            "url": url,
            "source_page": url,
            "offers": [],
            "availability": None,
            "variants": [],
            "specifications": {},
            "schema_types": [],
            "evidence": ["entity_extraction"],
            "confidence": 0.62,
        }


def _merge_entry(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    for key in ("description", "sku", "gtin", "brand", "category", "url", "availability"):
        if not merged.get(key) and incoming.get(key):
            merged[key] = incoming[key]
    for key in ("offers", "variants"):
        seen = {repr(item) for item in merged.get(key) or []}
        merged[key] = list(merged.get(key) or []) + [item for item in incoming.get(key) or [] if repr(item) not in seen]
    merged["specifications"] = {**(merged.get("specifications") or {}), **(incoming.get("specifications") or {})}
    merged["schema_types"] = list(dict.fromkeys([*(merged.get("schema_types") or []), *(incoming.get("schema_types") or [])]))
    merged["evidence"] = list(dict.fromkeys([*(merged.get("evidence") or []), *(incoming.get("evidence") or [])]))
    merged["confidence"] = max(float(merged.get("confidence") or 0), float(incoming.get("confidence") or 0))
    return merged


def compile_commercial_catalog(pages: Sequence[Any]) -> Dict[str, Any]:
    """Compile direct commercial facts from completed crawl pages."""
    by_identity: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    source_pages = set()

    for page in pages:
        page_url = str(getattr(page, "url", "") or "")
        if not page_url:
            continue
        for payload in _schema_payloads(page):
            for node in _walk_json(payload):
                entry = _entry_from_schema(node, page_url)
                if not entry:
                    continue
                key = (
                    str(entry.get("kind") or "").lower(),
                    str(entry.get("sku") or entry.get("gtin") or "").lower(),
                    str(entry.get("name") or "").lower(),
                )
                by_identity[key] = _merge_entry(by_identity[key], entry) if key in by_identity else entry
                source_pages.add(page_url)
        for entry in _fallback_product_entries(page):
            key = ("product", "", str(entry["name"]).lower())
            if key not in by_identity:
                by_identity[key] = entry
                source_pages.add(page_url)

    entries = sorted(by_identity.values(), key=lambda item: (str(item.get("kind")), str(item.get("name"))))
    by_name: Dict[str, List[str]] = defaultdict(list)
    by_sku: Dict[str, List[str]] = defaultdict(list)
    by_category: Dict[str, List[str]] = defaultdict(list)
    by_url: Dict[str, List[str]] = defaultdict(list)
    price_index: List[Dict[str, Any]] = []

    priced_entries = 0
    sku_entries = 0
    availability_entries = 0
    variant_count = 0
    specification_count = 0
    service_count = 0
    product_count = 0

    for entry in entries:
        catalog_id = entry["catalog_id"]
        by_name[str(entry.get("name") or "").strip().lower()].append(catalog_id)
        if entry.get("sku"):
            sku_entries += 1
            by_sku[str(entry["sku"]).strip().lower()].append(catalog_id)
        if entry.get("category"):
            by_category[str(entry["category"]).strip().lower()].append(catalog_id)
        if entry.get("url"):
            by_url[str(entry["url"])].append(catalog_id)
        if str(entry.get("kind") or "").lower() == "service":
            service_count += 1
        else:
            product_count += 1
        if entry.get("availability"):
            availability_entries += 1
        variant_count += len(entry.get("variants") or [])
        specification_count += len(entry.get("specifications") or {})
        offers = entry.get("offers") or []
        if any(offer.get("price") or offer.get("low_price") or offer.get("high_price") for offer in offers):
            priced_entries += 1
        for offer in offers:
            if offer.get("price") or offer.get("low_price") or offer.get("high_price"):
                price_index.append({
                    "catalog_id": catalog_id,
                    "name": entry.get("name"),
                    "price": offer.get("price"),
                    "low_price": offer.get("low_price"),
                    "high_price": offer.get("high_price"),
                    "currency": offer.get("currency"),
                    "availability": offer.get("availability"),
                    "url": offer.get("url") or entry.get("url"),
                })

    return {
        "schema": "orb_weaver.commercial_catalog.v1",
        "entry_count": len(entries),
        "product_count": product_count,
        "service_count": service_count,
        "priced_entry_count": priced_entries,
        "sku_model_count": sku_entries,
        "availability_count": availability_entries,
        "variant_count": variant_count,
        "specification_count": specification_count,
        "source_page_count": len(source_pages),
        "entries": entries,
        "indexes": {
            "by_name": dict(by_name),
            "by_sku_model": dict(by_sku),
            "by_category": dict(by_category),
            "by_url": dict(by_url),
            "prices": price_index,
        },
        "runtime_policy": {
            "deterministic_lookup_first": True,
            "llm_required_for_exact_catalog_facts": False,
            "source_evidence_required": True,
        },
    }
