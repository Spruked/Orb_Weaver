from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
SKG_ROOT = REPO_ROOT / "Orb_Vault_System" / "orb_vault_skg"
if str(SKG_ROOT) not in sys.path:
    sys.path.insert(0, str(SKG_ROOT))

from vault.orb_assistant import QueryRouter, VaultCoordinator  # noqa: E402
from vault.shared.constants import VaultConstants  # noqa: E402


class VaultSKGAdapter:
    """Read site-specific SKG vaults without falling back to bundled examples."""

    def __init__(self, priori_dir: Path | str, posteriori_dir: Path | str):
        self.coordinator = VaultCoordinator(
            weaver_output_dir=str(Path(priori_dir).resolve()),
            posteriori_data_dir=str(Path(posteriori_dir).resolve()),
        )

    def lookup(self, lane: str, query: str) -> Optional[Dict[str, Any]]:
        catalog_names = [
            entry.name
            for entry in self.coordinator.priori.catalog_state.entries.values()
            if getattr(entry, "name", None)
        ]
        intent, entities, routing_confidence = QueryRouter.route(query, catalog_names=catalog_names)
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


@lru_cache(maxsize=32)
def get_vault_skg_adapter(priori_dir: str, posteriori_dir: str) -> VaultSKGAdapter:
    return VaultSKGAdapter(priori_dir, posteriori_dir)
