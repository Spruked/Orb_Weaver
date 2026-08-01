"""
Organized Doubt / re-challenge — maintenance process, not a
governance report. MANDATORY structure, PLACEHOLDER thresholds.

Feedback loop (antifragility gap — see gaps.py: GAP_FEEDBACK) is
explicitly NOT implemented here. A successful re-challenge currently
only flags the atom; it does not propagate any correction back to
the atom's provenance/source. That propagation is the piece that
would make this antifragile rather than merely robust, and it's
the highest-priority addition once the earlier gaps are resolved.
"""

from dataclasses import dataclass
from typing import List

from .atoms import KnowledgeAtom
from .vault import Vault


@dataclass
class ReChallengeConfig:
    # NOTE: all four values below are Phase 1 empirical targets, not final.
    low_confidence_threshold: float = 0.35            # TODO: validate empirically
    contradiction_edge_increase_threshold: int = 2     # TODO: validate empirically
    neighbor_variance_threshold: float = 0.25          # TODO: validate empirically — also blocked on GAP_A
    max_cycles_without_revalidation: int = 500         # TODO: validate empirically


def needs_rechallenge(
    atom: KnowledgeAtom,
    vault: Vault,
    config: ReChallengeConfig,
    current_cycle: int,
    atom_last_validated_cycle: int,
) -> List[str]:
    """
    Returns the list of reasons this atom should be re-challenged.
    Empty list = no re-challenge needed.

    NOTE: "rising neighbor variance" is not evaluated here yet — it
    requires a distance metric over the atom's geometric neighbors,
    which depends on GAP_A (vector computation) and the
    stability/drift stubs in geometry.py being resolved first.
    """
    reasons = []

    if atom.confidence < config.low_confidence_threshold:
        reasons.append("low_confidence")

    contradiction_edges = [
        e for e in vault.edges_for(atom.atom_id)
        if e.relation.value == "contradicts"
    ]
    if len(contradiction_edges) >= config.contradiction_edge_increase_threshold:
        reasons.append("rising_contradictions")

    cycles_elapsed = current_cycle - atom_last_validated_cycle
    if cycles_elapsed >= config.max_cycles_without_revalidation:
        reasons.append("stale_revalidation")

    return reasons
