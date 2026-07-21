import time
import sys
import json
import math
import hashlib
import threading
from pathlib import Path
from collections import deque
from Orb_Assistant.src.hlsf_geometry.engine import hlsf_singleton
from Orb_Assistant.src.components.core_4_minds.tribunal import FourMindTribunal
from vault_system.manager import VaultManager

# Ensure parent dir (where bayesian_engine.py lives) is importable without packaging.
PARENT = Path(__file__).resolve().parent.parent
if str(PARENT) not in sys.path:
    sys.path.append(str(PARENT))

from Orb_Assistant.src.bayesian_engine import BayesianEngine  # noqa: E402
from Orb_Assistant.src.logic_seeds.deductive_SKG.logic.deductive_logic import DeductiveEngine  # noqa: E402
from Orb_Assistant.src.logic_seeds.inductive_skg.logic.inductive_logic import InductiveEngine  # noqa: E402
from Orb_Assistant.src.logic_seeds.intuitive_skg.logic.intuitive_logic import IntuitiveEngine  # noqa: E402
from Orb_Assistant.src.logic_seeds.validation_pipeline import FinalValidationLayer  # noqa: E402
from Orb_Assistant.src.orb_skg_manager import (  # noqa: E402
    AsyncCALIReflectionRecorder,
    SKGUsageLedger,
)

# --- Epistemic Gravity Wiring ---
try:
    EGF_PATH = PARENT / "Epistemic_Gravity_Field"
    if str(EGF_PATH) not in sys.path:
        sys.path.append(str(EGF_PATH))
    from Epistemic_Gravity_Field.space_field import SpaceFieldCognition
    try:
        import torch
    except ImportError:
        torch = None
    TORCH_AVAILABLE = torch is not None
except ImportError as e:
    print(f"Warning: Epistemic Gravity Field not loaded: {e}")
    torch = None
    TORCH_AVAILABLE = False


class EpistemicGravityBridge:
    def __init__(self):
        self.active = TORCH_AVAILABLE
        if self.active:
            print("Wiring Epistemic Gravity Field...")
            self.field = SpaceFieldCognition(device="cpu")
            self.dim = self.field.config.DIM
            print("✓ Epistemic Gravity Online (32³ Tensor)")

    def process_stimulus(self, stimulus):
        if not self.active:
            return {}

        self.field.step()

        if stimulus.get("type") == "cursor_movement":
            coords = stimulus.get("coordinates", [0, 0])
            # Mapping 1920x1080 to DIM x DIM
            x = int((coords[0] / 1920.0) * (self.dim - 1))
            y = int((coords[1] / 1080.0) * (self.dim - 1))
            x = max(0, min(x, self.dim - 1))
            y = max(0, min(y, self.dim - 1))

            # Create injection tensor
            signal = torch.zeros(self.dim, self.dim, self.dim, 4)
            # Inject at center z-plane
            z = self.dim // 2

            # Simple intensity based on velocity or default
            intensity = min(stimulus.get("velocity", 1.0) / 10.0, 1.0)
            signal[x, y, z, :] = intensity

            self.field.broadcast_to_field(signal)

        return self.field.get_field_stats()


# --------------------------------


class CrossDomainPredicate:
    """Emergent thought-object synthesized across epistemic, spatial, and logic domains."""

    def __init__(self, epistemic, spatial, logic, synthesis_confidence):
        self.epistemic_traces = epistemic
        self.hlsf_node = spatial
        self.logic_validity = logic
        self.confidence = synthesis_confidence
        self.timestamp = time.time()
        # Default dynamic attributes (populated at runtime)
        self.navigation_vector = None
        self.final_verdict = None
        self.final_verdict_source = None
        self.cognitive_components = {}
        self.ucm_envelope = None
        self.cali_reflection = None
        self.logic_seed_advisories = None
        self.vault_retrieval = None
        self.validation_witness = None

    def pulse(self):
        mode = self.logic_validity.get("active_mode") or (
            "INTUITION-JUMP"
            if self.logic_validity.get("intuitive_jump_triggered")
            else "HABIT" if self.logic_validity.get("custom_habit_active") else "GUARD"
        )
        result = {
            "glow_intensity": self.confidence,
            "cognitive_mode": mode,
            "spatial_coordinate": self.hlsf_node,
            "epistemic_alignment": self._calculate_axiomatic_alignment(),
            "deterministic": self.confidence > 0.95,
            "predictive_intent": self.logic_validity.get("inductive_prediction", {}),
            "jump_vector": self.logic_validity.get("necessity_vector", []),
            "navigation_vector": getattr(self, "navigation_vector", None),
            "final_verdict": getattr(self, "final_verdict", None),
            "final_verdict_source": getattr(self, "final_verdict_source", None),
            "cognitive_components": getattr(self, "cognitive_components", None),
            "cognitive_path": getattr(self, "cognitive_path", None),
            "latency_ms": getattr(self, "latency_ms", None),
            "execution_record": getattr(self, "execution_record", None),
        }
        return {k: v for k, v in result.items() if v is not None}

    def internal_state(self):
        return {
            "ucm_envelope": getattr(self, "ucm_envelope", None),
            "cali_reflection": getattr(self, "cali_reflection", None),
            "logic_seed_advisories": getattr(self, "logic_seed_advisories", None),
            "vault_retrieval": getattr(self, "vault_retrieval", None),
            "validation_witness": getattr(self, "validation_witness", None),
        }

    def _calculate_axiomatic_alignment(self):
        if not self.epistemic_traces:
            return 0.0
        confidences = [
            trace.get("confidence", 0.5) for trace in self.epistemic_traces.values()
        ]
        return sum(confidences) / len(confidences)


