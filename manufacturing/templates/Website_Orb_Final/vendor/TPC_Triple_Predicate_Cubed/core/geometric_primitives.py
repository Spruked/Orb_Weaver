
# core/geometric_primitives.py - Phasor-based geometric signatures
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
import math

PHI = (1 + np.sqrt(5)) / 2  # Golden ratio

@dataclass
class GlyphSignature:
    """Phasor-derived coordinate vector in 18D space field"""
    coordinates: np.ndarray  # 18-dimensional vector
    certainty: float         # 0.0 to 0.95 (hard cap)
    vivacity: float         # Energy level (0-1000)
    origin: str             # Source identifier
    
    def __post_init__(self):
        self.coordinates = np.asarray(self.coordinates, dtype=float).reshape(-1)
        if len(self.coordinates) != 18:
            raise ValueError("Glyph signatures must be 18-dimensional")
        if not np.all(np.isfinite(self.coordinates)):
            raise ValueError("Glyph signatures must contain only finite coordinates")
        self.certainty = float(np.clip(self.certainty, 0.0, 0.95))  # Hard cap per ECM
        self.vivacity = max(0.0, float(self.vivacity))
    
    @classmethod
    def from_stimulus(cls, stimulus: np.ndarray, origin: str = "unknown") -> "GlyphSignature":
        """Create a deterministic, structure-preserving 18D signature."""
        raw = np.asarray(stimulus, dtype=float).reshape(-1)
        if raw.size < 18:
            padded = np.pad(raw, (0, 18 - raw.size))
        else:
            padded = raw[:18].copy()

        if not np.all(np.isfinite(padded)):
            raise ValueError("Stimulus must contain only finite values")

        magnitude = np.linalg.norm(padded)
        if magnitude < 1e-12:
            return cls(
                coordinates=np.zeros(18),
                certainty=0.0,
                vivacity=800.0,
                origin=origin
            )

        direction = padded / magnitude

        centered = padded - np.mean(padded)
        contrast_norm = np.linalg.norm(centered)
        contrast = centered / contrast_norm if contrast_norm > 1e-12 else np.zeros(18)

        indices = np.arange(18, dtype=float)
        phases = 2 * np.pi * ((indices + 1) / PHI % 1.0)
        phase_mix = direction * np.cos(phases) + np.roll(direction, 1) * np.sin(phases)

        scale_anchor = np.zeros(18)
        scale_anchor[0] = np.tanh(magnitude / np.sqrt(18))

        coords = (
            0.65 * direction
            + 0.20 * phase_mix
            + 0.10 * contrast
            + 0.05 * scale_anchor
        )

        coord_norm = np.linalg.norm(coords)
        if coord_norm > 1e-12:
            coords = coords / coord_norm

        probs = np.abs(padded) / (np.sum(np.abs(padded)) + 1e-10)
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        max_entropy = np.log2(18)
        structure = 1 - entropy / max_entropy
        signal_strength = np.tanh(magnitude / np.sqrt(18))
        certainty = (0.55 * structure + 0.45 * signal_strength) * 0.95
        
        return cls(
            coordinates=coords,
            certainty=certainty,
            vivacity=800.0,  # Start high
            origin=origin
        )
    
    def geometric_distance(self, other: "GlyphSignature") -> float:
        """Cosine distance in geometric space (confidence score)"""
        norm_self = np.linalg.norm(self.coordinates)
        norm_other = np.linalg.norm(other.coordinates)
        if norm_self == 0 or norm_other == 0:
            return 1.0
        cosine_sim = np.dot(self.coordinates, other.coordinates) / (norm_self * norm_other)
        cosine_sim = float(np.clip(cosine_sim, -1.0, 1.0))
        return 1 - cosine_sim  # Distance = 1 - similarity
    
    def decay_vivacity(self, amount: float = 1.0):
        """Sovereign forgetting via vivacity decay"""
        self.vivacity -= amount
        if self.vivacity < 0:
            self.vivacity = 0


class SpaceField:
    """HLSF: 18-dimensional traversal environment with active working memory"""
    
    VIVACITY_CUTTER_TRIGGER = 700
    VIVACITY_CUTTER_RELEASE = 520
    
    def __init__(self, max_nodes: int = 10000):
        self.nodes: List[GlyphSignature] = []
        self.max_nodes = max_nodes
        self.edge_cutter_active = False
        self.dimensions = 18
        
    def insert(self, signature: GlyphSignature):
        """Insert with edge-cutter hysteresis"""
        self.nodes.append(signature)
        
        # Trigger vivacity-based pruning
        if len(self.nodes) > self.max_nodes * 0.8 and not self.edge_cutter_active:
            self.edge_cutter_active = True
            self._prune_low_vivacity()
        elif len(self.nodes) < self.max_nodes * 0.5 and self.edge_cutter_active:
            self.edge_cutter_active = False
            
    def _prune_low_vivacity(self):
        """Sovereign forgetting - remove nodes below threshold"""
        self.nodes = [n for n in self.nodes if n.vivacity > self.VIVACITY_CUTTER_RELEASE]
        
    def traverse(self, query: GlyphSignature, top_k: int = 5) -> List[Tuple[GlyphSignature, float]]:
        """Find nearest neighbors by geometric distance"""
        distances = [(node, query.geometric_distance(node)) for node in self.nodes]
        distances.sort(key=lambda x: x[1])
        return distances[:top_k]
    
    def global_decay(self):
        """Apply vivacity decay to all nodes"""
        for node in self.nodes:
            node.decay_vivacity(0.1)


print("[OK] Geometric primitives and HLSF implemented")
print(f"  - Golden ratio (PHI): {PHI:.6f}")
print(f"  - Dimensions: 18")
print(f"  - Vivacity hysteresis: {SpaceField.VIVACITY_CUTTER_TRIGGER}/{SpaceField.VIVACITY_CUTTER_RELEASE}")
