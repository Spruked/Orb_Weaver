"""
orb/vault/a_posteriori/verification_cognitive.py
Cognitive state for verification tracking.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..shared.types import KnowledgeNode


@dataclass
class VerificationCognitiveState:
    """
    Tracks verification status and pending evaluations.
    """

    # Nodes currently under verification
    under_verification: Dict[str, KnowledgeNode] = field(default_factory=dict)

    # Verification start timestamps
    verification_started: Dict[str, float] = field(default_factory=dict)

    # Owner approval status
    owner_approved_ids: set = field(default_factory=set)

    # Source consistency cache: node_id -> (last_checked, is_consistent)
    source_consistency_cache: Dict[str, tuple] = field(default_factory=dict)

    def start_verification(self, node: KnowledgeNode):
        """Mark node as under verification."""
        self.under_verification[node.node_id] = node
        self.verification_started[node.node_id] = datetime.utcnow().timestamp()

    def complete_verification(self, node_id: str, approved: bool):
        """Complete verification process."""
        self.under_verification.pop(node_id, None)
        self.verification_started.pop(node_id, None)
        if approved:
            self.owner_approved_ids.add(node_id)

    def is_owner_approved(self, node_id: str) -> bool:
        """Check if node has owner approval."""
        return node_id in self.owner_approved_ids

    def cache_source_check(self, node_id: str, is_consistent: bool):
        """Cache source consistency check result."""
        self.source_consistency_cache[node_id] = (datetime.utcnow().timestamp(), is_consistent)

    def get_cached_consistency(self, node_id: str, max_age_seconds: float = 3600) -> Optional[bool]:
        """Get cached consistency check if not stale."""
        if node_id not in self.source_consistency_cache:
            return None
        timestamp, result = self.source_consistency_cache[node_id]
        age = datetime.utcnow().timestamp() - timestamp
        if age > max_age_seconds:
            return None
        return result
