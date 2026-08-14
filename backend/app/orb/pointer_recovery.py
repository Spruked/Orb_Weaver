from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

from app.core.storage import require_vault_path


DEFAULT_THRESHOLDS = {
    "minimum_stable_ratio": 0.70,
    "minimum_stable_pointers": 10,
    "maximum_uncertain_ratio": 0.25,
    "maximum_duplicate_conflicts": 3,
    "maximum_automatic_recovery_attempts": 1,
}

UNCERTAINTY_REASONS = {
    "layout_not_stable",
    "selector_not_durable",
    "element_not_visible",
    "duplicate_semantic_target",
    "scroll_section_unresolved",
    "cross_route_mismatch",
    "responsive_variant",
    "decorative_only",
}


def assess_pointer_quality(
    pointer_map: Dict[str, Any],
    thresholds: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    policy = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    all_records = [item for item in pointer_map.get("records") or [] if isinstance(item, dict)]
    records = [
        item
        for item in all_records
        if item.get("status") in (None, "active")
        and item.get("finding_subreason") != "owner_rejected_pointer_identity"
    ]
    excluded = len(all_records) - len(records)
    total = len(records)
    classes = Counter(str(item.get("confidence_class") or "UNCERTAIN") for item in records)
    stable = classes["VERIFIED"] + classes["STABLE"]
    uncertain = classes["UNCERTAIN"] + classes["BLOCKED"]

    identities: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        route = _route(record.get("page_route"))
        identity = str(record.get("semantic_locator") or record.get("content_fingerprint") or "")
        if identity:
            identities[(route, identity)].append(record)
    duplicate_groups = [group for group in identities.values() if len(group) > 1]
    duplicate_conflicts = sum(len(group) - 1 for group in duplicate_groups)

    stable_ratio = stable / total if total else 0.0
    uncertain_ratio = uncertain / total if total else 1.0
    triggers: List[str] = []
    if stable_ratio < float(policy["minimum_stable_ratio"]):
        triggers.append("stable_ratio_below_threshold")
    if stable < int(policy["minimum_stable_pointers"]):
        triggers.append("stable_pointer_floor_not_met")
    if uncertain_ratio > float(policy["maximum_uncertain_ratio"]):
        triggers.append("uncertain_ratio_above_threshold")
    if duplicate_conflicts > int(policy["maximum_duplicate_conflicts"]):
        triggers.append("duplicate_conflicts_above_threshold")
    required = bool(triggers)
    return {
        "schema": "orb_weaver.pointer_quality.v1",
        "status": "POINTER_RECOVERY_REQUIRED" if required else "POINTER_READY",
        "recovery_required": required,
        "record_count": total,
        "total_record_count": len(all_records),
        "excluded_count": excluded,
        "stable_count": stable,
        "uncertain_count": uncertain,
        "stable_ratio": round(stable_ratio, 4),
        "uncertain_ratio": round(uncertain_ratio, 4),
        "duplicate_conflict_count": duplicate_conflicts,
        "confidence_classes": dict(classes),
        "thresholds": policy,
        "triggers": triggers,
    }


def classify_uncertainty(record: Dict[str, Any], peers: Iterable[Dict[str, Any]] = ()) -> List[str]:
    reasons: List[str] = []
    evidence = record.get("confidence_evidence") or {}
    locator = str(record.get("semantic_locator") or "")
    route = _route(record.get("page_route"))
    if evidence.get("locator_method") == "structural_css" or ":nth-of-type(" in locator:
        reasons.append("selector_not_durable")
    if record.get("target_type") in {"paragraph", "other"} and not record.get("allowed_actions"):
        reasons.append("decorative_only")
    if record.get("target_type") in {"heading", "section"} and not ("#" in locator or "[id=" in locator):
        reasons.append("scroll_section_unresolved")
    matching = [
        peer for peer in peers
        if peer is not record
        and _route(peer.get("page_route")) == route
        and (
            peer.get("semantic_locator") == record.get("semantic_locator")
            or peer.get("content_fingerprint") == record.get("content_fingerprint")
        )
    ]
    if matching:
        reasons.append("duplicate_semantic_target")
    if not reasons:
        reasons.append("layout_not_stable")
    return list(dict.fromkeys(reason for reason in reasons if reason in UNCERTAINTY_REASONS))


def reconcile_pointer_recovery(
    baseline_map: Dict[str, Any],
    capture: Dict[str, Any],
) -> Dict[str, Any]:
    baseline = [item for item in baseline_map.get("records") or [] if isinstance(item, dict)]
    observations = [item for item in capture.get("observations") or [] if isinstance(item, dict)]
    observed_by_key: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        for candidate in observation.get("candidates") or []:
            if isinstance(candidate, dict) and candidate.get("identity_key"):
                observed_by_key[str(candidate["identity_key"])].append({**candidate, "observation": observation})

    recovered: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []
    baseline_by_semantics: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for record in baseline:
        baseline_by_semantics[(_route(record.get("page_route")), _meaning(record))].append(record)

    for record in baseline:
        route = _route(record.get("page_route"))
        semantic_key = (route, _meaning(record))
        matches: List[Dict[str, Any]] = []
        for values in observed_by_key.values():
            matches.extend(
                value for value in values
                if _route(value.get("route")) == route
                and _candidate_matches_record(value, record)
            )
        render_ids = {str(item["observation"].get("render_id")) for item in matches}
        viewports = {str(item["observation"].get("viewport")) for item in matches}
        locators = {str(item.get("locator") or "") for item in matches if item.get("locator")}
        durable = bool(matches) and all(bool(item.get("durable")) for item in matches)
        unique = len(baseline_by_semantics[semantic_key]) == 1 and len(locators) <= max(1, len(viewports))
        consistent = len(render_ids) >= 2 and durable and unique
        if consistent:
            promoted = dict(record)
            promoted["semantic_locator"] = _preferred_locator(matches)
            promoted["confidence"] = max(float(record.get("confidence") or 0.0), 0.86)
            promoted["confidence_class"] = "STABLE"
            promoted["runtime_policy"] = {
                "behavior": "guide_and_verify_before_action",
                "may_point": True,
                "must_verify_before_action": True,
                "requires_confirmation": False,
            }
            promoted["confidence_evidence"] = {
                **(record.get("confidence_evidence") or {}),
                "verification_resolution": "consistent_across_recovery_renders",
                "render_count": len(render_ids),
                "viewports": sorted(viewports),
                "locators": sorted(locators),
                "last_verified_time": datetime.now(timezone.utc).isoformat(),
            }
            promoted["recovery_status"] = "promoted"
            content_versions = {str(item.get("text_fingerprint") or "") for item in matches}
            promoted["finding_class"] = "DYNAMIC" if len(content_versions) > 1 else "CONFIRMED"
            promoted["finding_subreason"] = "content_changed_identity_stable" if len(content_versions) > 1 else "consistent_multi_render_identity"
            promoted["pointer_health"] = "RECOVERED"
            recovered.append(promoted)
        else:
            reasons = classify_uncertainty(record, baseline)
            if matches and len(viewports) > 1 and len(locators) > 1:
                reasons.append("responsive_variant")
            if not matches:
                reasons.append("element_not_visible")
            unresolved_record = dict(record)
            unresolved_record["confidence_class"] = "UNCERTAIN"
            unresolved_record["runtime_policy"] = {
                "behavior": "explain_cautiously_without_unverified_point",
                "may_point": False,
                "must_verify_before_action": True,
                "requires_confirmation": True,
            }
            unresolved_record["recovery_status"] = "visual_review_required"
            unresolved_record["uncertainty_reasons"] = list(dict.fromkeys(reasons))
            if "duplicate_semantic_target" in unresolved_record["uncertainty_reasons"]:
                unresolved_record["finding_class"] = "CONFLICT"
            elif "responsive_variant" in unresolved_record["uncertainty_reasons"]:
                unresolved_record["finding_class"] = "TRANSIENT"
            else:
                unresolved_record["finding_class"] = "UNVERIFIED"
            unresolved_record["finding_subreason"] = unresolved_record["uncertainty_reasons"][0]
            unresolved_record["pointer_health"] = str(record.get("pointer_health") or "NEW")
            unresolved.append(unresolved_record)

    records = recovered + unresolved
    by_page: Dict[str, List[str]] = defaultdict(list)
    for record in records:
        by_page[str(record.get("page_route") or "")].append(str(record.get("target_id") or ""))
    result_map = {
        "schema": "orb_weaver.pointer_plot_map.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "records": records,
        "by_page": dict(by_page),
        "recovery": {
            "schema": "orb_weaver.pointer_recovery.v1",
            "promoted_count": len(recovered),
            "unresolved_count": len(unresolved),
            "render_count": len(observations),
            "routes": sorted({_route(item.get("url")) for item in observations}),
            "automatic_attempts_used": 1,
            "automatic_attempts_maximum": 1,
        },
    }
    result_map["quality"] = assess_pointer_quality(result_map)
    return result_map


def run_pointer_recovery_capture(
    base_url: str,
    routes: List[str],
    output_dir: Path,
    *,
    render_passes: int = 2,
) -> Dict[str, Any]:
    output_dir = require_vault_path(output_dir, "Pointer recovery capture")
    script = Path(__file__).with_name("pointer_recovery_capture.js")
    if not script.is_file():
        raise RuntimeError("Pointer recovery browser capture script is missing")
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required for Chromium pointer recovery")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "browser_capture.json"
    urls = [urljoin(base_url.rstrip("/") + "/", route.lstrip("/")) for route in routes]
    environment = {**os.environ}
    repo_frontend = Path(__file__).resolve().parents[3] / "frontend" / "node_modules"
    if repo_frontend.is_dir():
        environment["NODE_PATH"] = os.pathsep.join(filter(None, [str(repo_frontend), environment.get("NODE_PATH")]))
    command = [node, str(script), json.dumps(urls), str(output_file), str(max(2, render_passes)), str(output_dir)]
    completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=300, env=environment)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "Pointer recovery capture failed")[-4000:])
    if not output_file.is_file():
        raise RuntimeError("Pointer recovery capture did not produce evidence")
    return json.loads(output_file.read_text(encoding="utf-8"))


