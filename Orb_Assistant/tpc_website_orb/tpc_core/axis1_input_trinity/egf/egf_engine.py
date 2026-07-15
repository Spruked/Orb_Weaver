"""
EGF - Epistemic Gravity Field
Certainty-as-gravity. The physics engine for vault retrieval.
High-certainty geometric signatures have stronger gravitational pull.
Distance in geometric space IS the confidence score.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time


class RetrievalResult(Enum):
    EXACT = "exact"
    PARTIAL = "partial"
    NOVEL = "novel"
    ORTHOGONAL = "orthogonal"


@dataclass
class GravityWell:
    """A gravity well in the EGF - represents a vault entry."""
    signature: np.ndarray      # Geometric glyph signature
    mass: float               # Certainty/certainty weight
    vault_id: str
    content: str
    timestamp: float
    source: str               # 'a_priori' or 'a_posteriori'

    def gravitational_pull(self, query_signature: np.ndarray) -> float:
        """
        Compute gravitational pull on a query signature.
        F = G * m1 * m2 / r^2, but here we use certainty-as-gravity.
        """
        distance = np.linalg.norm(self.signature - query_signature)
        if distance < 1e-10:
            return float('inf')

        # Gravity falls off with distance, amplified by certainty mass
        pull = self.mass / (distance ** 2 + 0.1)
        return pull


class EpistemicGravityField:
    """
    The EGF manages vault retrieval through gravitational physics.
    High-certainty entries create stronger gravity wells.
    Query signatures are "pulled" toward matching entries.
    """

    def __init__(self, a_priori_vault, a_posteriori_vault):
        self.wells: Dict[str, GravityWell] = {}
        self.a_priori_vault = a_priori_vault
        self.a_posteriori_vault = a_posteriori_vault
        self.retrieval_history: List[Dict] = []

        # Load existing vault entries as gravity wells
        self._load_vault_wells()

    def _load_vault_wells(self):
        """Convert vault entries to gravity wells."""
        # A Priori wells (higher mass - structurally encoded)
        for entry in self.a_priori_vault.get_all_entries():
            well = GravityWell(
                signature=np.array(entry['signature']),
                mass=entry.get('certainty', 0.95),
                vault_id=entry['id'],
                content=entry['content'],
                timestamp=entry.get('timestamp', time.time()),
                source='a_priori'
            )
            self.wells[entry['id']] = well

        # A Posteriori wells (variable mass - empirically weighted)
        for entry in self.a_posteriori_vault.get_all_entries():
            well = GravityWell(
                signature=np.array(entry['signature']),
                mass=entry.get('certainty', 0.7),
                vault_id=entry['id'],
                content=entry['content'],
                timestamp=entry.get('timestamp', time.time()),
                source='a_posteriori'
            )
            self.wells[entry['id']] = well

    def retrieve(self, query_signature: np.ndarray, 
                 top_k: int = 5,
                 distance_threshold: float = 0.3) -> Tuple[RetrievalResult, List[Tuple[GravityWell, float]]]:
        """
        Retrieve vault entries via gravitational physics.

        Returns:
            RetrievalResult: Classification of retrieval
            List of (well, confidence_score) tuples
        """
        if len(self.wells) == 0:
            return RetrievalResult.NOVEL, []

        # Compute gravitational pull for all wells
        pulls = []
        for well in self.wells.values():
            pull = well.gravitational_pull(query_signature)
            pulls.append((well, pull))

        # Sort by pull strength (descending)
        pulls.sort(key=lambda x: x[1], reverse=True)

        # Top K results
        top_results = pulls[:top_k]

        # Compute distance-based confidence for top result
        if top_results:
            best_well = top_results[0][0]
            distance = np.linalg.norm(best_well.signature - query_signature)
            confidence = 1.0 / (1.0 + distance)
        else:
            distance = float('inf')
            confidence = 0.0

        # Classify retrieval
        if distance < 0.05:
            result = RetrievalResult.EXACT
        elif distance < distance_threshold:
            result = RetrievalResult.PARTIAL
        elif distance > 0.9:
            result = RetrievalResult.ORTHOGONAL
        else:
            result = RetrievalResult.NOVEL

        # Convert pull to confidence scores
        scored_results = []
        for well, pull in top_results:
            # Normalize pull to confidence
            conf = min(1.0, pull / (pull + 1.0))
            scored_results.append((well, conf))

        # Record retrieval
        self.retrieval_history.append({
            'timestamp': time.time(),
            'result_type': result.value,
            'top_confidence': scored_results[0][1] if scored_results else 0,
            'distance': distance
        })

        return result, scored_results

    def add_well(self, signature: np.ndarray, content: str, 
                 certainty: float, source: str, vault_id: str = None):
        """Add a new gravity well (typically from new a_posteriori learning)."""
        if vault_id is None:
            vault_id = f"well_{int(time.time() * 1000)}"

        well = GravityWell(
            signature=signature,
            mass=certainty,
            vault_id=vault_id,
            content=content,
            timestamp=time.time(),
            source=source
        )
        self.wells[vault_id] = well
        return well

    def get_field_stats(self) -> Dict:
        """Get statistics about the gravity field."""
        a_priori_count = sum(1 for w in self.wells.values() if w.source == 'a_priori')
        a_posteriori_count = sum(1 for w in self.wells.values() if w.source == 'a_posteriori')

        return {
            'total_wells': len(self.wells),
            'a_priori_wells': a_priori_count,
            'a_posteriori_wells': a_posteriori_count,
            'retrieval_count': len(self.retrieval_history),
            'field_density': len(self.wells) / 1000.0  # Normalized density
        }


# Singleton placeholder - needs vaults to be initialized first
_egf_instance = None

def get_egf(a_priori_vault=None, a_posteriori_vault=None) -> EpistemicGravityField:
    """Get or create singleton EGF instance."""
    global _egf_instance
    if _egf_instance is None and a_priori_vault is not None and a_posteriori_vault is not None:
        _egf_instance = EpistemicGravityField(a_priori_vault, a_posteriori_vault)
    return _egf_instance
