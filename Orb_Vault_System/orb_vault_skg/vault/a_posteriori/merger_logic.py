"""
orb/vault/a_posteriori/merger_logic.py
Deduplication, merge, and compression of redundant knowledge.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Set
import hashlib

from ..shared.types import KnowledgeNode, KnowledgeState, EntityType, VaultTimestamp, Confidence
from ..shared.confidence import ConfidenceEngine
from ..shared.constants import VaultConstants


class MergerLogic:
    """
    Merges duplicate knowledge and compresses clusters.
    Creates canonical forms from redundant nodes.
    """

    @staticmethod
    def find_duplicates(
        nodes: Dict[str, KnowledgeNode],
        similarity_threshold: float = VaultConstants.COMPRESSION_SIMILARITY_THRESHOLD
    ) -> List[List[str]]:
        """
        Find groups of duplicate/similar nodes.
        Returns list of node_id groups.
        """
        duplicates = []
        processed = set()

        for node_id, node in nodes.items():
            if node_id in processed:
                continue
            if node.state in (KnowledgeState.RETIRED, KnowledgeState.MERGED):
                continue

            group = [node_id]
            processed.add(node_id)

            for other_id, other in nodes.items():
                if other_id in processed:
                    continue
                if other.state in (KnowledgeState.RETIRED, KnowledgeState.MERGED):
                    continue

                if MergerLogic._nodes_similar(node, other, similarity_threshold):
                    group.append(other_id)
                    processed.add(other_id)

            if len(group) > 1:
                duplicates.append(group)

        return duplicates

    @staticmethod
    def merge_nodes(
        nodes: Dict[str, KnowledgeNode],
        group: List[str]
    ) -> KnowledgeNode:
        """
        Merge a group of similar nodes into one canonical node.
        """
        group_nodes = [nodes[nid] for nid in group]
        canonical = max(group_nodes, key=lambda n: n.confidence.value)

        merged_signals = dict(canonical.verification_signals)
        for node in group_nodes:
            if node.node_id == canonical.node_id:
                continue
            for signal, count in node.verification_signals.items():
                merged_signals[signal] = merged_signals.get(signal, 0) + count

        total_access = sum(n.access_count for n in group_nodes)

        merged_content = dict(canonical.content)
        merged_content["merged_sources"] = group

        new_confidence = ConfidenceEngine.calculate_verification_confidence(
            merged_signals,
            base_confidence=canonical.confidence.value,
            cap=VaultConstants.MAX_CONFIDENCE_CAP
        )

        merged_id = f"merged_{canonical.node_id}"
        return KnowledgeNode(
            node_id=merged_id,
            node_type=canonical.node_type,
            content=merged_content,
            confidence=new_confidence,
            state=KnowledgeState.PROMOTED,
            created_at=canonical.created_at,
            verified_at=canonical.verified_at,
            promoted_at=VaultTimestamp(),
            last_reinforced=canonical.last_reinforced,
            access_count=total_access,
            success_streak=canonical.success_streak,
            verification_signals=merged_signals,
        )

    @staticmethod
    def compress_cluster(
        nodes: Dict[str, KnowledgeNode],
        intent: str,
        entity_subset: Set[str]
    ) -> Optional[KnowledgeNode]:
        """
        Compress multiple nodes with same intent/entities into a pattern node.
        """
        cluster = [
            n for n in nodes.values()
            if n.content.get("intent") == intent
            and set(n.content.get("entities", [])) & entity_subset
            and n.state not in (KnowledgeState.RETIRED, KnowledgeState.MERGED)
        ]

        if len(cluster) < 3:
            return None

        answers = [n.content.get("resolution_result", "") for n in cluster]
        most_common = max(set(answers), key=answers.count)

        pattern_content = {
            "intent": intent,
            "entities": list(entity_subset),
            "resolution_result": most_common,
            "pattern_type": "compressed_cluster",
            "source_count": len(cluster),
        }

        pattern_id = f"pattern_{intent}_{hashlib.sha256(str(sorted(entity_subset)).encode()).hexdigest()[:8]}"
        avg_conf = sum(n.confidence.value for n in cluster) / len(cluster)

        return KnowledgeNode(
            node_id=pattern_id,
            node_type=EntityType.QUESTION_PATTERN,
            content=pattern_content,
            confidence=Confidence(value=min(avg_conf + 0.05, 0.95), cap=0.95),
            state=KnowledgeState.PROMOTED,
            created_at=VaultTimestamp(),
            promoted_at=VaultTimestamp(),
            access_count=sum(n.access_count for n in cluster),
        )

    @staticmethod
    def _nodes_similar(n1: KnowledgeNode, n2: KnowledgeNode, threshold: float) -> bool:
        if n1.node_type != n2.node_type:
            return False
        if n1.content.get("intent") != n2.content.get("intent"):
            return False

        entities1 = set(n1.content.get("entities", []))
        entities2 = set(n2.content.get("entities", []))
        if not entities1 or not entities2:
            return False

        overlap = len(entities1 & entities2) / len(entities1 | entities2)
        if overlap < 0.7:
            return False

        res1 = n1.content.get("resolution_result", "")
        res2 = n2.content.get("resolution_result", "")
        if res1 != res2:
            return False

        return True
