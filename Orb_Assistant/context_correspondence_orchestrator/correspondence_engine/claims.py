"""
KnowledgeClaim — INCOMPLETE. Schema is a working draft, NOT frozen.

Open questions (see gaps.py: GAP_F):
  - Exact field set for subject/predicate/object decomposition
  - How contradictions are represented (flag vs. edge vs. both)
  - What triggers Claim -> Atom promotion (confidence floor?
    automatic on sublimation completion? manual review?)
  - Whether this object or the Atom carries the correspondence
    vector (currently neither does — see gaps.py: GAP_A)

Do not treat this as final. It exists so SemanticSublimator has a
concrete return type to target, not because the design is settled.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class KnowledgeClaim:
    claim_id: str
    subject: str
    predicate: str
    object_: str  # trailing underscore: `object` shadows the builtin
    source_evidence_ids: List[str]
    provenance: str
    timestamp: datetime
    confidence: float
    contradicts_claim_ids: List[str] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")

    def promote_to_atom(self):
        """
        Claim -> Atom transition.

        NOT IMPLEMENTED. This sits directly on GAP_A and GAP_F:
        promotion requires a CorrespondenceVector, and no module
        currently owns computing one, and no confidence/validation
        threshold has been specified for when promotion should even
        happen. Resolve GAP_A before implementing this method.
        """
        raise NotImplementedError(
            "Claim->Atom promotion requires a CorrespondenceVector, and no "
            "module currently owns computing one. See gaps.py: GAP_A, GAP_F."
        )
