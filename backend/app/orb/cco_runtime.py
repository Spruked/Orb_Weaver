"""Runtime bridge from Website ORB turns into the CCO package."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
CCO_ROOT = REPO_ROOT / "Orb_Assistant" / "context_correspondence_orchestrator"
if CCO_ROOT.exists() and str(CCO_ROOT) not in sys.path:
    sys.path.insert(0, str(CCO_ROOT))

from context_correspondence_orchestrator.core.llm_abstraction import LocalFallbackLLM
from context_correspondence_orchestrator.core.task_analyzer import TaskAnalyzer
from context_correspondence_orchestrator.models import CompressionStrategy
from context_correspondence_orchestrator.strategies.vault_compile import VaultCompileStrategy


def build_runtime_trace(
    *,
    site_id: Optional[str],
    domain: str,
    transcript: str,
    target_url: Optional[str],
    route: str,
    website_context: Optional[Dict[str, Any]],
    page_capsule: Optional[Dict[str, Any]],
    operating_policy: Optional[Dict[str, Any]],
    answer_state: Optional[str],
    llm_source: str,
    learning_record_id: Optional[str],
    retrieved_ids: Optional[List[str]] = None,
    token_budget: int = 1200,
) -> Dict[str, Any]:
    """Build a CCO acceptance trace for a live Website ORB interaction."""

    task_profile = TaskAnalyzer().analyze(transcript)
    vault_records = _site_world_records(website_context, page_capsule, operating_policy, retrieved_ids)
    source = json.dumps(vault_records, sort_keys=True, ensure_ascii=True)
    compiled = VaultCompileStrategy(LocalFallbackLLM()).compress(
        source=source,
        task_profile=task_profile,
        target_budget=token_budget,
        preserve_exact=[record["fact_id"] for record in vault_records if record.get("fact_id")],
    )
    provenance = compiled.get("provenance") or {}
    retrieved_fact_ids = sorted(str(key) for key in provenance.keys())
    evidence_hash = hashlib.sha256((compiled.get("crystal_text") or "").encode("utf-8")).hexdigest()[:24]
    state = answer_state or "unknown"
    supported = state in {"known", "resolved"}
    return {
        "schema": "orb_weaver.cco_runtime_trace.v1",
        "component": "Context & Correspondence Orchestrator",
        "short_name": "CCO",
        "site_id": site_id,
        "domain": domain,
        "target_url": target_url,
        "route": route or "/",
        "task_profile": task_profile.model_dump(),
        "selected_strategy": CompressionStrategy.VAULT_COMPILE.value,
        "token_budget": token_budget,
        "evidence_package": {
            "package_hash": evidence_hash,
            "original_tokens": compiled.get("original_tokens"),
            "context_tokens": compiled.get("crystal_tokens"),
            "records_count": compiled.get("records_count"),
            "filtered_count": compiled.get("filtered_count"),
            "retrieved_fact_ids": retrieved_fact_ids,
            "source_namespaces": _source_namespaces(vault_records),
        },
        "correspondence_result": {
            "status": "supported" if supported else "gap_detected",
            "answer_state": state,
            "confidence_floor": 0.78 if supported else 0.0,
            "requires_owner_review": state == "unknown",
            "governance": "site_scoped_evidence_only",
        },
        "articulation": {
            "llm_source": llm_source,
            "mode": "voice_only_spoken_answer",
        },
        "write_back": {
            "posteriori_recorded": bool(learning_record_id),
            "learning_record_id": learning_record_id,
            "promotion_directly_allowed": False,
        },
    }


def _site_world_records(
    website_context: Optional[Dict[str, Any]],
    page_capsule: Optional[Dict[str, Any]],
    operating_policy: Optional[Dict[str, Any]],
    retrieved_ids: Optional[List[str]],
) -> List[Dict[str, Any]]:
    context = website_context or {}
    capsule = page_capsule or {}
    records: List[Dict[str, Any]] = []

    def add(fact_id: str, subject: str, predicate: str, obj: Any, source: str, confidence: float = 0.9) -> None:
        if obj in (None, "", [], {}):
            return
        records.append(
            {
                "fact_id": fact_id,
                "subject": subject,
                "predicate": predicate,
                "object": json.dumps(obj, sort_keys=True) if isinstance(obj, (dict, list)) else str(obj),
                "confidence": confidence,
                "timestamp": context.get("generated_at") or "",
                "source": source,
                "status": "active",
                "provenance": source,
            }
        )

    add("site.domain", "site", "domain", context.get("domain"), "site_world")
    add("site.name", "site", "name", context.get("site_name") or context.get("brand"), "site_world")
    add("site.summary", "site", "summary", context.get("site_summary"), "site_world")
    add("page.route", "current_page", "route", capsule.get("route"), "page_capsule")
    add("page.purpose", "current_page", "purpose", capsule.get("page_purpose"), "page_capsule")
    for index, fact in enumerate(context.get("key_facts") or []):
        add(f"site.key_fact.{index}", "site", "key_fact", fact, "site_world")
    for key, route in (context.get("route_hints") or {}).items():
        add(f"site.route_hint.{key}", "site", "route_hint", route, "site_world")
    for index, tool in enumerate(context.get("visitor_tools") or []):
        add(f"site.visitor_tool.{tool.get('id') or index}", "site", "visitor_tool", tool, "site_world")
    enforcement = (operating_policy or {}).get("enforcement") or {}
    add("policy.allowed_routes", "owner_policy", "allowed_routes", enforcement.get("allowed_routes"), "orb_dock_policy")
    add("policy.allowed_tools", "owner_policy", "allowed_tools", enforcement.get("allowed_tools"), "orb_dock_policy")
    behavior = (operating_policy or {}).get("behavior") or {}
    add("policy.job_description", "owner_policy", "job_description", behavior.get("job_description"), "orb_dock_policy")
    for item in retrieved_ids or []:
        add(f"retrieved.{item}", "runtime_retrieval", "used", item, "answer_path", 0.95)
    return records or [
        {
            "fact_id": "site.no_evidence",
            "subject": "site",
            "predicate": "has_authoritative_evidence",
            "object": "false",
            "confidence": 1.0,
            "timestamp": "",
            "source": "cco_runtime",
            "status": "active",
            "provenance": "no_site_world_records_available",
        }
    ]


def _source_namespaces(records: List[Dict[str, Any]]) -> List[str]:
    return sorted({str(record.get("source") or "unknown") for record in records})
