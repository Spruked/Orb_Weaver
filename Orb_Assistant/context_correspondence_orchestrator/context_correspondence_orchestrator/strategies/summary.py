"""
Context & Correspondence Orchestrator - Summary Strategy (Possibility A)
Aggressive summarization. Simplest implementation.
Good for: smaller sources, general tasks, speed.
Weakness: may lose obscure facts.
"""

from typing import Dict, Any, List
from .base import BaseStrategy
from ..models import TaskProfile


class SummaryStrategy(BaseStrategy):
    """Strategy A: Sophisticated summary."""

    def __init__(self, llm):
        super().__init__(llm)
        self.name = "summary"

    def compress(self, source: str, task_profile: TaskProfile,
                   target_budget: int, preserve_exact: List[str] = None) -> Dict[str, Any]:
        """Compress via aggressive summarization."""
        original_tokens = self._estimate_tokens(source)

        # Build task context string
        task_context = f"Task: {task_profile.intent}"
        if task_profile.domain:
            task_context += f" | Domain: {task_profile.domain}"
        if task_profile.priority_keywords:
            task_context += f" | Keywords: {', '.join(task_profile.priority_keywords[:10])}"

        # If source is small enough, just use it
        if original_tokens <= target_budget:
            crystal_text = source
        else:
            # Multi-pass summarization for large sources
            crystal_text = self._multi_pass_summarize(source, target_budget, task_context)

        # Ensure exact preserves
        crystal_text = self._ensure_preserved(crystal_text, preserve_exact or [])

        crystal_tokens = self._estimate_tokens(crystal_text)

        return {
            "crystal_text": crystal_text,
            "crystal_tokens": crystal_tokens,
            "original_tokens": original_tokens,
            "metadata": {
                "strategy": "summary",
                "task_context": task_context,
                "passes": 1 if original_tokens <= target_budget else "multi",
                "compression_ratio": original_tokens / max(crystal_tokens, 1)
            }
        }

    def _multi_pass_summarize(self, source: str, target_budget: int, task_context: str) -> str:
        """Iteratively summarize until within budget."""
        current = source
        max_iterations = 5

        for i in range(max_iterations):
            current_tokens = self._estimate_tokens(current)
            if current_tokens <= target_budget:
                break

            # Calculate target for this pass
            reduction_factor = 0.5 if current_tokens > target_budget * 4 else 0.7
            pass_target = int(target_budget / reduction_factor) if i == 0 else target_budget

            current = self.llm.summarize(current, pass_target, task_context)

        return current

    def query(self, crystal_data: Dict[str, Any], task: str,
              max_tokens: int = 1000, retrieve_depth: int = 2) -> Dict[str, Any]:
        """Answer using only the summary."""
        crystal_text = crystal_data["crystal_text"]

        answer = self.llm.answer(crystal_text, task, max_tokens)
        tokens_used = self._estimate_tokens(answer) + self._estimate_tokens(crystal_text)

        return {
            "answer": answer,
            "tokens_used": tokens_used,
            "retrieved_segments": [{"source": "summary", "text": crystal_text[:500]}],
            "confidence": 0.6,  # Lower confidence due to potential information loss
            "strategy": "summary"
        }
