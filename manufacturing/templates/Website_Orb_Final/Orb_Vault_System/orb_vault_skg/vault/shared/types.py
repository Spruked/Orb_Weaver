"""
orb/vault/shared/types.py
Core type definitions for A Priori and A Posteriori Vault SKGs.
All vault operations use these shared primitives.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Dict, List, Any, Set, Callable
import hashlib
import json


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class KnowledgeState(Enum):
    """Lifecycle states for posteriori knowledge nodes/edges."""
    CANDIDATE = auto()           # Newly observed, awaiting verification
    UNDER_VERIFICATION = auto()  # Multi-signal validation in progress
    PROMOTED = auto()            # Verified and active in learned layer
    WEAKENED = auto()            # Showing degradation signals
    RETIRED = auto()             # Removed from active use, archived
    MERGED = auto()              # Absorbed into canonical form


class VerificationSignal(Enum):
    """Signals that contribute to verification confidence."""
    REPETITION = auto()          # Same correspondence observed multiple times
    OUTCOME_SUCCESS = auto()     # Led to successful resolution
    SOURCE_CONSISTENT = auto()   # Source data unchanged since observation
    OWNER_APPROVED = auto()      # Explicit owner validation
    CROSS_REFERENCE = auto()     # Confirmed by independent path


class DegradationSignal(Enum):
    """Signals that trigger weakening or pruning."""
    CONTRADICTION = auto()       # Conflicts with higher-confidence knowledge
    STALENESS = auto()           # Not accessed for extended period
    SOURCE_CHANGED = auto()      # Underlying source data modified
    LOW_USEFULNESS = auto()      # Rarely contributes to resolutions
    DUPLICATION = auto()          # Redundant with other knowledge
    POOR_OUTCOME = auto()         # Led to failed resolution
    CONFIDENCE_DECAY = auto()     # Natural confidence erosion


class EntityType(Enum):
    """Types of entities in the knowledge graph."""
    PRODUCT = auto()
    SERVICE = auto()
    CATEGORY = auto()
    POLICY = auto()
    DEPARTMENT = auto()
    QUESTION_PATTERN = auto()
    ANSWER_TEMPLATE = auto()
    INTENT = auto()
    ATTRIBUTE = auto()
    RELATIONSHIP = auto()
    PRICE_POINT = auto()
    AVAILABILITY = auto()


class RelationType(Enum):
    """Types of relationships between entities."""
    ANSWERS = auto()             # answer → question
    BELONGS_TO = auto()          # product → category
    PRICED_AT = auto()           # product → price
    HANDLED_BY = auto()          # intent → department
    REQUIRES = auto()            # service → prerequisite
    SIMILAR_TO = auto()          # product → product
    SUPERSEDES = auto()          # new_knowledge → old_knowledge
    CONTRADICTS = auto()         # knowledge → conflicting_knowledge
    LEADS_TO = auto()            # question_pattern → resolution_path
    HAS_ATTRIBUTE = auto()       # entity → attribute
    LOCATED_AT = auto()          # business → address
    AVAILABLE_DURING = auto()    # service → hours


class IntentType(Enum):
    """Recognized visitor intent types for routing."""
    PRODUCT_PRICE = auto()
    PRODUCT_AVAILABILITY = auto()
    PRODUCT_INFO = auto()
    CATEGORY_BROWSE = auto()
    SERVICE_INQUIRY = auto()
    POLICY_QUESTION = auto()
    CONTACT_INFO = auto()
    HOURS_LOCATION = auto()
    COMPARISON = auto()
    RECOMMENDATION = auto()
    GENERAL = auto()


# ---------------------------------------------------------------------------
# Core Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VaultTimestamp:
    """Immutable timestamp with versioning support."""
    iso: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    unix: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    crawl_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"iso": self.iso, "unix": self.unix, "crawl_version": self.crawl_version}


@dataclass
class Confidence:
    """Confidence value with cap enforcement and provenance tracking."""
    value: float = 0.0
    cap: float = 0.95           # Default cap; 0.75 under peer tension
    provenance: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.value = max(0.0, min(self.value, self.cap))

    def adjust(self, delta: float, reason: str) -> "Confidence":
        new_val = max(0.0, min(self.value + delta, self.cap))
        new_prov = self.provenance + [reason]
        return Confidence(value=new_val, cap=self.cap, provenance=new_prov)

    def set_cap(self, new_cap: float, reason: str) -> "Confidence":
        capped = min(self.value, new_cap)
        new_prov = self.provenance + [f"cap_adjusted:{reason}"]
        return Confidence(value=capped, cap=new_cap, provenance=new_prov)


@dataclass
class Entity:
    """A node in the knowledge graph."""
    entity_id: str
    entity_type: EntityType
    canonical_name: str
    aliases: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    source_url: str = ""
    source_element: str = ""
    first_seen: VaultTimestamp = field(default_factory=VaultTimestamp)
    last_seen: VaultTimestamp = field(default_factory=VaultTimestamp)
    crawl_version: str = ""

    def fingerprint(self) -> str:
        """Deterministic hash for deduplication."""
        payload = f"{self.entity_type.name}:{self.canonical_name}:{sorted(self.aliases)}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class Relation:
    """An edge in the knowledge graph."""
    relation_id: str
    relation_type: RelationType
    source_id: str
    target_id: str
    weight: float = 1.0
    confidence: Confidence = field(default_factory=Confidence)
    attributes: Dict[str, Any] = field(default_factory=dict)
    first_seen: VaultTimestamp = field(default_factory=VaultTimestamp)
    last_accessed: VaultTimestamp = field(default_factory=VaultTimestamp)
    access_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    state: KnowledgeState = KnowledgeState.CANDIDATE

    def fingerprint(self) -> str:
        payload = f"{self.relation_type.name}:{self.source_id}:{self.target_id}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def record_access(self, success: bool):
        self.access_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.last_accessed = VaultTimestamp()


@dataclass
class Experience:
    """An immutable observation of an interaction."""
    experience_id: str
    timestamp: VaultTimestamp
    query_text: str
    detected_intent: IntentType
    detected_entities: List[str]
    resolution_path: str          # Which system resolved it (a_priori, a_posteriori, llm, tpc)
    resolution_result: str
    outcome_success: bool
    user_feedback: Optional[str] = None
    session_id: str = ""
    source_signals: List[VerificationSignal] = field(default_factory=list)

    def fingerprint(self) -> str:
        payload = f"{self.query_text}:{self.detected_intent.name}:{self.resolution_path}:{self.outcome_success}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class KnowledgeNode:
    """A Posteriori knowledge unit — can be promoted, reinforced, pruned."""
    node_id: str
    node_type: EntityType
    content: Dict[str, Any]
    confidence: Confidence
    state: KnowledgeState
    created_at: VaultTimestamp
    verified_at: Optional[VaultTimestamp] = None
    promoted_at: Optional[VaultTimestamp] = None
    last_reinforced: Optional[VaultTimestamp] = None
    access_count: int = 0
    success_streak: int = 0
    failure_streak: int = 0
    verification_signals: Dict[VerificationSignal, int] = field(default_factory=dict)
    degradation_signals: Dict[DegradationSignal, int] = field(default_factory=dict)
    merged_into: Optional[str] = None

    def add_verification_signal(self, signal: VerificationSignal):
        self.verification_signals[signal] = self.verification_signals.get(signal, 0) + 1

    def add_degradation_signal(self, signal: DegradationSignal):
        self.degradation_signals[signal] = self.degradation_signals.get(signal, 0) + 1


@dataclass
class CatalogEntry:
    """A Priori catalog entry — settled truth from crawl/owner."""
    entry_id: str
    entry_type: EntityType
    name: str
    sku: Optional[str] = None
    current_price: Optional[float] = None
    sale_price: Optional[float] = None
    currency: str = "USD"
    variant: Optional[str] = None
    availability: Optional[str] = None
    specifications: Dict[str, Any] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    source_url: str = ""
    source_element: str = ""
    last_seen: VaultTimestamp = field(default_factory=VaultTimestamp)
    crawl_version: str = ""
    owner_verified: bool = False

    def to_price_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.entry_id,
            "name": self.name,
            "sku": self.sku,
            "current_price": self.current_price,
            "sale_price": self.sale_price,
            "currency": self.currency,
            "variant": self.variant,
            "availability": self.availability,
            "source_url": self.source_url,
            "last_seen": self.last_seen.to_dict(),
        }


@dataclass
class QACorrespondence:
    """Verified question/answer pair — settled truth."""
    qa_id: str
    question_patterns: List[str]
    answer_template: str
    answer_variables: List[str] = field(default_factory=list)
    intent: IntentType = IntentType.GENERAL
    confidence: Confidence = field(default_factory=lambda: Confidence(value=0.9, cap=0.95))
    source: str = "owner"          # owner, crawl, verified_posteriori
    created_at: VaultTimestamp = field(default_factory=VaultTimestamp)
    access_count: int = 0
    success_count: int = 0


@dataclass
class PolicyRule:
    """Owner-approved policy statement."""
    rule_id: str
    category: str
    statement: str
    conditions: List[str] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    priority: int = 5              # 1 = highest
    source: str = "owner"
    created_at: VaultTimestamp = field(default_factory=VaultTimestamp)


@dataclass
class ResolutionResult:
    """Result returned from vault query."""
    success: bool
    answer: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    source: str = ""              # a_priori_catalog, a_priori_ontology, a_priori_qa, a_posteriori, llm, tpc
    confidence: float = 0.0
    entity_id: Optional[str] = None
    resolution_path: List[str] = field(default_factory=list)
    used_fallback: bool = False
