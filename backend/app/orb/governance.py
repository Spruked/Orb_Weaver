"""Governed Website ORB context assembly.

This module is deliberately a compiler for the active Website ORB path.  It
does not create a second memory or cognition system; it assembles the existing
site, policy, page, visitor, and resolver state around the authoritative
foundational standard.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.storage import IDENTITY_ROOT, LONG_TERM_MEMORY_ROOT, PERSISTENT_CACHE_ROOT, SHORT_TERM_MEMORY_ROOT, require_vault_path
from app.orb.vault_glyph_trace import record_vault_object


REPO_ROOT = Path(__file__).resolve().parents[3]
INCULCATION_PATH = REPO_ROOT / "artifacts" / "inculcation.md"
INCULCATION_VERSION = "artifacts/inculcation.md"
ARTICULATION_RUNTIME = "llama.cpp"
ARTICULATION_MODEL = "Qwen 2.5 1.5B Instruct Q4_K_M"


def _hash(value: Any) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _load_standard() -> str:
    if not INCULCATION_PATH.is_file():
        raise RuntimeError(f"Website ORB foundational standard is missing: {INCULCATION_PATH}")
    return INCULCATION_PATH.read_text(encoding="utf-8")


def _core_four(standard: str) -> str:
    match = re.search(
        r"### 2\. THE UNIVERSAL CORE FOUR REASONING BASELINE\n(.*?)(?=\n### 3\.)",
        standard,
        flags=re.DOTALL,
    )
    if not match:
        raise RuntimeError("Complete Core Four baseline could not be compiled")
    return match.group(1).strip()


def compile_website_orb_governance(
    *,
    website_context: Optional[Dict[str, Any]],
    page_capsule: Optional[Dict[str, Any]],
    operating_policy: Optional[Dict[str, Any]],
    memory_context: Optional[Dict[str, Any]],
    transcript: str,
    pointer_matches: Optional[list[Dict[str, Any]]] = None,
    experience_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compile persistent, deployment, and turn layers for one Website ORB turn."""

    standard = _load_standard()
    core_four = _core_four(standard)
    context = website_context or {}
    page = page_capsule or {}
    policy = operating_policy or {}
    memory = memory_context or {}
    deployment_identity = {
        "orb_name": "Weaver",
        "orb_category": "Website ORB",
        "site_name": context.get("site_name") or context.get("brand") or "Orb Weaver",
        "domain": context.get("domain") or context.get("current_domain"),
        "purpose": context.get("orb_role") or "Host and guide visitors on the Orb Weaver website.",
    }
    tool_manifest = context.get("visitor_tools") or []
    persistent = {
        "core_four": core_four,
        "professional_inculcation": standard,
        "standard_path": str(INCULCATION_PATH),
    }
    deployment = {
        "identity": deployment_identity,
        "site_world": context,
        "tool_manifest": tool_manifest,
        "operating_policy": policy,
    }
    turn = {
        "transcript": transcript,
        "current_page": page,
        "visitor_state": memory,
        "experience_context": experience_context,
        "pointer_matches": pointer_matches or [],
        "route": page.get("route") or "/",
    }
    return {
        "persistent": persistent,
        "deployment": deployment,
        "turn": turn,
        "versions": {
            "core_four_version": f"core-four/{_hash(core_four)}",
            "inculcation_version": f"{INCULCATION_VERSION}/{_hash(standard)}",
            "deployment_identity": f"{deployment_identity['site_name']}:{deployment_identity.get('domain') or 'unknown'}",
            "site_world_version": str(context.get("version") or context.get("source_version") or _hash(repr(context))),
            "tool_manifest_version": str(context.get("tool_manifest_version") or _hash(repr(tool_manifest))),
        },
    }


def initial_governance_trace(compiled: Dict[str, Any]) -> Dict[str, Any]:
    versions = compiled["versions"]
    return {
        "schema": "orb_weaver.website_governance_trace.v1",
        **versions,
        "tpc_state": "pending",
        "tpc_verification": "pending",
        "articulation_runtime": ARTICULATION_RUNTIME,
        "articulation_model": ARTICULATION_MODEL,
        "doctrine_version": "pending_post_articulation",
        "doctrine_checksum": "pending",
        "repair_count": 0,
        "status": "compiled",
    }


