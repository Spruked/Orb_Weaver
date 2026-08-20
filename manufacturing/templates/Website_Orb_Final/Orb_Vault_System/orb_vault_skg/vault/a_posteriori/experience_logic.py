"""
orb/vault/a_posteriori/experience_logic.py
Logic for capturing new experiences and creating candidate knowledge nodes.
Deterministic. Stateless. No side effects except through cognitive state.
"""

from __future__ import annotations
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Tuple

from ..shared.types import (
    Experience, KnowledgeNode, EntityType, KnowledgeState,
    IntentType, VerificationSignal, VaultTimestamp, Confidence
)
from ..shared.confidence import ConfidenceEngine
from ..shared.constants import VaultConstants


class ExperienceLogic:
    """
    Processes raw interactions into structured experiences.
    Creates candidate knowledge nodes from verified patterns.
    """

    @staticmethod
    def create_experience(
        query_text: str,
        detected_intent: IntentType,
        detected_entities: List[str],
        resolution_path: str,
        resolution_result: str,
        outcome_success: bool,
        session_id: str = "",
        user_feedback: Optional[str] = None,
        source_signals: Optional[List[VerificationSignal]] = None
    ) -> Experience:
        """
        Create an immutable experience record from an interaction.
        """
        exp_id = f"exp_{uuid.uuid4().hex[:12]}"
        return Experience(
            experience_id=exp_id,
            timestamp=VaultTimestamp(),
            query_text=query_text,
            detected_intent=detected_intent,
            detected_entities=detected_entities,
            resolution_path=resolution_path,
            resolution_result=resolution_result,
            outcome_success=outcome_success,
            user_feedback=user_feedback,
            session_id=session_id,
            source_signals=source_signals or [],
        )

    @staticmethod
    def extract_candidate_node(experience: Experience) -> Optional[KnowledgeNode]:
        """
        Extract a candidate knowledge node from a successful experience.
        Only creates candidates from successful resolutions.
        """
        if not experience.outcome_success:
            return None

        # Create a knowledge node representing this learned correspondence
        node_id = f"kn_{experience.fingerprint()}"

        content = {
            "query_pattern": experience.query_text,
            "intent": experience.detected_intent.name,
            "entities": experience.detected_entities,
            "resolution_result": experience.resolution_result,
            "resolution_path": experience.resolution_path,
        }

        # Initial confidence from experience signals
        signals = {}
        if experience.outcome_success:
            signals[VerificationSignal.OUTCOME_SUCCESS] = 1
        if VerificationSignal.REPETITION in experience.source_signals:
            signals[VerificationSignal.REPETITION] = experience.source_signals.count(VerificationSignal.REPETITION)

        confidence = ConfidenceEngine.calculate_verification_confidence(
            signals, base_confidence=0.1, cap=VaultConstants.MAX_CONFIDENCE_CAP
        )

        return KnowledgeNode(
            node_id=node_id,
            node_type=EntityType.QUESTION_PATTERN,
            content=content,
            confidence=confidence,
            state=KnowledgeState.CANDIDATE,
            created_at=VaultTimestamp(),
            verification_signals=signals,
        )

    @staticmethod
    def extract_intent_entity_pattern(
        experience: Experience
    ) -> Tuple[IntentType, List[str], str]:
        """
        Extract the intent-entity-resolution pattern from an experience.
        Used for pattern matching and deduplication.
        """
        return (
            experience.detected_intent,
            sorted(experience.detected_entities),
            experience.resolution_result,
        )

    @staticmethod
    def experiences_are_similar(
        exp1: Experience,
        exp2: Experience,
        text_threshold: float = 0.80
    ) -> bool:
        """
        Check if two experiences represent the same learned pattern.
        Uses intent match + entity overlap + text similarity.
        """
        # Intent must match
        if exp1.detected_intent != exp2.detected_intent:
            return False

        # Entity overlap
        entities1 = set(exp1.detected_entities)
        entities2 = set(exp2.detected_entities)
        if not entities1 and not entities2:
            entity_overlap = 1.0
        else:
            intersection = len(entities1 & entities2)
            union = len(entities1 | entities2)
            entity_overlap = intersection / union if union > 0 else 0

        # Text similarity (simple normalized approach)
        text_sim = ExperienceLogic._text_similarity(exp1.query_text, exp2.query_text)

        # Resolution must match
        resolution_match = exp1.resolution_result == exp2.resolution_result

        return entity_overlap >= 0.5 and text_sim >= text_threshold and resolution_match

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """Simple token overlap similarity."""
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        if not tokens1 or not tokens2:
            return 0.0
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        return intersection / union if union > 0 else 0.0
