"""
Correspondence Engine — scaffold.

Status: MANDATORY objects (evidence, vectors, atoms) are frozen and
validated. Pipeline connective tissue (correspondence vector
computation, sublimator extraction, geometry stability/drift checks,
ECM) is deliberately left as NotImplementedError rather than faked.

Read gaps.py before extending anything. Run demo_smoke_test.py to
see exactly what works today and where the honest stop points are.
"""

from .evidence import EvidenceItem
from .vectors import CorrespondenceVector
from .claims import KnowledgeClaim
from .atoms import KnowledgeAtom, CorrespondenceEdge, RelationType
from .sublimator import SemanticSublimator
from .vault import Vault
from . import geometry
from . import challenge
from . import gaps

__all__ = [
    "EvidenceItem",
    "CorrespondenceVector",
    "KnowledgeClaim",
    "KnowledgeAtom",
    "CorrespondenceEdge",
    "RelationType",
    "SemanticSublimator",
    "Vault",
    "geometry",
    "challenge",
    "gaps",
]
