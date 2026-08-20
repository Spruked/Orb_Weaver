from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class HLSFNode:
    """A coordinate in the High-Level Space Field."""

    n: int
    k: int
    coordinates: Tuple[float, ...]
    adjacency_value: float = 0.0
    cognitive_load: float = 1.0
    occupied_by: List[str] = field(default_factory=list)

    def recursive_adjacency(self, other: "HLSFNode") -> float:
        if self.n == 0 or self.k == 0:
            return 0.0
        base_adj = abs(self.n - other.n) * math.exp(-abs(self.k - other.k))
        return self.n * base_adj


class HLSFEngine:
    """Deterministic HLSF engine used inside the TPC-only website ORB runtime."""

    def __init__(self, dimension: int = 18):
        self.dimension = dimension
        self.field_map: Dict[str, HLSFNode] = {}
        self.cursor_position = (0.0,) * dimension
        self.pulse_frequency = 0.0
        self.max_field_density = 1000
        self.purge_trigger_threshold = 800
        self.purge_release_threshold = 650
        self.edge_cutter_threshold = self.purge_trigger_threshold
        self.purge_keep_ratio = 0.6
        self.edge_cutter_active = False
        self.hysteresis_band = self.purge_trigger_threshold - self.purge_release_threshold
        self.last_density_breach = 0

    def map_adjacency(self, stimulus: dict) -> HLSFNode:
        stimulus_key = repr(self._normalize(stimulus))
        stimulus_hash = self._stable_digest(stimulus_key)
        n_val = int(stimulus_hash[:8], 16) % self.dimension + 1
        k_val = int(stimulus_hash[8:16], 16) % 10 + 1

        coords = self._generate_coordinates(stimulus_key)
        node_id = self._node_id(n_val, k_val, coords)

        if node_id not in self.field_map:
            intensity = float(stimulus.get("intensity", 0.5))
            velocity = float(stimulus.get("velocity", 0.0))
            node = HLSFNode(
                n=n_val,
                k=k_val,
                coordinates=coords,
                cognitive_load=min(1.0 + (velocity / 5.0) + (intensity * 3.0), 10.0),
            )
            self.field_map[node_id] = node
        else:
            node = self.field_map[node_id]
            repetition_count = len(node.occupied_by)
            repetition_boost = 0.3 + 0.2 * math.log1p(repetition_count)
            intensity_boost = float(stimulus.get("intensity", 0.5)) * 1.5
            velocity_boost = float(stimulus.get("velocity", 0.0)) / 10.0
            node.cognitive_load = min(
                node.cognitive_load + repetition_boost + intensity_boost + velocity_boost,
                10.0,
            )
            if repetition_count <= 2 and node.cognitive_load < 1.5:
                node.cognitive_load = 1.5

        self._purge_if_needed(preserve_node_id=node_id, preserve_node=node)
        if node_id not in self.field_map:
            self.field_map[node_id] = node
        return self.field_map[node_id]

    def get_recursive_neighbors(self, center_node: HLSFNode, radius: int = 3) -> List[HLSFNode]:
        if len(self.field_map) > 500:
            return self._sampled_neighbors(center_node, radius, sample_size=100)

        neighbors = []
        for node in self.field_map.values():
            if node == center_node:
                continue
            adjacency = center_node.recursive_adjacency(node)
            if 0 < adjacency <= radius:
                node.adjacency_value = adjacency
                neighbors.append(node)
        neighbors.sort(key=lambda x: center_node.recursive_adjacency(x))
        return neighbors[:10]

    def calculate_thought_vector(self, nodes: List[HLSFNode]) -> Tuple[float, ...]:
        if not nodes:
            return (0.0,) * self.dimension

        vector = [0.0] * self.dimension
        total_weight = 0.0
        for node in nodes:
            weight = node.cognitive_load * (1.0 + node.adjacency_value)
            for i, coord in enumerate(node.coordinates[: self.dimension]):
                vector[i] += coord * weight
            total_weight += weight

        if total_weight > 0:
            vector = [v / total_weight for v in vector]
        return tuple(vector)

    def pulse(self) -> dict:
        self.pulse_frequency = (self.pulse_frequency + 0.1) % (2 * math.pi)
        return {
            "frequency": self.pulse_frequency,
            "field_density": len(self.field_map),
            "edge_cutter_active": self.edge_cutter_active,
        }

    def decay_vivacity(self, decay_factor: float = 0.99, floor: float = 0.5) -> None:
        for node in self.field_map.values():
            node.cognitive_load = max(node.cognitive_load * decay_factor, floor)

    def _sampled_neighbors(self, center_node: HLSFNode, radius: int, sample_size: int) -> List[HLSFNode]:
        samples = random.sample(list(self.field_map.values()), min(sample_size, len(self.field_map)))
        neighbors = []
        for node in samples:
            if node == center_node:
                continue
            adjacency = center_node.recursive_adjacency(node)
            if 0 < adjacency <= radius:
                node.adjacency_value = adjacency
                neighbors.append(node)
        return sorted(neighbors, key=lambda x: center_node.recursive_adjacency(x))[:5]

    def _generate_coordinates(self, seed: str) -> Tuple[float, ...]:
        coords = []
        for i in range(self.dimension):
            hash_val = int(self._stable_digest(f"{seed}:{i}")[:12], 16) % 1000 / 1000.0
            coords.append(hash_val * 2 - 1)
        return tuple(coords)

    def _purge_if_needed(self, preserve_node_id: str, preserve_node: HLSFNode) -> None:
        current_density = len(self.field_map)
        if self.edge_cutter_active and current_density <= self.purge_release_threshold:
            self.edge_cutter_active = False
            self.last_density_breach = 0

        should_purge = (
            current_density >= self.max_field_density
            or (not self.edge_cutter_active and current_density >= self.purge_trigger_threshold)
        )
        if not should_purge:
            return

        self.last_density_breach = current_density
        sorted_nodes = sorted(self.field_map.values(), key=lambda n: n.cognitive_load, reverse=True)
        soft_keep_cap = max(1, self.purge_release_threshold - 1)
        target_keep = min(
            max(int(self.max_field_density * self.purge_keep_ratio), 1),
            soft_keep_cap,
            len(sorted_nodes),
        )
        keep_nodes = [n for n in sorted_nodes if n.cognitive_load >= 1.5][:target_keep]
        if len(keep_nodes) < max(1, target_keep // 2):
            keep_nodes = sorted_nodes[:target_keep]

        existing_ids = {self._node_id(n.n, n.k, n.coordinates) for n in keep_nodes}
        if preserve_node_id not in existing_ids:
            keep_nodes.insert(0, preserve_node)

        self.field_map = {
            self._node_id(n.n, n.k, n.coordinates): n
            for n in keep_nodes[: min(self.max_field_density, soft_keep_cap)]
        }
        self.edge_cutter_active = True

    def _node_id(self, n: int, k: int, coords: Tuple[float, ...]) -> str:
        return f"NODE_{n}_{k}_{self._stable_digest(repr(coords))[:16]}"

    @staticmethod
    def _stable_digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize(value):
        if isinstance(value, dict):
            return {key: HLSFEngine._normalize(value[key]) for key in sorted(value)}
        if isinstance(value, list):
            return [HLSFEngine._normalize(item) for item in value]
        return value


hlsf_singleton = HLSFEngine(dimension=18)
