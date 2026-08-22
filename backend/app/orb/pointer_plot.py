from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from bs4 import BeautifulSoup, Tag


TARGET_TYPES = {
    "nav",
    "heading",
    "section",
    "paragraph",
    "form_field",
    "button",
    "faq_answer",
    "price_card",
    "policy_line",
    "download",
    "other",
}

SEMANTIC_REFERENCE_TARGET_TYPES = {"heading", "paragraph", "faq_answer", "policy_line"}
LIVE_GUIDANCE_TARGET_TYPES = {"nav", "form_field", "button", "price_card", "download"}
APPROVED_GUIDEABLE_SECTION_HINTS = {
    "signup", "sign up", "register", "contact", "pricing", "price", "plan", "package",
    "checkout", "cart", "preflight", "scan", "marketplace", "download", "demo", "orb",
}


def extract_pointer_plot_records(
    page_route: str,
    soup: BeautifulSoup,
    *,
    semantic_analysis: Optional[Dict[str, Any]] = None,
    entity_analysis: Optional[Dict[str, Any]] = None,
    max_records: int = 500,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    seen: set[str] = set()

    candidates = _candidate_elements(soup)
    for element, target_type in candidates:
        if len(records) >= max_records:
            break
        text = _visible_text(element)
        if not _is_viable_text(text, target_type):
            continue

        locator = _semantic_locator(element)
        if not locator:
            continue

        fingerprint = _fingerprint(text)
        context = _structural_context(element)
        target_id = _target_id(page_route, target_type, locator, fingerprint, context)
        aliases = _alias_groups(text, target_type, semantic_analysis or {}, entity_analysis or {})
        dedupe_key = f"{target_type}:{fingerprint}:{locator}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        pointer_class, admission_reason = _pointer_admission(element, target_type, text, locator, aliases)
        confidence = _confidence(element, target_type, text)
        confidence_class, runtime_policy = pointer_runtime_policy(confidence, pointer_class=pointer_class)
        verified_at = datetime.utcnow().isoformat()
        records.append(
            {
                "target_id": target_id,
                "page_route": page_route,
                "target_type": target_type,
                "pointer_class": pointer_class,
                "pointer_admission_reason": admission_reason,
                "meaning": _summarize_meaning(text, target_type),
                "intent_aliases": aliases["direct_aliases"],
                "direct_aliases": aliases["direct_aliases"],
                "topic_aliases": aliases["topic_aliases"],
                "content_fingerprint": fingerprint,
                "semantic_locator": locator,
                "anchor_strategy": _anchor_strategy(element, target_type),
                "structural_context": context,
                "confidence": confidence,
                "confidence_class": confidence_class,
                "runtime_policy": runtime_policy,
                "confidence_evidence": {
                    "baseline_resolution": "resolved",
                    "verification_resolution": "not_run",
                    "sentinel_resolution": "not_run",
                    "semantic_match": confidence,
                    "structural_stability": confidence,
                    "duplicate_risk": "unknown",
                    "alias_ambiguity": "unknown",
                    "locator_method": _locator_method(locator),
                    "last_verified_time": verified_at,
                    "source_revision": fingerprint,
                },
                "allowed_actions": _default_actions(target_type),
                "status": "active",
                "finding_class": "UNVERIFIED",
                "finding_subreason": "initial_extraction_not_independently_verified",
                "pointer_health": "NEW",
                "last_verified_at": verified_at,
                "source": "scan",
            }
        )

    return records


def pointer_plot_map_from_pages(pages: Iterable[Any]) -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    by_page: Dict[str, List[str]] = {}

    for page in pages:
        url = getattr(page, "url", None) or ""
        semantic = getattr(page, "semantic_analysis", None) or {}
        page_records = semantic.get("pointer_plot_records") or []
        if not isinstance(page_records, list):
            continue
        for record in page_records:
            if not isinstance(record, dict) or not record.get("target_id"):
                continue
            records.append(record)
            by_page.setdefault(url, []).append(record["target_id"])

    _mark_route_locator_conflicts(records)
    diagnostics = pointer_map_diagnostics(records)
    return {
        "schema": "orb_weaver.pointer_plot_map.v1",
        "generated_at": datetime.utcnow().isoformat(),
        "record_count": len(records),
        "guidance_record_count": diagnostics["live_guidance_candidates"],
        "reference_record_count": diagnostics["semantic_reference_records"],
        "diagnostics": diagnostics,
        "records": records,
        "by_page": by_page,
    }


def _candidate_elements(soup: BeautifulSoup) -> List[tuple[Tag, str]]:
    candidates: List[tuple[Tag, str]] = []

    for nav in soup.find_all("nav"):
        for anchor in nav.find_all("a", href=True):
            candidates.append((anchor, "nav"))

    for heading in soup.find_all(["h1", "h2", "h3"]):
        candidates.append((heading, "heading"))

    for section in soup.find_all(["main", "article", "section"]):
        if section.find(["h1", "h2", "h3"]):
            candidates.append((section, "section"))

    for details in soup.find_all("details"):
        candidates.append((details, "faq_answer"))

    for form in soup.find_all("form"):
        candidates.append((form, "section"))
        for field in form.find_all(["input", "select", "textarea"]):
            candidates.append((field, "form_field"))

    for button in soup.find_all(["button"]):
        candidates.append((button, "button"))

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if _looks_like_download(href):
            candidates.append((anchor, "download"))
        elif not anchor.find_parent("nav"):
            candidates.append((anchor, "button"))

    for paragraph in soup.find_all("p"):
        text = _visible_text(paragraph)
        if _looks_like_policy_line(text):
            candidates.append((paragraph, "policy_line"))
        elif 55 <= len(text) <= 360:
            candidates.append((paragraph, "paragraph"))

    for card in soup.find_all(["div", "article", "section"]):
        if _looks_like_price_card(card):
            candidates.append((card, "price_card"))

    return candidates


def _semantic_locator(element: Tag) -> str:
    explicit = _explicit_orb_locator(element)
    if explicit:
        return explicit

    for attr in ("id", "name", "aria-label", "data-testid", "data-test", "data-cy"):
        value = element.get(attr)
        if value:
            return f'{element.name}[{attr}="{_css_escape(str(value))}"]'

    if element.name == "a" and element.get("href"):
        return f'a[href="{_css_escape(str(element.get("href")))}"]'

    role = element.get("role")
    text = _visible_text(element)
    if role and text:
        return f'{element.name}[role="{_css_escape(str(role))}"][data-orb-text="{_fingerprint(text)}"]'

    parent = element.find_parent(["main", "article", "section", "nav", "form", "header", "footer"])
    scope = ""
    if parent and parent is not element:
        parent_id = parent.get("id")
        if parent_id:
            scope = f'#{_css_escape(str(parent_id))} '

    sibling_index = _same_tag_index(element)
    return f"{scope}{element.name}:nth-of-type({sibling_index})"


def _anchor_strategy(element: Tag, target_type: str) -> str:
    if target_type == "heading":
        return "heading_center"
    if target_type == "form_field":
        return "field_center"
    if target_type == "price_card":
        return "card_title"
    if target_type in {"paragraph", "policy_line", "faq_answer"}:
        return "text_start"
    if element.name in {"canvas", "svg"}:
        return "visual_rect"
    return "element_center"


def _structural_context(element: Tag) -> Dict[str, Any]:
    parent = element.find_parent(["main", "article", "section", "nav", "form", "header", "footer"])
    heading = _nearest_heading(element)
    landmark = parent.name if parent else "document"
    parent_locator = _parent_locator(parent) if parent else ""
    return {
        "landmark": landmark,
        "parent_locator": parent_locator,
        "parent_heading": heading,
        "ordinal_in_parent": _ordinal_in_parent(element, parent),
        "tag": element.name,
    }


def _nearest_heading(element: Tag) -> str:
    for previous in element.find_all_previous(["h1", "h2", "h3"], limit=1):
        text = _visible_text(previous)
        if text:
            return text[:120]
    parent = element.find_parent(["section", "article", "main"])
    if parent:
        heading = parent.find(["h1", "h2", "h3"])
        if heading:
            return _visible_text(heading)[:120]
    return ""


def _parent_locator(parent: Optional[Tag]) -> str:
    if not parent:
        return ""
    explicit = _explicit_orb_locator(parent)
    if explicit:
        return explicit
    if parent.get("id"):
        return f'#{_css_escape(str(parent.get("id")))}'
    return f"{parent.name}:nth-of-type({_same_tag_index(parent)})"


def _ordinal_in_parent(element: Tag, parent: Optional[Tag]) -> int:
    siblings = parent.find_all(element.name, recursive=False) if parent else []
    for index, sibling in enumerate(siblings, start=1):
        if sibling is element:
            return index
    return _same_tag_index(element)


def _explicit_orb_locator(element: Tag) -> Optional[str]:
    for attr, value in element.attrs.items():
        if attr == "data-orb-target" and value:
            return f'[data-orb-target="{_css_escape(str(value))}"]'
        if attr.startswith("data-orb-") and value:
            return f'[{attr}="{_css_escape(str(value))}"]'
    return None


def _visible_text(element: Tag) -> str:
    if element.name in {"input", "select", "textarea"}:
        parts = [
            str(element.get("aria-label") or ""),
            str(element.get("placeholder") or ""),
            str(element.get("name") or ""),
        ]
        element_id = element.get("id")
        if element_id:
            label = element.find_parent().find("label", attrs={"for": element_id}) if element.find_parent() else None
            if label:
                parts.append(label.get_text(" ", strip=True))
        return _normalize_text(" ".join(parts))
    return _normalize_text(element.get_text(" ", strip=True))


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _is_viable_text(text: str, target_type: str) -> bool:
    if target_type in {"form_field", "button", "nav", "download"}:
        return len(text) >= 2
    return len(text) >= 12


def _fingerprint(text: str) -> str:
    normalized = _normalize_text(text).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _target_id(page_route: str, target_type: str, semantic_locator: str, content_fingerprint: str, context: Dict[str, Any]) -> str:
    seed = "|".join(
        [
            _canonical_route(page_route),
            target_type,
            semantic_locator,
            str(context.get("parent_locator") or ""),
            content_fingerprint,
        ]
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"target_{digest}"


def _canonical_route(page_route: str) -> str:
    return re.sub(r"https?://[^/]+", "", page_route).rstrip("/") or "/"


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", _normalize_text(value).lower()).strip("-")
    return normalized[:80] or "target"


def _summarize_meaning(text: str, target_type: str) -> str:
    snippet = text if len(text) <= 96 else text[:93].rstrip() + "..."
    return f"{target_type.replace('_', ' ')}: {snippet}"


def _alias_groups(
    text: str,
    target_type: str,
    semantic_analysis: Dict[str, Any],
    entity_analysis: Dict[str, Any],
) -> Dict[str, List[str]]:
    compact = text[:120]
    direct_aliases = [
        compact,
    ]
    if target_type in {"button", "nav", "download", "form_field"}:
        direct_aliases.extend([
            f"go to {text[:80]}",
            f"open {text[:80]}",
            f"find {text[:80]}",
        ])
    elif target_type in {"heading", "section", "price_card"}:
        direct_aliases.extend([
            f"show {text[:80]}",
            f"jump to {text[:80]}",
        ])

    topic_aliases = [
        f"show me {text[:80]}",
        f"where is {text[:80]}",
    ]

    for term in (semantic_analysis.get("top_terms") or [])[:4]:
        value = term.get("term") if isinstance(term, dict) else str(term)
        if value:
            topic_aliases.append(f"information about {value}")

    for key in ("product_names", "organizations", "locations", "schema_org_entities"):
        for value in (entity_analysis.get(key) or [])[:2]:
            topic_aliases.append(f"{target_type.replace('_', ' ')} for {value}")

    return {
        "direct_aliases": _dedupe([_normalize_text(alias) for alias in direct_aliases if alias])[:8],
        "topic_aliases": _dedupe([_normalize_text(alias) for alias in topic_aliases if alias])[:8],
    }


def _confidence(element: Tag, target_type: str, text: str) -> float:
    score = 0.62
    if _explicit_orb_locator(element):
        score += 0.22
    if element.get("id") or element.get("aria-label"):
        score += 0.1
    if target_type in {"heading", "nav", "form_field", "button", "download"}:
        score += 0.06
    if 24 <= len(text) <= 220:
        score += 0.04
    return round(max(0.0, min(score, 0.96)), 2)


def _has_stable_guidance_identity(element: Tag, locator: str, aliases: Dict[str, List[str]]) -> bool:
    if _explicit_orb_locator(element):
        return True
    if element.get("id") or element.get("aria-label") or element.get("role"):
        return True
    if element.name == "a" and element.get("href"):
        return True
    if any(alias for alias in aliases.get("direct_aliases") or []):
        return _locator_method(locator) != "structural_css"
    return False


def _pointer_admission(
    element: Tag,
    target_type: str,
    text: str,
    locator: str,
    aliases: Dict[str, List[str]],
) -> tuple[str, str]:
    if target_type in SEMANTIC_REFERENCE_TARGET_TYPES:
        return "semantic_reference", "semantic_reference_content"
    if target_type == "section":
        combined = f"{text} {' '.join(aliases.get('direct_aliases') or [])}".lower()
        if not any(hint in combined for hint in APPROVED_GUIDEABLE_SECTION_HINTS):
            return "semantic_reference", "section_not_intentionally_guideable"
    if target_type in LIVE_GUIDANCE_TARGET_TYPES or target_type == "section":
        return ("live_guidance", "accepted_as_live_guidance") if _has_stable_guidance_identity(element, locator, aliases) else ("semantic_reference", "missing_stable_guidance_identity")
    return "semantic_reference", "unsupported_target_type_for_guidance"


def mark_route_locator_conflicts(records: List[Dict[str, Any]]) -> None:
    _mark_route_locator_conflicts(records)


def pointer_map_diagnostics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    route_locator: Dict[tuple[str, str], List[str]] = {}
    admission_reasons: Dict[str, int] = {}
    stable_guidance = 0
    unresolved_guidance = 0
    for record in records:
        reason = str(record.get("pointer_admission_reason") or "unknown")
        admission_reasons[reason] = admission_reasons.get(reason, 0) + 1
        if record.get("pointer_class") == "live_guidance":
            route = _canonical_route(str(record.get("page_route") or "/"))
            locator = str(record.get("semantic_locator") or "")
            route_locator.setdefault((route, locator), []).append(str(record.get("target_id") or ""))
            if record.get("confidence_class") in {"VERIFIED", "STABLE"} and (record.get("runtime_policy") or {}).get("may_point") is True:
                stable_guidance += 1
            else:
                unresolved_guidance += 1
    conflicts = [
        {"route": route, "semantic_locator": locator, "target_ids": target_ids, "count": len(target_ids)}
        for (route, locator), target_ids in route_locator.items()
        if locator and len(target_ids) > 1
    ]
    live_guidance = sum(1 for record in records if record.get("pointer_class") == "live_guidance")
    return {
        "schema": "orb_weaver.pointer_plot_diagnostics.v1",
        "raw_record_count": len(records),
        "semantic_reference_records": sum(1 for record in records if record.get("pointer_class") == "semantic_reference"),
        "live_guidance_candidates": live_guidance,
        "unique_verified_guidance_targets": stable_guidance,
        "unresolved_guidance_targets": unresolved_guidance,
        "route_locator_conflict_count": sum(item["count"] - 1 for item in conflicts),
        "route_locator_conflicts": conflicts[:200],
        "admission_reasons": admission_reasons,
        "guidance_readiness_percent": round((stable_guidance / live_guidance) * 100, 2) if live_guidance else 100.0,
    }


def _mark_route_locator_conflicts(records: List[Dict[str, Any]]) -> None:
    grouped: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
    for record in records:
        if record.get("pointer_class") != "live_guidance":
            continue
        locator = str(record.get("semantic_locator") or "")
        if not locator:
            continue
        grouped.setdefault((_canonical_route(str(record.get("page_route") or "/")), locator), []).append(record)
    for group in grouped.values():
        if len(group) <= 1:
            continue
        for record in group:
            record["confidence_class"] = "UNCERTAIN"
            record["finding_class"] = "CONFLICT"
            record["finding_subreason"] = "duplicate_route_locator_conflict"
            record["pointer_admission_reason"] = "duplicate_route_locator_conflict"
            policy = dict(record.get("runtime_policy") or {})
            policy.update({
                "behavior": "explain_without_unverified_point_until_locator_conflict_repaired",
                "may_point": False,
                "must_verify_before_action": True,
                "requires_confirmation": True,
            })
            record["runtime_policy"] = policy


def pointer_runtime_policy(confidence: float, *, pointer_class: str = "live_guidance") -> tuple[str, Dict[str, Any]]:
    """Translate evidence confidence into the product's enforced runtime boundary."""
    if pointer_class != "live_guidance":
        return "REFERENCE", {
            "behavior": "answer_from_site_world_without_pointer_obligation",
            "may_point": False,
            "must_verify_before_action": False,
            "requires_confirmation": False,
        }
    if confidence >= 0.90:
        return "VERIFIED", {
            "behavior": "guide_or_act_within_permission_policy",
            "may_point": True,
            "must_verify_before_action": False,
            "requires_confirmation": False,
        }
    if confidence >= 0.75:
        return "STABLE", {
            "behavior": "guide_and_verify_before_action",
            "may_point": True,
            "must_verify_before_action": True,
            "requires_confirmation": False,
        }
    if confidence >= 0.50:
        return "UNCERTAIN", {
            "behavior": "explain_cautiously_without_unverified_point",
            "may_point": False,
            "must_verify_before_action": True,
            "requires_confirmation": True,
        }
    return "BLOCKED", {
        "behavior": "voice_only_refusal_to_point_or_act",
        "may_point": False,
        "must_verify_before_action": True,
        "requires_confirmation": True,
    }


def _locator_method(locator: str) -> str:
    if locator.startswith("[data-orb-"):
        return "explicit_orb_attribute"
    if "[id=" in locator or locator.startswith("#"):
        return "element_id"
    if "aria-label" in locator:
        return "aria_label"
    if "data-testid" in locator or "data-test" in locator or "data-cy" in locator:
        return "test_attribute"
    return "structural_css"


def _default_actions(target_type: str) -> List[str]:
    if target_type in SEMANTIC_REFERENCE_TARGET_TYPES:
        return []
    if target_type in {"nav", "button"}:
        return ["point", "point_and_confirm_navigate"]
    return ["point"]


def _same_tag_index(element: Tag) -> int:
    index = 1
    sibling = element.previous_sibling
    while sibling is not None:
        if isinstance(sibling, Tag) and sibling.name == element.name:
            index += 1
        sibling = sibling.previous_sibling
    return index


def _css_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _has_button_class(element: Tag) -> bool:
    classes = element.get("class") or []
    return any("button" in str(item).lower() or "btn" in str(item).lower() for item in classes)


def _looks_like_download(href: str) -> bool:
    return bool(re.search(r"\.(pdf|zip|csv|docx?|xlsx?|pptx?)($|[?#])", href or "", flags=re.I))


def _looks_like_policy_line(text: str) -> bool:
    return bool(re.search(r"\b(privacy|terms|refund|cookie|consent|personal data|liability)\b", text or "", flags=re.I))


def _looks_like_price_card(element: Tag) -> bool:
    text = _visible_text(element)
    if len(text) > 520:
        return False
    has_price = bool(re.search(r"[$€£]\s?\d+|\bfree\b|\bper month\b|\bmonthly\b|\byearly\b", text, flags=re.I))
    classes = " ".join(str(item) for item in (element.get("class") or []))
    has_card_class = bool(re.search(r"\b(price|pricing|plan|tier|card)\b", classes, flags=re.I))
    return has_price and has_card_class


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result[:12]
