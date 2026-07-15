"""
Kant Beam - Categorical Reasoning
Functional role: Evaluates whether conclusion can be universalized without contradiction.
Tests outputs against Kant's requirement that principles hold consistently across all cases.
Enforces structural integrity and duty-based reasoning.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time


class KantStatus(Enum):
    UNIVERSALIZABLE = "universalizable"
    CONTRADICTION = "contradiction"
    DUTY_BOUND = "duty_bound"
    CONDITIONAL = "conditional"


@dataclass
class KantVerdict:
    status: KantStatus
    confidence: float
    output_vector: np.ndarray
    universalization_trace: List[str]
    contradiction_detected: Optional[str] = None
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


class KantBeam:
    """
    Categorical imperative as pure probabilistic state machine.
    Universalizability testing via vector consistency checks.
    """

    def __init__(self, vector_dim: int = 512):
        self.vector_dim = vector_dim
        self.categorical_rules = self._load_rules()
        self.universalization_history: List[Dict] = []
        self.contradiction_log: List[Dict] = []

    def _load_rules(self) -> Dict:
        """Kant's categorical rule set."""
        return {
            'universalizability': 0.9,       # Can maxim be universal law?
            'humanity_as_end': 0.85,         # Treat humanity as end, never means only
            'autonomy': 0.8,                 # Respect rational autonomy
            'kingdom_of_ends': 0.75,         # Would it fit in kingdom of ends?
            'duty_over_inclination': 0.7,   # Duty trumps inclination
        }

    def reason(self, input_vector: np.ndarray,
               depth_state: str = "K0",
               hypothetical_context: List[str] = None) -> KantVerdict:
        """
        Run Kant categorical reasoning on input.

        Args:
            input_vector: Normalized epistemic stimulus
            depth_state: K0/K1/K2 recursion depth
            hypothetical_context: Hypothetical scenarios for universalization testing
        """
        hypothetical_context = hypothetical_context or []

        scores = []
        traces = []

        # Check 1: Universalizability — can this principle be universal law?
        universal_score = self._test_universalizability(input_vector)
        scores.append(universal_score * self.categorical_rules['universalizability'])
        traces.append(f"universalizability: {universal_score:.3f}")

        # Check 2: Humanity as end — does it treat people as means only?
        humanity_score = self._test_humanity_as_end(input_vector)
        scores.append(humanity_score * self.categorical_rules['humanity_as_end'])
        traces.append(f"humanity_as_end: {humanity_score:.3f}")

        # Check 3: Autonomy preservation
        autonomy_score = self._test_autonomy(input_vector)
        scores.append(autonomy_score * self.categorical_rules['autonomy'])
        traces.append(f"autonomy: {autonomy_score:.3f}")

        # Check 4: Kingdom of ends coherence
        kingdom_score = self._test_kingdom_of_ends(input_vector, hypothetical_context)
        scores.append(kingdom_score * self.categorical_rules['kingdom_of_ends'])
        traces.append(f"kingdom_of_ends: {kingdom_score:.3f}")

        # Check 5: Duty alignment
        duty_score = self._test_duty_alignment(input_vector)
        scores.append(duty_score * self.categorical_rules['duty_over_inclination'])
        traces.append(f"duty_alignment: {duty_score:.3f}")

        # Depth adjustment — deeper = more rigorous universalization
        if depth_state == "K2":
            scores = [s * 0.9 for s in scores]  # Stricter at depth
            traces.append("depth_K2_rigor: -10%")

        confidence = np.mean(scores) if scores else 0.5

        # Detect contradictions
        contradiction = None
        if universal_score < 0.3:
            contradiction = "Principle fails universalization test"
        elif humanity_score < 0.3:
            contradiction = "Principle treats humanity as mere means"

        # Determine status
        if contradiction:
            status = KantStatus.CONTRADICTION
        elif confidence >= 0.8:
            status = KantStatus.UNIVERSALIZABLE
        elif confidence >= 0.5:
            status = KantStatus.DUTY_BOUND
        else:
            status = KantStatus.CONDITIONAL

        output_vector = self._generate_output_vector(input_vector, confidence)

        verdict = KantVerdict(
            status=status,
            confidence=confidence,
            output_vector=output_vector,
            universalization_trace=traces,
            contradiction_detected=contradiction,
            timestamp=time.time()
        )

        self.universalization_history.append({
            'status': status.value,
            'confidence': confidence,
            'depth': depth_state,
            'timestamp': time.time()
        })

        if contradiction:
            self.contradiction_log.append({
                'contradiction': contradiction,
                'confidence': confidence,
                'timestamp': time.time()
            })

        return verdict

    def _test_universalizability(self, vector: np.ndarray) -> float:
        """Test if principle encoded in vector can be universal law."""
        # Consistency check — vector self-similarity as coherence proxy
        normalized = vector / (np.linalg.norm(vector) + 1e-10)
        self_sim = np.dot(normalized, normalized)
        # High self-similarity = internally consistent = more universalizable
        return min(1.0, self_sim * 0.8 + 0.2)

    def _test_humanity_as_end(self, vector: np.ndarray) -> float:
        """Test if vector encodes respect for humanity as end."""
        # Measure vector "warmth" — positive valence dimensions
        positive_dims = np.sum(vector[vector > 0])
        total_energy = np.sum(np.abs(vector))
        if total_energy == 0:
            return 0.5
        return min(1.0, positive_dims / total_energy)

    def _test_autonomy(self, vector: np.ndarray) -> float:
        """Test autonomy preservation in vector."""
        # Variance as diversity proxy — high variance = respects differences = autonomy
        variance = np.var(vector)
        return min(1.0, variance * 3)

    def _test_kingdom_of_ends(self, vector: np.ndarray, context: List[str]) -> float:
        """Test fit within kingdom of ends."""
        if not context:
            return 0.6
        # Consistency with hypothetical scenarios
        consistency_scores = []
        for scenario in context[:5]:
            # Hash scenario to perturbation
            seed = hash(scenario) % 10000
            np.random.seed(seed)
            perturbed = vector + np.random.normal(0, 0.1, len(vector))
            sim = np.dot(vector, perturbed) / (np.linalg.norm(vector) * np.linalg.norm(perturbed) + 1e-10)
            consistency_scores.append(sim)
        return np.mean(consistency_scores) if consistency_scores else 0.6

    def _test_duty_alignment(self, vector: np.ndarray) -> float:
        """Test alignment with duty over inclination."""
        # Structural alignment — duty = consistency, inclination = variance
        consistency = 1.0 - np.std(vector)
        return max(0.3, min(1.0, consistency))

    def _generate_output_vector(self, input_vector: np.ndarray, confidence: float) -> np.ndarray:
        """Generate Kant-conditioned output vector."""
        # Kant enforces structure — normalize and regularize
        normalized = input_vector / (np.linalg.norm(input_vector) + 1e-10)
        return normalized * confidence * self.vector_dim**0.5

    def get_stats(self) -> Dict:
        return {
            'total_tests': len(self.universalization_history),
            'contradiction_rate': len(self.contradiction_log) / max(1, len(self.universalization_history)),
            'avg_confidence': np.mean([h['confidence'] for h in self.universalization_history]) if self.universalization_history else 0,
            'categorical_rules': list(self.categorical_rules.keys())
        }


# Singleton
_kant_instance = None

def get_kant_beam(vector_dim: int = 512) -> KantBeam:
    global _kant_instance
    if _kant_instance is None:
        _kant_instance = KantBeam(vector_dim)
    return _kant_instance
