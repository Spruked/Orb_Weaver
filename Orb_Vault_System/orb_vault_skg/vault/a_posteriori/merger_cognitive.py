"""
orb/vault/a_posteriori/merger_cognitive.py
Cognitive state for merge/compress operations.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..shared.types import KnowledgeNode


@dataclass
class MergerCognitiveState:
    """
    Tracks canonical forms and merge history.
    """

    canonical_nodes: Dict[str, KnowledgeNode] = field(default_factory=dict)
    merge_map: Dict[str, str] = field(default_factory=dict)
    compressed_patterns: Dict[str, KnowledgeNode] = field(default_factory=dict)
    merge_history: List[Dict[str, Any]] = field(default_factory=list)

    def register_canonical(self, canonical: KnowledgeNode, source_ids: List[str]):
        self.canonical_nodes[canonical.node_id] = canonical
        for sid in source_ids:
            self.merge_map[sid] = canonical.node_id
        from datetime import datetime
        self.merge_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "canonical_id": canonical.node_id,
            "source_ids": source_ids,
            "action": "merge",
        })

    def register_compression(self, pattern: KnowledgeNode, source_ids: List[str]):
        self.compressed_patterns[pattern.node_id] = pattern
        for sid in source_ids:
            self.merge_map[sid] = pattern.node_id
        from datetime import datetime
        self.merge_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "pattern_id": pattern.node_id,
            "source_ids": source_ids,
            "action": "compress",
        })

    def get_canonical(self, node_id: str) -> Optional[KnowledgeNode]:
        canonical_id = self.merge_map.get(node_id, node_id)
        return self.canonical_nodes.get(canonical_id) or self.compressed_patterns.get(canonical_id)

    def is_merged(self, node_id: str) -> bool:
        return node_id in self.merge_map
