"""
KnowledgeAtom and CorrespondenceEdge — MANDATORY / FROZEN.

KnowledgeAtom = stored geometric memory object (post-sublimation,
post-correspondence-scoring). Small, immutable where practical.
Deliberately does NOT carry relationships, history, or contradictions
directly — that was the "god object" problem in an earlier draft.

CorrespondenceEdge = relational link between atoms. The graph carries
relational meaning; nodes stay lightweight.

NOTE: Nothing in this file computes a CorrespondenceVector. See
gaps.py: GAP_A for why that's a deliberate omission, not an oversight.

This module owns only local structural invariants. It does NOT verify:
- whether referenced atoms actually exist
- whether a relationship is semantically justified
- whether duplicate edges already exist
- whether vector values were correctly computed
- whether confidence values are epistemically deserved
- whether a SUPERSEDES or DRIFTS_FROM relationship is chronologically valid

Those responsibilities belong to the Vault, graph, Correspondence Engine,
or governance layers.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .vectors import CorrespondenceVector


@dataclass(frozen=True)
class KnowledgeAtom:
    atom_id: str
    observation: str
    correspondence_vector: CorrespondenceVector
    confidence: float
    provenance: str
    timestamp: datetime

    def __post_init__(self) -> None:
        if not self.atom_id:
            raise ValueError("atom_id must be non-empty")

        if not self.observation:
            raise ValueError("observation must be non-empty")

        if not isinstance(self.correspondence_vector, CorrespondenceVector):
            raise TypeError(
                "correspondence_vector must be a CorrespondenceVector"
            )

        if not isinstance(self.confidence, (int, float)):
            raise TypeError(
                f"confidence must be numeric, got "
                f"{type(self.confidence).__name__}"
            )

        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(
                f"confidence must be in [0,1], got {self.confidence}"
            )

        if not self.provenance:
            raise ValueError("provenance must be non-empty")

        if not isinstance(self.timestamp, datetime):
            raise TypeError(
                f"timestamp must be datetime, got "
                f"{type(self.timestamp).__name__}"
            )


class RelationType(Enum):
    """
    Closed vocabulary for atom-to-atom relationships.

    Enum, not a free string. An earlier draft used `relation: str`,
    which invites silent typo-driven failures in downstream logic
    such as re-challenge triggers, contradiction handling, and
    drift detection.
    """

    CORROBORATES = "corroborates"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"
    DRIFTS_FROM = "drifts_from"
    DEPENDS_ON = "depends_on"


@dataclass(frozen=True)
class CorrespondenceEdge:
    source_atom_id: str
    target_atom_id: str
    relation: RelationType
    weight: float
    confidence: float
    timestamp: datetime

    def __post_init__(self) -> None:
        if not self.source_atom_id:
            raise ValueError("source_atom_id must be non-empty")

        if not self.target_atom_id:
            raise ValueError("target_atom_id must be non-empty")

        if self.source_atom_id == self.target_atom_id:
            raise ValueError("an edge cannot connect an atom to itself")

        if not isinstance(self.relation, RelationType):
            raise TypeError(
                f"relation must be RelationType, got "
                f"{type(self.relation).__name__}"
            )

        if not isinstance(self.weight, (int, float)):
            raise TypeError(
                f"weight must be numeric, got "
                f"{type(self.weight).__name__}"
            )

        if not 0.0 <= float(self.weight) <= 1.0:
            raise ValueError(
                f"weight must be in [0,1], got {self.weight}"
            )

        if not isinstance(self.confidence, (int, float)):
            raise TypeError(
                f"confidence must be numeric, got "
                f"{type(self.confidence).__name__}"
            )

        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(
                f"confidence must be in [0,1], got {self.confidence}"
            )

        if not isinstance(self.timestamp, datetime):
            raise TypeError(
                f"timestamp must be datetime, got "
                f"{type(self.timestamp).__name__}"
            )