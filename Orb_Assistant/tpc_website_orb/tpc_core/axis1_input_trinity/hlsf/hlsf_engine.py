"""
HLSF - High-Level Space Field
18-dimensional traversal environment. Active working memory.
Vivacity decay and sovereign forgetting via edge-cutter hysteresis.
Trigger 700, release 520.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import time
import json
from pathlib import Path


@dataclass
class SpaceNode:
    """A node in the HLSF - represents a concept/idea in the reasoning space."""
    id: str
    coordinates: np.ndarray  # 18-dimensional position
    vivacity: float = 1.0    # Activation level (0-1)
    timestamp: float = field(default_factory=time.time)
    glyph_signature: np.ndarray = None  # Geometric signature for vault retrieval
    connections: Dict[str, float] = field(default_factory=dict)  # node_id -> weight
    depth_level: int = 0  # K0=0, K1=1, K2=2
    source_beam: str = ""  # Which philosopher beam created this node

    def __post_init__(self):
        if self.glyph_signature is None:
            self.glyph_signature = self._compute_glyph()

    def _compute_glyph(self) -> np.ndarray:
        """Compute geometric glyph signature from coordinates."""
        # Phasor-derived coordinate vector with golden-ratio phase damping
        phi = (1 + np.sqrt(5)) / 2  # Golden ratio
        phases = np.exp(1j * phi * np.arange(len(self.coordinates)))
        glyph = np.fft.ifft(np.fft.fft(self.coordinates) * phases).real
        return glyph / (np.linalg.norm(glyph) + 1e-10)

    def distance_to(self, other: 'SpaceNode') -> float:
        """Geometric distance in HLSF space."""
        return np.linalg.norm(self.coordinates - other.coordinates)

    def similarity_to(self, other: 'SpaceNode') -> float:
        """Cosine similarity between nodes."""
        dot = np.dot(self.coordinates, other.coordinates)
        norm = np.linalg.norm(self.coordinates) * np.linalg.norm(other.coordinates)
        return dot / (norm + 1e-10)


class EdgeCutter:
    """
    Sovereign forgetting mechanism.
    Trigger: 700 nodes, Release: 520 nodes.
    Prunes low-vivacity nodes to prevent overcrowding.
    """

    TRIGGER_THRESHOLD = 700
    RELEASE_TARGET = 520
    DECAY_RATE = 0.001  # Per-tick vivacity decay

    def __init__(self):
        self.cut_count = 0
        self.last_cut_time = time.time()

    def should_trigger(self, node_count: int) -> bool:
        """Check if edge cutter should fire."""
        return node_count >= self.TRIGGER_THRESHOLD

    def cut(self, nodes: Dict[str, SpaceNode]) -> Dict[str, SpaceNode]:
        """
        Perform sovereign forgetting.
        Remove lowest-vivacity nodes until below release target.
        """
        if not self.should_trigger(len(nodes)):
            return nodes

        # Sort by vivacity (ascending)
        sorted_nodes = sorted(nodes.items(), key=lambda x: x[1].vivacity)

        # Keep top nodes by vivacity
        keep_count = self.RELEASE_TARGET
        pruned = dict(sorted_nodes[-keep_count:])

        self.cut_count += 1
        self.last_cut_time = time.time()

        print(f"[EdgeCutter] Cut {len(nodes) - len(pruned)} nodes. "
              f"Remaining: {len(pruned)}. Cut #{self.cut_count}")

        return pruned

    def decay_vivacity(self, nodes: Dict[str, SpaceNode]):
        """Apply time-based vivacity decay to all nodes."""
        current_time = time.time()
        for node in nodes.values():
            age = current_time - node.timestamp
            node.vivacity *= np.exp(-self.DECAY_RATE * age)


class HLSF:
    """
    High-Level Space Field - 18-dimensional reasoning environment.
    """

    DIMENSIONS = 18

    def __init__(self, persistence_path: str = None):
        self.nodes: Dict[str, SpaceNode] = {}
        self.edge_cutter = EdgeCutter()
        self.persistence_path = persistence_path
        self.node_counter = 0

        if persistence_path and Path(persistence_path).exists():
            self._load_state()

    def create_node(self, coordinates: np.ndarray = None, 
                    depth_level: int = 0,
                    source_beam: str = "",
                    vivacity: float = 1.0) -> SpaceNode:
        """Create a new node in the space field."""
        if coordinates is None:
            coordinates = np.random.randn(self.DIMENSIONS)
            coordinates = coordinates / np.linalg.norm(coordinates)

        self.node_counter += 1
        node_id = f"node_{self.node_counter}_{int(time.time() * 1000)}"

        node = SpaceNode(
            id=node_id,
            coordinates=coordinates,
            vivacity=vivacity,
            depth_level=depth_level,
            source_beam=source_beam
        )

        self.nodes[node_id] = node

        # Check edge cutter
        if self.edge_cutter.should_trigger(len(self.nodes)):
            self.nodes = self.edge_cutter.cut(self.nodes)

        return node

    def connect_nodes(self, node_a_id: str, node_b_id: str, weight: float = 1.0):
        """Create a weighted connection between two nodes."""
        if node_a_id in self.nodes and node_b_id in self.nodes:
            self.nodes[node_a_id].connections[node_b_id] = weight
            self.nodes[node_b_id].connections[node_a_id] = weight

    def find_nearest(self, coordinates: np.ndarray, k: int = 5) -> List[Tuple[SpaceNode, float]]:
        """Find k nearest nodes to given coordinates."""
        distances = []
        for node in self.nodes.values():
            dist = np.linalg.norm(node.coordinates - coordinates)
            distances.append((node, dist))

        distances.sort(key=lambda x: x[1])
        return distances[:k]

    def find_by_glyph_similarity(self, glyph: np.ndarray, threshold: float = 0.8) -> List[SpaceNode]:
        """Find nodes with similar glyph signatures."""
        matches = []
        for node in self.nodes.values():
            if node.glyph_signature is not None:
                sim = np.dot(glyph, node.glyph_signature) / (
                    np.linalg.norm(glyph) * np.linalg.norm(node.glyph_signature) + 1e-10
                )
                if sim >= threshold:
                    matches.append(node)
        return matches

    def traverse(self, start_node_id: str, depth: int = 3) -> List[SpaceNode]:
        """Breadth-first traversal from a starting node."""
        if start_node_id not in self.nodes:
            return []

        visited = {start_node_id}
        queue = [(start_node_id, 0)]
        result = [self.nodes[start_node_id]]

        while queue:
            current_id, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue

            node = self.nodes[current_id]
            for neighbor_id, weight in node.connections.items():
                if neighbor_id not in visited and weight > 0.3:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, current_depth + 1))
                    result.append(self.nodes[neighbor_id])

        return result

    def get_field_density(self, center: np.ndarray, radius: float) -> float:
        """Measure node density around a point."""
        count = 0
        for node in self.nodes.values():
            if np.linalg.norm(node.coordinates - center) < radius:
                count += 1
        return count / (len(self.nodes) + 1e-10)

    def tick(self):
        """Periodic maintenance - decay vivacity, check edge cutter."""
        self.edge_cutter.decay_vivacity(self.nodes)
        if self.edge_cutter.should_trigger(len(self.nodes)):
            self.nodes = self.edge_cutter.cut(self.nodes)

    def _save_state(self):
        """Persist HLSF state to disk."""
        if not self.persistence_path:
            return

        state = {
            'node_counter': self.node_counter,
            'nodes': {}
        }

        for node_id, node in self.nodes.items():
            state['nodes'][node_id] = {
                'coordinates': node.coordinates.tolist(),
                'vivacity': node.vivacity,
                'timestamp': node.timestamp,
                'depth_level': node.depth_level,
                'source_beam': node.source_beam,
                'connections': node.connections
            }

        Path(self.persistence_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.persistence_path, 'w') as f:
            json.dump(state, f)

    def _load_state(self):
        """Load HLSF state from disk."""
        try:
            with open(self.persistence_path, 'r') as f:
                state = json.load(f)

            self.node_counter = state.get('node_counter', 0)

            for node_id, data in state.get('nodes', {}).items():
                node = SpaceNode(
                    id=node_id,
                    coordinates=np.array(data['coordinates']),
                    vivacity=data['vivacity'],
                    timestamp=data['timestamp'],
                    depth_level=data['depth_level'],
                    source_beam=data['source_beam']
                )
                node.connections = data.get('connections', {})
                self.nodes[node_id] = node

            print(f"[HLSF] Loaded {len(self.nodes)} nodes from persistence")
        except Exception as e:
            print(f"[HLSF] Load failed: {e}")


# Singleton
_hlsf_instance = None

def get_hlsf(persistence_path: str = None) -> HLSF:
    """Get or create singleton HLSF instance."""
    global _hlsf_instance
    if _hlsf_instance is None:
        _hlsf_instance = HLSF(persistence_path)
    return _hlsf_instance
