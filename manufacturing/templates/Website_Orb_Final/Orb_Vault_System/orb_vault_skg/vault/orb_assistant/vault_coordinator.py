"""
orb/vault/orb_assistant/vault_coordinator.py
Orchestrates A Priori and A Posteriori vaults.
Routes queries, manages learning loop, coordinates with TPC/LLM.

Expected package structure:
    Orb_Vault_System/
    ├── Orb_Vault/              ← this code (vault/)
    │   ├── a_priori/
    │   ├── a_posteriori/
    │   ├── orb_assistant/
    │   └── shared/
    └── vaults/
        ├── A_Priori_Vault/     ← compiled data from Orb Weaver
        │   ├── catalog.json
        │   ├── ontology.json
        │   ├── qa.json
        │   └── policies.json
        └── A_Posteriori_Vault/ ← learned experience data
            ├── posteriori_state.json
            └── ledger/
"""

from __future__ import annotations
import os
from typing import Dict, List, Any, Optional

from ..shared.types import ResolutionResult, IntentType
from ..shared.constants import VaultConstants

from ..a_priori.priori_logic import PrioriVault
from ..a_posteriori.posteriori_logic import PosterioriVault


class VaultCoordinator:
    """
    Coordinates both vaults for the ORB Assistant.
    Implements TTI (True Technical Intelligence) routing:
    1. A Priori catalog (fastest, deterministic)
    2. A Priori ontology/QA (structured truth)
    3. A Posteriori learned (verified experience)
    4. TPC/LLM fallback (generative)
    """

    # Default paths relative to this file: vault/orb_assistant/vault_coordinator.py
    # Goes up two levels to Orb_Vault_System/, then into vaults/
    DEFAULT_PRIORI_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "vaults", "A_Priori_Vault"
    )
    DEFAULT_POSTERIORI_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "vaults", "A_Posteriori_Vault"
    )

    def __init__(
        self,
        weaver_output_dir: Optional[str] = None,
        posteriori_data_dir: Optional[str] = None
    ):
        """
        Initialize vault coordinator.

        Args:
            weaver_output_dir: Path to A Priori compiled data.
                Defaults to ../vaults/A_Priori_Vault (relative to package root).
            posteriori_data_dir: Path to A Posteriori learned data.
                Defaults to ../vaults/A_Posteriori_Vault (relative to package root).
        """
        self.priori_dir = weaver_output_dir or self.DEFAULT_PRIORI_DIR
        self.posteriori_dir = posteriori_data_dir or self.DEFAULT_POSTERIORI_DIR

        # Ensure posteriori directory exists (creates ledger/ subfolder on first run)
        os.makedirs(self.posteriori_dir, exist_ok=True)
        os.makedirs(os.path.join(self.posteriori_dir, "ledger"), exist_ok=True)

        self.priori = PrioriVault(self.priori_dir)
        self.posteriori = PosterioriVault(self.posteriori_dir)
        self.last_resolution_path: List[str] = []

    def resolve(self, query_text: str, intent: IntentType, entities: List[str], session_id: str = "") -> ResolutionResult:
        """
        Resolve a visitor query using the full vault stack.

        Routing order:
            1. A Priori catalog (direct price/product lookup)
            2. A Priori ontology/QA (business knowledge)
            3. A Posteriori learned (verified experience patterns)
            4. Escalate to TPC/LLM if all vault layers miss
        """
        self.last_resolution_path = []

        # LAYER 1: A Priori Catalog (fastest path for product/pricing)
        if intent.name in VaultConstants.CATALOG_INTENTS:
            result = self.priori.query(query_text, intent, entities)
            if result.success and result.confidence >= VaultConstants.ROUTE_APRIORI_MIN_CONFIDENCE:
                self.last_resolution_path = ["a_priori", "catalog", "direct"]
                self._learn_resolution(query_text, intent, entities, result, True, session_id)
                return result

        # LAYER 2: A Priori Ontology/QA (business knowledge)
        result = self.priori.query(query_text, intent, entities)
        if result.success and result.confidence >= VaultConstants.ROUTE_APRIORI_MIN_CONFIDENCE:
            self.last_resolution_path = ["a_priori", "ontology_qa"]
            self._learn_resolution(query_text, intent, entities, result, True, session_id)
            return result

        # LAYER 3: A Posteriori Learned (verified experience)
        result = self.posteriori.query(query_text, intent, entities)
        if result.success and result.confidence >= VaultConstants.ROUTE_APOSTERIORI_MIN_CONFIDENCE:
            self.last_resolution_path = ["a_posteriori", "learned"]
            self._reinforce_posteriori(result.entity_id or "", True)
            return result

        # LAYER 4: Return failure -- caller escalates to TPC/LLM
        self.last_resolution_path = ["vault", "no_match", "escalate_to_tpc"]
        return ResolutionResult(
            success=False,
            source="vault_coordinator",
            resolution_path=self.last_resolution_path,
            used_fallback=True,
        )

    def report_outcome(self, query_text: str, intent: IntentType, entities: List[str],
                       resolution_source: str, answer: str, success: bool, session_id: str = ""):
        """
        Report outcome for learning.
        Call this after ANY resolution (vault or LLM/TPC) so the posteriori vault learns.
        """
        self.posteriori.ingest_experience(
            query_text=query_text,
            detected_intent=intent,
            detected_entities=entities,
            resolution_path=resolution_source,
            resolution_result=answer,
            outcome_success=success,
            session_id=session_id,
        )

    def run_maintenance(self):
        """
        Run posteriori vault maintenance cycle.
        Call this on a schedule (e.g., daily cron) to:
            - Apply time decay to stale knowledge
            - Detect and flag contradictions
            - Prune degraded knowledge (weaken/merge/compress/retire)
            - Evaluate candidates for promotion
        """
        self.posteriori.run_maintenance()

    def reload_priori(self):
        """
        Reload A Priori from Orb Weaver output.
        Call this after Orb Weaver completes a new crawl.
        """
        self.priori.reload()

    def get_stats(self) -> Dict[str, Any]:
        """Get combined vault statistics."""
        return {
            "a_priori": self.priori.get_stats(),
            "a_posteriori": self.posteriori.get_stats(),
            "priori_dir": self.priori_dir,
            "posteriori_dir": self.posteriori_dir,
        }

    def _learn_resolution(self, query_text: str, intent: IntentType, entities: List[str],
                        result: ResolutionResult, success: bool, session_id: str):
        """Record successful A Priori resolution for posteriori learning."""
        if result.source.startswith("a_priori"):
            self.posteriori.ingest_experience(
                query_text=query_text,
                detected_intent=intent,
                detected_entities=entities,
                resolution_path=result.source,
                resolution_result=result.answer or "",
                outcome_success=success,
                session_id=session_id,
            )

    def _reinforce_posteriori(self, node_id: str, success: bool):
        """Reinforce a posteriori node from usage."""
        if node_id:
            self.posteriori.report_outcome(node_id, success)