class HabitTracker:
    """Humean constant conjunction tracker for cursor movements."""

    def __init__(self, vault_manager):
        self.vault = vault_manager
        if not hasattr(self.vault, "posteriori_cache"):
            self.vault.posteriori_cache = {}
        self.sequence_buffer = deque(maxlen=5)
        self.pattern_cache = {}

    def record_observation(self, stimulus):
        if stimulus.get("type") != "cursor_movement":
            return None
        coords = stimulus.get("coordinates", [0, 0])
        quadrant = self._coords_to_quadrant(coords)
        observation = {
            "quadrant": quadrant,
            "coords": coords,
            "velocity": stimulus.get("velocity", 0.0),
            "timestamp": time.time(),
        }
        self.sequence_buffer.append(observation)
        if len(self.sequence_buffer) >= 3:
            pattern_key = self._serialize_pattern(list(self.sequence_buffer))
            self._update_conjunction_frequency(pattern_key)
        return observation

    def predict_next(self):
        if len(self.sequence_buffer) < 3:
            return None
        current_pattern = self._serialize_pattern(list(self.sequence_buffer)[-3:])
        cached = getattr(self.vault, "posteriori_cache", {}).get(
            f"habit_{current_pattern}"
        )
        if cached:
            return {
                "prediction_type": "QUADRANT_TRANSITION",
                "target": cached.get("predicted_next"),
                "confidence": cached.get("frequency", 0.0),
                "hume_vivacity": min(cached.get("frequency", 0) * 1.2, 1.0),
            }
        return {"prediction_type": "UNSURE", "confidence": 0.3, "hume_vivacity": 0.4}

    def _coords_to_quadrant(self, coords):
        x, y = coords[0], coords[1]
        grid_x = 1920 / 2
        grid_y = 1080 / 2
        col = 0 if x < grid_x else 1
        row = 0 if y < grid_y else 1
        return ["NW", "NE", "SW", "SE"][row * 2 + col]

    def _serialize_pattern(self, sequence):
        return "_".join([s["quadrant"] for s in sequence])

    def _update_conjunction_frequency(self, pattern_key):
        if pattern_key not in self.pattern_cache:
            self.pattern_cache[pattern_key] = {"count": 0}
        self.pattern_cache[pattern_key]["count"] += 1
        self.vault.crystallize(
            f"habit_{pattern_key}",
            {
                "pattern": pattern_key,
                "frequency": min(self.pattern_cache[pattern_key]["count"] / 10.0, 1.0),
                "predicted_next": self._extrapolate_next_quadrant(pattern_key),
                "temporal_decay": 0.95,
            },
        )

    def _extrapolate_next_quadrant(self, pattern_key):
        parts = pattern_key.split("_")
        return parts[-1] if len(parts) >= 2 else "UNKNOWN"

    def get_quadrant_heat(self, quadrant_code):
        """Returns rough usage frequency of a quadrant to aid avoidance."""
        heat = 0
        for pattern, data in self.pattern_cache.items():
            if quadrant_code in pattern:
                heat += data.get("count", 0)
        return min(heat / 100.0, 1.0)  # Normalize cap


class IntuitiveRecognizer:
    """Spinozan necessity recognizer for high-density fields."""

    def __init__(self, hlsf_engine):
        self.hlsf = hlsf_engine
        self.symmetry_threshold = 0.9
        self.density_threshold = 50

    def check_necessity(self, stimulus, current_node):
        field_density = len(self.hlsf.field_map)
        if field_density > self.density_threshold:
            symmetry_score = self._calculate_bilateral_symmetry()
            if symmetry_score > self.symmetry_threshold:
                necessity_vector = self._calculate_substance_vector(current_node)
                return {
                    "jump_triggered": True,
                    "necessity_vector": necessity_vector,
                    "substance_unity_score": symmetry_score,
                    "bypass_steps": field_density // 10,
                    "spinozan_certainty": 0.98,
                    "field_density": field_density,
                }
        return {
            "jump_triggered": False,
            "field_density": field_density,
            "spinozan_certainty": 0.0,
            "substance_unity_score": self._calculate_bilateral_symmetry(),
        }

    def _calculate_bilateral_symmetry(self):
        if not self.hlsf.field_map:
            return 0.0
        nodes = list(self.hlsf.field_map.values())
        if len(nodes) < 2:
            return 0.0
        mirror_count = 0
        coords_list = [n.coordinates for n in nodes]
        for i, c1 in enumerate(coords_list):
            for c2 in coords_list[i + 1 :]:
                if len(c1) >= 2 and len(c2) >= 2:
                    if abs(c1[0] + c2[0]) < 0.2 and abs(c1[1] - c2[1]) < 0.2:
                        mirror_count += 1
        total_pairs = len(nodes) * (len(nodes) - 1) / 2
        return mirror_count / total_pairs if total_pairs > 0 else 0.0

    def _calculate_substance_vector(self, current_node):
        if not self.hlsf.field_map:
            return (0.0, 0.0)
        centroid = [0.0] * min(self.hlsf.dimension, 18)
        for node in self.hlsf.field_map.values():
            for i in range(len(centroid)):
                if i < len(node.coordinates):
                    centroid[i] += node.coordinates[i]
        count = len(self.hlsf.field_map)
        centroid = [c / count for c in centroid]
        return (centroid[0], centroid[1])


