"""
Spinoza Beam - Geometric Determinism
Functional role: Reduces claims to definitions, axioms, and demonstrable propositions.
Grants full confidence only if derivable through clear chain of logical demonstration.
Demands necessity rather than plausibility — proof-based confidence.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time


class SpinozaStatus(Enum):
    DEMONSTRATED = "demonstrated"
    PROBABLE = "probable"
    INSUFFICIENT_PROOF = "insufficient_proof"
    CONTRADICTION = "contradiction"


@dataclass
class SpinozaVerdict:
    status: SpinozaStatus
    confidence: float
    output_vector: np.ndarray
    proof_trace: List[str]
    necessity_score: float
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


class SpinozaBeam:
    """
    Geometric determinism as pure probabilistic state machine.
    Necessity through logical demonstration encoded as vector constraints.
    """

    def __init__(self, vector_dim: int = 512):
        self.vector_dim = vector_dim
        self.geometric_rules = self._load_rules()
        self.demonstration_history: List[Dict] = []
        self.insufficient_log: List[Dict] = []

    def _load_rules(self) -> Dict:
        """Spinoza's geometric rule set."""
        return {
            'necessity': 0.95,               # Must follow necessarily from axioms
            'axiomatic_grounding': 0.9,      # Must trace to definitions/axioms
            'causal_chain': 0.85,          # Causation = logical implication
            'substance_unity': 0.7,         # One substance, infinite attributes
            'adequate_ideas': 0.8,          # Adequate ideas = true ideas
            'conatus': 0.6,                 # Striving to persevere in being
        }

    def reason(self, input_vector: np.ndarray,
               depth_state: str = "K0",
               axiom_set: List[str] = None) -> SpinozaVerdict:
        """
        Run Spinoza geometric determinism on input.

        Args:
            input_vector: Normalized epistemic stimulus
            depth_state: K0/K1/K2 recursion depth
            axiom_set: Available axioms/definitions for demonstration
        """
        axiom_set = axiom_set or []

        scores = []
        traces = []

        # Check 1: Necessity — does it follow necessarily?
        necessity_score = self._test_necessity(input_vector)
        scores.append(necessity_score * self.geometric_rules['necessity'])
        traces.append(f"necessity: {necessity_score:.3f}")

        # Check 2: Axiomatic grounding
        axiom_score = self._test_axiomatic_grounding(input_vector, axiom_set)
        scores.append(axiom_score * self.geometric_rules['axiomatic_grounding'])
        traces.append(f"axiomatic_grounding: {axiom_score:.3f}")

        # Check 3: Causal chain completeness
        causal_score = self._test_causal_chain(input_vector)
        scores.append(causal_score * self.geometric_rules['causal_chain'])
        traces.append(f"causal_chain: {causal_score:.3f}")

        # Check 4: Substance unity — internal consistency
        unity_score = self._test_substance_unity(input_vector)
        scores.append(unity_score * self.geometric_rules['substance_unity'])
        traces.append(f"substance_unity: {unity_score:.3f}")

        # Check 5: Adequate ideas — clarity and distinctness
        adequate_score = self._test_adequate_ideas(input_vector)
        scores.append(adequate_score * self.geometric_rules['adequate_ideas'])
        traces.append(f"adequate_ideas: {adequate_score:.3f}")

        # Depth adjustment — Spinoza demands more proof at depth
        if depth_state == "K2":
            scores = [s * 0.88 for s in scores]
            traces.append("depth_K2_necessity_rigor: -12%")

        confidence = np.mean(scores) if scores else 0.5
        necessity_score = necessity_score

        # Determine status
        if necessity_score >= 0.9 and axiom_score >= 0.8:
            status = SpinozaStatus.DEMONSTRATED
        elif confidence >= 0.6:
            status = SpinozaStatus.PROBABLE
        elif confidence >= 0.3:
            status = SpinozaStatus.INSUFFICIENT_PROOF
        else:
            status = SpinozaStatus.CONTRADICTION

        output_vector = self._generate_output_vector(input_vector, confidence)

        verdict = SpinozaVerdict(
            status=status,
            confidence=confidence,
            output_vector=output_vector,
            proof_trace=traces,
            necessity_score=necessity_score,
            timestamp=time.time()
        )

        self.demonstration_history.append({
            'status': status.value,
            'confidence': confidence,
            'necessity': necessity_score,
            'depth': depth_state,
            'timestamp': time.time()
        })

        if status == SpinozaStatus.INSUFFICIENT_PROOF:
            self.insufficient_log.append({
                'confidence': confidence,
                'traces': traces,
                'timestamp': time.time()
            })

        return verdict

    def _test_necessity(self, vector: np.ndarray) -> float:
        """Test if conclusion follows necessarily from premises."""
        # Deterministic structure — low entropy = necessity
        normalized = np.abs(vector) / (np.sum(np.abs(vector)) + 1e-10)
        entropy = -np.sum(normalized * np.log2(normalized + 1e-10))
        max_entropy = np.log2(len(vector))
        necessity = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 1.0
        return max(0.0, min(1.0, necessity))

    def _test_axiomatic_grounding(self, vector: np.ndarray, axioms: List[str]) -> float:
        """Test traceability to axioms/definitions."""
        if not axioms:
            return 0.4  # No axioms = weak grounding
        # More axioms = better grounding potential
        axiom_coverage = min(1.0, len(axioms) / 20)
        # Vector sparsity as grounding proxy — axioms = foundation
        sparsity = np.count_nonzero(vector) / len(vector)
        grounding = axiom_coverage * 0.5 + (1 - sparsity) * 0.5
        return min(1.0, grounding)

    def _test_causal_chain(self, vector: np.ndarray) -> float:
        """Test completeness of causal chain."""
        # Smooth transitions between dimensions = complete chain
        diffs = np.diff(vector)
        smoothness = 1.0 - np.std(diffs)
        return max(0.0, min(1.0, smoothness))

    def _test_substance_unity(self, vector: np.ndarray) -> float:
        """Test internal consistency (one substance = one coherent vector)."""
        # Self-coherence — vector should not contradict itself
        sign_changes = np.sum(np.diff(np.sign(vector)) != 0)
        max_changes = len(vector) - 1
        unity = 1.0 - (sign_changes / max_changes) if max_changes > 0 else 1.0
        return max(0.0, min(1.0, unity))

    def _test_adequate_ideas(self, vector: np.ndarray) -> float:
        """Test clarity and distinctness (adequate ideas)."""
        # Clear = high magnitude, distinct = well-separated peaks
        magnitude = np.linalg.norm(vector)
        peaks = len(np.where(np.diff(np.sign(np.diff(vector))))[0])
        clarity = min(1.0, magnitude / 10)
        distinctness = 1.0 - min(1.0, peaks / len(vector))
        return (clarity + distinctness) / 2

    def _generate_output_vector(self, input_vector: np.ndarray, confidence: float) -> np.ndarray:
        """Generate Spinoza-conditioned output vector."""
        # Spinoza demands geometric structure — project onto deterministic subspace
        # Use SVD-like approach: keep principal components
        u, s, vh = np.linalg.svd(input_vector.reshape(1, -1), full_matrices=False)
        # Keep top components proportional to confidence
        k = max(1, int(confidence * len(s)))
        s_truncated = np.zeros_like(s)
        s_truncated[:k] = s[:k]
        reconstructed = (u * s_truncated) @ vh
        return reconstructed.flatten()

    def get_stats(self) -> Dict:
        return {
            'total_tests': len(self.demonstration_history),
            'insufficient_rate': len(self.insufficient_log) / max(1, len(self.demonstration_history)),
            'avg_confidence': np.mean([h['confidence'] for h in self.demonstration_history]) if self.demonstration_history else 0,
            'avg_necessity': np.mean([h['necessity'] for h in self.demonstration_history]) if self.demonstration_history else 0,
            'geometric_rules': list(self.geometric_rules.keys())
        }


# Singleton
_spinoza_instance = None

def get_spinoza_beam(vector_dim: int = 512) -> SpinozaBeam:
    global _spinoza_instance
    if _spinoza_instance is None:
        _spinoza_instance = SpinozaBeam(vector_dim)
    return _spinoza_instance
