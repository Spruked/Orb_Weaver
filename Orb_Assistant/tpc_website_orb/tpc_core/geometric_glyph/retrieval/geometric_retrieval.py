"""
Geometric Glyph Retrieval
Retrieval spectrum:
- Known signature → exact vault retrieval
- Near signature → weighted partial retrieval + confidence score
- Distant signature → novel input, triggers philosopher recursion
- Orthogonal → genuinely unknown, ECM escalation
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time

from Orb_Assistant.tpc_website_orb.tpc_core.geometric_glyph.signatures.glyph_signatures import GlyphSignature, get_glyph_engine


class RetrievalResult(Enum):
    EXACT = "exact"
    PARTIAL = "partial"
    NOVEL = "novel"
    UNKNOWN = "unknown"


@dataclass
class RetrievalOutput:
    result: RetrievalResult
    confidence: float
    matched_entries: List[Dict]
    distance: float
    recommendation: str
    timestamp: float


class GeometricRetrieval:
    """
    Geometric retrieval engine.
    Distance in geometric space IS the confidence score.
    """

    def __init__(self, vault_interface=None, dimensions: int = 18):
        self.glyph_engine = get_glyph_engine(dimensions)
        self.vault = vault_interface
        self.retrieval_history: List[Dict] = []
        self.thresholds = {
            'exact': 0.05,
            'near': 0.3,
            'distant': 0.7
        }

    def retrieve(self, query_vector: np.ndarray, 
                 certainty: float = 0.5) -> RetrievalOutput:
        """
        Perform geometric retrieval on query vector.

        Returns classification and recommended action.
        """
        # Generate query signature
        query_sig = self.glyph_engine.generate(
            query_vector, certainty=certainty, source="retrieval_query"
        )

        # If vault available, search for matches
        if self.vault:
            matches = self._vault_search(query_sig)
        else:
            matches = []

        # Determine classification
        if matches:
            best_distance = matches[0]['distance']
            classification = self.glyph_engine.classify_retrieval(best_distance)

            if classification == "exact":
                result = RetrievalResult.EXACT
                confidence = 1.0 - best_distance
                recommendation = "Return vault entry directly"
            elif classification == "near":
                result = RetrievalResult.PARTIAL
                confidence = 1.0 - best_distance
                recommendation = "Weighted partial retrieval + philosopher verification"
            else:
                result = RetrievalResult.NOVEL
                confidence = 0.3
                recommendation = "Trigger philosopher recursion"
        else:
            result = RetrievalResult.UNKNOWN
            confidence = 0.1
            recommendation = "ECM escalation — genuinely unknown input"
            best_distance = 1.0

        output = RetrievalOutput(
            result=result,
            confidence=confidence,
            matched_entries=matches,
            distance=best_distance,
            recommendation=recommendation,
            timestamp=time.time()
        )

        self.retrieval_history.append({
            'result': result.value,
            'confidence': confidence,
            'distance': best_distance,
            'timestamp': time.time()
        })

        return output

    def _vault_search(self, query_sig: GlyphSignature) -> List[Dict]:
        """Search vault for geometrically similar signatures."""
        # This is a placeholder — actual vault integration would go here
        # Returns mock results for architecture demonstration
        return []

    def batch_retrieve(self, query_vectors: List[np.ndarray],
                       certainties: List[float] = None) -> List[RetrievalOutput]:
        """Batch retrieval for efficiency."""
        certainties = certainties or [0.5] * len(query_vectors)
        return [self.retrieve(v, c) for v, c in zip(query_vectors, certainties)]

    def get_stats(self) -> Dict:
        if not self.retrieval_history:
            return {'total_queries': 0}

        results = [r['result'] for r in self.retrieval_history]
        return {
            'total_queries': len(self.retrieval_history),
            'exact_rate': results.count('exact') / len(results),
            'partial_rate': results.count('partial') / len(results),
            'novel_rate': results.count('novel') / len(results),
            'unknown_rate': results.count('unknown') / len(results),
            'avg_confidence': np.mean([r['confidence'] for r in self.retrieval_history]),
            'thresholds': self.thresholds
        }


# Singleton
_retrieval_engine = None

def get_geometric_retrieval(vault_interface=None, dimensions: int = 18) -> GeometricRetrieval:
    global _retrieval_engine
    if _retrieval_engine is None:
        _retrieval_engine = GeometricRetrieval(vault_interface, dimensions)
    return _retrieval_engine
