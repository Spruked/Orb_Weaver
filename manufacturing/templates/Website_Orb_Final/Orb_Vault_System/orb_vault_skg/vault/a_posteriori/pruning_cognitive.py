"""
orb/vault/a_posteriori/pruning_cognitive.py
Cognitive state for pruning operations.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..shared.types import KnowledgeNode


@dataclass
class PruningCognitiveState:
    """
    Tracks pruning history and archived nodes.
    """

    # Retired nodes (archived, not deleted)
    retired_nodes: Dict[str, KnowledgeNode] = field(default_factory=dict)

    # Pruning history: [(timestamp, node_id, action, reason)]
    pruning_log: List[tuple] = field(default_factory=list)

    # Compression log: [(timestamp, source_ids, target_id)]
    compression_log: List[tuple] = field(default_factory=list)

    # Merge log: [(timestamp, source_id, target_id, reason)]
    merge_log: List[tuple] = field(default_factory=list)

    # Last prune timestamp
    last_prune_timestamp: float = 0.0

    # Pruning statistics
    total_pruned: int = 0
    total_weakened: int = 0
    total_merged: int = 0
    total_compressed: int = 0

    def record_prune(self, node_id: str, action: str, reason: str):
        """Record a pruning action."""
        from datetime import datetime
        timestamp = datetime.utcnow().isoformat()
        self.pruning_log.append((timestamp, node_id, action, reason))

        if action == "retire":
            self.total_pruned += 1
        elif action == "weaken":
            self.total_weakened += 1
        elif action == "merge":
            self.total_merged += 1
        elif action == "compress":
            self.total_compressed += 1

    def archive_node(self, node: KnowledgeNode):
        """Move node to retired archive."""
        self.retired_nodes[node.node_id] = node

    def record_compression(self, source_ids: List[str], target_id: str):
        """Record a compression operation."""
        from datetime import datetime
        self.compression_log.append((datetime.utcnow().isoformat(), source_ids, target_id))

    def record_merge(self, source_id: str, target_id: str, reason: str):
        """Record a merge operation."""
        from datetime import datetime
        self.merge_log.append((datetime.utcnow().isoformat(), source_id, target_id, reason))

    def get_stats(self) -> Dict[str, Any]:
        """Get pruning statistics."""
        return {
            "total_pruned": self.total_pruned,
            "total_weakened": self.total_weakened,
            "total_merged": self.total_merged,
            "total_compressed": self.total_compressed,
            "retired_archive_size": len(self.retired_nodes),
            "last_prune": self.last_prune_timestamp,
        }