def finalize_governance_trace(
    compiled: Dict[str, Any],
    *,
    resolved: Dict[str, Any],
    doctrine_trace: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    trace = initial_governance_trace(compiled)
    lane = str(resolved.get("source_lane") or "unknown")
    evidence_ids = [str(item) for item in resolved.get("evidence_ids") or []]
    trace["governance_trace_id"] = f"GT-RUNTIME-{_hash({'versions': compiled['versions'], 'answer_hash': resolved.get('answer_hash'), 'evidence_ids': evidence_ids})[:24]}"
    deterministic = (
        lane in {"control", "catalog", "apriori", "posteriori", "site_world"}
        and bool(resolved.get("query_correspondence_verified", True))
    )
    trace.update(
        {
            "tpc_state": "passed" if deterministic else "correspondence_not_verified",
            "tpc_verification": (
                {"state": "verified", "source_lane": lane, "evidence_ids": evidence_ids}
                if deterministic
                else {
                    "state": "query_correspondence_not_verified",
                    "source_lane": lane,
                    "source_truth_confidence": resolved.get("source_truth_confidence"),
                    "query_correspondence_confidence": resolved.get("query_correspondence_confidence"),
                }
            ),
            "doctrine_version": (doctrine_trace or {}).get("doctrine_version") or "unknown",
            "doctrine_checksum": (doctrine_trace or {}).get("checksum", {}).get("passed", False),
            "repair_count": len((doctrine_trace or {}).get("checksum", {}).get("failures") or []),
            "resolution_source": lane,
            "verification_state": resolved.get("verification_state"),
            "status": "approved" if (doctrine_trace or {}).get("checksum", {}).get("passed") else "governance_incomplete",
        }
    )
    return trace


def prompt_layers(compiled: Dict[str, Any]) -> str:
    """Return the complete governed context for the configured articulation model."""
    return (
        "GOVERNED WEBSITE ORB ASSEMBLY. Preserve every layer and do not summarize or omit the persistent standard.\n"
        "PERSISTENT / IMMUTABLE LAYER:\n"
        f"{compiled['persistent']['professional_inculcation']}\n\n"
        "DEPLOYMENT LAYER:\n"
        f"{compiled['deployment']}\n\n"
        "TURN LAYER:\n"
        f"{compiled['turn']}\n"
        "TPC resolves deterministic truth before articulation. Doctrine v1 checks the final spoken output before release."
    )


def persist_governance_artifacts(
    compiled: Dict[str, Any],
    trace: Dict[str, Any],
    *,
    session_key: str,
) -> list[str]:
    """Persist the live binding evidence in the canonical Vault Matrix."""
    now = datetime.now(timezone.utc).isoformat()
    versions = compiled["versions"]
    trace_id = str(trace.get("governance_trace_id") or _hash(json.dumps(trace, sort_keys=True)))
    glyph_trace_refs: list[str] = []

    def write_json(path: Path, payload: Dict[str, Any]) -> None:
        path = require_vault_path(path, "Website ORB governance artifact")
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.tmp")
        temp.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        temp.replace(path)

    write_json(
        IDENTITY_ROOT / "orb_weaver_website_orb.json",
        {
            "schema": "orb_weaver.website_orb_identity.v1",
            "updated_at": now,
            "identity": compiled["deployment"]["identity"],
            "core_four_version": versions["core_four_version"],
            "inculcation_version": versions["inculcation_version"],
        },
    )
    glyph_trace_refs.append(record_vault_object(
        object_id="orb_weaver_website_orb",
        object_type="deployment_identity",
        vault_partition="identity",
        content=compiled["deployment"]["identity"],
        governance_trace_id=trace_id,
        source_ids=[versions["inculcation_version"]],
        verification_state="VERIFIED",
    )["glyph_trace_id"])
    write_json(
        PERSISTENT_CACHE_ROOT / "website_orb_governance_manifest.json",
        {
            "schema": "orb_weaver.website_orb_governance_cache.v1",
            "updated_at": now,
            "articulation_runtime": trace.get("articulation_runtime"),
            "articulation_model": trace.get("articulation_model"),
            **versions,
        },
    )
    glyph_trace_refs.append(record_vault_object(
        object_id="website_orb_governance_manifest",
        object_type="persistent_governance_cache",
        vault_partition="persistent_cache",
        content=versions,
        governance_trace_id=trace_id,
        source_ids=list(versions.values()),
        verification_state="VERIFIED",
    )["glyph_trace_id"])
    safe_session = _hash(session_key)[:24]
    write_json(
        SHORT_TERM_MEMORY_ROOT / "website_orb" / f"{safe_session}.json",
        {
            "schema": "orb_weaver.website_orb_short_term_memory.v1",
            "updated_at": now,
            "session_scope": "authenticated" if session_key.startswith("customer:") else "anonymous_site_session",
            "session_key_hash": safe_session,
            "current_route": compiled["turn"].get("route"),
            "current_page": compiled["turn"].get("current_page"),
            "governance_trace_id": trace_id,
        },
    )
    glyph_trace_refs.append(record_vault_object(
        object_id=f"website_orb_short_term_memory:{safe_session}",
        object_type="short_term_memory",
        vault_partition="short_term_memory",
        content={"session_key_hash": safe_session, "route": compiled["turn"].get("route")},
        governance_trace_id=trace_id,
        source_ids=[trace_id],
        verification_state="VERIFIED",
    )["glyph_trace_id"])
    write_json(
        LONG_TERM_MEMORY_ROOT / "tpc" / f"{safe_session}.json",
        {
            "schema": "orb_weaver.website_orb_tpc_trace.v1",
            "updated_at": now,
            "governance_trace_id": trace_id,
            "tpc_state": trace.get("tpc_state"),
            "tpc_verification": trace.get("tpc_verification"),
            "resolution_source": trace.get("resolution_source"),
            "evidence_ids": (trace.get("tpc_verification") or {}).get("evidence_ids", []),
        },
    )
    glyph_trace_refs.append(record_vault_object(
        object_id=f"website_orb_tpc:{safe_session}",
        object_type="tpc_trace",
        vault_partition="long_term_memory/tpc",
        content=trace.get("tpc_verification"),
        governance_trace_id=trace_id,
        source_ids=(trace.get("tpc_verification") or {}).get("evidence_ids", []),
        verification_state="VERIFIED" if trace.get("tpc_state") == "passed" else "PROVISIONAL",
    )["glyph_trace_id"])
    return glyph_trace_refs
