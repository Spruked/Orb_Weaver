import json
from collections import Counter, deque
from dataclasses import asdict
from pathlib import Path
from typing import Dict
from .cognitive_state import InductiveCognition
from vault_system.paths import worker_vault


class InductiveEngine:
    def __init__(self, worker_root: Path):
        self.root = worker_root
        self.vault_path = worker_vault("inductive_skg")
        self.cognition = InductiveCognition(self.vault_path)

        # Placeholder for existing methods
        self.conjunction_memory = self.cognition.conjunction_memory
        seed_root = Path(__file__).resolve().parents[2] / "inductive"
        self.seed_definitions = [
            self._load_seed(seed_root / "cursor_habit.json"),
            self._load_seed(seed_root / "moral_habit.json"),
        ]
        cursor_seed = self.seed_definitions[0]
        parameters = cursor_seed.get("learning_parameters", {})
        self.minimum_samples = int(parameters.get("min_samples", 3))
        self.observations = deque(
            maxlen=int(parameters.get("conjunction_window", 5))
        )

    @staticmethod
    def _load_seed(path: Path) -> Dict:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def observe_stimulus(self, stimulus):
        if stimulus.get("type") != "cursor_movement":
            return None
        coordinates = stimulus.get("coordinates", [0, 0])
        x, y = float(coordinates[0]), float(coordinates[1])
        quadrant = ("N" if y < 540 else "S") + ("W" if x < 960 else "E")
        if len(self.observations) >= 2:
            context = "→".join(item["quadrant"] for item in list(self.observations)[-2:])
            memory = self.conjunction_memory.setdefault(context, Counter())
            memory[quadrant] += 1
        observation = {
            "quadrant": quadrant,
            "coordinates": [x, y],
            "velocity": float(stimulus.get("velocity", 0.0)),
        }
        self.observations.append(observation)
        return observation

    def predict_next(self):
        if len(self.observations) < self.minimum_samples:
            return {"predictive": False}
        context = "→".join(item["quadrant"] for item in list(self.observations)[-2:])
        targets = self.conjunction_memory.get(context)
        if not targets:
            return {"predictive": False}
        predicted_next, count = targets.most_common(1)[0]
        total = sum(targets.values()) or 1
        confidence = count / total
        return {
            "predictive": True,
            "pattern": f"{context}→{predicted_next}",
            "predicted_next": predicted_next,
            "confidence": confidence,
            "vivacity": min(1.0, total / max(self.minimum_samples, 1)),
            "seed_ids": [seed.get("seed_id") for seed in self.seed_definitions],
        }

    # New additions
    def advise_orb(self, stimulus: Dict, hlsf_context: Dict) -> Dict:
        self.observe_stimulus(stimulus)
        prediction = self.predict_next()

        if prediction["predictive"]:
            # Record for tracking
            verdict_id = self.cognition.record_verdict(prediction, stimulus)

            # Adjust confidence by historical accuracy
            pattern = prediction["pattern"]
            if pattern in self.cognition.pattern_accuracy:
                stats = self.cognition.pattern_accuracy[pattern]
                historical_acc = (
                    stats["correct"] / stats["total"] if stats["total"] > 0 else 0.5
                )
                adjusted_conf = prediction["confidence"] * (0.5 + 0.5 * historical_acc)
            else:
                adjusted_conf = (
                    prediction["confidence"] * 0.8
                )  # Penalty for novel patterns

            return {
                "advisory_type": "inductive",
                "verdict_id": verdict_id,
                "verdict": "pattern_continuation_likely",
                "conclusion": prediction["predicted_next"],
                "confidence": adjusted_conf,
                "raw_confidence": prediction["confidence"],
                "vivacity": prediction["vivacity"],
                "ethics_alignment": self.cognition._calculate_ethics_alignment(
                    prediction
                ),
                "deterministic": False,
                "weight": adjusted_conf * 0.3,
            }

        return {
            "advisory_type": "inductive",
            "verdict_id": None,
            "verdict": "novel_situation",
            "confidence": 0.0,
            "weight": 0.05,
            "seed_ids": [seed.get("seed_id") for seed in self.seed_definitions],
        }

    def validate_verdict(self, verdict_id: str, actual: str):
        self.cognition.validate_verdict(verdict_id, actual)

    def process_idle(self):
        return self.cognition.idle_recursive_process()

    def export_tracelog(self):
        return [
            asdict(t)
            for t in self.cognition.verdict_tracelog
            if t.was_correct is not None
        ]