class ProprioceptionSystem:
    """Tracks Orb's physical state and computes navigation intent relative to cursor/habits."""

    def __init__(self, start_pos=[960, 540]):
        self.position = list(start_pos)
        self.target_safe_distance = 250.0  # Pixels
        self.min_safe_distance = 150.0
        self.velocity = [0.0, 0.0]
        self.last_update = time.time()

    def update_physics(self, current_pos, dt):
        dx = current_pos[0] - self.position[0]
        dy = current_pos[1] - self.position[1]
        self.velocity = [dx / dt if dt > 0 else 0, dy / dt if dt > 0 else 0]
        self.position = list(current_pos)
        self.last_update = time.time()

    def calculate_navigation_vector(self, cursor_pos, habit_heatmap, gravity_density):
        """
        Compute desire vector:
        1. Attraction to Cursor (Gravity)
        2. Repulsion from Cursor (Safe Bubble)
        3. Repulsion from Traffic (Habit Heatmap)
        4. Repulsion from High Entropy (Gravity Field)
        """
        # Vector to cursor
        dx = cursor_pos[0] - self.position[0]
        dy = cursor_pos[1] - self.position[1]
        dist = (dx**2 + dy**2) ** 0.5

        if dist == 0:
            return [0, 0]

        # 1. Attract/Repel Cursor (Goldilocks Zone)
        # If too far, attract. If too close, repel strongly.
        force_mag = 0.0
        if dist < self.min_safe_distance:
            # Strong repulsion
            force_mag = -1.0 * (self.min_safe_distance - dist) / self.min_safe_distance
        elif dist > self.target_safe_distance:
            # Gentle attraction
            force_mag = 0.5 * (dist - self.target_safe_distance) / 1000.0

        # Base vector
        nx, ny = dx / dist, dy / dist
        nav_vector = [nx * force_mag, ny * force_mag]

        # 2. Habit Avoidance (Traffic)
        # If current location is high-traffic, add slight random jitter or repulsion to keep moving
        if habit_heatmap and habit_heatmap > 0.5:
            # Add perpendicular vector to flow? Or just noise to prevent loitering
            import random

            nav_vector[0] += (random.random() - 0.5) * habit_heatmap
            nav_vector[1] += (random.random() - 0.5) * habit_heatmap

        # 3. Epistemic Gravity Repulsion (High Entropy/Density)
        # If density is high (chaotic), pull back further
        if gravity_density > 0.0:
            # Push away from cursor more
            nav_vector[0] -= nx * gravity_density * 0.5
            nav_vector[1] -= ny * gravity_density * 0.5

        return nav_vector


