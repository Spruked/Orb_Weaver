"""
orb/vault/a_posteriori/verification_logic.py
Multi-signal verification engine.
Determines when candidate knowledge has enough evidence to be trusted.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..shared.types import (
    KnowledgeNode, Experience, VerificationSignal, KnowledgeState, VaultTimestamp
)
from ..shared.confidence import ConfidenceEngine
from ..shared.constants import VaultConstants


class VerificationLogic:
    """
    Applies multiple verification signals to candidate knowledge.
    No learning. Pure evaluation of evidence.
    """

    @staticmethod
    def evaluate_candidate(
        node: KnowledgeNode,
        supporting_experiences: List[Experience],
        owner_approved: bool = False
    ) -> KnowledgeNode:
        """
        Evaluate a candidate node against all available evidence.
        Returns updated node (may modify state).
        """
        # Gather all verification signals
        signals = dict(node.verification_signals)

        # Repetition signal
        if len(supporting_experiences) >= 2:
            signals[VerificationSignal.REPETITION] = signals.get(VerificationSignal.REPETITION, 0) + len(supporting_experiences)

        # Outcome success signals
        success_count = sum(1 for e in supporting_experiences if e.outcome_success)
        if success_count > 0:
            signals[VerificationSignal.OUTCOME_SUCCESS] = signals.get(VerificationSignal.OUTCOME_SUCCESS, 0) + success_count

        # Owner approval
        if owner_approved:
            signals[VerificationSignal.OWNER_APPROVED] = signals.get(VerificationSignal.OWNER_APPROVED, 0) + 1

        # Cross-reference: check if resolution path is consistent
        resolution_paths = set(e.resolution_path for e in supporting_experiences)
        if len(resolution_paths) >= 2:
            signals[VerificationSignal.CROSS_REFERENCE] = signals.get(VerificationSignal.CROSS_REFERENCE, 0) + 1

        # Update node signals
        for signal, count in signals.items():
            node.verification_signals[signal] = count

        # Recalculate confidence
        node.confidence = ConfidenceEngine.calculate_verification_confidence(
            node.verification_signals,
            base_confidence=0.0,
            cap=VaultConstants.MAX_CONFIDENCE_CAP
        )

        # Check if ready for promotion
        if VerificationLogic.meets_promotion_criteria(node):
            node.state = KnowledgeState.UNDER_VERIFICATION

        return node

    @staticmethod
    def meets_promotion_criteria(node: KnowledgeNode) -> bool:
        """Check if candidate meets minimum criteria for promotion consideration."""
        return ConfidenceEngine.promotion_threshold_met(
            node.verification_signals,
            min_signals=VaultConstants.VERIFICATION_MIN_SIGNALS,
            min_confidence=VaultConstants.VERIFICATION_MIN_CONFIDENCE
        )

    @staticmethod
    def verify_source_consistency(
        node: KnowledgeNode,
        current_source_data: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Check if the source data that generated this node is still consistent.
        Returns True if consistent, False if source has changed.
        """
        if current_source_data is None:
            # Cannot verify, assume consistent
            return True

        # Compare node content against current source
        node_result = node.content.get("resolution_result", "")
        # Simple check: if source contains the answer, it's consistent
        source_text = str(current_source_data)
        return node_result in source_text or len(node_result) < 10

    @staticmethod
    def count_supporting_evidence(
        node: KnowledgeNode,
        ledger_records: List[Dict[str, Any]]
    ) -> int:
        """Count ledger records that support this node's pattern."""
        node_intent = node.content.get("intent", "")
        node_entities = set(node.content.get("entities", []))

        count = 0
        for record in ledger_records:
            if record["detected_intent"] != node_intent:
                continue
            record_entities = set(record.get("detected_entities", []))
            if node_entities & record_entities:  # Overlap
                if record["outcome_success"]:
                    count += 1

        return count
