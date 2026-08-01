"""
Context & Correspondence Orchestrator - LLM Abstraction Layer
Provides a unified interface for LLM calls with pluggable backends.
Includes a local fallback for demonstration without API keys.
"""

import os
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import hashlib


class LLMInterface(ABC):
    """Abstract interface for language model operations."""

    @abstractmethod
    def summarize(self, text: str, max_tokens: int, task_context: str = "") -> str:
        """Summarize text to fit within max_tokens."""
        pass

    @abstractmethod
    def answer(self, context: str, question: str, max_tokens: int = 1000) -> str:
        """Answer a question given context."""
        pass

    @abstractmethod
    def extract_keywords(self, text: str, n: int = 10) -> List[str]:
        """Extract top n keywords from text."""
        pass

    @abstractmethod
    def classify_relevance(self, chunk: str, task: str) -> float:
        """Classify how relevant a chunk is to a task (0.0-1.0)."""
        pass


class LocalFallbackLLM(LLMInterface):
    """
    Local fallback that uses deterministic text processing.
    No API calls, no external dependencies.
    Suitable for demonstration and CPU-only environments.
    """

    STOPWORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
        "from", "as", "into", "through", "during", "before", "after", "above",
        "below", "between", "under", "again", "further", "then", "once", "here",
        "there", "when", "where", "why", "how", "all", "each", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only", "own",
        "same", "so", "than", "too", "very", "just", "and", "but", "if", "or",
        "because", "until", "while", "this", "that", "these", "those", "i", "me",
        "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours",
        "yourself", "yourselves", "he", "him", "his", "himself", "she", "her",
        "hers", "herself", "it", "its", "itself", "they", "them", "their",
        "theirs", "themselves", "what", "which", "who", "whom", "whose", "am"
    }

    def __init__(self):
        self._cache = {}

    def _token_count(self, text: str) -> int:
        """Rough token estimation: ~0.75 tokens per word for English."""
        return int(len(text.split()) * 0.75)

    def _word_freq(self, text: str) -> Dict[str, int]:
        """Calculate word frequencies excluding stopwords."""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        freq = {}
        for w in words:
            if w not in self.STOPWORDS:
                freq[w] = freq.get(w, 0) + 1
        return freq

    def summarize(self, text: str, max_tokens: int, task_context: str = "") -> str:
        """
        Deterministic summarization:
        1. Split into sentences
        2. Score sentences by keyword density + position
        3. Select top sentences up to token budget
        4. Preserve order
        """
        cache_key = hashlib.md5(f"{text[:500]}:{max_tokens}:{task_context}".encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        sentences = re.split(r'(?<=[.!?])\s+', text)
        if not sentences:
            return text[:int(max_tokens * 1.3)]

        # Get task keywords for relevance scoring
        task_keywords = set()
        if task_context:
            task_keywords = set(re.findall(r'\b[a-zA-Z]{3,}\b', task_context.lower()))

        # Score sentences
        scored = []
        for i, sent in enumerate(sentences):
            score = 0.0
            words = re.findall(r'\b[a-zA-Z]{3,}\b', sent.lower())

            # Keyword density
            freq = self._word_freq(sent)
            score += len(freq) * 0.5

            # Position bias (first and last sentences often important)
            if i == 0:
                score += 3.0
            elif i == len(sentences) - 1:
                score += 2.0
            elif i < len(sentences) * 0.1:
                score += 1.5

            # Task relevance
            if task_keywords:
                matches = sum(1 for w in words if w in task_keywords)
                score += matches * 2.0

            # Length penalty (prefer medium-length sentences)
            word_count = len(words)
            if 5 <= word_count <= 30:
                score += 1.0

            # Presence of numbers/identifiers (often important facts)
            if re.search(r'\b\d+\b|[A-Z]{2,}-?\d+', sent):
                score += 1.5

            scored.append((score, i, sent))

        # Sort by score descending
        scored.sort(reverse=True)

        # Greedily select sentences up to token budget
        selected = []
        current_tokens = 0
        for score, idx, sent in scored:
            sent_tokens = self._token_count(sent)
            if current_tokens + sent_tokens <= max_tokens:
                selected.append((idx, sent))
                current_tokens += sent_tokens

        # Restore original order
        selected.sort(key=lambda x: x[0])
        result = " ".join(sent for _, sent in selected)

        self._cache[cache_key] = result
        return result

    def answer(self, context: str, question: str, max_tokens: int = 1000) -> str:
        """
        Deterministic QA: find most relevant sentences and format as answer.
        """
        cache_key = hashlib.md5(f"{context[:500]}:{question}".encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        q_keywords = set(re.findall(r'\b[a-zA-Z]{3,}\b', question.lower()))
        sentences = re.split(r'(?<=[.!?])\s+', context)

        scored = []
        for sent in sentences:
            words = set(re.findall(r'\b[a-zA-Z]{3,}\b', sent.lower()))
            overlap = len(words & q_keywords)
            score = overlap * 2.0

            # Boost sentences with question words nearby
            if any(w in words for w in ["because", "therefore", "thus", "since", "due"]):
                score += 1.0

            scored.append((score, sent))

        scored.sort(reverse=True)

        # Take top sentences up to budget
        selected = []
        current_tokens = 0
        for score, sent in scored[:10]:  # Top 10 most relevant
            sent_tokens = self._token_count(sent)
            if current_tokens + sent_tokens <= max_tokens * 0.8:
                selected.append(sent)
                current_tokens += sent_tokens

        if not selected:
            return "Based on the available context, I cannot find a specific answer to this question."

        answer = " ".join(selected)
        self._cache[cache_key] = answer
        return answer

    def extract_keywords(self, text: str, n: int = 10) -> List[str]:
        """Extract top keywords by frequency."""
        freq = self._word_freq(text)
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:n]]

    def classify_relevance(self, chunk: str, task: str) -> float:
        """Simple TF overlap relevance score."""
        chunk_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', chunk.lower()))
        task_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', task.lower()))

        if not task_words:
            return 0.5

        overlap = len(chunk_words & task_words)
        return min(overlap / len(task_words) * 2.0, 1.0)