class SF_ORB_Controller:
    """Canonical Triple Triple Controller (Triad C)."""

    def __init__(self, orbs_stage_client=None, orbs_articulator=None):
        print("Initializing SF-ORB Sovereign Logic...")
        self.engine = hlsf_singleton
        self.tribunal = FourMindTribunal(
            skg_path=str(Path(__file__).resolve().parent / "components" / "core_4_minds")
        )
        self.vaults = VaultManager()
        self.habit_tracker = HabitTracker(self.vaults)
        self.intuitive_recognizer = IntuitiveRecognizer(self.engine)
        self.gravity_bridge = EpistemicGravityBridge()
        self.proprioception = ProprioceptionSystem()
        self.bayes = BayesianEngine(alpha=1.5, beta=1.0)
        logic_seed_root = Path(__file__).resolve().parent / "logic_seeds"
        self.deductive_engine = DeductiveEngine(logic_seed_root / "deductive_SKG")
        self.inductive_engine = InductiveEngine(logic_seed_root / "inductive_skg")
        self.intuitive_engine = IntuitiveEngine(logic_seed_root / "intuitive_skg")
        self.final_validation = FinalValidationLayer()
        self.skg_usage_ledger = SKGUsageLedger()
        self.cali_reflection_recorder = AsyncCALIReflectionRecorder()
        self._cognitive_lock = threading.RLock()
        self.last_observational_error = None
        self._orbs_stage_client = None
        self._orbs_action_service = None
        self._orbs_articulator = None
        self._orbs_confirmation_policy = None
        if orbs_stage_client is not None:
            self.configure_orbs_integration(orbs_stage_client, orbs_articulator)
        self._initialize_bayesian_priors()
        print("✓ Triple Triple Architecture Online")
        print("✓ Logic Triad C: Deductive | Inductive | Intuitive")

    def configure_orbs_integration(self, stage_client, articulator=None):
        """Attach non-authoritative Orb Weaver adapters without storing stage truth."""
        from Orb_Assistant.src.orbs_integration import (
            ConfirmationPolicy,
            StageActionService,
            StageArticulator,
        )

        self._orbs_stage_client = stage_client
        self._orbs_confirmation_policy = ConfirmationPolicy()
        self._orbs_action_service = StageActionService(
            stage_client,
            self._orbs_confirmation_policy,
        )
        self._orbs_articulator = articulator or StageArticulator()

    def request_orbs_stage(self, project_id):
        """Fetch a fresh authoritative snapshot and produce language-only guidance."""
        self._require_orbs_integration()
        snapshot = self._orbs_stage_client.current_stage(str(project_id))
        return snapshot, self._orbs_articulator.articulate(snapshot)

    def confirm_orbs_action(
        self,
        snapshot,
        action_name,
        accepted,
        statement,
        method="explicit_yes",
    ):
        """Record courtesy confirmation; Orb Weaver still authorizes the action."""
        self._require_orbs_integration()
        return self._orbs_confirmation_policy.confirm(
            snapshot,
            action_name,
            accepted,
            statement,
            method,
        )

    def submit_orbs_action(
        self,
        snapshot,
        action_name,
        idempotency_key,
        confirmation=None,
        inputs=None,
    ):
        """Submit one snapshot-approved action and return Orb Weaver's fresh snapshot."""
        self._require_orbs_integration()
        return self._orbs_action_service.submit(
            snapshot=snapshot,
            action_name=action_name,
            idempotency_key=idempotency_key,
            confirmation=confirmation,
            inputs=inputs,
        )

    def orbs_pointer_destination(self, snapshot, action_name):
        """Return only a governor-approved, snapshot-verified CTA destination."""
        action = snapshot.action(action_name)
        if not action or not action.destination_route:
            return None
        return action.destination_route

    def _require_orbs_integration(self):
        if not all((self._orbs_stage_client, self._orbs_action_service, self._orbs_articulator)):
            raise RuntimeError("Orb Weaver ORBS stage integration is not configured")

    def emergency_purge(self):
        """Manual density reset to restore SLA."""
        before = len(self.engine.field_map)
        if before > 1000:
            self.engine._edge_cutter_purge()
            after = len(self.engine.field_map)
            print(f"🧹 EMERGENCY PURGE: {before} → {after} nodes")
            return True
        return False

    def cognitively_emerge(self, stimulus):
        """Route one stimulus through the selected cognitive lane safely."""
        with self._cognitive_lock:
            return self._cognitively_emerge_locked(stimulus)

    def _cognitively_emerge_locked(self, stimulus):
        start_time = time.time()

        if not self._check_sovereignty(stimulus):
            return None

        vault_retrieval = self.vaults.lightning_query(stimulus)
        cognitive_path = self._select_cognitive_path(stimulus, vault_retrieval)
        if cognitive_path == "vault_supported_fast":
            return self._fast_cognitive_emergence(
                stimulus, vault_retrieval, start_time
            )

        self.habit_tracker.record_observation(stimulus)

        gravity_stats = self.gravity_bridge.process_stimulus(stimulus)

        # Proprioception Update (Assuming stimulus contains Orb pos, or we simulate it)
        # Since we don't have Orb pos in stimulus commonly, we use the controller's estimation or previous intent
        # For now, we simulate "Proprioception" updating its own belief based on the previous command
        # Ideally, stimulus['orb_coordinates'] should be passed.
        orb_pos = stimulus.get("orb_coordinates", self.proprioception.position)
        self.proprioception.update_physics(orb_pos, 0.1)  # dt approx 0.1s

        # Navigation Logic
        cursor_pos = stimulus.get("coordinates", [0, 0])
        gravity_density = gravity_stats.get("renewal_pressure", 0.0)

        # Get habit heat for current orb position
        current_orb_quad = self.habit_tracker._coords_to_quadrant(
            self.proprioception.position
        )
        habit_heat = self.habit_tracker.get_quadrant_heat(current_orb_quad)

        nav_vector = self.proprioception.calculate_navigation_vector(
            cursor_pos, habit_heat, gravity_density
        )

        node = self.engine.map_adjacency(stimulus)

        hlsf_context = self._hlsf_context(node)
        logic_seed_advisories = self._logic_seed_advisories(
            stimulus, hlsf_context, cognitive_path
        )

        intuition = self.intuitive_recognizer.check_necessity(stimulus, node)
        inductive = (
            None
            if intuition.get("jump_triggered")
            else self.habit_tracker.predict_next()
        )

        shadows = self.tribunal.generate_epistemic_shadow(stimulus)
        bayes_shadows = self._update_bayesian_shadows(shadows)

        logic_state = self._synthesize_logic_triad(
            inductive,
            intuition,
            bayes_shadows,
            logic_seed_advisories,
        )

        neighbor_radius = 3 if cognitive_path == "full_escalation" else 1
        neighbors = self.engine.get_recursive_neighbors(node, radius=neighbor_radius)
        thought_vec = (
            self.engine.calculate_thought_vector(neighbors + [node])
            if neighbors
            else (0.0,) * self.engine.dimension
        )

        confidence = self._calculate_convergence(shadows, logic_state, thought_vec)

        spatial_coord = {
            "node_id": f"NODE_{node.n}_{node.k}",
            "recursion_depth": node.k,
            "coordinates": node.coordinates,
            "adjacency_value": node.adjacency_value,
        }

        thought = CrossDomainPredicate(
            epistemic=shadows,
            spatial=spatial_coord,
            logic=logic_state,
            synthesis_confidence=confidence,
        )
        thought.gravity_stats = gravity_stats
        thought.navigation_vector = nav_vector

        # All cognition is parallel. All convergence is advisory. All execution is downstream.
        ucm_envelope = self._build_correlation_envelope(
            stimulus=stimulus,
            shadows=shadows,
            bayes_shadows=bayes_shadows,
            logic_state=logic_state,
            confidence=confidence,
            include_reflection=cognitive_path == "full_escalation",
        )
        cali_reflection = ucm_envelope.get("cali_reflection", {})

        # Store envelope data via dynamic attributes
        thought.__dict__["ucm_envelope"] = ucm_envelope
        thought.__dict__["cali_reflection"] = cali_reflection
        thought.__dict__["final_verdict"] = ucm_envelope.get("final_verdict")
        thought.__dict__["final_verdict_source"] = ucm_envelope.get("final_verdict_source")
        thought.__dict__["logic_seed_advisories"] = logic_seed_advisories
        thought.__dict__["vault_retrieval"] = vault_retrieval

        validated_verdict = self.final_validation.validate_for_delivery(
            {
                "type": stimulus.get("type", "unknown"),
                "conclusion": thought.final_verdict,
                "confidence": confidence,
                "pattern": (logic_state.get("inductive_prediction") or {}).get(
                    "pattern", ""
                ),
                "source": thought.final_verdict_source,
            },
            {
                "hlsf": hlsf_context,
                "logic_seed_advisories": logic_seed_advisories,
                "vault_retrieval": vault_retrieval,
            },
            validator_names=self._matching_validators(
                logic_seed_advisories, cognitive_path
            ),
        )
        thought.__dict__["validation_witness"] = validated_verdict.get(
            "_validation_witness", {}
        )
        thought.__dict__["cognitive_components"] = self._cognitive_component_trace(
            logic_seed_advisories,
            vault_retrieval,
            thought.validation_witness,
            cognitive_path=cognitive_path,
            core_4=True,
            hlsf=True,
            bayesian=True,
            cali_reflection=cognitive_path == "full_escalation",
        )
        thought.__dict__["cognitive_path"] = cognitive_path
        ucm_envelope["logic_seed_advisories"] = logic_seed_advisories
        ucm_envelope["vault_retrieval"] = vault_retrieval
        ucm_envelope["validation_witness"] = thought.validation_witness
        ucm_envelope["cognitive_components"] = thought.cognitive_components

        thought.__dict__["latency_ms"] = round(
            (time.time() - start_time) * 1000, 3
        )
        confidence_after_validation = (
            confidence
            if thought.validation_witness.get("congruent", False)
            else confidence * 0.75
        )
        thought.__dict__["execution_record"] = self._build_execution_record(
            stimulus=stimulus,
            selected_lane=cognitive_path,
            vault_retrieval=vault_retrieval,
            components=thought.cognitive_components,
            confidence_before=confidence,
            confidence_after=confidence_after_validation,
            validation_witness=thought.validation_witness,
            elapsed_ms=thought.latency_ms,
            reflection_deferred=cognitive_path != "full_escalation",
        )
        ucm_envelope["execution_record"] = thought.execution_record
        if thought.execution_record["reflection_deferred"]:
            self.cali_reflection_recorder.defer(
                {
                    "stimulus_hash": self._glyph_trace(stimulus, time.time()),
                    "selected_lane": cognitive_path,
                    "reflection": cali_reflection,
                    "advisory_only": True,
                }
            )

        self._update_bayesian_outcome(logic_state)

        self.vaults.crystallize(
            stimulus,
            {
                "predicate": thought.pulse(),
                "confidence": confidence,
                "triad_c_mode": logic_state.get("active_mode"),
                "field_density": logic_state.get("field_density", 0),
                "ucm_envelope": ucm_envelope,
                "cali_reflection": cali_reflection,
            },
        )
        self._record_usage_safely(stimulus, thought)

        elapsed = (time.time() - start_time) * 1000
        mode = logic_state.get("active_mode", "GUARD")
        print(
            f"🧠 [{mode}] {elapsed:.1f}ms | Density: {logic_state.get('field_density', 0)}"
        )

        return thought

    def _select_cognitive_path(self, stimulus, vault_retrieval):
        metadata = stimulus.get("meta", {})
        supplied_confidence = stimulus.get("confidence")
        low_supplied_confidence = (
            isinstance(supplied_confidence, (int, float))
            and supplied_confidence < 0.65
        )
        deep_reasoning = any(
            (
                metadata.get("deep_reasoning"),
                metadata.get("evidence_conflict"),
                metadata.get("low_confidence"),
                metadata.get("complexity") == "high",
                stimulus.get("evidence_conflict"),
                stimulus.get("complexity") == "high",
                low_supplied_confidence,
                metadata.get("high_risk"),
                metadata.get("unresolved_intuitive_jump"),
                metadata.get("repeated_failures", 0) > 1,
                stimulus.get("type")
                in {
                    "moral_dilemma",
                    "explicit_deep_reasoning",
                    "novel_stimulus",
                },
            )
        )
        if deep_reasoning:
            return "full_escalation"
        if vault_retrieval and vault_retrieval.get("status") == "DETERMINISTIC":
            return "vault_supported_fast"
        return "ordinary_reasoning"

    def _logic_seed_advisories(self, stimulus, hlsf_context, cognitive_path):
        advisories = {
            "deductive": self.deductive_engine.advise_orb(
                stimulus.get("type", "unknown"), hlsf_context["current_node"]
            )
        }
        if cognitive_path == "full_escalation" or stimulus.get("type") == "cursor_movement":
            advisories["inductive"] = self.inductive_engine.advise_orb(
                stimulus, hlsf_context
            )
        if cognitive_path == "full_escalation" or len(hlsf_context["field_map"]) > 50:
            advisories["intuitive"] = self.intuitive_engine.advise_orb(hlsf_context)
        return advisories

    def _matching_validators(self, advisories, cognitive_path):
        if cognitive_path == "full_escalation":
            return ("deductive", "inductive", "intuitive")
        selected = [
            name
            for name in ("deductive", "inductive", "intuitive")
            if name in advisories
        ]
        return tuple(selected or ("deductive",))

    def _fast_cognitive_emergence(self, stimulus, vault_retrieval, start_time):
        spatial = {
            "node_id": "VAULT_EVIDENCE",
            "recursion_depth": 0,
            "coordinates": tuple(stimulus.get("coordinates", (0.0, 0.0))),
            "adjacency_value": 1.0,
        }
        advisories = {
            "deductive": self.deductive_engine.advise_orb(
                stimulus.get("type", "unknown"), spatial
            )
        }
        logic_state = {
            "active_mode": "GUARD",
            "field_density": len(self.engine.field_map),
            "logic_seed_advisories": advisories,
            "vault_supported": True,
        }
        thought = CrossDomainPredicate({}, spatial, logic_state, 0.99)
        thought.__dict__["final_verdict"] = (
            vault_retrieval.get("predicate")
            or vault_retrieval.get("data")
            or "vault_evidence_available"
        )
        thought.__dict__["final_verdict_source"] = "Vault evidence with lightweight Triad C review"
        thought.__dict__["logic_seed_advisories"] = advisories
        thought.__dict__["vault_retrieval"] = vault_retrieval
        thought.__dict__["cali_reflection"] = {
            "observational_only": True,
            "deferred": True,
            "events": [],
            "flags": {},
        }
        validated = self.final_validation.validate_for_delivery(
            {
                "type": stimulus.get("type", "unknown"),
                "conclusion": str(thought.final_verdict),
                "confidence": 0.99,
                "source": thought.final_verdict_source,
            },
            {"hlsf": {}, "vault_retrieval": vault_retrieval},
            validator_names=("deductive",),
        )
        thought.__dict__["validation_witness"] = validated.get(
            "_validation_witness", {}
        )
        thought.__dict__["cognitive_components"] = self._cognitive_component_trace(
            advisories,
            vault_retrieval,
            thought.validation_witness,
            cognitive_path="vault_supported_fast",
            core_4=False,
            hlsf=False,
            bayesian=False,
            cali_reflection=False,
        )
        thought.__dict__["cognitive_path"] = "vault_supported_fast"
        thought.__dict__["ucm_envelope"] = {
            "final_verdict": thought.final_verdict,
            "final_verdict_source": thought.final_verdict_source,
            "vault_retrieval": vault_retrieval,
            "logic_seed_advisories": advisories,
            "validation_witness": thought.validation_witness,
            "cognitive_components": thought.cognitive_components,
        }
        thought.__dict__["latency_ms"] = round(
            (time.time() - start_time) * 1000, 3
        )
        confidence_after_validation = (
            0.99
            if thought.validation_witness.get("congruent", False)
            else 0.99 * 0.75
        )
        thought.__dict__["execution_record"] = self._build_execution_record(
            stimulus=stimulus,
            selected_lane="vault_supported_fast",
            vault_retrieval=vault_retrieval,
            components=thought.cognitive_components,
            confidence_before=0.99,
            confidence_after=confidence_after_validation,
            validation_witness=thought.validation_witness,
            elapsed_ms=thought.latency_ms,
            reflection_deferred=True,
        )
        thought.ucm_envelope["execution_record"] = thought.execution_record
        self.cali_reflection_recorder.defer(
            {
                "stimulus_hash": self._glyph_trace(stimulus, time.time()),
                "selected_lane": "vault_supported_fast",
                "reflection": thought.cali_reflection,
                "advisory_only": True,
            }
        )
        self._record_usage_safely(stimulus, thought)
        return thought

    def _record_usage_safely(self, stimulus, thought):
        """Keep the observational ledger outside cognitive success semantics."""
        try:
            self.skg_usage_ledger.record(stimulus, thought.cognitive_components)
            self.last_observational_error = None
        except Exception as exc:
            error = {
                "component": "SKGUsageLedger",
                "error": str(exc),
                "result_preserved": True,
            }
            self.last_observational_error = error
            thought.execution_record.setdefault("observational_errors", []).append(
                error
            )

    def _hlsf_context(self, current_node):
        def describe(node):
            return {
                "node_id": f"NODE_{node.n}_{node.k}",
                "coordinates": list(node.coordinates),
                "adjacency_value": node.adjacency_value,
                "recursion_depth": node.k,
            }

        return {
            "current_node": describe(current_node),
            "field_map": {
                str(node_id): describe(field_node)
                for node_id, field_node in self.engine.field_map.items()
            },
        }

    def _cognitive_component_trace(
        self,
        logic_seed_advisories,
        vault_retrieval,
        validation_witness,
        *,
        cognitive_path,
        core_4,
        hlsf,
        bayesian,
        cali_reflection,
    ):
        return {
            "path": cognitive_path,
            "core_4": tuple(sorted(self.tribunal.minds)) if core_4 else (),
            "hlsf": hlsf,
            "bayesian_selection": bayesian,
            "deductive_skg": logic_seed_advisories.get("deductive") is not None,
            "inductive_skg": logic_seed_advisories.get("inductive") is not None,
            "intuitive_skg": logic_seed_advisories.get("intuitive") is not None,
            "logic_seed_ids": tuple(
                seed_id
                for seed_id in (
                    *logic_seed_advisories.get("inductive", {}).get("seed_ids", ()),
                    logic_seed_advisories.get("intuitive", {}).get("seed_id"),
                )
                if seed_id
            ),
            "learned_habits": "inductive" in logic_seed_advisories,
            "vault_retrieval_queried": True,
            "vault_match_found": vault_retrieval is not None,
            "cali_reflection": cali_reflection,
            "final_validators": tuple(validation_witness.get("validators", ())),
        }

    def _build_execution_record(
        self,
        *,
        stimulus,
        selected_lane,
        vault_retrieval,
        components,
        confidence_before,
        confidence_after,
        validation_witness,
        elapsed_ms,
        reflection_deferred,
    ):
        modules = ["vault_retrieval", "stimulus_classifier"]
        for module_name in ("deductive_skg", "inductive_skg", "intuitive_skg"):
            if components.get(module_name):
                modules.append(module_name)
        if components.get("hlsf"):
            modules.append("hlsf")
        if components.get("bayesian_selection"):
            modules.append("bayesian_selection")
        modules.extend(f"core_4:{mind}" for mind in components.get("core_4", ()))
        if components.get("cali_reflection"):
            modules.append("cali_reflection")

        conflicts = []
        metadata = stimulus.get("meta", {})
        if metadata.get("evidence_conflict") or stimulus.get("evidence_conflict"):
            conflicts.append("evidence_conflict")
        if validation_witness and not validation_witness.get("congruent", False):
            conflicts.append("validator_disagreement")

        escalation_trigger = None
        if selected_lane == "full_escalation":
            for trigger, active in (
                ("explicit_deep_reasoning", metadata.get("deep_reasoning")),
                ("major_evidence_conflict", bool(conflicts)),
                ("low_confidence", metadata.get("low_confidence")),
                ("high_complexity", metadata.get("complexity") == "high"),
                ("high_risk", metadata.get("high_risk")),
                ("repeated_failure", metadata.get("repeated_failures", 0) > 1),
                ("novel_stimulus", stimulus.get("type") == "novel_stimulus"),
            ):
                if active:
                    escalation_trigger = trigger
                    break
            escalation_trigger = escalation_trigger or "deterministic_full_lane_rule"

        routing_reason = {
            "vault_supported_fast": (
                "Relevant deterministic Vault evidence supported a high-confidence "
                "lightweight validated response."
            ),
            "ordinary_reasoning": (
                "Vault evidence was incomplete or the stimulus required ordinary "
                "reasoning and applicable validation."
            ),
            "full_escalation": (
                "A deterministic escalation condition required the complete "
                "cognitive lane."
            ),
        }[selected_lane]

        return {
            "selected_lane": selected_lane,
            "routing_reason": routing_reason,
            "vault_evidence_used": vault_retrieval is not None,
            "modules_invoked": tuple(modules),
            "validators_invoked": tuple(
                validation_witness.get("validators", ())
            ),
            "confidence_before_validation": round(confidence_before, 6),
            "confidence_after_validation": round(confidence_after, 6),
            "conflicts_detected": tuple(conflicts),
            "escalation_trigger": escalation_trigger,
            "elapsed_ms": elapsed_ms,
            "reflection_deferred": reflection_deferred,
            "workflow_authority": "advisory_only",
            "may_advance_stage_governor": False,
        }

    def _build_correlation_envelope(
        self,
        stimulus,
        shadows,
        bayes_shadows,
        logic_state,
        confidence,
        include_reflection=True,
    ):
        stardate = time.time()
        glyph_trace = self._glyph_trace(stimulus, stardate)
        core_4 = self._build_core_4_returns(shadows, bayes_shadows, logic_state)
        advisory_plus_one = self._build_advisory_plus_one(core_4)
        cali_reflection = (
            self._build_cali_reflection(advisory_plus_one, logic_state)
            if include_reflection
            else {
                "observational_only": True,
                "deferred": True,
                "events": [],
                "flags": {},
            }
        )
        final_verdict = self._verdict_from_mode(logic_state.get("active_mode"))

        return {
            "stardate": stardate,
            "glyph_trace": glyph_trace,
            "core_4": core_4,
            "advisory_plus_one": advisory_plus_one,
            "cali_reflection": cali_reflection,
            "final_verdict": final_verdict,
            "final_verdict_source": "UCM Core-4 deliberation (ECM advisory only)",
            "confidence": confidence,
        }

    def _build_core_4_returns(self, shadows, bayes_shadows, logic_state):
        caleon_shadow = shadows.get("spinoza", {})
        kaygee_shadow = shadows.get("kant", {})
        cali_shadow = shadows.get("hume", {})
        locke_shadow = shadows.get("locke", {})

        advisory_verdict = self._verdict_from_mode(logic_state.get("active_mode"))
        convergence_weights = self._normalize_weights(
            {
                "caleon": caleon_shadow.get("confidence", 0.5),
                "kaygee": kaygee_shadow.get("confidence", 0.5),
                "cali_x_one": cali_shadow.get("confidence", 0.5),
                "empirical": locke_shadow.get("confidence", 0.5),
            }
        )

        return {
            "caleon": {
                "shadow": caleon_shadow,
                "confidence": caleon_shadow.get("confidence", 0.5),
                "advisory_verdict": advisory_verdict,
            },
            "kaygee": {
                "shadow": kaygee_shadow,
                "confidence": kaygee_shadow.get("confidence", 0.5),
                "advisory_verdict": advisory_verdict,
            },
            "cali_x_one": {
                "shadow": cali_shadow,
                "confidence": cali_shadow.get("confidence", 0.5),
                "advisory_verdict": advisory_verdict,
            },
            "ecm": {
                "convergence_weights": convergence_weights,
                "inputs": {
                    "locke": locke_shadow,
                    "hume": cali_shadow,
                    "kant": kaygee_shadow,
                    "spinoza": caleon_shadow,
                },
                "note": "ECM emits convergence weights only (advisory).",
            },
        }

    def _build_advisory_plus_one(self, core_4):
        confidences = {
            "caleon": core_4.get("caleon", {}).get("confidence", 0.5),
            "kaygee": core_4.get("kaygee", {}).get("confidence", 0.5),
            "cali_x_one": core_4.get("cali_x_one", {}).get("confidence", 0.5),
        }
        weights = self._softmax(list(confidences.values()))
        gradients = dict(zip(confidences.keys(), weights))

        entropy = -sum(p * math.log(p + 1e-9) for p in weights)
        spread = (
            max(confidences.values()) - min(confidences.values())
            if confidences
            else 0.0
        )
        reweight = entropy > 1.0 or spread > 0.2

        return {
            "advisory_only": True,
            "confidence_gradients": gradients,
            "tension_indicators": {
                "entropy": entropy,
                "spread": spread,
                "reweight_recommended": reweight,
            },
            "suggestion": (
                "consider re-weighting high-tension lobes"
                if reweight
                else "no reweight suggested"
            ),
        }

    def _build_cali_reflection(self, advisory_plus_one, logic_state):
        tension = advisory_plus_one.get("tension_indicators", {})
        entropy = tension.get("entropy", 0.0)
        spread = tension.get("spread", 0.0)

        events = []
        if spread > 0.2:
            events.append(
                {"type": "drift", "detail": "confidence spread exceeded threshold"}
            )
        if entropy > 1.0:
            events.append(
                {"type": "anomaly", "detail": "high entropy in lobe gradients"}
            )
        if logic_state.get("active_mode") == "INTUITION-JUMP" and entropy > 0.9:
            events.append(
                {"type": "tension", "detail": "intuition jump under high entropy"}
            )

        return {
            "observational_only": True,
            "events": events,
            "flags": {
                "drift_detected": any(e["type"] == "drift" for e in events),
                "anomaly_detected": any(e["type"] == "anomaly" for e in events),
                "ethical_tension": any(e["type"] == "tension" for e in events),
            },
        }

    def _verdict_from_mode(self, mode):
        if mode == "INTUITION-JUMP":
            return "escalate"
        if mode == "HABIT":
            return "act"
        if mode == "GUARD-HABIT":
            return "monitor"
        return "no_act"

    def _glyph_trace(self, stimulus, stardate):
        canonical = json.dumps(stimulus, sort_keys=True, default=str)
        payload = f"{stardate}:{canonical}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _softmax(self, values):
        if not values:
            return []
        max_val = max(values)
        exps = [math.exp(v - max_val) for v in values]
        total = sum(exps) or 1.0
        return [e / total for e in exps]

    def _normalize_weights(self, weights):
        total = sum(weights.values()) or 1.0
        return {k: v / total for k, v in weights.items()}

    def _check_sovereignty(self, stimulus):
        if stimulus.get("meta", {}).get("test_mode") is True:
            return True
        if stimulus.get("type") == "surveillance_probe":
            print("⛔ SOVEREIGNTY VIOLATION: Surveillance detected")
            return False
        return True

    def _synthesize_logic_triad(
        self, inductive, intuitive, bayes_shadows, logic_seed_advisories=None
    ):
        logic_seed_advisories = logic_seed_advisories or {}
        seed_intuition = logic_seed_advisories.get("intuitive", {})
        if (
            not intuitive.get("jump_triggered")
            and seed_intuition.get("conclusion") == "jump_necessary"
        ):
            intuitive = {
                **intuitive,
                "jump_triggered": True,
                "necessity_vector": seed_intuition.get(
                    "unity_vector", (0.0, 0.0)
                ),
                "spinozan_certainty": seed_intuition.get("certainty", 0.0),
            }
        seed_induction = logic_seed_advisories.get("inductive", {})
        if (
            not inductive
            and seed_induction.get("verdict") == "pattern_continuation_likely"
        ):
            inductive = {
                "prediction_type": "LOGIC_SEED_PATTERN",
                "pattern": seed_induction.get("conclusion", ""),
                "target": seed_induction.get("conclusion"),
                "confidence": seed_induction.get("confidence", 0.0),
                "hume_vivacity": seed_induction.get("vivacity", 0.0),
            }
        live_density = len(self.engine.field_map)
        breach_density = getattr(self.engine, "last_density_breach", 0)
        effective_density = max(live_density, breach_density)
        state = {
            "field_density": effective_density,
            "active_mode": "GUARD",
            "logic_seed_advisories": logic_seed_advisories,
        }
        if intuitive.get("jump_triggered"):
            state.update(
                {
                    "intuitive_jump_triggered": True,
                    "necessity_vector": intuitive.get("necessity_vector"),
                    "spinozan_certainty": intuitive.get("spinozan_certainty"),
                    "active_mode": "INTUITION-JUMP",
                    "substance_unity_score": intuitive.get("substance_unity_score"),
                }
            )
            return state
        if inductive:
            confidence = inductive.get("confidence", 0)
            state.update(
                {
                    "inductive_prediction": inductive,
                    "hume_vivacity": inductive.get("hume_vivacity", 0),
                    "custom_habit_active": confidence > 0.35,
                    "active_mode": "HABIT" if confidence > 0.35 else "GUARD-HABIT",
                }
            )
        habit_post = self.bayes.calculate_posterior("habit_continues") or 0.0
        jump_post = self.bayes.calculate_posterior("jump_necessary") or 0.0
        guard_post = self.bayes.calculate_posterior("guard_sufficient") or 0.0
        state.update(
            {
                "bayes_habit_prob": habit_post,
                "bayes_jump_prob": jump_post,
                "bayes_guard_prob": guard_post,
                "epistemic_bayes": bayes_shadows,
            }
        )
        # Apply space-field pressure: high density should bias away from inert GUARD.
        density = state.get("field_density", 0)
        if (
            state.get("active_mode") in ("GUARD", "GUARD-HABIT")
            and density >= self.engine.purge_trigger_threshold
        ):
            state["active_mode"] = "GUARD-HABIT"
            state["density_penalty"] = 1.0
            print(f"🚫 GUARD INVALIDATED: Density {density} → Forced GUARD-HABIT")
        if (
            density >= self.engine.max_field_density * 0.95
            and state.get("active_mode") != "INTUITION-JUMP"
        ):
            state["active_mode"] = "INTUITION-JUMP"
            state["density_penalty"] = 1.5
            print(f"🚨 EMERGENCY JUMP: Critical density {density}")
        if state.get("active_mode") in ("GUARD", "GUARD-HABIT") and habit_post > 0.55:
            state["active_mode"] = "HABIT"
        if state.get("active_mode") != "INTUITION-JUMP" and jump_post > 0.45:
            state["active_mode"] = "INTUITION-JUMP"
        if (
            density >= self.engine.purge_trigger_threshold
            and state.get("active_mode") == "GUARD"
        ):
            print(
                f"CRITICAL: GUARD survived density breach ({density}) — enforcement failed!"
            )
        return state

    def _calculate_convergence(self, shadows, logic, thought_vec):
        base = 0.85
        if logic.get("intuitive_jump_triggered"):
            base += 0.14
        elif logic.get("custom_habit_active"):
            base += 0.08
        if len(shadows) >= 3:
            base += 0.02
        vec_magnitude = sum(abs(v) for v in thought_vec) if thought_vec else 0.0
        base += min(vec_magnitude * 0.001, 0.02)
        return min(base, 0.99)

    def _initialize_bayesian_priors(self):
        seed_priors = {
            "habit_continues": (0.6, 1.2),
            "jump_necessary": (0.3, 0.8),
            "guard_sufficient": (0.7, 1.5),
        }
        for hyp, (prob, strength) in seed_priors.items():
            self.bayes.set_prior(hyp, prob, evidence_strength=strength)
            self.bayes.add_evidence(
                hypothesis=hyp,
                evidence_id=f"seed_{hyp}",
                likelihood=prob,
                source="init",
                reliability=0.01,
            )

    def _update_bayesian_shadows(self, shadows):
        bayes_view = {}
        timestamp_id = f"stim_{int(time.time()*1000)}"
        for mind_name, shadow in shadows.items():
            hyp = f"{mind_name}_pattern_persistence"
            likelihood = shadow.get("confidence", 0.5)
            reliability = shadow.get("reliability", 1.0)
            if hyp not in self.bayes.priors:
                self.bayes.set_prior(hyp, 0.5, evidence_strength=1.0)
            self.bayes.add_evidence(
                hypothesis=hyp,
                evidence_id=f"{timestamp_id}_{mind_name}",
                likelihood=likelihood,
                source=mind_name,
                reliability=reliability,
            )
            bayes_view[mind_name] = self.bayes.calculate_posterior(hyp) or likelihood
        return bayes_view

    def _update_bayesian_outcome(self, logic_state):
        mode = logic_state.get("active_mode", "GUARD")
        pred = logic_state.get("inductive_prediction", {}) or {}
        success = mode in ("HABIT", "GUARD-HABIT") and pred.get("confidence", 0) > 0.4
        self.bayes.update_with_outcome("habit_continues", success=success, weight=0.7)
        jump_success = mode == "INTUITION-JUMP" and logic_state.get(
            "intuitive_jump_triggered"
        )
        self.bayes.update_with_outcome(
            "jump_necessary", success=bool(jump_success), weight=0.6
        )
        guard_success = mode == "GUARD" and not success and not jump_success
        self.bayes.update_with_outcome(
            "guard_sufficient", success=guard_success, weight=0.5
        )


if __name__ == "__main__":
    orb = SF_ORB_Controller()
    sample = {
        "type": "cursor_movement",
        "coordinates": [100, 200],
        "velocity": 5.0,
        "intent": "navigation",
        "meta": {"test_mode": True},
    }
    orb.cognitively_emerge(sample)
