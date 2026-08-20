"""
orb/vault/a_priori/qa_logic.py
Verified question/answer correspondences.
Pattern matching for known visitor questions.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional

from ..shared.types import QACorrespondence, ResolutionResult, IntentType


class QALogic:
    """
    QA correspondence matcher.
    Finds best-matching verified Q&A pair.
    """

    @staticmethod
    def match_question(
        qa_pairs: Dict[str, QACorrespondence],
        query_text: str,
        intent: Optional[IntentType] = None
    ) -> Optional[QACorrespondence]:
        best_match = None
        best_score = 0.0
        query_lower = query_text.lower()
        query_tokens = set(query_lower.split())

        for qa in qa_pairs.values():
            if intent and qa.intent not in {intent, IntentType.GENERAL}:
                continue
            for pattern in qa.question_patterns:
                score = QALogic._pattern_match_score(query_lower, query_tokens, pattern)
                if score > best_score and score > 0.75:
                    best_score = score
                    best_match = qa

        return best_match

    @staticmethod
    def _pattern_match_score(query: str, query_tokens: set, pattern: str) -> float:
        pattern_lower = pattern.lower()
        pattern_tokens = set(pattern_lower.split())

        if query == pattern_lower:
            return 1.0
        if pattern_lower in query or query in pattern_lower:
            return 0.9

        if not pattern_tokens:
            return 0.0

        overlap = len(query_tokens & pattern_tokens) / len(query_tokens | pattern_tokens)
        if query.startswith(pattern_lower[:20]):
            overlap += 0.1

        return min(1.0, overlap)

    @staticmethod
    def render_answer(qa: QACorrespondence, variables: Optional[Dict[str, str]] = None) -> str:
        answer = qa.answer_template
        if variables:
            for key, value in variables.items():
                answer = answer.replace(f"{{{key}}}", value)
        return answer

    @staticmethod
    def query_qa(
        qa_pairs: Dict[str, QACorrespondence],
        query_text: str,
        intent: Optional[IntentType] = None,
        variables: Optional[Dict[str, str]] = None
    ) -> ResolutionResult:
        match = QALogic.match_question(qa_pairs, query_text, intent)
        if not match:
            return ResolutionResult(
                success=False,
                source="a_priori_qa",
                resolution_path=["qa", "no_match"],
            )

        answer = QALogic.render_answer(match, variables)
        return ResolutionResult(
            success=True,
            answer=answer,
            data={
                "qa_id": match.qa_id,
                "intent": match.intent.name,
                "patterns": match.question_patterns,
            },
            source="a_priori_qa",
            confidence=match.confidence.value,
            entity_id=match.qa_id,
            resolution_path=["qa", "pattern_match"],
        )
