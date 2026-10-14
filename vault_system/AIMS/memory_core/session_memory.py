"""Session-scoped working memory for a host conversation.

This layer deliberately retains the meaningful active visit in full.  It is
volatile: a host must explicitly distil an end-of-session outcome before any
material becomes durable.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


SESSION_EVENT_KINDS = {
    "message", "question", "choice", "route", "page_visit", "capability",
    "tool_result", "correction", "goal", "unresolved", "evidence", "action",
}


@dataclass
class SessionEvent:
    kind: str
    payload: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    relevance: float = 0.5
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {"event_id": self.event_id, "kind": self.kind, "payload": self.payload,
                "tags": self.tags, "relevance": self.relevance, "occurred_at": self.occurred_at}


class SessionMemory:
    """Full active-session record with query-time selection, never silent trimming."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = time.time()
        self._events: List[SessionEvent] = []

    def record(self, kind: str, payload: Dict[str, Any], tags: Optional[Iterable[str]] = None,
               relevance: float = 0.5) -> SessionEvent:
        if kind not in SESSION_EVENT_KINDS:
            raise ValueError(f"Unsupported session event kind: {kind}")
        event = SessionEvent(kind=kind, payload=dict(payload), tags=list(tags or []),
                             relevance=max(0.0, min(1.0, float(relevance))))
        self._events.append(event)
        return event

    def events(self) -> List[SessionEvent]:
        return list(self._events)

    def context(self, query: str = "", limit: int = 24) -> List[Dict[str, Any]]:
        """Return the most relevant slice without discarding the full session."""
        tokens = {token.casefold() for token in query.split() if token}
        now = time.time()

        def score(event: SessionEvent) -> float:
            text = f"{event.kind} {event.tags} {event.payload}".casefold()
            lexical = sum(token in text for token in tokens) / max(1, len(tokens)) if tokens else 0.0
            recency = max(0.0, 1.0 - ((now - event.occurred_at) / 14400.0))
            kind_bonus = 0.18 if event.kind in {"goal", "unresolved", "choice", "correction", "tool_result"} else 0.0
            return (0.48 * lexical) + (0.30 * event.relevance) + (0.14 * recency) + kind_bonus

        ordered = sorted(self._events, key=lambda event: (-score(event), event.occurred_at, event.event_id))
        return [{**event.to_dict(), "context_score": score(event)} for event in ordered[:max(1, limit)]]

    def summary(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for event in self._events:
            counts[event.kind] = counts.get(event.kind, 0) + 1
        return {"session_id": self.session_id, "event_count": len(self._events), "by_kind": counts}
