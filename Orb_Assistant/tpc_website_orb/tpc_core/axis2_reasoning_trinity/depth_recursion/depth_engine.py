"""
Depth Recursion: K0 -> K1 -> K2
Extracted from Cali X One pattern.
Gives philosopher loops layered depth.
Three levels prevent flat softmax loops from settling into false attractors.
"""

import numpy as np
from typing import Callable, List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class DepthLevel(Enum):
    K0 = 0  # Surface: Direct stimulus response
    K1 = 1  # Abstraction: Pattern extraction from K0 output
    K2 = 2  # Deep: Meta-reasoning about K1 abstractions


@dataclass
class DepthState:
    """State at a given depth level."""
    level: DepthLevel
    input_vector: np.ndarray
    output_vector: np.ndarray
    confidence: float
    abstraction_score: float
    recursion_depth: int = 0


class DepthRecursionEngine:
    """
    K0 -> K1 -> K2 depth recursion mechanic.
    Each level's output becomes the next level's input.
    """

    def __init__(self, feature_dim: int = 512):
        self.feature_dim = feature_dim
        self.abstraction_matrix_k0_k1 = np.random.randn(feature_dim, feature_dim) * 0.1
        self.abstraction_matrix_k1_k2 = np.random.randn(feature_dim, feature_dim) * 0.05

        # Orthogonalize to prevent information collapse
        self._orthogonalize_matrices()

    def _orthogonalize_matrices(self):
        """Ensure abstraction matrices preserve information."""
        # Simple orthogonalization via QR decomposition
        q, _ = np.linalg.qr(self.abstraction_matrix_k0_k1)
        self.abstraction_matrix_k0_k1 = q

        q, _ = np.linalg.qr(self.abstraction_matrix_k1_k2)
        self.abstraction_matrix_k1_k2 = q

    def k0_surface(self, stimulus: np.ndarray, 
                   philosopher_processors: List[Callable]) -> DepthState:
        """
        K0: Surface level processing.
        Direct response to normalized stimulus.
        All philosopher beams receive the same input.
        """
        # Run all philosopher processors in parallel
        k0_outputs = []
        for processor in philosopher_processors:
            output = processor(stimulus, depth=0)
            k0_outputs.append(output)

        # Average outputs (equal weight at K0)
        combined = np.mean(k0_outputs, axis=0)
        confidence = np.std(k0_outputs)  # Low std = high confidence

        return DepthState(
            level=DepthLevel.K0,
            input_vector=stimulus,
            output_vector=combined,
            confidence=1.0 - confidence,
            abstraction_score=0.0
        )

    def k1_abstraction(self, k0_state: DepthState,
                       philosopher_processors: List[Callable]) -> DepthState:
        """
        K1: Abstraction level.
        K0 output becomes input for pattern extraction.
        """
        # Transform through abstraction matrix
        abstracted_input = np.dot(self.abstraction_matrix_k0_k1, k0_state.output_vector)

        # Run philosophers on abstracted input
        k1_outputs = []
        for processor in philosopher_processors:
            output = processor(abstracted_input, depth=1)
            k1_outputs.append(output)

        combined = np.mean(k1_outputs, axis=0)

        # Measure abstraction: how much did we diverge from K0?
        abstraction_score = np.linalg.norm(combined - k0_state.output_vector)
        confidence = np.std(k1_outputs)

        return DepthState(
            level=DepthLevel.K1,
            input_vector=abstracted_input,
            output_vector=combined,
            confidence=1.0 - confidence,
            abstraction_score=abstraction_score
        )

    def k2_deep(self, k1_state: DepthState,
                  philosopher_processors: List[Callable]) -> DepthState:
        """
        K2: Deep meta-reasoning.
        K1 abstraction becomes input for meta-reasoning.
        """
        # Deep transformation
        deep_input = np.dot(self.abstraction_matrix_k1_k2, k1_state.output_vector)

        # Run philosophers on deep input
        k2_outputs = []
        for processor in philosopher_processors:
            output = processor(deep_input, depth=2)
            k2_outputs.append(output)

        combined = np.mean(k2_outputs, axis=0)

        # Meta-reasoning score
        meta_score = np.linalg.norm(combined - k1_state.output_vector)
        confidence = np.std(k2_outputs)

        return DepthState(
            level=DepthLevel.K2,
            input_vector=deep_input,
            output_vector=combined,
            confidence=1.0 - confidence,
            abstraction_score=meta_score
        )

    def recurse(self, stimulus: np.ndarray,
                philosopher_processors: List[Callable]) -> Dict[DepthLevel, DepthState]:
        """
        Full K0 -> K1 -> K2 recursion pipeline.
        Returns states at all three depth levels.
        """
        # K0: Surface
        k0 = self.k0_surface(stimulus, philosopher_processors)

        # K1: Abstraction
        k1 = self.k1_abstraction(k0, philosopher_processors)

        # K2: Deep
        k2 = self.k2_deep(k1, philosopher_processors)

        return {
            DepthLevel.K0: k0,
            DepthLevel.K1: k1,
            DepthLevel.K2: k2
        }

    def detect_false_attractor(self, states: Dict[DepthLevel, DepthState]) -> bool:
        """
        Detect if the recursion settled into a false attractor.
        True attractors show increasing abstraction across depths.
        """
        k0_k1_diff = np.linalg.norm(states[DepthLevel.K1].output_vector - 
                                     states[DepthLevel.K0].output_vector)
        k1_k2_diff = np.linalg.norm(states[DepthLevel.K2].output_vector - 
                                     states[DepthLevel.K1].output_vector)

        # If differences are too small, we may be in a false attractor
        # (all depths producing same output)
        if k0_k1_diff < 0.01 and k1_k2_diff < 0.01:
            return True

        return False

    def synthesize_depth_output(self, states: Dict[DepthLevel, DepthState],
                                weights: List[float] = None) -> np.ndarray:
        """
        Synthesize final output from all depth levels.
        Default: weighted combination favoring deeper levels.
        """
        if weights is None:
            weights = [0.2, 0.3, 0.5]  # K0, K1, K2

        outputs = [
            states[DepthLevel.K0].output_vector * weights[0],
            states[DepthLevel.K1].output_vector * weights[1],
            states[DepthLevel.K2].output_vector * weights[2]
        ]

        return np.sum(outputs, axis=0)
