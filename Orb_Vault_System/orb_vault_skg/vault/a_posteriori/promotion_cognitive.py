"""
orb/vault/a_posteriori/promotion_cognitive.py
Cognitive state for promotion tracking.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..shared.types import KnowledgeNode


@dataclass
class PromotionCognitiveState:
    """
    Tracks promotion history and pending promotions.
    """

    # Promoted nodes (active learned layer)
    promoted_nodes: Dict[str, KnowledgeNode] = field(default_factory=dict)

    # Promotion history: node_id -> [(timestamp, reason)]
    promotion_history: Dict[str, List[tuple]] = field(default_factory=dict)

    # Demotion history
    demotion_history: Dict[str, List[tuple]] = field(default_factory=dict)

    # Pending promotions awaiting final check
    pending_promotions: Dict[str, KnowledgeNode] = field(default_factory=dict)

    def register_promotion(self, node: KnowledgeNode, reason: str):
        """Record a successful promotion."""
        self.promoted_nodes[node.node_id] = node
        if node.node_id not in self.promotion_history:
            self.promotion_history[node.node_id] = []
        from datetime import datetime
        self.promotion_history[node.node_id].append((datetime.utcnow().isoformat(), reason))
        self.pending_promotions.pop(node.node_id, None)

    def register_demotion(self, node_id: str, reason: str):
        """Record a demotion."""
        self.promoted_nodes.pop(node_id, None)
        if node_id not in self.demotion_history:
            self.demotion_history[node_id] = []
        from datetime import datetime
        self.demotion_history[node_id].append((datetime.utcnow().isoformat(), reason))

    def get_promoted_count(self) -> int:
        """Count active promoted nodes."""
        return len(self.promoted_nodes)

    def is_promoted(self, node_id: str) -> bool:
        """Check if node is in promoted state."""
        return node_id in self.promoted_nodes
