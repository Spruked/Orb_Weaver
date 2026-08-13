"""
Context & Correspondence Orchestrator - Vault Compile Strategy (ORBS-specific)
Deterministic compilation of structured vault records into compact representation.
Does NOT compress natural language - compiles structured data.
Every line traceable back to authoritative vault source.
"""

import json
from typing import Dict, Any, List
from .base import BaseStrategy
from ..models import TaskProfile


class VaultCompileStrategy(BaseStrategy):
    """
    ORBS-specific: Compiles structured vault records deterministically.

    Vault schema expected:
    {
        "fact_id": str,
        "subject": str,
        "predicate": str, 
        "object": str,
        "confidence": float,
        "timestamp": str,
        "source": str,
        "supersedes": Optional[str],
        "status": str,
        "provenance": str
    }
    """

    def __init__(self, llm):
        super().__init__(llm)
        self.name = "vault_compile"

    def compress(self, source: str, task_profile: TaskProfile,
                   target_budget: int, preserve_exact: List[str] = None) -> Dict[str, Any]:
        """Compile vault records into compact deterministic representation."""

        # Try to parse as JSON records
        try:
            records = json.loads(source) if source.strip().startswith("[") else self._parse_records(source)
        except json.JSONDecodeError:
            records = self._parse_records(source)

        if not isinstance(records, list):
            records = [records]

        original_tokens = self._estimate_tokens(source)

        # Filter by task relevance
        filtered = self._filter_by_task(records, task_profile)

        # Compile into compact format
        compiled = self._compile_records(filtered, task_profile)

        # Add provenance mapping
        provenance = {r.get("fact_id", f"V{i}"): r for i, r in enumerate(filtered)}

        crystal_text = compiled
        crystal_tokens = self._estimate_tokens(crystal_text)

        return {
            "crystal_text": crystal_text,
            "crystal_tokens": crystal_tokens,
            "original_tokens": original_tokens,
            "records_count": len(records),
            "filtered_count": len(filtered),
            "provenance": provenance,
            "metadata": {
                "strategy": "vault_compile",
                "task_domain": task_profile.domain,
                "compilation_type": "deterministic",
                "compression_ratio": original_tokens / max(crystal_tokens, 1),
                "traceable": True
            }
        }

    def _parse_records(self, source: str) -> List[Dict]:
        """Parse vault records from text format."""
        records = []
        lines = source.strip().split("\n")
        current = {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("---") and current:
                records.append(current)
                current = {}
                continue

            if ":" in line:
                key, val = line.split(":", 1)
                current[key.strip().lower()] = val.strip()

        if current:
            records.append(current)

        return records if records else [{"raw": source}]

    def _filter_by_task(self, records: List[Dict], task_profile: TaskProfile) -> List[Dict]:
        """Filter records by task relevance."""
        if not task_profile.priority_keywords and not task_profile.entities:
            return records

        keywords = set(k.lower() for k in task_profile.priority_keywords)
        keywords.update(e.lower() for e in task_profile.entities)

        scored = []
        for record in records:
            text = " ".join(str(v) for v in record.values()).lower()
            score = sum(1 for kw in keywords if kw in text)
            scored.append((score, record))

        scored.sort(key=lambda item: item[0], reverse=True)

        # Keep top 80% or all if small
        cutoff = max(1, int(len(scored) * 0.8))
        return [r for _, r in scored[:cutoff]] if len(scored) > 10 else [r for _, r in scored]

    def _compile_records(self, records: List[Dict], task_profile: TaskProfile) -> str:
        """Compile records into compact deterministic format."""
        lines = []
        lines.append(f"# COMPILED VAULT CRYSTAL")
        lines.append(f"# Domain: {task_profile.domain or 'general'}")
        lines.append(f"# Intent: {task_profile.intent}")
        lines.append(f"# Records: {len(records)}")
        lines.append("")

        # Active facts
        active_facts = [r for r in records if r.get("status", "active").lower() == "active"]
        lines.append(f"## ACTIVE FACTS ({len(active_facts)})")

        for r in active_facts:
            fact_id = r.get("fact_id", "?")
            subject = r.get("subject", "?")
            predicate = r.get("predicate", "?")
            obj = r.get("object", "?")
            conf = r.get("confidence", "?")
            lines.append(f"{fact_id}: {subject} {predicate} {obj} [c:{conf}]")

        lines.append("")

        # Superseded facts (for contradiction awareness)
        superseded = [r for r in records if r.get("supersedes") or r.get("status", "").lower() == "superseded"]
        if superseded:
            lines.append(f"## SUPERSEDED ({len(superseded)})")
            for r in superseded:
                fact_id = r.get("fact_id", "?")
                sup = r.get("supersedes", "?")
                lines.append(f"{fact_id}: supersedes {sup}")
            lines.append("")

        # Contradictions
        contradictions = self._find_contradictions(records)
        if contradictions:
            lines.append(f"## CONTRADICTIONS ({len(contradictions)})")
            for c in contradictions:
                lines.append(f"{c['fact_a']} vs {c['fact_b']}: {c['subject']}")
            lines.append("")

        # Source provenance summary
        sources = {}
        for r in records:
            src = r.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1

        lines.append("## SOURCES")
        for src, count in sorted(sources.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"- {src}: {count} records")

        return "\n".join(lines)

    def _find_contradictions(self, records: List[Dict]) -> List[Dict]:
        """Find potential contradictions in records."""
        contradictions = []
        by_subject = {}

        for r in records:
            subj = r.get("subject", "").lower()
            if subj:
                by_subject.setdefault(subj, []).append(r)

        for subj, recs in by_subject.items():
            if len(recs) > 1:
                # Check for same predicate, different object
                by_pred = {}
                for r in recs:
                    pred = r.get("predicate", "").lower()
                    by_pred.setdefault(pred, []).append(r)

                for pred, pred_recs in by_pred.items():
                    if len(pred_recs) > 1:
                        objs = [r.get("object", "") for r in pred_recs]
                        if len(set(objs)) > 1:
                            contradictions.append({
                                "subject": subj,
                                "predicate": pred,
                                "fact_a": pred_recs[0].get("fact_id", "?"),
                                "fact_b": pred_recs[1].get("fact_id", "?"),
                                "objects": objs
                            })

        return contradictions

    def query(self, crystal_data: Dict[str, Any], task: str,
              max_tokens: int = 1000, retrieve_depth: int = 2) -> Dict[str, Any]:
        """Answer from compiled vault crystal with full provenance."""
        crystal_text = crystal_data["crystal_text"]
        provenance = crystal_data.get("provenance", {})

        answer = self.llm.answer(crystal_text, task, max_tokens)

        # Extract referenced fact IDs from answer for provenance
        import re
        fact_refs = re.findall(r'[A-Z]?\d+', answer)
        provenance_refs = []
        for ref in fact_refs:
            if ref in provenance:
                provenance_refs.append({
                    "fact_id": ref,
                    "record": provenance[ref]
                })

        return {
            "answer": answer,
            "tokens_used": self._estimate_tokens(answer) + self._estimate_tokens(crystal_text),
            "retrieved_segments": [{"source": "vault_crystal", "text": crystal_text[:500]}],
            "confidence": 0.85,  # High confidence due to structured source
            "provenance": provenance_refs,
            "strategy": "vault_compile"
        }
