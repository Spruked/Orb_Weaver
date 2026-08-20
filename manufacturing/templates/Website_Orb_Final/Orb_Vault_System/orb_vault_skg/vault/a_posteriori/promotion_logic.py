"""
orb/vault/a_posteriori/promotion_logic.py
Promotion gate: candidate → promoted.
Deterministic criteria. No ambiguity.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional

from ..shared.types import KnowledgeNode, KnowledgeState, VaultTimestamp, VerificationSignal
from ..shared.confidence import ConfidenceEngine
from ..shared.constants import VaultConstants


class PromotionLogic:
    """
    Decides when candidate knowledge graduates to promoted status.
    Once promoted, the knowledge enters the active learned layer.
    """

    @staticmethod
    def evaluate_promotion(node: KnowledgeNode) -> tuple[bool, str]:
        """
        Evaluate if a node should be promoted.
        Returns (should_promote, reason).
        """
        # Must be in candidate or under_verification state
        if node.state not in (KnowledgeState.CANDIDATE, KnowledgeState.UNDER_VERIFICATION):
            return False, f"invalid_state:{node.state.name}"

        # Check minimum confidence
        if node.confidence.value < VaultConstants.VERIFICATION_MIN_CONFIDENCE:
            return False, f"confidence_too_low:{node.confidence.value:.3f}"

        # Check signal diversity
        active_signals = [s for s, c in node.verification_signals.items() if c > 0]
        if len(active_signals) < VaultConstants.VERIFICATION_MIN_SIGNALS:
            return False, f"insufficient_signals:{len(active_signals)}"

        # Check success streak
        if node.success_streak < VaultConstants.PROMOTION_MIN_SUCCESS_STREAK:
            return False, f"insufficient_success_streak:{node.success_streak}"

        # Check access count
        if node.access_count < VaultConstants.PROMOTION_MIN_ACCESS_COUNT:
            return False, f"insufficient_access:{node.access_count}"

        # Check for unresolved degradation signals
        critical_degradation = (
            node.degradation_signals.get(VerificationSignal, 0)  # type: ignore
            if hasattr(VerificationSignal, 'CONTRADICTION')
            else 0
        )
        # Actually check degradation
        from ..shared.types import DegradationSignal
        contradiction_count = node.degradation_signals.get(DegradationSignal.CONTRADICTION, 0)
        if contradiction_count >= 2:
            return False, f"unresolved_contradictions:{contradiction_count}"

        return True, "all_criteria_met"

    @staticmethod
    def promote(node: KnowledgeNode) -> KnowledgeNode:
        """
        Promote a node to active learned layer.
        This is a state transition with immutable timestamp.
        """
        node.state = KnowledgeState.PROMOTED
        node.promoted_at = VaultTimestamp()
        # Boost confidence slightly on promotion
        node.confidence = node.confidence.adjust(0.05, "promotion_boost")
        return node

    @staticmethod
    def demote(node: KnowledgeNode, reason: str) -> KnowledgeNode:
        """
        Demote a promoted node back to weakened state.
        Triggered by degradation signals.
        """
        node.state = KnowledgeState.WEAKENED
        node.confidence = node.confidence.adjust(-0.15, f"demotion:{reason}")
        return node
