from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse


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
    records = [item for item in pointer_map.get("records") or [] if isinstance(item, dict)]
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
    candidate_meaning = str(candidate.get("accessible_name") or candidate.get("text") or "").lower().strip()
    record_meaning = _meaning(record)
    if candidate.get("locator") == record.get("semantic_locator"):
        return True
    if record_meaning and candidate_meaning:
        return record_meaning in candidate_meaning or candidate_meaning in record_meaning
    return bool(record.get("content_fingerprint") and candidate.get("text_fingerprint") == record.get("content_fingerprint"))


def _preferred_locator(matches: List[Dict[str, Any]]) -> str:
    locators = Counter(str(item.get("locator")) for item in matches if item.get("locator"))
    return locators.most_common(1)[0][0] if locators else ""
