"""Site-scoped Website ORB learning vault records.

This module does not create a second memory system. It standardizes how the
existing single Vault records Website ORB interactions so verified site learning
can later be promoted through owner-approved gates.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from app.core.storage import client_root, require_vault_path


LEARNING_LOOP_SCHEMA = "orb_weaver.website_orb_site_learning_loop.v1"
POSTERIORI_RECORD_SCHEMA = "orb_weaver.website_orb_posteriori_interaction.v1"
STUMP_LEDGER_SCHEMA = "orb_weaver.website_orb_stump_ledger.v1"
VERIFIED_CASES_SCHEMA = "orb_weaver.website_orb_verified_cases.v1"
PROMOTION_QUEUE_SCHEMA = "orb_weaver.website_orb_promotion_queue.v1"
PROMOTION_TEMPLATE_SCHEMA = "orb_weaver.website_orb_promotion_template.v1"

ANSWER_STATES = {"known", "resolved", "clarification_required", "unknown"}
SENSITIVE_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "what",
    "where",
    "with",
    "you",
    "your",
}


def clean_site_domain(value: str) -> str:
    normalized = (value or "").strip().lower()
    normalized = re.sub(r"^https?://", "", normalized).split("/", 1)[0]
    return normalized[4:] if normalized.startswith("www.") else normalized


def sanitize_text(value: str, *, limit: int = 1000) -> str:
    text = re.sub(r"\s+", " ", (value or "").strip())
    for pattern in SENSITIVE_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text[:limit]


def normalize_intent(value: str) -> str:
    return " ".join(sorted(_tokens(value)))[:240]


def _tokens(value: str) -> Set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9_-]{1,}", (value or "").lower())
        if token not in STOPWORDS
    }


def _score(query: str, candidate: Iterable[str]) -> float:
    query_tokens = _tokens(query)
    candidate_tokens: Set[str] = set()
    for value in candidate:
        candidate_tokens.update(_tokens(str(value)))
    if not query_tokens or not candidate_tokens:
        return 0.0
    overlap = query_tokens & candidate_tokens
    return len(overlap) / max(1, min(len(query_tokens), len(candidate_tokens)))


def site_learning_root(domain: str) -> Path:
    root = require_vault_path(client_root(clean_site_domain(domain)) / "website_orb_learning", "Website ORB site learning root")
    root.mkdir(parents=True, exist_ok=True)
    for directory in ("posteriori", "stump_ledger", "promotion_queue", "indexes"):
        require_vault_path(root / directory, "Website ORB site learning namespace").mkdir(parents=True, exist_ok=True)
    return root


def learning_loop_template(site_id: str, domain: str) -> Dict[str, Any]:
    generated_at = datetime.utcnow().isoformat()
    return {
        "schema": LEARNING_LOOP_SCHEMA,
        "site_id": site_id,
        "domain": clean_site_domain(domain),
        "generated_at": generated_at,
        "scope": {
            "site_specific": True,
            "cross_customer_learning": False,
            "shared_visitor_data": False,
            "single_storage_authority": "vault_system",
        },
        "vaults": {
            "apriori": {
                "role": "Trusted Site World compiled from website scans and owner-approved materials.",
                "mutable_by_visitor_conversation": False,
                "promotion_required": True,
            },
            "posteriori": {
                "role": "Observed interaction evidence and outcomes. This is not automatically truth.",
                "stores_raw_conversation_by_default": False,
                "privacy_filter_required": True,
            },
        },
        "answer_states": ["known", "resolved", "clarification_required", "unknown"],
        "runtime_loop": [
            "resolve_route_screen_and_intent",
            "search_site_apriori_evidence",
            "search_verified_site_posteriori_cases",
            "answer_or_clarify_or_admit_unknown",
            "restrict_actions_to_stage_governor_allowed_actions",
            "record_interaction_outcome",
            "detect_gap_and_queue_owner_review",
            "promote_only_verified_resolutions",
        ],
        "promotion_gate": {
            "never_promote_from_one_conversation": True,
            "requires_site_evidence_or_owner_confirmation": True,
            "requires_pii_scrub": True,
            "requires_contradiction_check": True,
            "manual_approval_required_for": [
                "pricing",
                "legal",
                "medical",
                "contractual",
                "financial",
                "reputation_sensitive",
            ],
        },
        "deterministic_reuse_rule": "Reuse only verified prior answers whose evidence, route scope, freshness, policy and outcome still match.",
    }


def clean_slate_files(site_id: str, domain: str) -> Dict[str, str]:
    template = learning_loop_template(site_id, domain)
    now = template["generated_at"]
    return {
        "website_orb_learning/learning-loop-template.json": json.dumps(template, indent=2),
        "website_orb_learning/posteriori/interactions.jsonl": "",
        "website_orb_learning/stump_ledger/stump-ledger.json": json.dumps(
            {
                "schema": STUMP_LEDGER_SCHEMA,
                "site_id": site_id,
                "domain": clean_site_domain(domain),
                "generated_at": now,
                "entries": [],
            },
            indent=2,
        ),
        "website_orb_learning/promotion_queue/promotion-queue.json": json.dumps(
            {
                "schema": PROMOTION_QUEUE_SCHEMA,
                "site_id": site_id,
                "domain": clean_site_domain(domain),
                "generated_at": now,
                "items": [],
            },
            indent=2,
        ),
        "website_orb_learning/apriori-promotion-template.json": json.dumps(
            {
                "schema": PROMOTION_TEMPLATE_SCHEMA,
                "site_id": site_id,
                "domain": clean_site_domain(domain),
                "required_fields": [
                    "approved_answer",
                    "supporting_evidence",
                    "scope",
                    "expiration_conditions",
                    "rollback_reference",
                    "owner_or_low_risk_auto_approval",
                ],
                "forbidden_fields": ["raw_visitor_conversation", "unsanitized_personal_data"],
            },
            indent=2,
        ),
        "website_orb_learning/verified_cases.json": json.dumps(
            {
                "schema": VERIFIED_CASES_SCHEMA,
                "site_id": site_id,
                "domain": clean_site_domain(domain),
                "generated_at": now,
                "cases": [],
            },
            indent=2,
        ),
    }


def classify_answer_state(
    *,
    source: str,
    transcript: str,
    spoken_output: str,
    evidence_refs: Optional[List[str]] = None,
) -> str:
    normalized_question = transcript.lower()
    normalized_answer = spoken_output.lower()
    if any(term in normalized_question for term in ("which one", "what do you mean", "can you clarify")):
        return "clarification_required"
    if any(term in normalized_answer for term in ("cannot verify", "do not have enough", "not enough evidence", "i cannot answer")):
        return "unknown"
    if source in {"verified-posteriori-case"}:
        return "resolved"
    if source in {"orb-runtime-context", "website-tool-cache", "TOOL_CACHE_HIT", "preflight-tool-cache"} or evidence_refs:
        return "known"
    if any(term in normalized_answer for term in ("which", "what kind", "can you tell me", "could you clarify")):
        return "clarification_required"
    return "unknown"


def lookup_verified_case(domain: str, transcript: str, route: str) -> Optional[Dict[str, Any]]:
    root = site_learning_root(domain)
    payload = _read_json(root / "verified_cases.json") or {}
    candidates = payload.get("cases") or []
    best: Optional[Dict[str, Any]] = None
    best_score = 0.0
    for case in candidates:
        if not isinstance(case, dict) or not case.get("approved_answer"):
            continue
        scope = case.get("scope") or {}
        routes = set(scope.get("routes") or [])
        if routes and route not in routes:
            continue
        score = _score(transcript, [case.get("normalized_intent", ""), *(case.get("phrases") or [])])
        if score > best_score:
            best = case
            best_score = score
    if best and best_score >= 0.62:
        return {
            "spoken_output": str(best.get("approved_answer") or "").strip(),
            "llm_source": "verified-posteriori-case",
            "case_id": best.get("case_id"),
            "cache_score": round(best_score, 3),
            "evidence_refs": best.get("supporting_evidence") or [],
        }
    return None


def record_interaction(
    *,
    domain: str,
    transcript: str,
    spoken_output: str,
    answer_state: str,
    llm_source: str,
    target_url: Optional[str],
    route: str,
    evidence_refs: Optional[List[str]] = None,
    retrieval_failure: Optional[str] = None,
    policy_version: Optional[Any] = None,
    outcome: Optional[Dict[str, Any]] = None,
) -> str:
    root = site_learning_root(domain)
    captured_at = datetime.utcnow().isoformat()
    normalized_transcript = sanitize_text(transcript)
    normalized_answer = sanitize_text(spoken_output, limit=1200)
    intent = normalize_intent(normalized_transcript)
    record_id = hashlib.sha256(f"{domain}:{captured_at}:{intent}:{normalized_answer}".encode("utf-8")).hexdigest()[:24]
    state = answer_state if answer_state in ANSWER_STATES else "unknown"
    record = {
        "schema": POSTERIORI_RECORD_SCHEMA,
        "record_id": record_id,
        "captured_at": captured_at,
        "domain": clean_site_domain(domain),
        "route": route or "/",
        "target_url": target_url,
        "normalized_intent": intent,
        "visitor_wording_sanitized": normalized_transcript,
        "response_given_sanitized": normalized_answer,
        "answer_state": state,
        "llm_source": llm_source,
        "retrieved_evidence": evidence_refs or [],
        "retrieval_failure": retrieval_failure,
        "policy_version": policy_version,
        "outcome": outcome or {"status": "not_observed"},
        "privacy": {
            "raw_conversation_stored": False,
            "pii_scrubbed": True,
            "site_scoped": True,
        },
    }
    interactions_path = require_vault_path(root / "posteriori" / "interactions.jsonl", "Website ORB posteriori interactions")
    with interactions_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")
    if state == "unknown":
        _upsert_stump(root, record)
    return record_id


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else None
    except Exception:
        return None
    return None


def _upsert_stump(root: Path, record: Dict[str, Any]) -> None:
    path = require_vault_path(root / "stump_ledger" / "stump-ledger.json", "Website ORB stump ledger")
    ledger = _read_json(path) or {
        "schema": STUMP_LEDGER_SCHEMA,
        "domain": record["domain"],
        "generated_at": record["captured_at"],
        "entries": [],
    }
    entries = ledger.setdefault("entries", [])
    intent = record["normalized_intent"]
    route = record["route"]
    existing = next(
        (
            entry
            for entry in entries
            if entry.get("normalized_intent") == intent and entry.get("route") == route
        ),
        None,
    )
    if existing:
        existing["frequency"] = int(existing.get("frequency") or 1) + 1
        existing["last_seen_at"] = record["captured_at"]
        existing.setdefault("example_questions", [])
        if record["visitor_wording_sanitized"] not in existing["example_questions"][:10]:
            existing["example_questions"] = [record["visitor_wording_sanitized"], *existing["example_questions"]][:10]
    else:
        entries.append(
            {
                "stump_id": f"stump_{record['record_id']}",
                "normalized_intent": intent,
                "route": route,
                "first_seen_at": record["captured_at"],
                "last_seen_at": record["captured_at"],
                "frequency": 1,
                "example_questions": [record["visitor_wording_sanitized"]],
                "why_retrieval_failed": record.get("retrieval_failure") or "no_authoritative_site_evidence",
                "missing_information": "Owner-approved site answer or site evidence is required.",
                "risk_level": "owner_review",
                "commercial_importance": "unclassified",
                "status": "owner_review_needed",
            }
        )
    entries.sort(key=lambda entry: (-int(entry.get("frequency") or 0), str(entry.get("last_seen_at") or "")))
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=True), encoding="utf-8")