def publish_recovered_pointer_map(pointer_map: Dict[str, Any], target: Path) -> None:
    """Atomically publish the reconciled map without replacing the Site World."""
    target = require_vault_path(target, "Recovered pointer map")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(pointer_map, handle, indent=2, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, target)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def promote_owner_verified_pointer(
    pointer_map: Dict[str, Any],
    target_id: str,
    *,
    reviewer: str,
    signature_hash: str,
    notes: str = "",
    decided_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Promote exactly one reviewed pointer without granting any click authority."""
    required_identity = {
        "target_id",
        "page_route",
        "meaning",
        "semantic_locator",
        "content_fingerprint",
        "allowed_actions",
    }
    result = dict(pointer_map)
    records: List[Dict[str, Any]] = []
    promoted = False
    timestamp = decided_at or datetime.now(timezone.utc).isoformat()
    for original in pointer_map.get("records") or []:
        record = dict(original)
        if str(record.get("target_id") or "") != target_id:
            records.append(record)
            continue
        missing = sorted(key for key in required_identity if not record.get(key))
        if missing:
            raise ValueError(f"Pointer identity is incomplete: {', '.join(missing)}")
        if record.get("status") not in (None, "active"):
            raise ValueError("Only an active pointer may receive owner verification")
        prior_health = str(record.get("pointer_health") or "NEW")
        record["confidence"] = max(float(record.get("confidence") or 0.0), 0.95)
        record["confidence_class"] = "VERIFIED"
        record["pointer_health"] = "OWNER_VERIFIED"
        record["runtime_policy"] = {
            "behavior": "guide_and_verify_before_action",
            "may_point": True,
            "must_verify_before_action": True,
            "requires_confirmation": False,
            "may_click": False,
            "may_navigate": False,
        }
        authority = {
            "state": "OWNER_VERIFIED",
            "reviewer": reviewer,
            "signature_hash": signature_hash,
            "decided_at": timestamp,
            "notes": notes,
            "identity_hash": _pointer_identity_hash(record),
        }
        record["owner_authority"] = authority
        record["authority_history"] = [
            *(record.get("authority_history") or []),
            {
                "event": "owner_verified",
                "from": prior_health,
                "to": "OWNER_VERIFIED",
                **authority,
            },
        ]
        promoted = True
        records.append(record)
    if not promoted:
        raise KeyError(f"Pointer target not found: {target_id}")
    result["records"] = records
    result["record_count"] = len(records)
    result["by_page"] = _records_by_page(records)
    result["quality"] = assess_pointer_quality(result)
    return result


def reject_owner_pointer(
    pointer_map: Dict[str, Any],
    target_id: str,
    *,
    reviewer: str,
    signature_hash: str,
    notes: str = "",
    decided_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Record an owner rejection and make the target ineligible for guidance."""
    result = dict(pointer_map)
    records: List[Dict[str, Any]] = []
    rejected = False
    timestamp = decided_at or datetime.now(timezone.utc).isoformat()
    for original in pointer_map.get("records") or []:
        record = dict(original)
        if str(record.get("target_id") or "") != target_id:
            records.append(record)
            continue
        prior_health = str(record.get("pointer_health") or "NEW")
        record["confidence_class"] = "BLOCKED"
        record["pointer_health"] = "OWNER_REJECTED"
        record["runtime_policy"] = {
            "behavior": "voice_only_owner_rejected",
            "may_point": False,
            "must_verify_before_action": True,
            "requires_confirmation": True,
            "may_click": False,
            "may_navigate": False,
        }
        record["finding_class"] = "BLOCKED"
        record["finding_subreason"] = "owner_rejected_pointer_identity"
        record["authority_history"] = [
            *(record.get("authority_history") or []),
            {
                "event": "owner_rejected",
                "from": prior_health,
                "to": "OWNER_REJECTED",
                "reviewer": reviewer,
                "signature_hash": signature_hash,
                "decided_at": timestamp,
                "notes": notes,
                "identity_hash": _pointer_identity_hash(record),
            },
        ]
        rejected = True
        records.append(record)
    if not rejected:
        raise KeyError(f"Pointer target not found: {target_id}")
    result["records"] = records
    result["record_count"] = len(records)
    result["by_page"] = _records_by_page(records)
    result["quality"] = assess_pointer_quality(result)
    return result


def merge_canonical_pointer_authority(
    previous_map: Dict[str, Any],
    candidate_map: Dict[str, Any],
    *,
    reconciled_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Carry owner authority forward only when the complete target identity survives."""
    timestamp = reconciled_at or datetime.now(timezone.utc).isoformat()
    previous_owner = {
        str(record.get("target_id")): record
        for record in previous_map.get("records") or []
        if record.get("pointer_health") == "OWNER_VERIFIED"
    }
    records: List[Dict[str, Any]] = []
    retained: set[str] = set()
    for original in candidate_map.get("records") or []:
        record = dict(original)
        target_id = str(record.get("target_id") or "")
        prior = previous_owner.get(target_id)
        if prior and _pointer_identity_hash(prior) == _pointer_identity_hash(record):
            record["confidence"] = max(float(record.get("confidence") or 0.0), 0.95)
            record["confidence_class"] = "VERIFIED"
            record["pointer_health"] = "OWNER_VERIFIED"
            record["runtime_policy"] = dict(prior.get("runtime_policy") or {})
            record["owner_authority"] = dict(prior.get("owner_authority") or {})
            record["authority_history"] = [
                *(prior.get("authority_history") or []),
                {
                    "event": "owner_authority_retained_after_rescan",
                    "from": "OWNER_VERIFIED",
                    "to": "OWNER_VERIFIED",
                    "decided_at": timestamp,
                    "identity_hash": _pointer_identity_hash(record),
                },
            ]
            retained.add(target_id)
        records.append(record)

    for target_id, prior in previous_owner.items():
        if target_id in retained:
            continue
        stale = dict(prior)
        stale["status"] = "inactive"
        stale["confidence_class"] = "BLOCKED"
        stale["pointer_health"] = "DEPRECATED"
        stale["runtime_policy"] = {
            "behavior": "voice_only_stale_owner_identity",
            "may_point": False,
            "must_verify_before_action": True,
            "requires_confirmation": True,
            "may_click": False,
            "may_navigate": False,
        }
        stale["finding_class"] = "UNVERIFIED"
        stale["finding_subreason"] = "owner_verified_identity_not_confirmed_by_rescan"
        stale["authority_history"] = [
            *(prior.get("authority_history") or []),
            {
                "event": "owner_authority_demoted_after_rescan",
                "from": "OWNER_VERIFIED",
                "to": "DEPRECATED",
                "decided_at": timestamp,
                "identity_hash": _pointer_identity_hash(prior),
            },
        ]
        records.append(stale)

    result = dict(candidate_map)
    result["records"] = records
    result["record_count"] = len(records)
    result["by_page"] = _records_by_page(records)
    result["authority_reconciliation"] = {
        "schema": "orb_weaver.pointer_authority_reconciliation.v1",
        "reconciled_at": timestamp,
        "previous_owner_verified_count": len(previous_owner),
        "retained_count": len(retained),
        "demoted_count": len(previous_owner) - len(retained),
    }
    result["quality"] = assess_pointer_quality(result)
    return result


def _pointer_identity_hash(record: Dict[str, Any]) -> str:
    identity = {
        "target_id": record.get("target_id"),
        "page_route": _route(record.get("page_route")),
        "meaning": _meaning(record),
        "semantic_locator": record.get("semantic_locator"),
        "content_fingerprint": record.get("content_fingerprint"),
        "structural_context": record.get("structural_context") or {},
        "allowed_actions": sorted(str(item) for item in record.get("allowed_actions") or []),
    }
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _records_by_page(records: Iterable[Dict[str, Any]]) -> Dict[str, List[str]]:
    by_page: Dict[str, List[str]] = defaultdict(list)
    for record in records:
        by_page[str(record.get("page_route") or "")].append(str(record.get("target_id") or ""))
    return dict(by_page)


def recovery_routes(pointer_map: Dict[str, Any], configured: Optional[List[str]] = None) -> List[str]:
    if configured:
        routes = configured
    else:
        uncertain = [
            _route(item.get("page_route"))
            for item in pointer_map.get("records") or []
            if item.get("confidence_class") in {"UNCERTAIN", "BLOCKED", None}
        ]
        routes = [route for route, _count in Counter(uncertain).most_common(8)]
    normalized = list(dict.fromkeys(_route(route) for route in routes if route is not None))
    return normalized or ["/"]


def _route(value: Any) -> str:
    raw = str(value or "/")
    parsed = urlparse(raw if "://" in raw else f"https://pointer.invalid{raw if raw.startswith('/') else '/' + raw}")
    return (parsed.path or "/").rstrip("/") or "/"


def _meaning(record: Dict[str, Any]) -> str:
    raw = str(record.get("meaning") or "").lower().strip()
    return raw.split(":", 1)[-1].strip()


def _candidate_matches_record(candidate: Dict[str, Any], record: Dict[str, Any]) -> bool:
    candidate_meaning = _normalized_identity_text(candidate.get("accessible_name") or candidate.get("text"))
    record_meaning = _normalized_identity_text(_meaning(record))
    if not candidate_meaning or not record_meaning:
        return False
    if candidate_meaning == record_meaning:
        return True

    candidate_words = _identity_words(candidate_meaning)
    record_words = _identity_words(record_meaning)
    if not candidate_words or not record_words:
        return False
    overlap = candidate_words & record_words
    candidate_coverage = len(overlap) / len(candidate_words)
    record_coverage = len(overlap) / len(record_words)
    same_locator = candidate.get("locator") == record.get("semantic_locator")
    if same_locator:
        return candidate_coverage >= 0.75 and record_coverage >= 0.75
    return candidate_coverage >= 0.9 and record_coverage >= 0.9


def _normalized_identity_text(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _identity_words(value: str) -> set[str]:
    stop_words = {"a", "an", "and", "the", "to", "of", "for"}
    return {
        word
        for word in value.split()
        if word not in stop_words and not word.isdigit()
    }


def _preferred_locator(matches: List[Dict[str, Any]]) -> str:
    locators = Counter(str(item.get("locator")) for item in matches if item.get("locator"))
    return locators.most_common(1)[0][0] if locators else ""
