import json
from pathlib import Path
from typing import Dict
from .cognitive_state import IntuitiveCognition
from vault_system.paths import worker_vault


class IntuitiveEngine:
    def __init__(self, worker_root: Path):
        self.root = worker_root
        self.vault_path = worker_vault("intuitive_skg")
        self.cognition = IntuitiveCognition(self.vault_path)
        seed_path = Path(__file__).resolve().parents[2] / "intuitive" / "pattern_recognition.json"
        with seed_path.open("r", encoding="utf-8") as handle:
            self.seed_definition = json.load(handle)
        conditions = self.seed_definition.get("trigger_conditions", {})
        self.density_threshold = int(conditions.get("hlsf_field_density_threshold", 50))
        rule = self.seed_definition.get("bypass_logic", {}).get("deterministic_rule", "")
        self.symmetry_threshold = 0.9 if "0.9" in rule else self.cognition.unity_threshold

    def check_necessity(self, current_node, field_map):
        density = len(field_map)
        coordinates = []
        for node in field_map.values():
            coords = node.get("coordinates", []) if isinstance(node, dict) else getattr(node, "coordinates", [])
            if len(coords) >= 2:
                coordinates.append((float(coords[0]), float(coords[1])))
        mirrors = 0
        for index, first in enumerate(coordinates):
            for second in coordinates[index + 1 :]:
                if abs(first[0] + second[0]) < 0.2 and abs(first[1] - second[1]) < 0.2:
                    mirrors += 1
        pairs = len(coordinates) * (len(coordinates) - 1) / 2
        symmetry = mirrors / pairs if pairs else 0.0
        if coordinates:
            vector = (
                sum(point[0] for point in coordinates) / len(coordinates),
                sum(point[1] for point in coordinates) / len(coordinates),
            )
        else:
            vector = (0.0, 0.0)
        necessity = density > self.density_threshold and symmetry > self.symmetry_threshold
        return {
            "necessity": necessity,
            "density": density,
            "symmetry": symmetry,
            "certainty": min(0.99, 0.5 + (symmetry / 2)) if necessity else 0.0,
            "vector": vector,
            "bypass_depth": density // 10 if necessity else 0,
            "unity_score": symmetry,
            "seed_id": self.seed_definition.get("seed_id"),
        }

    # Integration
    def advise_orb(self, hlsf_data: Dict) -> Dict:
        field_map = hlsf_data.get("field_map", {})
        current_node = hlsf_data.get("current_node")

        necessity = self.check_necessity(current_node, field_map)

        if necessity["necessity"]:
            verdict_id = self.cognition.record_necessity_verdict(necessity, hlsf_data)

            # Weight by apriori validation if available
            cond_hash = f"d{necessity['density']}_s{int(necessity['symmetry']*100)}"
            if cond_hash in self.cognition.apriori_necessities:
                ap = self.cognition.apriori_necessities[cond_hash]
                bonus_weight = min(0.1, ap.validation_count * 0.01)
                base_weight = 0.35
            else:
                bonus_weight = 0
                base_weight = 0.35

            return {
                "advisory_type": "intuitive",
                "verdict_id": verdict_id,
                "verdict": "substance_unity_achieved",
                "conclusion": "jump_necessary",
                "certainty": necessity["certainty"],
                "unity_vector": necessity["vector"],
                "ethics_alignment": necessity.get("unity_score", 0),
                "deterministic": True,
                "weight": (necessity["certainty"] * base_weight) + bonus_weight,
                "apriori_validated": cond_hash in self.cognition.apriori_necessities,
                "seed_id": self.seed_definition.get("seed_id"),
            }

        return {
            "advisory_type": "intuitive",
            "verdict_id": None,
            "verdict": "field_dispersed",
            "certainty": 0.0,
            "weight": 0.0,
            "seed_id": self.seed_definition.get("seed_id"),
        }

    def validate_verdict(self, verdict_id: str, was_optimal: bool):
        self.cognition.validate_necessity(verdict_id, was_optimal)

    def process_idle(self):
        return self.cognition.idle_recursive_process()
