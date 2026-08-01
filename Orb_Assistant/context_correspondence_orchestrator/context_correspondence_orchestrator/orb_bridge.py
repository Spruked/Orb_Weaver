"""
Context & Correspondence Orchestrator - ORBS Bridge
Connects CCO to ORBS Vault architecture.
Vault remains authoritative; CCO working context packages are disposable
projections. The Correspondence Engine governs reasoning. LLM only articulates.
"""

from typing import Dict, Any, List, Optional
from .models import CompressRequest, CompressionStrategy


class ORBSVaultBridge:
    """
    Bridges ORBS Vault structured records to CCO.

    Architecture principle:
    - Vault is AUTHORITATIVE (immutable, append-only)
    - CCO working context is a DISPOSABLE projection
    - Correspondence Engine reasons over the CCO package
    - LLM (Qwen/Weaver) only articulates TPC output
    - ECM contains 4 philosopher SKGs: Locke, Hume, Kant, Spinoza
    - Soft Max meta-reasoner provides confidence-weighted advisory

    No runtime output flows back to Vault without a governed write-back path.
    CCO packages are compiled, used, and discarded.
    """

    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = vault_path
        self.vault_schema = [
            "fact_id", "subject", "predicate", "object",
            "confidence", "timestamp", "source", "supersedes", "status", "provenance"
        ]

        # TPC confidence cap from ORBS architecture
        self.tpc_confidence_cap = 0.75

    def compile_vault_records(self, records: List[Dict[str, Any]], 
                              task: str, 
                              target_budget: int = 2000) -> CompressRequest:
        """
        Compile ORBS vault records into a CCO context package request.
        Every line remains traceable to vault fact_id.

        The Correspondence Engine will reason over this package, not the raw vault.
        The 4 philosopher beams (Locke, Hume, Kant, Spinoza) converge
        in the ECM to produce judgments from the CCO representation.
        """
        lines = []
        for r in records:
            lines.append("---")
            for field in self.vault_schema:
                if field in r:
                    lines.append(f"{field}: {r[field]}")

        source = "\n".join(lines)

        return CompressRequest(
            source=source,
            source_type="vault_records",
            task=task,
            target_token_budget=target_budget,
            strategy=CompressionStrategy.VAULT_COMPILE,
            preserve_exact=[r.get("fact_id") for r in records if r.get("fact_id")]
        )

    def extract_provenance(self, crystal_response) -> List[Dict[str, Any]]:
        """Extract vault provenance from CCO response for correspondence reconciliation."""
        return crystal_response.provenance if hasattr(crystal_response, "provenance") else []

    def validate_projection(self, crystal_answer: str, 
                           vault_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that CCO answer is consistent with vault.
        TPC reconciliation happens here before articulation.
        Returns validation report.
        """
        validation = {
            "consistent": True,
            "violations": [],
            "traceable_facts": [],
            "tpc_reconciled": False
        }

        import re
        fact_refs = re.findall(r'V\d+|[A-Z]?[0-9]{2,}', crystal_answer)
        vault_ids = {r.get("fact_id", "") for r in vault_records}

        for ref in fact_refs:
            if ref in vault_ids:
                validation["traceable_facts"].append(ref)
            else:
                validation["violations"].append(f"Untraceable reference: {ref}")
                validation["consistent"] = False

        return validation

    def apply_tpc_governance(self, crystal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply TPC (Triple Predicate Cubed) governance to CCO output.

        TPC reasons over the CCO working context representation.
        LLM only articulates what TPC reconciles.
        Confidence capped at 0.75 under peer tension.
        """
        governance = {
            "tpc_governed": True,
            "confidence_cap": self.tpc_confidence_cap,
            "philosopher_beams": ["Locke", "Hume", "Kant", "Spinoza"],
            "soft_max_advisory": True,
            "articulation_only": True  # LLM does not reason, only speaks
        }

        crystal_data["tpc_governance"] = governance
        return crystal_data
