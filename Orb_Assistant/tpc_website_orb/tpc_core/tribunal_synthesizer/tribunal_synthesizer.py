"""
Tribunal Synthesizer
Takes all four philosopher verdicts and produces a synthesis.
NOT a simple average — a weighted synthesis based on beam confidence.
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class TribunalOutput:
    synthesized_vector: np.ndarray
    confidence: float
    reasoning: str
    beam_weights: Dict[str, float]
    dissent_flags: List[str]


class TribunalSynthesizer:
    """
    Weighted synthesis of four philosopher beams.
    Higher-confidence beams get more weight.
    Dissenting beams are flagged but not silenced.
    """

    def __init__(self, vector_dim: int = 512):
        self.vector_dim = vector_dim
        self.synthesis_history: List[Dict] = []

    def synthesize(self, verdicts: Dict, 
                   coherence_reading=None,
                   min_participation: int = 4) -> TribunalOutput:
        """
        Synthesize philosopher verdicts into unified output.

        Args:
            verdicts: Dict of {beam_name: verdict_object}
            coherence_reading: Optional phase coherence reading
            min_participation: Minimum beams required

        Returns:
            TribunalOutput with weighted synthesis
        """
        if len(verdicts) < min_participation:
            return self._insufficient_output(verdicts)

        # Extract outputs and confidences
        outputs = []
        weights = []
        reasoning_parts = []
        dissent_flags = []

        for name, verdict in verdicts.items():
            outputs.append(verdict.output_vector)
            weights.append(verdict.confidence)
            reasoning_parts.append(
                f"{name}: conf={verdict.confidence:.3f}"
            )

            # Flag low-confidence beams as dissenting
            if verdict.confidence < 0.3:
                dissent_flags.append(f"{name}_low_confidence")

        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            normalized_weights = [w / total_weight for w in weights]
        else:
            normalized_weights = [0.25] * len(weights)

        # Weighted synthesis
        synthesized = np.zeros(self.vector_dim)
        for output, weight in zip(outputs, normalized_weights):
            # Pad or truncate to match vector_dim
            if len(output) < self.vector_dim:
                padded = np.zeros(self.vector_dim)
                padded[:len(output)] = output
                output = padded
            elif len(output) > self.vector_dim:
                output = output[:self.vector_dim]
            synthesized += output * weight

        # Overall confidence
        confidence = np.mean(weights)

        # Apply coherence adjustment
        if coherence_reading and hasattr(coherence_reading, 'coherence_score'):
            confidence *= coherence_reading.coherence_score

        # Hard cap at 0.95
        confidence = min(0.95, confidence)

        reasoning = " | ".join(reasoning_parts)

        beam_weights = {
            name: w for name, w in zip(verdicts.keys(), normalized_weights)
        }

        output = TribunalOutput(
            synthesized_vector=synthesized,
            confidence=confidence,
            reasoning=reasoning,
            beam_weights=beam_weights,
            dissent_flags=dissent_flags
        )

        self.synthesis_history.append({
            'confidence': confidence,
            'dissent_count': len(dissent_flags),
            'beam_count': len(verdicts),
            'weights': beam_weights
        })

        return output

    def _insufficient_output(self, verdicts: Dict) -> TribunalOutput:
        """Handle insufficient beam participation."""
        return TribunalOutput(
            synthesized_vector=np.zeros(self.vector_dim),
            confidence=0.1,
            reasoning=f"INSUFFICIENT: Only {len(verdicts)} beams participated",
            beam_weights={},
            dissent_flags=["insufficient_participation"]
        )

    def get_stats(self) -> Dict:
        if not self.synthesis_history:
            return {'total_syntheses': 0}

        return {
            'total_syntheses': len(self.synthesis_history),
            'avg_confidence': np.mean([s['confidence'] for s in self.synthesis_history]),
            'avg_dissent': np.mean([s['dissent_count'] for s in self.synthesis_history]),
            'insufficient_events': sum(1 for s in self.synthesis_history if s['dissent_count'] > 0)
        }


# Singleton
_tribunal_instance = None

def get_tribunal_synthesizer(vector_dim: int = 512) -> TribunalSynthesizer:
    global _tribunal_instance
    if _tribunal_instance is None:
        _tribunal_instance = TribunalSynthesizer(vector_dim)
    return _tribunal_instance
