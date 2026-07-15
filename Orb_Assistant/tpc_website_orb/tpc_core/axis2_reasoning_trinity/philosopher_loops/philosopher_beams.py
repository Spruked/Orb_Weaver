"""
Four Philosopher ML Recursion Loops
Hume, Kant, Locke, and Spinoza run as pure probabilistic state machines.
No LLM, no transformer attention.
Softmax probability loops operating on their respective rule sets.
They run simultaneously via MultiBeamRunner.
Cross-influence via ShadowPropagation carries confidence metrics only — not logic.
No philosopher can contaminate another's reasoning.
"""

import numpy as np
from typing import Dict, List, Tuple, Callable, Optional
from dataclasses import dataclass
from enum import Enum
import time
from abc import ABC, abstractmethod


class BeamStatus(Enum):
    CONVERGED = "converged"
    DIVERGED = "diverged"
    OSCILLATING = "oscillating"
    PROCESSING = "processing"


@dataclass
class PhilosopherVerdict:
    """Output from a single philosopher beam."""
    beam_name: str
    confidence: float
    output_vector: np.ndarray
    status: BeamStatus
    reasoning_trace: List[str]
    iteration_count: int
    timestamp: float


class PhilosopherBeam(ABC):
    """
    Abstract base for each philosopher beam.
    Each beam is a pure probabilistic state machine.
    """

    def __init__(self, name: str, feature_dim: int = 512):
        self.name = name
        self.feature_dim = feature_dim
        self.weight = 0.25  # Initial equal weight
        self.state = np.zeros(feature_dim)
        self.iteration_count = 0
        self.max_iterations = 100
        self.convergence_threshold = 0.001
        self.reasoning_trace: List[str] = []

    @abstractmethod
    def _rule_set(self, input_vec: np.ndarray, state: np.ndarray) -> np.ndarray:
        """
        The core rule set for this philosopher.
        Must return a new state vector.
        """
        pass

    @abstractmethod
    def _evaluate(self, state: np.ndarray) -> Tuple[float, BeamStatus]:
        """
        Evaluate the current state.
        Returns (confidence, status).
        """
        pass

    def process(self, input_vec: np.ndarray, depth: int = 0) -> np.ndarray:
        """
        Run the philosopher's softmax recursion loop.
        Returns the final output vector.
        """
        self.state = input_vec.copy()
        self.iteration_count = 0
        self.reasoning_trace = []

        prev_state = None
        oscillation_buffer = []

        for i in range(self.max_iterations):
            self.iteration_count = i

            # Apply rule set
            new_state = self._rule_set(input_vec, self.state)

            # Softmax normalization
            new_state = self._softmax(new_state)

            # Check convergence
            if prev_state is not None:
                delta = np.linalg.norm(new_state - prev_state)

                if delta < self.convergence_threshold:
                    self.reasoning_trace.append(f"Converged at iteration {i}")
                    break

                # Detect oscillation
                oscillation_buffer.append(delta)
                if len(oscillation_buffer) > 10:
                    oscillation_buffer.pop(0)
                    if self._detect_oscillation(oscillation_buffer):
                        self.reasoning_trace.append(f"Oscillation detected at iteration {i}")
                        break

            prev_state = self.state.copy()
            self.state = new_state

        return self.state

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Stable softmax."""
        exp_x = np.exp(x - np.max(x))
        return exp_x / (np.sum(exp_x) + 1e-10)

    def _detect_oscillation(self, buffer: List[float]) -> bool:
        """Detect if the system is oscillating."""
        if len(buffer) < 5:
            return False
        # Check if deltas are cycling
        diffs = [abs(buffer[i] - buffer[i-1]) for i in range(1, len(buffer))]
        return np.std(diffs) < 0.0001 and np.mean(diffs) > 0.001

    def get_verdict(self, input_vec: np.ndarray, depth: int = 0) -> PhilosopherVerdict:
        """Get full verdict with metadata."""
        output = self.process(input_vec, depth)
        confidence, status = self._evaluate(output)

        return PhilosopherVerdict(
            beam_name=self.name,
            confidence=confidence,
            output_vector=output,
            status=status,
            reasoning_trace=self.reasoning_trace.copy(),
            iteration_count=self.iteration_count,
            timestamp=time.time()
        )


class HumeBeam(PhilosopherBeam):
    """
    Hume — Empirical Skepticism
    Enforces strict empirical grounding.
    Claims admissible only if traceable to original impression/observation.
    Causal inferences treated as probabilistic, not necessary.
    """

    def __init__(self, feature_dim: int = 512):
        super().__init__("Hume", feature_dim)
        self.empirical_anchor_weight = 0.8
        self.skepticism_threshold = 0.3

    def _rule_set(self, input_vec: np.ndarray, state: np.ndarray) -> np.ndarray:
        """
        Hume's rule set: Discount claims lacking empirical anchoring.
        Treat causal inferences as probabilistic.
        """
        # Measure "empirical anchoring" via signal variance
        # High variance = rich sensory detail = more empirical
        variance = np.var(input_vec)

        # Skeptical discounting
        if variance < self.skepticism_threshold:
            # Low empirical content - heavily discount
            discount = 0.3
            self.reasoning_trace.append(f"Low empirical variance ({variance:.3f}), discounting")
        else:
            discount = 1.0
            self.reasoning_trace.append(f"Empirical variance adequate ({variance:.3f})")

        # Probabilistic causal inference (no necessary connections)
        causal_weight = 0.7  # Never claim necessity
        new_state = state * discount * causal_weight + input_vec * (1 - causal_weight)

        return new_state

    def _evaluate(self, state: np.ndarray) -> Tuple[float, BeamStatus]:
        """Hume evaluates based on empirical support."""
        variance = np.var(state)
        confidence = min(1.0, variance * 2.0)

        if confidence > 0.7:
            status = BeamStatus.CONVERGED
        elif confidence < 0.3:
            status = BeamStatus.DIVERGED
        else:
            status = BeamStatus.PROCESSING

        return confidence, status


class KantBeam(PhilosopherBeam):
    """
    Kant — Categorical Reasoning
    Evaluates whether conclusion can be universalized without contradiction.
    Tests against requirement that principles hold consistently across all cases.
    Enforces structural integrity and duty-based reasoning.
    """

    def __init__(self, feature_dim: int = 512):
        super().__init__("Kant", feature_dim)
        self.universalizability_matrix = np.eye(feature_dim) * 0.9

    def _rule_set(self, input_vec: np.ndarray, state: np.ndarray) -> np.ndarray:
        """
        Kant's rule set: Universalize the principle.
        Check for internal contradictions.
        """
        # Universalization test: apply principle to itself
        universalized = np.dot(self.universalizability_matrix, state)

        # Check for contradiction (inconsistency in vector)
        contradiction = np.std(universalized - state)

        if contradiction > 0.5:
            # Internal contradiction found
            self.reasoning_trace.append(f"Contradiction detected ({contradiction:.3f}), rejecting")
            new_state = state * 0.1  # Heavy penalty
        else:
            self.reasoning_trace.append(f"Universalizable ({contradiction:.3f})")
            new_state = state * 0.7 + universalized * 0.3

        return new_state

    def _evaluate(self, state: np.ndarray) -> Tuple[float, BeamStatus]:
        """Kant evaluates based on structural consistency."""
        # Measure how well the state represents a universalizable principle
        consistency = 1.0 - np.std(state)
        confidence = max(0.0, consistency)

        if confidence > 0.8:
            status = BeamStatus.CONVERGED
        elif confidence < 0.4:
            status = BeamStatus.DIVERGED
        else:
            status = BeamStatus.PROCESSING

        return confidence, status


class LockeBeam(PhilosopherBeam):
    """
    Locke — Consent and Rights Reasoning
    Examines whether conclusion respects individual autonomy.
    Evaluates whether reasoning preserves rights of agents involved.
    Prevents endorsing outputs that violate rights or undermine legitimate authority.
    """

    def __init__(self, feature_dim: int = 512):
        super().__init__("Locke", feature_dim)
        self.rights_preservation_weight = 0.9
        self.autonomy_threshold = 0.5

    def _rule_set(self, input_vec: np.ndarray, state: np.ndarray) -> np.ndarray:
        """
        Locke's rule set: Check rights preservation.
        Ensure autonomy is respected.
        """
        # Measure "autonomy preservation" via vector symmetry
        # Asymmetric distributions suggest imposition on some parties
        skewness = np.mean((state - np.mean(state)) ** 3)

        if abs(skewness) > self.autonomy_threshold:
            # Asymmetric - may violate rights of some
            self.reasoning_trace.append(f"Rights asymmetry detected ({skewness:.3f}), balancing")
            # Rebalance toward center
            correction = -skewness * np.ones_like(state) * 0.3
            new_state = state + correction
        else:
            self.reasoning_trace.append(f"Rights balanced ({skewness:.3f})")
            new_state = state * self.rights_preservation_weight + input_vec * 0.1

        return new_state

    def _evaluate(self, state: np.ndarray) -> Tuple[float, BeamStatus]:
        """Locke evaluates based on rights preservation."""
        # Balanced distribution = rights respected
        balance = 1.0 - abs(np.mean(state) - 0.5) * 2
        confidence = max(0.0, balance)

        if confidence > 0.75:
            status = BeamStatus.CONVERGED
        elif confidence < 0.3:
            status = BeamStatus.DIVERGED
        else:
            status = BeamStatus.PROCESSING

        return confidence, status


class SpinozaBeam(PhilosopherBeam):
    """
    Spinoza — Geometric Determinism
    Reduces claims to definitions, axioms, demonstrable propositions.
    Grants full confidence only if derived through clear logical demonstration.
    Demands necessity, not plausibility.
    """

    def __init__(self, feature_dim: int = 512):
        super().__init__("Spinoza", feature_dim)
        self.axiom_basis = np.ones(feature_dim) / feature_dim  # Uniform axiom basis
        self.necessity_threshold = 0.9

    def _rule_set(self, input_vec: np.ndarray, state: np.ndarray) -> np.ndarray:
        """
        Spinoza's rule set: Derive from axioms.
        Demand demonstrable necessity.
        """
        # Measure how well state derives from axiom basis
        derivation = np.dot(state, self.axiom_basis)

        if derivation < self.necessity_threshold:
            # Insufficient derivation from axioms
            self.reasoning_trace.append(f"Insufficient derivation ({derivation:.3f}), demanding proof")
            # Pull toward axiom basis
            new_state = state * 0.5 + self.axiom_basis * 0.5
        else:
            self.reasoning_trace.append(f"Axiomatic derivation confirmed ({derivation:.3f})")
            new_state = state * 0.9 + input_vec * 0.1

        return new_state

    def _evaluate(self, state: np.ndarray) -> Tuple[float, BeamStatus]:
        """Spinoza evaluates based on demonstrable necessity."""
        # Necessity = closeness to derivation from axioms
        necessity = np.dot(state, self.axiom_basis)
        confidence = necessity

        if confidence > 0.85:
            status = BeamStatus.CONVERGED
        elif confidence < 0.5:
            status = BeamStatus.DIVERGED
        else:
            status = BeamStatus.PROCESSING

        return confidence, status


class ShadowPropagation:
    """
    Cross-influence between philosopher beams.
    Carries confidence metrics only — NOT logic.
    No philosopher can contaminate another's reasoning.
    """

    def __init__(self, beams: List[PhilosopherBeam]):
        self.beams = {beam.name: beam for beam in beams}
        self.shadow_weights = {name: 0.0 for name in self.beams}
        self.propagation_matrix = np.eye(len(beams)) * 0.1  # Weak coupling

    def propagate(self, verdicts: Dict[str, PhilosopherVerdict]) -> Dict[str, float]:
        """
        Propagate confidence shadows between beams.
        Returns adjusted weights for each beam.
        """
        confidences = {name: v.confidence for name, v in verdicts.items()}

        # Compute shadow influence
        beam_names = list(self.beams.keys())
        n = len(beam_names)

        shadow_adjustments = {}
        for i, name in enumerate(beam_names):
            # Sum of other beams' confidence as shadow
            shadow = sum(confidences[other] for other in beam_names if other != name)
            shadow_adjustments[name] = shadow / (n - 1) if n > 1 else 0

        return shadow_adjustments


class MultiBeamRunner:
    """
    Runs all four philosopher beams simultaneously.
    Manages parallel execution and shadow propagation.
    """

    def __init__(self, feature_dim: int = 512):
        self.beams = [
            HumeBeam(feature_dim),
            KantBeam(feature_dim),
            LockeBeam(feature_dim),
            SpinozaBeam(feature_dim)
        ]
        self.shadow_prop = ShadowPropagation(self.beams)
        self.beam_map = {beam.name: beam for beam in self.beams}

    def run_all(self, input_vec: np.ndarray, depth: int = 0) -> Dict[str, PhilosopherVerdict]:
        """
        Run all four beams on the same input.
        Returns verdicts from all beams.
        """
        verdicts = {}

        # Run each beam (in parallel in production, sequential here)
        for beam in self.beams:
            verdict = beam.get_verdict(input_vec, depth)
            verdicts[beam.name] = verdict

        # Propagate shadows
        shadows = self.shadow_prop.propagate(verdicts)

        # Adjust beam weights based on shadows
        for name, shadow in shadows.items():
            self.beam_map[name].weight = 0.25 + shadow * 0.1  # Small adjustment

        return verdicts

    def get_convergence_status(self, verdicts: Dict[str, PhilosopherVerdict]) -> Dict:
        """Analyze convergence patterns across all beams."""
        converged = sum(1 for v in verdicts.values() if v.status == BeamStatus.CONVERGED)
        diverged = sum(1 for v in verdicts.values() if v.status == BeamStatus.DIVERGED)
        oscillating = sum(1 for v in verdicts.values() if v.status == BeamStatus.OSCILLATING)

        avg_confidence = np.mean([v.confidence for v in verdicts.values()])

        return {
            'converged_count': converged,
            'diverged_count': diverged,
            'oscillating_count': oscillating,
            'average_confidence': avg_confidence,
            'consensus': converged >= 3,
            'contested': diverged >= 2
        }


# Factory
def create_philosopher_beams(feature_dim: int = 512) -> MultiBeamRunner:
    """Create and return a MultiBeamRunner with all four philosopher beams."""
    return MultiBeamRunner(feature_dim)
