"""
orb/vault/a_posteriori/contradiction_logic.py
Detects conflicts between knowledge nodes and with A Priori truth.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Set, Tuple

from ..shared.types import (
    KnowledgeNode, DegradationSignal, EntityType, RelationType, Confidence
)
from ..shared.confidence import ConfidenceEngine


class ContradictionLogic:
    """
    Detects contradictions without resolving them.
    Flags conflicts for pruning or demotion.
    """

    @staticmethod
    def detect_node_contradiction(
        node1: KnowledgeNode,
        node2: KnowledgeNode
    ) -> Optional[Dict[str, Any]]:
        """
        Check if two nodes contradict each other.
        Returns contradiction details or None.
        """
        # Must be same intent type to contradict
        intent1 = node1.content.get("intent", "")
        intent2 = node2.content.get("intent", "")
        if intent1 != intent2:
            return None

        # Must share entities
        entities1 = set(node1.content.get("entities", []))
        entities2 = set(node2.content.get("entities", []))
        if not (entities1 & entities2):
            return None

        # Check if resolutions differ
        res1 = node1.content.get("resolution_result", "")
        res2 = node2.content.get("resolution_result", "")

        if res1 == res2:
            return None  # Same answer, not a contradiction

        # Calculate contradiction severity
        severity = ContradictionLogic._calculate_severity(node1, node2)

        return {
            "type": "node_contradiction",
            "node1_id": node1.node_id,
            "node2_id": node2.node_id,
            "shared_entities": list(entities1 & entities2),
            "resolution1": res1,
            "resolution2": res2,
            "severity": severity,
            "confidence_delta": abs(node1.confidence.value - node2.confidence.value),
        }

    @staticmethod
    def detect_priori_contradiction(
        posteriori_node: KnowledgeNode,
        priori_fact: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a posteriori node contradicts settled A Priori truth.
        A Priori always wins in contradictions.
        """
        # Extract comparable fields
        posteriori_result = posteriori_node.content.get("resolution_result", "")
        priori_result = priori_fact.get("answer", priori_fact.get("current_price", ""))

        if not posteriori_result or not priori_result:
            return None

        # Simple string comparison (can be enhanced with semantic similarity)
        if str(posteriori_result).lower().strip() == str(priori_result).lower().strip():
            return None

        # Check entity overlap
        post_entities = set(posteriori_node.content.get("entities", []))
        prior_entities = set(priori_fact.get("entities", []))
        if not (post_entities & prior_entities):
            return None

        return {
            "type": "priori_contradiction",
            "posteriori_node_id": posteriori_node.node_id,
            "priori_fact_id": priori_fact.get("entry_id", "unknown"),
            "posteriori_result": posteriori_result,
            "priori_result": priori_result,
            "severity": 1.0,  # Always maximum — A Priori wins
        }

    @staticmethod
    def detect_source_change(
        node: KnowledgeNode,
        current_source_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if the source data that created this node has changed.
        """
        # Check if node's resolution result still exists in source
        result = node.content.get("resolution_result", "")
        source_text = str(current_source_data)

        if result and result not in source_text:
            return {
                "type": "source_change",
                "node_id": node.node_id,
                "missing_result": result,
                "severity": 0.7,
            }

        return None

    @staticmethod
    def _calculate_severity(node1: KnowledgeNode, node2: KnowledgeNode) -> float:
        """Calculate contradiction severity (0.0 - 1.0)."""
        # Higher severity when both nodes have high confidence
        avg_conf = (node1.confidence.value + node2.confidence.value) / 2

        # Higher severity for promoted nodes
        from ..shared.types import KnowledgeState
        state_multiplier = 1.0
        if node1.state == KnowledgeState.PROMOTED and node2.state == KnowledgeState.PROMOTED:
            state_multiplier = 1.5

        severity = min(1.0, avg_conf * state_multiplier)
        return severity

    @staticmethod
    def find_all_contradictions(
        target_node: KnowledgeNode,
        all_nodes: Dict[str, KnowledgeNode]
    ) -> List[Dict[str, Any]]:
        """Find all contradictions for a given node."""
        contradictions = []
        for other_id, other_node in all_nodes.items():
            if other_id == target_node.node_id:
                continue
            result = ContradictionLogic.detect_node_contradiction(target_node, other_node)
            if result:
                contradictions.append(result)
        return contradictions
