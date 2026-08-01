"""
Context & Correspondence Orchestrator - Hierarchical Strategy (Possibility C)
Multi-level memory: raw → sections → topics → global crystal.
Good for: very large sources, complex domains, deep navigation.
Most sophisticated design.
"""

from typing import Dict, Any, List
from .base import BaseStrategy
from ..models import TaskProfile


class HierarchicalStrategy(BaseStrategy):
    """Strategy C: Hierarchical memory with multi-level representation."""

    def __init__(self, llm):
        super().__init__(llm)
        self.name = "hierarchical"
        self.levels = 4

    def compress(self, source: str, task_profile: TaskProfile,
                   target_budget: int, preserve_exact: List[str] = None) -> Dict[str, Any]:
        """Build hierarchical representation."""
        original_tokens = self._estimate_tokens(source)

        task_context = f"{task_profile.intent} | {task_profile.domain or 'general'}"

        # Level 0: Raw sections (chunked)
        l0_chunks = self._chunk_text(source, chunk_size=600, overlap=60)

        # Level 1: Section summaries
        l1_summaries = []
        for chunk in l0_chunks[:100]:  # Limit for performance
            summary = self.llm.summarize(chunk, 150, task_context)
            l1_summaries.append({
                "summary": summary,
                "source_range": f"chunk_{len(l1_summaries)}",
                "tokens": self._estimate_tokens(summary)
            })

        # Level 2: Topic clusters (group and summarize L1)
        l2_topics = self._build_topics(l1_summaries, task_context)

        # Level 3: Global crystal (summarize L2)
        l3_crystal = self._build_global_crystal(l2_topics, task_context, target_budget)

        # Ensure exact preserves
        if preserve_exact:
            l3_crystal += "\n\n[EXACT PRESERVES]\n" + "\n".join(f"- {s}" for s in preserve_exact)

        crystal_tokens = self._estimate_tokens(l3_crystal)

        return {
            "crystal_text": l3_crystal,
            "crystal_tokens": crystal_tokens,
            "original_tokens": original_tokens,
            "levels": {
                "l0": {"count": len(l0_chunks), "sample": l0_chunks[0][:200] if l0_chunks else ""},
                "l1": {"count": len(l1_summaries), "summaries": [s["summary"][:100] for s in l1_summaries[:5]]},
                "l2": {"count": len(l2_topics), "topics": [t["topic"][:100] for t in l2_topics[:5]]},
                "l3": {"crystal": l3_crystal[:500]}
            },
            "l0_chunks": [{"id": i, "text": c} for i, c in enumerate(l0_chunks)],
            "l1_summaries": l1_summaries,
            "l2_topics": l2_topics,
            "metadata": {
                "strategy": "hierarchical",
                "task_context": task_context,
                "compression_ratio": original_tokens / max(crystal_tokens, 1),
                "levels_built": self.levels
            }
        }

    def _build_topics(self, l1_summaries: List[Dict], task_context: str) -> List[Dict]:
        """Group L1 summaries into topic clusters."""
        if len(l1_summaries) <= 5:
            # Few summaries, each is its own topic
            return [{"topic": s["summary"], "sources": [s["source_range"]], "tokens": s["tokens"]} 
                    for s in l1_summaries]

        # Group into batches of ~5 summaries
        topics = []
        batch_size = max(1, len(l1_summaries) // 5)
        for i in range(0, len(l1_summaries), batch_size):
            batch = l1_summaries[i:i + batch_size]
            combined = "\n".join(s["summary"] for s in batch)
            topic_summary = self.llm.summarize(combined, 200, task_context)
            topics.append({
                "topic": topic_summary,
                "sources": [s["source_range"] for s in batch],
                "tokens": self._estimate_tokens(topic_summary)
            })

        return topics

    def _build_global_crystal(self, l2_topics: List[Dict], task_context: str, 
                               target_budget: int) -> str:
        """Build the L3 global crystal from topics."""
        combined = "\n\n".join(t["topic"] for t in l2_topics)

        if self._estimate_tokens(combined) <= target_budget:
            return combined

        return self.llm.summarize(combined, target_budget, task_context)

    def query(self, crystal_data: Dict[str, Any], task: str,
              max_tokens: int = 1000, retrieve_depth: int = 2) -> Dict[str, Any]:
        """Navigate hierarchy based on query."""
        l3_crystal = crystal_data["crystal_text"]
        l2_topics = crystal_data.get("l2_topics", [])
        l1_summaries = crystal_data.get("l1_summaries", [])
        l0_chunks = crystal_data.get("l0_chunks", [])

        # Step 1: Try answering from L3 crystal
        context = l3_crystal
        answer = self.llm.answer(context, task, max_tokens)

        # Step 2: If confidence seems low or answer is vague, drill down
        # Simple heuristic: if answer is very short or contains uncertainty
        uncertainty_markers = ["i cannot", "not found", "no information", "unclear", 
                                "don't know", "not sure", "insufficient"]
        needs_drill = any(m in answer.lower() for m in uncertainty_markers)

        retrieved = [{"level": 3, "text": l3_crystal[:300]}]

        if needs_drill and retrieve_depth >= 2 and l2_topics:
            # Find most relevant L2 topic
            query_vec = self._vectorize_text(task)
            best_topic = None
            best_score = -1

            for topic in l2_topics:
                topic_vec = self._vectorize_text(topic["topic"])
                score = self._vector_similarity(query_vec, topic_vec)
                if score > best_score:
                    best_score = score
                    best_topic = topic

            if best_topic and best_score > 0.1:
                context += f"\n\n[RELEVANT TOPIC] {best_topic['topic']}"
                retrieved.append({"level": 2, "text": best_topic["topic"][:300], "score": round(best_score, 3)})

                # Drill to L1 if depth allows
                if retrieve_depth >= 3 and l1_summaries:
                    # Find L1 summaries linked to this topic
                    for src in best_topic.get("sources", [])[:3]:
                        for l1 in l1_summaries:
                            if l1["source_range"] == src:
                                context += f"\n\n[DETAIL] {l1['summary']}"
                                retrieved.append({"level": 1, "text": l1["summary"][:300]})
                                break

        # Re-answer with enriched context if we drilled down
        if len(retrieved) > 1:
            answer = self.llm.answer(context, task, max_tokens)

        confidence = 0.7 if len(retrieved) > 1 else 0.55

        return {
            "answer": answer,
            "tokens_used": self._estimate_tokens(answer) + self._estimate_tokens(context),
            "retrieved_segments": retrieved,
            "confidence": round(confidence, 2),
            "strategy": "hierarchical"
        }

    def _vectorize_text(self, text: str) -> Dict[str, float]:
        """Simple vectorization for hierarchy navigation."""
        import re
        from collections import Counter
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        freq = Counter(words)
        total = sum(freq.values())
        if total == 0:
            return {}
        return {w: c / total for w, c in freq.items()}

    def _vector_similarity(self, v1: Dict[str, float], v2: Dict[str, float]) -> float:
        """Cosine similarity."""
        import math
        all_words = set(v1.keys()) | set(v2.keys())
        dot = sum(v1.get(w, 0) * v2.get(w, 0) for w in all_words)
        n1 = math.sqrt(sum(x ** 2 for x in v1.values()))
        n2 = math.sqrt(sum(x ** 2 for x in v2.values()))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)
