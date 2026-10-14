"""Formal, bounded outcome evidence for retrieval and governed actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class OutcomeSignal:
    session_id: str
    cognitive_event_id: str
    outcome: str
    quality: float
    confidence: float
    retrieval_id: Optional[str] = None
    action_id: Optional[str] = None
    capability: Optional[str] = None
    result: Optional[str] = None
    visitor_response: Optional[str] = None
    evidence_ids: List[str] = field(default_factory=list)
    delay_ms: Optional[int] = None

    def __post_init__(self):
        if not self.session_id or not self.cognitive_event_id or not self.outcome:
            raise ValueError("OutcomeSignal requires session_id, cognitive_event_id, and outcome")
        if not 0.0 <= self.quality <= 1.0 or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("OutcomeSignal quality and confidence must be within [0, 1]")
        if self.delay_ms is not None and self.delay_ms < 0:
            raise ValueError("OutcomeSignal delay_ms cannot be negative")

    @property
    def is_material(self) -> bool:
        return self.quality * self.confidence >= 0.50

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id, "cognitive_event_id": self.cognitive_event_id,
            "retrieval_id": self.retrieval_id, "action_id": self.action_id,
            "capability": self.capability, "outcome": self.outcome, "quality": self.quality,
            "confidence": self.confidence, "result": self.result,
            "visitor_response": self.visitor_response, "evidence_ids": list(self.evidence_ids),
            "delay_ms": self.delay_ms,
        }
