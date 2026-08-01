"""
Context & Correspondence Orchestrator - Base Strategy
Abstract base class for all compression strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..models import TaskProfile
from ..core.llm_abstraction import LLMInterface


class BaseStrategy(ABC):
    """Abstract base for context compression strategies."""

    def __init__(self, llm: LLMInterface):
        self.llm = llm
        self.name = "base"

    @abstractmethod
    def compress(self, source: str, task_profile: TaskProfile, 
                   target_budget: int, preserve_exact: List[str] = None) -> Dict[str, Any]:
        """
        Compress source into crystal representation.

        Returns dict with:
        - crystal_text: the compressed representation
        - crystal_tokens: token count of crystal
        - original_tokens: token count of source
        - metadata: strategy-specific metadata
        """
        pass

    @abstractmethod
    def query(self, crystal_data: Dict[str, Any], task: str, 
              max_tokens: int = 1000, retrieve_depth: int = 2) -> Dict[str, Any]:
        """
        Query the crystal for a specific task.

        Returns dict with:
        - answer: the response text
        - tokens_used: tokens consumed
        - retrieved_segments: list of source segments used
        - confidence: confidence score 0.0-1.0
        """
        pass

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation."""
        return int(len(text.split()) * 0.75)

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks by words."""
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            if end >= len(words):
                break
            start = end - overlap
        return chunks

    def _ensure_preserved(self, crystal_text: str, preserve_exact: List[str]) -> str:
        """Ensure exact strings are preserved in crystal."""
        if not preserve_exact:
            return crystal_text

        missing = [s for s in preserve_exact if s not in crystal_text]
        if missing:
            appendix = "\n\n[EXACT PRESERVES]\n" + "\n".join(f"- {s}" for s in missing)
            crystal_text += appendix
        return crystal_text
