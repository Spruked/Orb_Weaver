"""
Semantic Sublimator — EvidenceItem(s) -> KnowledgeClaim.

MANDATORY scope, INCOMPLETE implementation.

Frozen responsibility: normalize irregular evidence into structured
claims, preserve contradictions, attach provenance. Nothing more.
Explicitly OUT of scope for this module:
  - correspondence vector computation (see gaps.py: GAP_A)
  - distance metrics / geometric placement (owned by geometry.py)
  - Mahalanobis / metric selection (owned by geometry.py)

The actual subject-predicate-object extraction from irregular
evidence text is a real reasoning task. It is not stubbed here with
fake string-splitting that would misrepresent it as solved — see
gaps.py: GAP_F ("KnowledgeClaim Extraction Rules" was identified as
required documentation and has not been written).
"""

from typing import List

from .evidence import EvidenceItem
from .claims import KnowledgeClaim


class SemanticSublimator:
    def sublimate(self, evidence_items: List[EvidenceItem]) -> KnowledgeClaim:
        """
        Convert one or more corroborating/conflicting EvidenceItems
        into a single structured KnowledgeClaim.

        NOT IMPLEMENTED. Extraction logic (how subject/predicate/object
        are derived from EvidenceItem.claim text) has not been designed
        — only the module boundary has been agreed. See gaps.py: GAP_F.
        """
        if not evidence_items:
            raise ValueError("cannot sublimate an empty evidence set")
        raise NotImplementedError(
            "Extraction rules (subject/predicate/object derivation) "
            "are undesigned. See gaps.py: GAP_F."
        )
