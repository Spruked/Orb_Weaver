"""
orb/vault/a_posteriori/pruning_logic.py
Self-pruning engine.
Removes knowledge based on usefulness and validity, NOT age.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from ..shared.types import (
    KnowledgeNode, KnowledgeState, DegradationSignal, VaultTimestamp, Confidence
)
from ..shared.confidence import ConfidenceEngine
from ..shared.constants import VaultConstants


class PruningLogic:
    """
    Prunes knowledge based on usefulness and validity signals.
    Never prunes based on age alone.
    """

    @staticmethod
    def evaluate_for_pruning(node: KnowledgeNode) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Evaluate a node for pruning.
        Returns (action, details).
        Actions: retain, weaken, merge, compress, retire
        """
        # Calculate days since last use
        days_since_use = 999
        if node.last_reinforced:
            days_since_use = (datetime.utcnow().timestamp() - node.last_reinforced.unix) / 86400

        # Check degradation severity
        total_degradation = sum(node.degradation_signals.values())

        # Decision tree

        # 1. Severe degradation + low confidence → retire
        if total_degradation >= 5 and node.confidence.value < 0.25:
            return "retire", {
                "reason": "severe_degradation",
                "degradation_count": total_degradation,
                "confidence": node.confidence.value,
            }

        # 2. Source changed + low confidence → retire
        if (node.degradation_signals.get(DegradationSignal.SOURCE_CHANGED, 0) > 0 and 
            node.confidence.value < 0.30):
            return "retire", {
                "reason": "source_changed_untrusted",
                "confidence": node.confidence.value,
            }

        # 3. Contradicted + cannot resolve → weaken or retire
        contradiction_count = node.degradation_signals.get(DegradationSignal.CONTRADICTION, 0)
        if contradiction_count >= 3 and node.confidence.value < 0.35:
            return "retire", {
                "reason": "persistently_contradicted",
                "contradiction_count": contradiction_count,
            }
        elif contradiction_count >= 2 and node.confidence.value < 0.50:
            return "weaken", {
                "reason": "contradicted",
                "contradiction_count": contradiction_count,
            }

        # 4. Low usefulness + stale → merge or compress
        if (node.access_count < VaultConstants.PRUNE_MIN_ACCESS_COUNT and 
            days_since_use > VaultConstants.PRUNE_STALENESS_DAYS and
            node.confidence.value < VaultConstants.PRUNE_WEAKEN_THRESHOLD):

            # If it has some value, compress instead of retire
            if node.confidence.value > 0.15:
                return "compress", {
                    "reason": "low_use_stale_compressible",
                    "access_count": node.access_count,
                    "days_since_use": days_since_use,
                }
            else:
                return "retire", {
                    "reason": "low_use_stale",
                    "access_count": node.access_count,
                    "days_since_use": days_since_use,
                }

        # 5. Poor outcomes → weaken
        poor_outcome_count = node.degradation_signals.get(DegradationSignal.POOR_OUTCOME, 0)
        if poor_outcome_count >= 3:
            return "weaken", {
                "reason": "repeated_poor_outcomes",
                "poor_outcome_count": poor_outcome_count,
            }

        # 6. Duplication detected → merge
        duplication_count = node.degradation_signals.get(DegradationSignal.DUPLICATION, 0)
        if duplication_count >= 2:
            return "merge", {
                "reason": "duplicate_detected",
                "duplication_count": duplication_count,
            }

        # 7. Natural decay below threshold → weaken
        if node.confidence.value < VaultConstants.PRUNE_CONFIDENCE_THRESHOLD:
            return "weaken", {
                "reason": "confidence_decayed",
                "confidence": node.confidence.value,
            }

        # Default: retain
        return "retire", {
            "reason": "confidence_critical",
            "confidence": node.confidence.value,
        } if node.confidence.value < 0.10 else ("retain", None)

    @staticmethod
    def execute_weaken(node: KnowledgeNode, reason: str) -> KnowledgeNode:
        """Weaken a node: reduce confidence, mark state."""
        node.state = KnowledgeState.WEAKENED
        node.confidence = node.confidence.adjust(-0.20, f"weaken:{reason}")
        return node

    @staticmethod
    def execute_retire(node: KnowledgeNode, reason: str) -> KnowledgeNode:
        """Retire a node: remove from active use, archive."""
        node.state = KnowledgeState.RETIRED
        node.confidence = Confidence(value=0.0, cap=0.95, provenance=[f"retired:{reason}"])
        return node

    @staticmethod
    def should_periodic_prune(
        total_nodes: int,
        retired_count: int,
        last_prune_timestamp: float
    ) -> bool:
        """
        Determine if periodic pruning should run.
        Based on node count and time since last prune.
        """
        days_since_prune = (datetime.utcnow().timestamp() - last_prune_timestamp) / 86400

        # Prune if: weekly OR node count high OR retired ratio high
        if days_since_prune >= 7:
            return True
        if total_nodes > 5000:
            return True
        if total_nodes > 0 and retired_count / total_nodes > 0.3:
            return True

        return False
