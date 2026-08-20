"""
orb/vault/a_posteriori/experience_cognitive.py
Cognitive state for experience capture.
Holds candidate queue, recent experiences buffer, and pattern index.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import deque

from ..shared.types import Experience, KnowledgeNode


@dataclass
class ExperienceCognitiveState:
    """
    Mutable cognitive state for the experience capture system.
    Separated from logic per architecture rules.
    """

    # Recent experiences buffer (last N for quick pattern detection)
    recent_buffer: deque = field(default_factory=lambda: deque(maxlen=100))

    # Candidate nodes awaiting verification
    candidate_queue: Dict[str, KnowledgeNode] = field(default_factory=dict)

    # Pattern index: intent+entity_hash -> list of experience IDs
    pattern_index: Dict[str, List[str]] = field(default_factory=dict)

    # Entity -> experiences mapping
    entity_index: Dict[str, List[str]] = field(default_factory=dict)

    # Session tracking
    session_experiences: Dict[str, List[str]] = field(default_factory=dict)

    def add_to_buffer(self, experience: Experience):
        """Add experience to recent buffer."""
        self.recent_buffer.append(experience)

    def queue_candidate(self, node: KnowledgeNode):
        """Add a candidate node to verification queue."""
        self.candidate_queue[node.node_id] = node

    def index_experience(self, experience: Experience):
        """Index experience by pattern and entities."""
        # Pattern index
        pattern_key = f"{experience.detected_intent.name}:{'|'.join(sorted(experience.detected_entities))}"
        if pattern_key not in self.pattern_index:
            self.pattern_index[pattern_key] = []
        self.pattern_index[pattern_key].append(experience.experience_id)

        # Entity index
        for entity in experience.detected_entities:
            if entity not in self.entity_index:
                self.entity_index[entity] = []
            self.entity_index[entity].append(experience.experience_id)

        # Session index
        if experience.session_id:
            if experience.session_id not in self.session_experiences:
                self.session_experiences[experience.session_id] = []
            self.session_experiences[experience.session_id].append(experience.experience_id)

    def get_similar_experiences(
        self,
        intent_name: str,
        entities: List[str],
        lookback: int = 50
    ) -> List[Experience]:
        """Get recent experiences matching intent+entity pattern."""
        pattern_key = f"{intent_name}:{'|'.join(sorted(entities))}"
        exp_ids = self.pattern_index.get(pattern_key, [])

        # Filter from recent buffer
        results = []
        for exp in list(self.recent_buffer)[-lookback:]:
            if exp.experience_id in exp_ids:
                results.append(exp)
        return results

    def get_candidate_count(self) -> int:
        """Count candidates awaiting verification."""
        return len(self.candidate_queue)

    def remove_candidate(self, node_id: str):
        """Remove candidate from queue (promoted or pruned)."""
        self.candidate_queue.pop(node_id, None)
