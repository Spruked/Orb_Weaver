"""Independent two-pass browser verification for extracted pointer candidates.

Pointer extraction is discovery only. This module resolves each live-guidance
candidate against two fresh rendered DOMs, checks target semantics and stable
identity, and grants point authority only when both observations agree. Anything
else remains quarantined from runtime guidance.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag


LIVE_GUIDANCE_TYPES = {"nav", "form_field", "button", "price_card", "download", "section"}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _fingerprint(value: str) -> str:
    return hashlib.sha256(_normalize_text(value).lower().encode("utf-8")).hexdigest()[:16]


def _visible_text(element: Tag) -> str:
    if element.name in {"input", "select", "textarea"}:
        parts = [
            str(element.get("aria-label") or ""),
            str(element.get("placeholder") or ""),
            str(element.get("name") or ""),
        ]
        element_id = element.get("id")
        if element_id:
            root = element.find_parent() or element
            label = root.find("label", attrs={"for": element_id})
            if label:
                parts.append(label.get_text(" ", strip=True))
        return _normalize_text(" ".join(parts))
    return _normalize_text(element.get_text(" ", strip=True))


def _hidden(element: Tag) -> bool:
    current: Optional[Tag] = element
    for _ in range(8):
        if current is None:
            break
        if current.has_attr("hidden") or str(current.get("aria-hidden") or "").lower() == "true":
            return True
        style = str(current.get("style") or "").replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style or "opacity:0" in style:
            return True
        current = current.parent if isinstance(current.parent, Tag) else None
    if element.name == "input" and str(element.get("type") or "").lower() == "hidden":
        return True
    return False


def _expected_tag(record: Dict[str, Any], element: Tag) -> bool:
    target_type = str(record.get("target_type") or "")
    if target_type == "form_field":
        return element.name in {"input", "select", "textarea"}
    if target_type == "nav":
        return element.name in {"a", "button"}
    if target_type == "download":
        return element.name == "a" and bool(element.get("href"))
    if target_type == "button":
        return element.name in {"a", "button", "input"} or str(element.get("role") or "").lower() == "button"
    if target_type in {"price_card", "section"}:
        return element.name in {"section", "article", "div", "main", "form"}
    return target_type in LIVE_GUIDANCE_TYPES


def _synthetic_role_locator(locator: str) -> Optional[Tuple[str, str, str]]:
    match = re.fullmatch(
        r'([a-zA-Z0-9_-]+)\[role="([^"]+)"\]\[data-orb-text="([a-f0-9]{16})"\]',
        locator.strip(),
    )
    return (match.group(1), match.group(2), match.group(3)) if match else None


def _resolve(soup: BeautifulSoup, record: Dict[str, Any]) -> List[Tag]:
    locator = str(record.get("semantic_locator") or "").strip()
    if not locator:
        return []
    synthetic = _synthetic_role_locator(locator)
    if synthetic:
        tag, role, fingerprint = synthetic
        return [
            element for element in soup.find_all(tag, attrs={"role": role})
            if _fingerprint(_visible_text(element)) == fingerprint
        ]
    try:
        selected = soup.select(locator)
    except Exception:
        return []
    return [element for element in selected if isinstance(element, Tag)]


def _signature(element: Tag) -> Dict[str, Any]:
    return {
        "tag": element.name,
        "id": str(element.get("id") or ""),
        "name": str(element.get("name") or ""),
        "role": str(element.get("role") or ""),
        "aria_label": str(element.get("aria-label") or ""),
        "href": str(element.get("href") or ""),
        "type": str(element.get("type") or ""),
        "text_fingerprint": _fingerprint(_visible_text(element)),
    }


def _identity_consistent(first: Dict[str, Any], second: Dict[str, Any], expected_fingerprint: str) -> bool:
    if first.get("tag") != second.get("tag"):
        return False
    for key in ("id", "name", "role", "aria_label", "href", "type"):
        a = str(first.get(key) or "")
        b = str(second.get(key) or "")
        if a or b:
            if a != b:
                return False
    first_fp = str(first.get("text_fingerprint") or "")
    second_fp = str(second.get("text_fingerprint") or "")
    if expected_fingerprint:
        return first_fp == expected_fingerprint and second_fp == expected_fingerprint
    return bool(first_fp and first_fp == second_fp)


def verify_pointer_records(
    records: Iterable[Dict[str, Any]],
    first_html: str,
    second_html: str,
    page_url: str,
) -> Dict[str, Any]:
    source_records = [dict(record) for record in records if isinstance(record, dict)]
    first_soup = BeautifulSoup(first_html or "", "lxml")
    second_soup = BeautifulSoup(second_html or "", "lxml")

    locator_counts = Counter(
        str(record.get("semantic_locator") or "")
        for record in source_records
        if record.get("pointer_class") == "live_guidance" and record.get("semantic_locator")
    )

    verified = 0
    unresolved = 0
    reference = 0
    reasons = Counter()
    verified_ids: List[str] = []

    for record in source_records:
        if record.get("pointer_class") != "live_guidance" or str(record.get("target_type") or "") not in LIVE_GUIDANCE_TYPES:
            reference += 1
            continue

        locator = str(record.get("semantic_locator") or "")
        reason: Optional[str] = None
        if not locator:
            reason = "locator_missing"
        elif locator_counts[locator] > 1:
            reason = "duplicate_route_locator_conflict"
        else:
            first_matches = _resolve(first_soup, record)
            second_matches = _resolve(second_soup, record)
            if len(first_matches) != 1 or len(second_matches) != 1:
                reason = "locator_not_unique_on_both_passes"
            elif _hidden(first_matches[0]) or _hidden(second_matches[0]):
                reason = "element_hidden_on_rendered_pass"
            elif not _expected_tag(record, first_matches[0]) or not _expected_tag(record, second_matches[0]):
                reason = "resolved_element_type_mismatch"
            else:
                first_sig = _signature(first_matches[0])
                second_sig = _signature(second_matches[0])
                expected_fp = str(record.get("content_fingerprint") or "")
                if not _identity_consistent(first_sig, second_sig, expected_fp):
                    reason = "identity_or_content_changed_between_passes"
                else:
                    now = datetime.now(timezone.utc).isoformat()
                    record["confidence_class"] = "VERIFIED"
                    record["lifecycle_state"] = "REVERIFIED"
                    record["finding_class"] = "CONFIRMED"
                    record["finding_subreason"] = "consistent_independent_browser_rescan"
                    record["pointer_health"] = "VERIFIED"
                    record["runtime_policy"] = {
                        "behavior": "guide_and_live_verify_before_action",
                        "may_point": True,
                        "must_verify_before_action": True,
                        "requires_confirmation": False,
                    }
                    record["confidence_evidence"] = {
                        **(record.get("confidence_evidence") or {}),
                        "baseline_resolution": "observed_once",
                        "verification_resolution": "resolved_on_first_render_and_reverified_on_second_render",
                        "sentinel_resolution": "rendered_rescan_passed",
                        "browser_verification_passes": 2,
                        "first_signature": first_sig,
                        "second_signature": second_sig,
                        "last_verified_time": now,
                        "verified_page_url": page_url,
                    }
                    record["last_verified_at"] = now
                    verified += 1
                    verified_ids.append(str(record.get("target_id") or ""))

        if reason:
            unresolved += 1
            reasons[reason] += 1
            record["confidence_class"] = "UNVERIFIED"
            record["lifecycle_state"] = "QUARANTINED"
            record["finding_class"] = "CONFLICT" if "conflict" in reason else "UNVERIFIED"
            record["finding_subreason"] = reason
            record["pointer_health"] = "QUARANTINED"
            record["runtime_policy"] = {
                "behavior": "explain_without_unverified_point",
                "may_point": False,
                "must_verify_before_action": True,
                "requires_confirmation": True,
            }
            record["confidence_evidence"] = {
                **(record.get("confidence_evidence") or {}),
                "verification_resolution": "failed_two_pass_browser_verification",
                "sentinel_resolution": "not_authorized_for_guidance",
                "browser_verification_failure": reason,
            }
            record.pop("last_verified_at", None)

    return {
        "schema": "orb_weaver.pointer_browser_verification.v1",
        "records": source_records,
        "summary": {
            "candidate_count": verified + unresolved,
            "verified_and_reverified_count": verified,
            "quarantined_count": unresolved,
            "reference_count": reference,
            "verified_target_ids": verified_ids,
            "failure_reasons": dict(reasons),
            "status": "VERIFIED_SUBSET" if verified else ("NO_GUIDANCE_CANDIDATES" if verified + unresolved == 0 else "NO_VERIFIED_GUIDANCE"),
            "evidence_state": "VERIFIED" if verified else "REQUIRES_VERIFICATION",
        },
    }


__all__ = ["verify_pointer_records"]
