"""
Hume Beam - Empirical Skepticism
Functional role: Enforces strict empirical grounding.
A claim is admissible only if traceable to impression, observation, or measurable experience.
Causal inferences treated as probabilistic, not necessary.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time


class HumeStatus(Enum):
    ADMISSIBLE = "admissible"
    REJECTED = "rejected"
    PROBABILISTIC = "probabilistic"
    INSUFFICIENT = "insufficient"


@dataclass
class HumeVerdict:
    status: HumeStatus
    confidence: float
    output_vector: np.ndarray
    empirical_trace: List[str]
    rejection_reason: Optional[str] = None
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


class HumeBeam:
    """
    Empirical skepticism as pure probabilistic state machine.
    No LLM. No transformer. Pure softmax probability loops on rule sets.
    """

    def __init__(self, vector_dim: int = 512):
        self.vector_dim = vector_dim
        self.empirical_rules = self._load_rules()
        self.observation_history: List[Dict] = []
        self.rejection_log: List[Dict] = []

    def _load_rules(self) -> Dict:
        """Hume's empirical rule set encoded as probabilistic constraints."""
        return {
            'impression_required': 0.7,      # Need sensory impression
            'causal_probabilistic': 0.8,     # Causation is habit, not necessity
            'abstract_skepticism': 0.6,      # Be skeptical of abstract claims
            'constant_conjunction': 0.75,    # Causation = constant conjunction
            'missing_shade_blue': 0.5,       # Can imagine without experiencing
        }

    def reason(self, input_vector: np.ndarray, 
               depth_state: str = "K0",
               empirical_context: List[str] = None) -> HumeVerdict:
        """
        Run Hume empirical skepticism on input.

        Args:
            input_vector: Normalized epistemic stimulus vector
            depth_state: K0/K1/K2 recursion depth
            empirical_context: List of empirical observations
        """
        empirical_context = empirical_context or []

        # Rule-based probability scoring
        scores = []
        traces = []

        # Check 1: Is there empirical grounding?
        has_impression = self._check_impression(input_vector, empirical_context)
        scores.append(has_impression * self.empirical_rules['impression_required'])
        traces.append(f"impression_check: {has_impression:.3f}")

        # Check 2: Are causal claims probabilistic?
        causal_score = self._check_causal_nature(input_vector)
        scores.append(causal_score * self.empirical_rules['causal_probabilistic'])
        traces.append(f"causal_probabilistic: {causal_score:.3f}")

        # Check 3: Abstract vs concrete
        abstraction_score = self._measure_abstraction(input_vector)
        scores.append((1 - abstraction_score) * self.empirical_rules['abstract_skepticism'])
        traces.append(f"abstraction_penalty: {abstraction_score:.3f}")

        # Check 4: Constant conjunction evidence
        conjunction_score = self._check_constant_conjunction(input_vector, empirical_context)
        scores.append(conjunction_score * self.empirical_rules['constant_conjunction'])
        traces.append(f"constant_conjunction: {conjunction_score:.3f}")

        # Depth adjustment — deeper recursion = more skepticism
        if depth_state == "K2":
            scores = [s * 0.85 for s in scores]  # More skeptical at depth
            traces.append("depth_K2_skepticism: -15%")

        # Calculate confidence
        if scores:
            confidence = np.mean(scores)
        else:
            confidence = 0.5

        # Determine status
        if confidence >= 0.7:
            status = HumeStatus.ADMISSIBLE
        elif confidence >= 0.4:
            status = HumeStatus.PROBABILISTIC
        elif confidence >= 0.2:
            status = HumeStatus.INSUFFICIENT
        else:
            status = HumeStatus.REJECTED

        # Generate output vector
        output_vector = self._generate_output_vector(input_vector, confidence)

        verdict = HumeVerdict(
            status=status,
            confidence=confidence,
            output_vector=output_vector,
            empirical_trace=traces,
            timestamp=time.time()
        )

        self.observation_history.append({
            'input_sample': input_vector[:10].tolist(),
            'verdict': status.value,
            'confidence': confidence,
            'depth': depth_state,
            'timestamp': time.time()
        })

        if status == HumeStatus.REJECTED:
            self.rejection_log.append({
                'confidence': confidence,
                'traces': traces,
                'timestamp': time.time()
            })

        return verdict

    def _check_impression(self, vector: np.ndarray, context: List[str]) -> float:
        """Check if input has empirical impression grounding."""
        # Vector magnitude as proxy for sensory richness
        magnitude = np.linalg.norm(vector)
        # Context length as proxy for observational backing
        context_score = min(1.0, len(context) / 10)
        return (magnitude / 10.0) * 0.5 + context_score * 0.5

    def _check_causal_nature(self, vector: np.ndarray) -> float:
        """Score how much the input makes causal claims."""
        # Use vector variance as proxy for causal complexity
        variance = np.var(vector)
        # High variance = more causal claims = more skepticism needed
        return max(0.0, 1.0 - variance * 2)

    def _measure_abstraction(self, vector: np.ndarray) -> float:
        """Measure abstraction level of input."""
        # Entropy as abstraction proxy
        normalized = np.abs(vector) / (np.sum(np.abs(vector)) + 1e-10)
        entropy = -np.sum(normalized * np.log2(normalized + 1e-10))
        return min(1.0, entropy / 5.0)

    def _check_constant_conjunction(self, vector: np.ndarray, context: List[str]) -> float:
        """Check for constant conjunction evidence in context."""
        if not context:
            return 0.3
        # More repeated observations = higher conjunction score
        unique_obs = len(set(context))
        total_obs = len(context)
        if total_obs == 0:
            return 0.3
        repetition_ratio = 1.0 - (unique_obs / total_obs)
        return 0.3 + repetition_ratio * 0.7

    def _generate_output_vector(self, input_vector: np.ndarray, confidence: float) -> np.ndarray:
        """Generate Hume-conditioned output vector."""
        # Scale by confidence — Hume deflates overconfident claims
        scaled = input_vector * (0.5 + 0.5 * confidence)
        # Add empirical noise (Hume's probabilistic nature)
        noise = np.random.normal(0, 0.05, self.vector_dim)
        return scaled + noise

    def get_stats(self) -> Dict:
        return {
            'total_reasonings': len(self.observation_history),
            'rejection_rate': len(self.rejection_log) / max(1, len(self.observation_history)),
            'avg_confidence': np.mean([o['confidence'] for o in self.observation_history]) if self.observation_history else 0,
            'rule_set': list(self.empirical_rules.keys())
        }


# Singleton
_hume_instance = None

def get_hume_beam(vector_dim: int = 512) -> HumeBeam:
    global _hume_instance
    if _hume_instance is None:
        _hume_instance = HumeBeam(vector_dim)
    return _hume_instance
