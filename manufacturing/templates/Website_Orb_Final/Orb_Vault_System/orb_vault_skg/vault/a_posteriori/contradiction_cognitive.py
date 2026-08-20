"""
orb/vault/a_posteriori/contradiction_cognitive.py
Cognitive state for contradiction tracking.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..shared.types import KnowledgeNode


@dataclass
class ContradictionCognitiveState:
    """
    Tracks detected contradictions and their resolution status.
    """

    # Active contradictions: contradiction_id -> details
    active_contradictions: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Node -> list of contradiction IDs
    node_contradictions: Dict[str, List[str]] = field(default_factory=dict)

    # Resolved contradictions history
    resolved_contradictions: List[Dict[str, Any]] = field(default_factory=list)

    # Source change tracking: node_id -> last known source hash
    source_hashes: Dict[str, str] = field(default_factory=dict)

    def register_contradiction(self, contradiction: Dict[str, Any]) -> str:
        """Register a new contradiction. Returns contradiction ID."""
        import uuid
        cid = f"contr_{uuid.uuid4().hex[:12]}"
        self.active_contradictions[cid] = contradiction

        # Link to nodes
        if "node1_id" in contradiction:
            n1 = contradiction["node1_id"]
            if n1 not in self.node_contradictions:
                self.node_contradictions[n1] = []
            self.node_contradictions[n1].append(cid)

        if "node2_id" in contradiction:
            n2 = contradiction["node2_id"]
            if n2 not in self.node_contradictions:
                self.node_contradictions[n2] = []
            self.node_contradictions[n2].append(cid)

        if "posteriori_node_id" in contradiction:
            n = contradiction["posteriori_node_id"]
            if n not in self.node_contradictions:
                self.node_contradictions[n] = []
            self.node_contradictions[n].append(cid)

        return cid

    def resolve_contradiction(self, cid: str, resolution: str, winner_id: Optional[str] = None):
        """Mark a contradiction as resolved."""
        if cid in self.active_contradictions:
            contr = self.active_contradictions.pop(cid)
            contr["resolution"] = resolution
            contr["winner_id"] = winner_id
            from datetime import datetime
            contr["resolved_at"] = datetime.utcnow().isoformat()
            self.resolved_contradictions.append(contr)

    def get_node_contradiction_count(self, node_id: str) -> int:
        """Count active contradictions involving a node."""
        return len(self.node_contradictions.get(node_id, []))

    def has_contradictions(self, node_id: str) -> bool:
        """Check if node has any active contradictions."""
        return self.get_node_contradiction_count(node_id) > 0
