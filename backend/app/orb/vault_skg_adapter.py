from __future__ import annotations

import hashlib
import json
import sys
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
SKG_ROOT = REPO_ROOT / "Orb_Vault_System" / "orb_vault_skg"
if str(SKG_ROOT) not in sys.path:
    sys.path.insert(0, str(SKG_ROOT))

from vault.orb_assistant import QueryRouter, VaultCoordinator  # noqa: E402
from vault.shared.constants import VaultConstants  # noqa: E402


class VaultSKGAdapter:
    """Connect a site runtime to its existing A Priori/A Posteriori SKG."""

    def __init__(self, priori_dir: Path | str, posteriori_dir: Path | str):
        self.coordinator = VaultCoordinator(
            weaver_output_dir=str(Path(priori_dir).resolve()),
            posteriori_data_dir=str(Path(posteriori_dir).resolve()),
        )
        self._lock = threading.RLock()

    def _route(self, query: str):
        catalog_names = [
            entry.name
            for entry in self.coordinator.priori.catalog_state.entries.values()
            if getattr(entry, "name", None)
        ]
        return QueryRouter.route(query, catalog_names=catalog_names)

    def lookup(self, lane: str, query: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            intent, entities, routing_confidence = self._route(query)
            if lane == "apriori":
                result = self.coordinator.priori.query(query, intent, entities)
                threshold = VaultConstants.ROUTE_APRIORI_MIN_CONFIDENCE
            elif lane == "posteriori":
                result = self.coordinator.posteriori.query(query, intent, entities)
                threshold = VaultConstants.ROUTE_APOSTERIORI_MIN_CONFIDENCE
            else:
                raise ValueError(f"Unsupported SKG lane: {lane}")
        if not result.success or not result.answer or result.confidence < threshold:
            return None
        return {
            "answer": result.answer,
            "source": result.source or f"vault_skg_{lane}",
            "confidence": float(result.confidence),
            "evidence_ids": [str(result.entity_id)] if result.entity_id else [],
            "routing_confidence": float(routing_confidence),
            "resolution_path": list(result.resolution_path or []),
            "data": result.data,
        }

    def report_outcome(
        self,
        *,
        query: str,
        resolution_source: str,
        answer: str,
        success: bool,
        session_id: str = "",
    ) -> Dict[str, Any]:
        """Feed a completed turn into the existing posteriori learning lifecycle."""
        with self._lock:
            intent, entities, routing_confidence = self._route(query)
            before_ids = set(self.coordinator.posteriori.exp_cog.candidate_queue)
            experience_id = self.coordinator.report_outcome(
                query_text=query,
                intent=intent,
                entities=entities,
                resolution_source=resolution_source,
                answer=answer,
                success=success,
                session_id=session_id,
            )
            self.coordinator.run_maintenance()
            candidates = self.coordinator.posteriori.exp_cog.candidate_queue
            promoted = self.coordinator.posteriori.prom_cog.promoted_nodes
            new_ids = set(candidates) - before_ids
            candidate = candidates.get(next(iter(new_ids), ""))
            if candidate is None:
                normalized = " ".join(query.lower().split())
                for node in [*candidates.values(), *promoted.values()]:
                    patterns = [node.content.get("query_pattern", ""), *(node.content.get("aliases") or [])]
                    if normalized in {" ".join(str(item).lower().split()) for item in patterns}:
                        candidate = node
                        break
            return {
                "experience_id": experience_id,
                "candidate_id": getattr(candidate, "node_id", None),
                "candidate_state": getattr(getattr(candidate, "state", None), "name", None),
                "candidate_confidence": float(candidate.confidence.value) if candidate is not None else None,
                "intent": intent.name,
                "entities": entities,
                "routing_confidence": float(routing_confidence),
                "stats": self.coordinator.get_stats(),
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return self.coordinator.get_stats()


def materialize_site_apriori(priori_dir: Path | str, apriori: Mapping[str, Any]) -> str:
    """Persist active compiled A Priori artifacts where the site SKG expects them."""
    root = Path(priori_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    documents = {
        "catalog.json": dict(apriori.get("catalog") or {"entries": []}),
        "qa.json": dict(apriori.get("qa") or {"entries": []}),
        "ontology.json": dict(apriori.get("ontology") or {"nodes": [], "edges": []}),
        "policies.json": dict(apriori.get("policies") or {"rules": []}),
    }
    encoded = json.dumps(documents, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    version = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
    for filename, document in documents.items():
        path = root / filename
        content = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(content, encoding="utf-8")
            temporary.replace(path)
    return version


@lru_cache(maxsize=32)
def get_vault_skg_adapter(priori_dir: str, posteriori_dir: str, source_version: str = "") -> VaultSKGAdapter:
    return VaultSKGAdapter(priori_dir, posteriori_dir)
