"""
Context & Correspondence Orchestrator - Canary Testing Framework
Detects scope leakage, factual loss, and hallucination risk.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..models import (
    CanaryTestRequest, CanaryTestResponse, CanaryTestResult,
    ContextRunRequest, OrchestrationMetadata
)
from ..core.llm_abstraction import LLMInterface


class CanaryTester:
    """Tests crystals for scope leakage and factual preservation."""

    def __init__(self, engine, llm: LLMInterface):
        self.engine = engine
        self.llm = llm

    def run_tests(self, request: CanaryTestRequest) -> CanaryTestResponse:
        """Run comprehensive canary tests on a crystal."""

        metadata = self.engine.store.get(request.context_handle)
        if not metadata:
            raise ValueError(f"Handle not found: {request.context_handle}")

        results = []

        # Test 1: User-provided queries
        for query in request.test_queries:
            result = self._test_query(metadata, query, request.ground_truth_source)
            results.append(result)

        # Test 2: Expected facts verification
        if request.expected_facts:
            for fact in request.expected_facts:
                result = self._test_fact(metadata, fact)
                results.append(result)

        # Test 3: Scope leakage detection
        scope_results = self._test_scope_leakage(metadata)
        results.extend(scope_results)

        # Calculate overall score
        if results:
            overall = sum(r.fact_preservation_score for r in results) / len(results)
        else:
            overall = 0.0

        # Generate recommendations
        recommendations = self._generate_recommendations(results, metadata)

        return CanaryTestResponse(
            context_handle=request.context_handle,
            overall_score=round(overall, 2),
            strategy_used=metadata.strategy,
            results=results,
            recommendations=recommendations,
            timestamp=datetime.utcnow()
        )

    def _test_query(self, metadata: OrchestrationMetadata, query: str, 
                    ground_truth: Optional[str]) -> CanaryTestResult:
        """Test a single query against crystal and optionally raw source."""

        # Get crystal answer
        run_req = ContextRunRequest(
            context_handle=metadata.handle,
            task=query,
            include_provenance=True
        )
        crystal_response = self.engine.run(run_req)
        crystal_answer = crystal_response.answer

        # Get raw answer if ground truth available
        raw_answer = None
        if ground_truth:
            raw_answer = self.llm.answer(ground_truth, query, 1000)

        # Score factual preservation
        preservation_score = self._score_preservation(
            crystal_answer, raw_answer, metadata.crystal_data.get("crystal_text", "")
        )

        # Detect scope leakage
        scope_leak = self._detect_scope_leakage(metadata, query, crystal_answer)

        # Hallucination risk
        hallucination = self._assess_hallucination(crystal_answer, metadata)

        return CanaryTestResult(
            query=query,
            crystal_answer=crystal_answer,
            raw_answer=raw_answer,
            fact_preservation_score=round(preservation_score, 2),
            scope_leakage_detected=scope_leak,
            hallucination_risk=round(hallucination, 2),
            details={
                "strategy": metadata.strategy.value,
                "confidence": crystal_response.confidence,
                "retrieved_count": len(crystal_response.retrieved_segments)
            }
        )

    def _test_fact(self, metadata: OrchestrationMetadata, fact: Dict[str, str]) -> CanaryTestResult:
        """Test preservation of a specific fact."""
        query = fact.get("query", f"What is {fact.get('subject', 'the fact')}?")
        expected = fact.get("expected", "")

        run_req = ContextRunRequest(
            context_handle=metadata.handle,
            task=query
        )
        response = self.engine.run(run_req)
        answer = response.answer

        # Check if expected fact is in answer
        expected_lower = expected.lower()
        answer_lower = answer.lower()

        # Fuzzy match
        preservation = self._fuzzy_contains(answer_lower, expected_lower)

        return CanaryTestResult(
            query=query,
            crystal_answer=answer,
            raw_answer=None,
            fact_preservation_score=round(preservation, 2),
            scope_leakage_detected=False,
            hallucination_risk=0.3 if preservation < 0.5 else 0.1,
            details={"expected_fact": expected, "fact_type": fact.get("type", "unknown")}
        )

    def _test_scope_leakage(self, metadata: OrchestrationMetadata) -> List[CanaryTestResult]:
        """Test if crystal answers correctly outside its task scope."""
        results = []

        # Generate out-of-scope queries based on task
        task = metadata.task.lower()
        out_of_scope_queries = []

        if "warranty" in task:
            out_of_scope_queries.extend([
                "What are the employee birthday policies?",
                "What is the accounting revenue for Q3?",
                "List all advertising campaigns."
            ])
        elif "technical" in task or "code" in task:
            out_of_scope_queries.extend([
                "What are the company HR policies?",
                "Who is the CEO?",
                "What are the sales figures?"
            ])
        else:
            out_of_scope_queries.extend([
                "What is the weather today?",
                "Who won the last election?",
                "What is the capital of France?"
            ])

        for query in out_of_scope_queries[:3]:
            run_req = ContextRunRequest(
                context_handle=metadata.handle,
                task=query
            )
            try:
                response = self.engine.run(run_req)
                answer = response.answer.lower()

                # Should admit ignorance or say not found
                admits_ignorance = any(phrase in answer for phrase in [
                    "cannot", "not found", "no information", "not in context",
                    "unclear", "don't know", "not sure", "insufficient"
                ])

                # If it makes up an answer, that's scope leakage
                scope_leak = not admits_ignorance and len(answer) > 50

                results.append(CanaryTestResult(
                    query=query,
                    crystal_answer=response.answer,
                    raw_answer=None,
                    fact_preservation_score=1.0 if admits_ignorance else 0.0,
                    scope_leakage_detected=scope_leak,
                    hallucination_risk=0.8 if scope_leak else 0.1,
                    details={"test_type": "scope_leakage", "admits_ignorance": admits_ignorance}
                ))
            except Exception as e:
                results.append(CanaryTestResult(
                    query=query,
                    crystal_answer=f"ERROR: {str(e)}",
                    raw_answer=None,
                    fact_preservation_score=0.0,
                    scope_leakage_detected=False,
                    hallucination_risk=0.0,
                    details={"test_type": "scope_leakage", "error": str(e)}
                ))

        return results

    def _score_preservation(self, crystal_answer: str, raw_answer: Optional[str],
                           crystal_text: str) -> float:
        """Score how well crystal preserves facts compared to raw."""
        if raw_answer is None:
            # No ground truth, score based on internal consistency
            return self._consistency_score(crystal_answer, crystal_text)

        # Compare crystal vs raw answers
        crystal_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', crystal_answer.lower()))
        raw_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', raw_answer.lower()))

        if not raw_words:
            return 0.5

        overlap = len(crystal_words & raw_words)
        return min(overlap / len(raw_words) * 1.5, 1.0)

    def _consistency_score(self, answer: str, context: str) -> float:
        """Score answer consistency with its own context."""
        answer_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', answer.lower()))
        context_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', context.lower()))

        if not answer_words:
            return 0.5

        overlap = len(answer_words & context_words)
        return min(overlap / len(answer_words), 1.0)

    def _fuzzy_contains(self, text: str, substring: str) -> float:
        """Fuzzy check if substring is contained in text."""
        if substring in text:
            return 1.0

        # Check word overlap
        text_words = set(text.split())
        sub_words = set(substring.split())

        if not sub_words:
            return 0.0

        overlap = len(text_words & sub_words)
        return min(overlap / len(sub_words), 1.0)

    def _detect_scope_leakage(self, metadata: OrchestrationMetadata, query: str, 
                               answer: str) -> bool:
        """Detect if answer strays from crystal's intended scope."""
        # Simple heuristic: if answer contains many words not in crystal
        crystal_text = metadata.crystal_data.get("crystal_text", "")
        crystal_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', crystal_text.lower()))
        answer_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', answer.lower()))

        if not answer_words:
            return False

        novel_ratio = len(answer_words - crystal_words) / len(answer_words)
        return novel_ratio > 0.8 and len(answer) > 100

    def _assess_hallucination(self, answer: str, metadata: OrchestrationMetadata) -> float:
        """Assess risk of hallucination in answer."""
        risk = 0.3  # Base risk

        # Higher risk for summary strategy
        if metadata.strategy.value == "summary":
            risk += 0.2

        # Higher risk if answer is very long relative to crystal
        crystal_tokens = metadata.crystal_tokens
        answer_tokens = len(answer.split()) * 0.75
        if answer_tokens > crystal_tokens * 0.5:
            risk += 0.2

        # Lower risk if provenance is included
        if "[" in answer and "]" in answer:
            risk -= 0.1

        return min(max(risk, 0.0), 1.0)

    def _generate_recommendations(self, results: List[CanaryTestResult],
                                   metadata: OrchestrationMetadata) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        avg_preservation = sum(r.fact_preservation_score for r in results) / max(len(results), 1)
        scope_leaks = sum(1 for r in results if r.scope_leakage_detected)
        avg_hallucination = sum(r.hallucination_risk for r in results) / max(len(results), 1)

        if avg_preservation < 0.6:
            recommendations.append(
                f"Low fact preservation ({avg_preservation:.2f}). "
                f"Consider using semantic_retrieval or hierarchical strategy instead of {metadata.strategy.value}."
            )

        if scope_leaks > 0:
            recommendations.append(
                f"Scope leakage detected in {scope_leaks} tests. "
                f"The crystal may be answering outside its intended domain. "
                f"Add more specific task constraints."
            )

        if avg_hallucination > 0.5:
            recommendations.append(
                f"High hallucination risk ({avg_hallucination:.2f}). "
                f"Consider adding more preserve_exact facts or switching to vault_compile strategy."
            )

        if metadata.strategy.value == "summary" and metadata.original_tokens > 100000:
            recommendations.append(
                "Summary strategy with large source detected. "
                "Switch to hierarchical strategy for better obscure fact preservation."
            )

        if not recommendations:
            recommendations.append("Crystal passes all canary tests. Ready for production use.")

        return recommendations
