"""
orb/vault/a_posteriori/reinforcement_logic.py
Usage-based reinforcement: successful use strengthens relationships.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..shared.types import KnowledgeNode, VaultTimestamp
from ..shared.confidence import ConfidenceEngine
from ..shared.constants import VaultConstants


class ReinforcementLogic:
    """
    Reinforces knowledge weights based on usage outcomes.
    Success strengthens. Failure weakens. Streaks amplify.
    """

    @staticmethod
    def reinforce_from_usage(
        node: KnowledgeNode,
        success: bool,
        query_text: str = "",
        resolution_time_ms: float = 0.0
    ) -> KnowledgeNode:
        """
        Reinforce a node based on usage outcome.
        Updates confidence, streaks, and access counts.
        """
        # Update access tracking
        node.access_count += 1
        node.last_reinforced = VaultTimestamp()

        # Update streaks
        if success:
            node.success_streak += 1
            node.failure_streak = 0
        else:
            node.failure_streak += 1
            node.success_streak = 0

        # Apply confidence reinforcement
        streak = node.success_streak if success else node.failure_streak
        node.confidence = ConfidenceEngine.reinforce(node.confidence, success, streak)

        # Bonus for fast resolution (indicates good match)
        if success and resolution_time_ms < 100:
            node.confidence = node.confidence.adjust(0.01, "fast_resolution")

        return node

    @staticmethod
    def calculate_usefulness_score(node: KnowledgeNode) -> float:
        """
        Calculate a usefulness score for pruning decisions.
        Combines access frequency, success rate, and recency.
        """
        if node.access_count == 0:
            return 0.0

        success_rate = node.success_count / node.access_count if node.access_count > 0 else 0

        # Recency factor
        days_since_use = 999
        if node.last_reinforced:
            days_since_use = (datetime.utcnow().timestamp() - node.last_reinforced.unix) / 86400

        recency_factor = max(0, 1.0 - (days_since_use / 30))  # Decay over 30 days

        # Access frequency factor (log-scaled)
        import math
        freq_factor = math.log1p(node.access_count) / math.log1p(100)

        usefulness = (success_rate * 0.4) + (recency_factor * 0.3) + (freq_factor * 0.3)
        return min(1.0, usefulness)

    @staticmethod
    def decay_stale_knowledge(node: KnowledgeNode) -> KnowledgeNode:
        """
        Apply time decay to knowledge that hasn't been used.
        Called during periodic maintenance.
        """
        if not node.last_reinforced:
            return node

        days_since = (datetime.utcnow().timestamp() - node.last_reinforced.unix) / 86400
        node.confidence = ConfidenceEngine.apply_time_decay(node.confidence, days_since)

        return node
