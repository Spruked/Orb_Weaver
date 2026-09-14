"""Narrow A.I.M.S. bridge for the Website ORB cognition path.

This module records a full active visit in volatile A.I.M.S. session memory,
but returns only a relevance-selected context slice to the language model.  It
does not grant tool permissions or select routes; governance remains the sole
authority for both.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.storage import RUNTIME_ROOT


_AIMS_ROOT = Path(__file__).resolve().parents[3] / "vault_system" / "AIMS"
if str(_AIMS_ROOT) not in sys.path:
    sys.path.insert(0, str(_AIMS_ROOT))

from memory_core import AIMSMemorySystem, OutcomeSignal  # noqa: E402
from memory_core.skg import graphqlite_backend_factory  # noqa: E402


_system: Optional[AIMSMemorySystem] = None


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
    # Legacy callers without the browser session id still receive memory, but
    # cannot accidentally obtain durable cross-visitor context.
    return f"request-scope:{_visitor_key(customer_id) or 'anonymous'}"


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


def _selected_context(
    query: str, anonymous_session_id: Optional[str], customer_id: Optional[str], limit: int = 12,
) -> Dict[str, Any]:
    """Read bounded A.I.M.S. context without manufacturing a new visitor event."""
    aims = _aims()
    session_id = _session_id(anonymous_session_id, customer_id)
    if session_id not in aims.sessions:
        aims.start_session(session_id)
    selected = aims.session_context(session_id, query, limit=limit)
    prior: List[Dict[str, Any]] = []
    key = _visitor_key(customer_id)
    if key:
        prior = aims.retrieve_prior_session_outcomes(key, query, limit=3)
    return {
        "provider": "aims",
        "session_id": session_id,
        "full_session_event_count": selected["session"]["event_count"],
        "relevant_session_context": [_compact(event) for event in selected["context"]],
        "prior_session_outcomes": prior,
        "authority_note": "AIMS context is advisory only; Vault/SKG evidence and Stage Governor remain authoritative.",
    }


def context_for_turn(
    transcript: str, anonymous_session_id: Optional[str], customer_id: Optional[str],
    target_url: Optional[str] = None, experience: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Record a real visitor turn and return only selected session/prior context."""
    aims = _aims()
    session_id = _session_id(anonymous_session_id, customer_id)
    if session_id not in aims.sessions:
        aims.start_session(session_id)
    aims.remember_session_event(session_id, "message", {"text": transcript}, tags=["visitor"], relevance=0.9)
    if target_url:
        aims.remember_session_event(session_id, "page_visit", {"url": target_url}, tags=["navigation"], relevance=0.65)
    if experience:
        aims.remember_session_event(session_id, "action", _compact(experience), tags=["tour", "experience"], relevance=0.8)
    return _selected_context(transcript, anonymous_session_id, customer_id)


def context_for_agency(
    query: str, anonymous_session_id: Optional[str], customer_id: Optional[str],
) -> Dict[str, Any]:
    """Retrieve Agency context without recording cognition plumbing as visitor speech.

    Real visitor declarations and runtime observations are recorded through the
    explicit Website ORB turn/observe paths. Candidate selection, question
    compilation, and semantic classification are retrieval operations only.
    """
    return _selected_context(query, anonymous_session_id, customer_id)


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
    aims.record_outcome_signal(OutcomeSignal(
        session_id=session_id,
        cognitive_event_id=f"turn:{aims_context['full_session_event_count']}",
        outcome="response_delivered", quality=0.25, confidence=0.5,
        action_id=str((action or {}).get("action_id") or "") or None,
        capability=str((action or {}).get("capability") or "") or None,
        result="observed" if result else "not_observed",
        visitor_response="pending",
    ))


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
