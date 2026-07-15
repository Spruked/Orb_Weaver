"""
Geometric Glyph Signatures
Phasor-derived coordinate vectors in the space field's dimensional geometry.
Uses complex phasor math with golden-ratio phase damping.

Why geometric over hash-based:
- Hashes match or they don't — one bit difference and retrieval fails entirely
- Geometric signatures give proximity as a feature — near matches carry weighted partial retrieval
- Distance in geometric space IS the confidence score — no separate calculation
- Hash signatures would be a foreign object in a geometrically coherent system
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import hashlib
import time


# Golden ratio for phase damping
PHI = (1 + np.sqrt(5)) / 2


@dataclass
class GlyphSignature:
    """A geometric glyph signature in phasor coordinate space."""
    coordinates: np.ndarray          # Phasor-derived coordinate vector
    dimensions: int                   # Number of dimensions
    certainty: float                  # Certainty that generated this signature
    timestamp: float                  # Creation time
    source: str                     # Source module

    @property
    def magnitude(self) -> float:
        return np.linalg.norm(self.coordinates)

    @property
    def phase_vector(self) -> np.ndarray:
        """Extract phase component."""
        return np.angle(self.coordinates.astype(np.complex128))


class GlyphSignatureEngine:
    """
    Generates and manages geometric glyph signatures.
    Uses phasor math with golden-ratio phase damping for geometric coherence.
    """

    def __init__(self, dimensions: int = 18):
        self.dimensions = dimensions
        self.phi = PHI
        self.signature_cache: Dict[str, GlyphSignature] = {}
        self.retrieval_stats = {'exact': 0, 'near': 0, 'distant': 0, 'orthogonal': 0}

    def generate(self, input_vector: np.ndarray, certainty: float = 0.5,
                 source: str = "unknown") -> GlyphSignature:
        """
        Generate a geometric glyph signature from input vector.

        Uses phasor transformation:
        1. Map input to complex phasor space
        2. Apply golden-ratio phase damping
        3. Project to geometric coordinate space
        """
        # Normalize input
        normalized = input_vector / (np.linalg.norm(input_vector) + 1e-10)

        # Pad or truncate to target dimensions
        if len(normalized) < self.dimensions:
            padded = np.zeros(self.dimensions)
            padded[:len(normalized)] = normalized
            normalized = padded
        elif len(normalized) > self.dimensions:
            normalized = normalized[:self.dimensions]

        # Phasor transformation: map to complex unit circle
        angles = normalized * 2 * np.pi
        phasors = np.exp(1j * angles)

        # Golden-ratio phase damping
        damped = self._apply_phi_damping(phasors)

        # Project to geometric coordinates (real part = x, imag part = y equivalent)
        coordinates = np.concatenate([
            np.real(damped),
            np.imag(damped)
        ])

        # Normalize final coordinates
        coordinates = coordinates / (np.linalg.norm(coordinates) + 1e-10)

        sig = GlyphSignature(
            coordinates=coordinates,
            dimensions=self.dimensions,
            certainty=certainty,
            timestamp=time.time(),
            source=source
        )

        # Cache
        sig_id = self._hash_signature(sig)
        self.signature_cache[sig_id] = sig

        return sig

    def _apply_phi_damping(self, phasors: np.ndarray) -> np.ndarray:
        """Apply golden-ratio phase damping to phasor array."""
        n = len(phasors)
        damped = np.zeros(n, dtype=np.complex128)

        for i in range(n):
            # Phase damping factor based on golden ratio
            damping = np.exp(-i / (self.phi * n))
            # Apply to both magnitude and phase
            damped[i] = phasors[i] * damping * np.exp(1j * i * 2 * np.pi / self.phi)

        return damped

    def _hash_signature(self, sig: GlyphSignature) -> str:
        """Create deterministic hash from signature coordinates."""
        coord_bytes = sig.coordinates.tobytes()
        return hashlib.sha256(coord_bytes).hexdigest()[:16]

    def compare(self, sig_a: GlyphSignature, sig_b: GlyphSignature) -> float:
        """
        Compare two signatures. Returns distance in geometric space.
        Distance IS the confidence score.
        """
        # Cosine similarity between coordinate vectors
        dot = np.dot(sig_a.coordinates, sig_b.coordinates)
        norm_a = np.linalg.norm(sig_a.coordinates)
        norm_b = np.linalg.norm(sig_b.coordinates)

        similarity = dot / (norm_a * norm_b + 1e-10)
        distance = 1.0 - similarity

        return distance

    def classify_retrieval(self, distance: float) -> str:
        """
        Classify retrieval based on distance:
        - Known signature → exact vault retrieval
        - Near signature → weighted partial retrieval + confidence score
        - Distant signature → novel input, triggers philosopher recursion
        - Orthogonal → genuinely unknown, ECM escalation
        """
        if distance < 0.05:
            self.retrieval_stats['exact'] += 1
            return "exact"
        elif distance < 0.3:
            self.retrieval_stats['near'] += 1
            return "near"
        elif distance < 0.7:
            self.retrieval_stats['distant'] += 1
            return "distant"
        else:
            self.retrieval_stats['orthogonal'] += 1
            return "orthogonal"

    def get_stats(self) -> Dict:
        return {
            'dimensions': self.dimensions,
            'phi': self.phi,
            'cached_signatures': len(self.signature_cache),
            'retrieval_stats': self.retrieval_stats.copy()
        }


# Singleton
_glyph_engine = None

def get_glyph_engine(dimensions: int = 18) -> GlyphSignatureEngine:
    global _glyph_engine
    if _glyph_engine is None:
        _glyph_engine = GlyphSignatureEngine(dimensions)
    return _glyph_engine
