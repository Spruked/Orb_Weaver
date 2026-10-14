"""Narrow A.I.M.S. bridge for the Website ORB cognition path.

This module records a full active visit in volatile A.I.M.S. session memory,
but returns only a relevance-selected context slice to the language model.  It
does not grant tool permissions or select routes; governance remains the sole
authority for both.
"""

from __future__ import annotations

import hashlib
import sys
import time
import uuid
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.core.storage import RUNTIME_ROOT


_AIMS_ROOT = Path(__file__).resolve().parents[3] / "vault_system" / "AIMS"
if str(_AIMS_ROOT) not in sys.path:
    sys.path.insert(0, str(_AIMS_ROOT))

from memory_core import AIMSMemorySystem, OutcomeSignal  # noqa: E402
from memory_core.skg import graphqlite_backend_factory  # noqa: E402


_system: Optional[AIMSMemorySystem] = None
VISITOR_SESSION_TTL_SECONDS = 30 * 60
_visitor_session_accounts: Dict[str, str] = {}
AIMS_RECALL_MAX_BYTES = 6000
AIMS_RECALL_MAX_PRIOR_OUTCOMES = 4
AIMS_RECALL_MAX_INDEXED_EVIDENCE = 6


def _aims() -> AIMSMemorySystem:
    global _system
    if _system is None:
        store = Path(RUNTIME_ROOT) / "website_orb_aims"
        try:
            # GraphQLite is an optional, rebuildable accelerator. The Vault
            # ledger is still created first and remains the only authority.
            _system = AIMSMemorySystem(
                store, skg_backend_factory=graphqlite_backend_factory(store / "derived_graphs"),
            )
        except RuntimeError as error:
            if "GraphQLite is not installed" not in str(error):
                raise
            _system = AIMSMemorySystem(store)
    return _system


def _visitor_key(customer_id: Optional[str]) -> Optional[str]:
    if not customer_id:
        return None
    # A local stable pseudonym is enough to associate explicit outcomes; it
    # prevents the durable ledger from carrying an account identifier itself.
    return hashlib.sha256(f"website-orb:{customer_id}".encode("utf-8")).hexdigest()


def _session_id(anonymous_session_id: Optional[str], customer_id: Optional[str]) -> str:
    if anonymous_session_id:
        scope = "authenticated" if customer_id else "anonymous"
        return f"{scope}:{anonymous_session_id}"
    # Without an explicit browser session id, isolate this request rather than
    # deriving a reusable key from an account. This prevents accidental
    # cross-session identity carry-over.
    return f"request-scope:{uuid.uuid4().hex}"


def _compact(value: Any, depth: int = 0) -> Any:
    if depth > 3:
        return str(value)[:240]
    if isinstance(value, str):
        return value[:700]
    if isinstance(value, list):
        return [_compact(item, depth + 1) for item in value[:12]]
    if isinstance(value, dict):
        return {str(key)[:80]: _compact(item, depth + 1) for key, item in list(value.items())[:16]}
    return value


def _site_scope(target_url: Optional[str]) -> Optional[str]:
    """Return a normalized tenant boundary; missing scope means no recall."""
    if not target_url:
        return None
    hostname = (urlparse(str(target_url)).hostname or "").casefold().rstrip(".")
    return hostname or None


