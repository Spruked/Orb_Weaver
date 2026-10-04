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
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.storage import RUNTIME_ROOT


_AIMS_ROOT = Path(__file__).resolve().parents[3] / "vault_system" / "AIMS"
if str(_AIMS_ROOT) not in sys.path:
    sys.path.insert(0, str(_AIMS_ROOT))

from memory_core import AIMSMemorySystem, OutcomeSignal  # noqa: E402
from memory_core.skg import graphqlite_backend_factory  # noqa: E402


_system: Optional[AIMSMemorySystem] = None
VISITOR_SESSION_TTL_SECONDS = 30 * 60
_visitor_session_accounts: Dict[str, str] = {}


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
    return {
        "provider": "aims",
        "session_id": session_id,
        "full_session_event_count": selected["session"]["event_count"],
        "relevant_session_context": [_compact(event) for event in selected["context"]],
        "prior_session_outcomes": [],
        "authority_note": "AIMS context is advisory, session-scoped, and not cross-session account memory.",
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
    return _selected_context(transcript, anonymous_session_id, customer_id)


def context_for_agency(
    query: str, anonymous_session_id: Optional[str], customer_id: Optional[str],
) -> Dict[str, Any]:
    """Retrieve Agency context without recording cognition plumbing as visitor speech.

    Real visitor declarations and runtime observations are recorded through the
    explicit Website ORB turn/observe paths. Candidate selection, question
    compilation, and semantic classification are retrieval operations only.
    """
    _prune_expired_visitor_sessions()
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
