from __future__ import annotations

from typing import List, Tuple

import numpy as np
import torch

from .space_field import (
    CoherenceState,
    CubeTensorState,
    DiffusionField,
    SpaceFieldCognition,
    SpaceFieldConfig,
)


class EpistemicGravityField:
    """
    TPC-compatible entry point for the cloned Epistemic_Gravity_Field repo.
    The full SpaceFieldCognition substrate is retained and exposed while the
    legacy geometric retrieval methods remain available to the pipeline.
    """

    def __init__(
        self,
        space_field=None,
        device: str = "cpu",
        cognition: SpaceFieldCognition | None = None,
    ):
        self.space_field = space_field
        self.cognition = cognition or SpaceFieldCognition(device=device)
        self.gravity_constant = 1.0

    def calculate_gravity_well(self, signature) -> np.ndarray:
        mass = float(signature.certainty) ** 2
        return np.asarray(signature.coordinates, dtype=float) * mass * self.gravity_constant

    def attract_similar(self, query, candidates: List) -> List[Tuple[object, float]]:
        scored = []
        for candidate in candidates:
            distance = query.geometric_distance(candidate)
            gravity = self.calculate_gravity_well(candidate)
            projection = np.dot(query.coordinates, gravity) / (np.linalg.norm(gravity) + 1e-10)
            effective_distance = max(0.0, distance * (1 - 0.3 * projection))
            scored.append((candidate, effective_distance))

        scored.sort(key=lambda item: item[1])
        return scored

    def broadcast_signature(self, signature):
        signal = self._signature_to_signal(signature)
        self.cognition.broadcast_to_field(signal)
        return signal

    def step(self, steps: int = 1):
        for _ in range(max(0, steps)):
            self.cognition.step()

    def get_certainty_gradient(self, position: np.ndarray) -> np.ndarray:
        if self.space_field is None:
            return np.zeros(18)

        try:
            from core.geometric_primitives import GlyphSignature
        except ImportError:
            from ..core.geometric_primitives import GlyphSignature

        nearby = self.space_field.traverse(
            GlyphSignature(position, 0.5, 500, "gradient_query"),
            top_k=5,
        )
        if not nearby:
            return np.zeros(18)

        gradient = np.zeros(18)
        for node, distance in nearby:
            direction = node.coordinates - position
            if distance > 0:
                gradient += direction * node.certainty / distance

        return gradient / (np.linalg.norm(gradient) + 1e-10)

    def get_field_stats(self) -> dict:
        return self.cognition.get_field_stats()

    def _signature_to_signal(self, signature):
        dim = self.cognition.config.DIM
        channels = self.cognition.config.DIFFUSION_CHANNELS
        signal = torch.zeros(dim, dim, dim, channels, device=self.cognition.device)
        coords = np.asarray(signature.coordinates, dtype=float)
        values = [float(np.mean(chunk)) for chunk in np.array_split(coords, channels)]
        center = dim // 2
        signal[center, center, center, :] = torch.tensor(
            values,
            dtype=signal.dtype,
            device=self.cognition.device,
        ) * float(signature.certainty)
        return signal


__all__ = [
    "CoherenceState",
    "CubeTensorState",
    "DiffusionField",
    "EpistemicGravityField",
    "SpaceFieldCognition",
    "SpaceFieldConfig",
]