def _bounded_recall(prior: List[Dict[str, Any]], indexed: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Keep durable recall small enough to be safe for the cognition prompt."""
    selected_prior: List[Dict[str, Any]] = []
    selected_indexed: List[Dict[str, Any]] = []
    for item in [*prior[:AIMS_RECALL_MAX_PRIOR_OUTCOMES], *indexed[:AIMS_RECALL_MAX_INDEXED_EVIDENCE]]:
        candidate_prior = selected_prior + ([item] if item in prior[:AIMS_RECALL_MAX_PRIOR_OUTCOMES] else [])
        candidate_indexed = selected_indexed + ([item] if item in indexed[:AIMS_RECALL_MAX_INDEXED_EVIDENCE] else [])
        candidate = {"prior_session_outcomes": candidate_prior, "indexed_evidence": candidate_indexed}
        if len(json.dumps(candidate, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) > AIMS_RECALL_MAX_BYTES:
            continue
        if item in prior[:AIMS_RECALL_MAX_PRIOR_OUTCOMES]:
            selected_prior.append(item)
        else:
            selected_indexed.append(item)
    return {"prior_session_outcomes": selected_prior, "indexed_evidence": selected_indexed}


def _prune_expired_visitor_sessions(now: Optional[float] = None) -> None:
    """Sweep only Website ORB visitor sessions; other A.I.M.S. users are untouched."""
    current = now if now is not None else time.time()
    aims = _aims()
    for session_id, session in list(aims.sessions.items()):
        if not (session_id.startswith("anonymous:") or
                session_id.startswith("authenticated:") or
                session_id.startswith("request-scope:")):
            continue
        if current - float(getattr(session, "created_at", current)) >= VISITOR_SESSION_TTL_SECONDS:
            aims.sessions.pop(session_id, None)
            _visitor_session_accounts.pop(session_id, None)


def _selected_context(
    query: str, anonymous_session_id: Optional[str], customer_id: Optional[str], limit: int = 12,
    target_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Read bounded A.I.M.S. context without manufacturing a new visitor event."""
    aims = _aims()
    _prune_expired_visitor_sessions()
    session_id = _session_id(anonymous_session_id, customer_id)
    if session_id not in aims.sessions:
        aims.start_session(session_id)
    if customer_id and anonymous_session_id:
        _visitor_session_accounts[session_id] = str(customer_id)
    selected = aims.session_context(session_id, query, limit=limit)
    site_scope = _site_scope(target_url)
    prior: List[Dict[str, Any]] = []
    indexed: List[Dict[str, Any]] = []
    # Only an authenticated, explicitly identified visitor gets private prior
    # outcomes. Anonymous sessions intentionally have no durable identity key.
    visitor_key = _visitor_key(customer_id)
    if visitor_key and site_scope:
        prior = aims.retrieve_prior_session_outcomes(
            visitor_key, query, limit=AIMS_RECALL_MAX_PRIOR_OUTCOMES, site_scope=site_scope,
        )
    if site_scope:
        receipt = aims.retrieve(
            query, mode="POSTERIOR_ONLY", limit=AIMS_RECALL_MAX_INDEXED_EVIDENCE,
            site_scope=site_scope,
        )
        indexed = [
            {
                "atom_id": item.get("atom_id"),
                "statement": _compact(item.get("statement", "")),
                "authority_class": item.get("authority_class", "assertion"),
                "status": item.get("status"),
                "confidence": item.get("confidence"),
                "source_record_id": item.get("source_record_id"),
                "source_glyph": item.get("source_glyph"),
                "relevance_score": item.get("relevance_score"),
                "retrieval_id": receipt.get("retrieval_id"),
                "authority": "advisory_evidence_only",
            }
            for item in receipt.get("results", [])
        ]
    recall = _bounded_recall(prior, indexed)
    return {
        "provider": "aims",
        "session_id": session_id,
        "full_session_event_count": selected["session"]["event_count"],
        "relevant_session_context": [_compact(event) for event in selected["context"]],
        "prior_session_outcomes": recall["prior_session_outcomes"],
        "indexed_evidence": recall["indexed_evidence"],
        "recall": {
            "site_scope": site_scope,
            "authenticated_visitor_scope": bool(visitor_key and site_scope),
            "max_bytes": AIMS_RECALL_MAX_BYTES,
            "source": "aims_durable_outcomes_and_posterior_vault",
        },
        "authority_note": "AIMS context and durable recall are advisory evidence; TPC, Correspondence Engine, and Doctrine v1 remain governing authority.",
    }


def context_for_turn(
    transcript: str, anonymous_session_id: Optional[str], customer_id: Optional[str],
    target_url: Optional[str] = None, experience: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Record a real visitor turn and return only selected session/prior context."""
    aims = _aims()
    _prune_expired_visitor_sessions()
    session_id = _session_id(anonymous_session_id, customer_id)
    if session_id not in aims.sessions:
        aims.start_session(session_id)
    if customer_id and anonymous_session_id:
        _visitor_session_accounts[session_id] = str(customer_id)
    aims.remember_session_event(session_id, "message", {"text": transcript}, tags=["visitor"], relevance=0.9)
    if target_url:
        aims.remember_session_event(session_id, "page_visit", {"url": target_url}, tags=["navigation"], relevance=0.65)
    if experience:
        aims.remember_session_event(session_id, "action", _compact(experience), tags=["tour", "experience"], relevance=0.8)
    return _selected_context(transcript, anonymous_session_id, customer_id, target_url=target_url)


def context_for_agency(
    query: str, anonymous_session_id: Optional[str], customer_id: Optional[str],
    target_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve Agency context without recording cognition plumbing as visitor speech.

    Real visitor declarations and runtime observations are recorded through the
    explicit Website ORB turn/observe paths. Candidate selection, question
    compilation, and semantic classification are retrieval operations only.
    """
    _prune_expired_visitor_sessions()
    return _selected_context(query, anonymous_session_id, customer_id, target_url=target_url)


def record_turn_result(
    aims_context: Optional[Dict[str, Any]], spoken_output: str,
    action: Optional[Dict[str, Any]] = None, result: Optional[Dict[str, Any]] = None,
) -> None:
    """Write response/action observations and a non-reinforcing outcome signal.

    The signal is deliberately weak until the visitor or verified capability
    provides outcome evidence. This prevents delivery itself from becoming a
    claim of success.
    """
    if not aims_context:
        return
    aims = _aims()
    session_id = str(aims_context["session_id"])
    aims.remember_session_event(session_id, "message", {"text": spoken_output, "speaker": "weaver"}, tags=["weaver"], relevance=0.7)
    if action:
        aims.remember_session_event(session_id, "action", _compact(action), tags=["governed_action"], relevance=0.85)
    if result:
        aims.remember_session_event(session_id, "tool_result", _compact(result), tags=["result"], relevance=0.85)
    # Routine delivery is not a retained account memory or durable learning
    # event. It remains in the active in-process session only.


def end_session(session_id: str, account_id: Optional[str] = None) -> bool:
    """Purge volatile A.I.M.S. session state at session termination."""
    aims = _aims()
    if not (session_id.startswith("anonymous:") or
            session_id.startswith("authenticated:") or
            session_id.startswith("request-scope:")):
        return False
    if session_id.startswith("authenticated:"):
        if not account_id or _visitor_session_accounts.get(session_id) != str(account_id):
            return False
        _visitor_session_accounts.pop(session_id, None)
    return aims.sessions.pop(session_id, None) is not None


def record_verified_outcome(
    session_id: str, outcome: str, quality: float, confidence: float,
    action_id: Optional[str] = None, capability: Optional[str] = None,
    result: Optional[str] = None, evidence_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Explicit integration point for verified action/visitor outcomes."""
    return _aims().record_outcome_signal(OutcomeSignal(
        session_id=session_id, cognitive_event_id=f"verified:{outcome}", outcome=outcome,
        quality=quality, confidence=confidence, action_id=action_id, capability=capability,
        result=result, evidence_ids=evidence_ids or [],
    ))