class OpenAILLM(LLMInterface):
    """OpenAI API implementation."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", base_url: Optional[str] = None):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required. Install: pip install openai")

        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), base_url=base_url)
        self.model = model

    def summarize(self, text: str, max_tokens: int, task_context: str = "") -> str:
        prompt = f"Summarize the following text to approximately {max_tokens} tokens."
        if task_context:
            prompt += f" Focus on information relevant to: {task_context}"
        prompt += f"\n\n{text[:15000]}"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=min(max_tokens, 4000),
            temperature=0.3
        )
        return response.choices[0].message.content

    def answer(self, context: str, question: str, max_tokens: int = 1000) -> str:
        prompt = f"Context:\n{context[:12000]}\n\nQuestion: {question}\nAnswer concisely:"
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3
        )
        return response.choices[0].message.content

    def extract_keywords(self, text: str, n: int = 10) -> List[str]:
        prompt = f"Extract the top {n} most important keywords from this text. Return as comma-separated list:\n\n{text[:5000]}"
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1
        )
        content = response.choices[0].message.content
        return [k.strip() for k in content.split(",") if k.strip()]

    def classify_relevance(self, chunk: str, task: str) -> float:
        prompt = f"Rate how relevant this text is to the task on a scale of 0.0 to 1.0. Return only the number.\n\nTask: {task}\n\nText: {chunk[:1000]}\n\nRelevance (0.0-1.0):"
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.1
        )
        try:
            return float(response.choices[0].message.content.strip())
        except (ValueError, TypeError):
            return 0.5


def get_llm(provider: str = "auto", **kwargs) -> LLMInterface:
    """Factory function to get appropriate LLM interface."""
    if provider == "auto":
        provider = os.getenv("CCO_LLM_PROVIDER", "local")

    if provider == "openai":
        return OpenAILLM(**kwargs)
    elif provider == "local":
        return LocalFallbackLLM()
    else:
        # Default to local fallback
        return LocalFallbackLLM()
