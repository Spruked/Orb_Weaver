"""
Context & Correspondence Orchestrator - Semantic Retrieval Strategy (Possibility B)
Compressed representation + index into original source.
Good for: larger sources, factual queries, need for obscure details.
"""

import re
import math
from typing import Dict, Any, List, Tuple
from collections import Counter
from .base import BaseStrategy
from ..models import TaskProfile


class SemanticRetrievalStrategy(BaseStrategy):
    """Strategy B: Semantic representation + retrieval index."""

    def __init__(self, llm):
        super().__init__(llm)
        self.name = "semantic_retrieval"

    def compress(self, source: str, task_profile: TaskProfile,
                   target_budget: int, preserve_exact: List[str] = None) -> Dict[str, Any]:
        """Create semantic map + chunk index."""
        original_tokens = self._estimate_tokens(source)

        # Chunk the source
        chunks = self._chunk_text(source, chunk_size=400, overlap=40)

        # Build TF-IDF-like index for each chunk
        chunk_vectors = []
        for i, chunk in enumerate(chunks):
            vec = self._vectorize(chunk)
            chunk_vectors.append({
                "id": i,
                "text": chunk,
                "vector": vec,
                "tokens": self._estimate_tokens(chunk)
            })

        # Build global semantic map (summary of summaries)
        task_context = f"{task_profile.intent} | {task_profile.domain or 'general'}"
        semantic_map = self._build_semantic_map(chunks, task_profile, target_budget)

        # Store full chunks for retrieval
        crystal_text = semantic_map

        # Ensure exact preserves
        if preserve_exact:
            for exact in preserve_exact:
                if not any(exact in c["text"] for c in chunk_vectors):
                    chunk_vectors.append({
                        "id": len(chunk_vectors),
                        "text": f"[PRESERVED] {exact}",
                        "vector": self._vectorize(exact),
                        "tokens": self._estimate_tokens(exact)
                    })

        crystal_tokens = self._estimate_tokens(crystal_text)

        return {
            "crystal_text": crystal_text,
            "crystal_tokens": crystal_tokens,
            "original_tokens": original_tokens,
            "chunks": chunk_vectors,
            "num_chunks": len(chunks),
            "metadata": {
                "strategy": "semantic_retrieval",
                "task_context": task_context,
                "compression_ratio": original_tokens / max(crystal_tokens, 1),
                "avg_chunk_tokens": sum(c["tokens"] for c in chunk_vectors) / max(len(chunk_vectors), 1)
            }
        }

    def _vectorize(self, text: str) -> Dict[str, float]:
        """Simple TF vector for a text chunk."""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        freq = Counter(words)
        total = sum(freq.values())
        if total == 0:
            return {}
        return {w: count / total for w, count in freq.items()}

    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Cosine similarity between two TF vectors."""
        all_words = set(vec1.keys()) | set(vec2.keys())
        dot = sum(vec1.get(w, 0) * vec2.get(w, 0) for w in all_words)
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def _build_semantic_map(self, chunks: List[str], task_profile: TaskProfile, 
                            target_budget: int) -> str:
        """Build a high-level semantic map from chunks."""
        # Summarize each chunk briefly
        chunk_summaries = []
        for chunk in chunks[:50]:  # Limit to avoid too much processing
            summary = self.llm.summarize(chunk, 80, 
                f"{task_profile.intent} {task_profile.domain or ''}")
            chunk_summaries.append(summary)

        # Combine and summarize again
        combined = "\n".join(chunk_summaries)
        if self._estimate_tokens(combined) > target_budget:
            semantic_map = self.llm.summarize(combined, target_budget,
                f"{task_profile.intent} {task_profile.domain or ''}")
        else:
            semantic_map = combined

        return semantic_map

    def query(self, crystal_data: Dict[str, Any], task: str,
              max_tokens: int = 1000, retrieve_depth: int = 2) -> Dict[str, Any]:
        """Retrieve relevant chunks + answer."""
        chunks = crystal_data.get("chunks", [])
        semantic_map = crystal_data["crystal_text"]

        if not chunks:
            # Fallback to summary-only
            answer = self.llm.answer(semantic_map, task, max_tokens)
            return {
                "answer": answer,
                "tokens_used": self._estimate_tokens(answer) + self._estimate_tokens(semantic_map),
                "retrieved_segments": [{"source": "semantic_map", "text": semantic_map[:500]}],
                "confidence": 0.5,
                "strategy": "semantic_retrieval"
            }

        # Vectorize the query
        query_vec = self._vectorize(task)

        # Score all chunks
        scored = []
        for chunk in chunks:
            sim = self._cosine_similarity(query_vec, chunk["vector"])
            scored.append((sim, chunk))

        scored.sort(reverse=True)

        # Retrieve top-k chunks up to budget
        top_k = min(retrieve_depth * 3, 10)
        retrieved = []
        context_parts = [semantic_map]
        current_tokens = self._estimate_tokens(semantic_map)

        for sim, chunk in scored[:top_k]:
            chunk_tokens = chunk["tokens"]
            if current_tokens + chunk_tokens > max_tokens * 3:  # Context budget
                break
            context_parts.append(f"[SOURCE {chunk['id']}] {chunk['text']}")
            retrieved.append({
                "chunk_id": chunk["id"],
                "similarity": round(sim, 3),
                "text": chunk["text"][:300]
            })
            current_tokens += chunk_tokens

        context = "\n\n".join(context_parts)
        answer = self.llm.answer(context, task, max_tokens)

        # Confidence based on retrieval quality
        avg_sim = sum(r["similarity"] for r in retrieved) / max(len(retrieved), 1) if retrieved else 0
        confidence = min(0.6 + avg_sim * 0.3, 0.95)

        return {
            "answer": answer,
            "tokens_used": self._estimate_tokens(answer) + current_tokens,
            "retrieved_segments": retrieved,
            "confidence": round(confidence, 2),
            "strategy": "semantic_retrieval"
        }
