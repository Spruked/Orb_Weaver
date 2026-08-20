
import os
import json
import math
import random
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
from collections import defaultdict
import hashlib
import time
from pathlib import Path

PHI = (1 + np.sqrt(5)) / 2  # golden ratio

def generate_phasor_glyph(stimulus: Dict, base_conf: float, dim: int = 18) -> np.ndarray:
    """Returns 18D complex phasor vector with golden-ratio damping."""
    # Seed from stimulus hash for determinism
    seed = hash(str(stimulus)) & 0xFFFFFFFF
    np.random.seed(seed)

    phases = np.random.uniform(0, 2 * np.pi, dim)
    magnitudes = np.ones(dim) * base_conf

    # Golden-ratio phase damping (successive rotation by PHI)
    damping = np.array([PHI ** -i for i in range(dim)])
    phases = phases * damping

    # Convert to complex phasors
    phasors = magnitudes * np.exp(1j * phases)

    # Final real-valued projection for cosine similarity in EGF
    glyph = np.real(phasors) + np.imag(phasors)  # 18D real vector
    return glyph / np.linalg.norm(glyph)  # unit vector

# ============================================================
# TPC - Triple Predicate Cubed
# Core Implementation with All Nuances & Refinements
# ============================================================

class Philosophers(Enum):
    HUME = "hume"
    KANT = "kant"
    LOCKE = "locke"
    SPINOZA = "spinoza"

@dataclass
class GeometricGlyph:
    """Phasor-derived coordinate vector in HLSF dimensional geometry"""
    coordinates: np.ndarray
    phase_angle: float
    vivacity: float = 1.0
    golden_ratio_damping: float = 0.618033988749895
    
    def __post_init__(self):
        if len(self.coordinates) != 18:
            raise ValueError("HLSF requires exactly 18 dimensions")
        self.coordinates = self.coordinates.astype(np.float64)
        self._apply_phase_damping()
    
    def _apply_phase_damping(self):
        """Golden-ratio phase damping as per specification"""
        damping = self.golden_ratio_damping ** (self.phase_angle / (2 * np.pi))
        self.coordinates *= damping
    
    def distance_to(self, other: 'GeometricGlyph') -> float:
        """Geometric distance IS the confidence score"""
        return float(np.linalg.norm(self.coordinates - other.coordinates))
    
    def cosine_similarity(self, other: 'GeometricGlyph') -> float:
        """Cosine similarity for vault retrieval"""
        dot = np.dot(self.coordinates, other.coordinates)
        norm = np.linalg.norm(self.coordinates) * np.linalg.norm(other.coordinates)
        return float(dot / norm) if norm > 0 else 0.0
    
    def to_dict(self) -> dict:
        return {
            "coordinates": self.coordinates.tolist(),
            "phase_angle": self.phase_angle,
            "vivacity": self.vivacity
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GeometricGlyph':
        return cls(
            coordinates=np.array(data["coordinates"]),
            phase_angle=data["phase_angle"],
            vivacity=data.get("vivacity", 1.0)
        )

@dataclass
class DriftPing:
    """Forward-only confirmation handshake chain"""
    gate_id: str
    timestamp: float
    signal_hash: str
    previous_ping_hash: Optional[str] = None
    confirmed: bool = False
    
    def compute_hash(self) -> str:
        data = f"{self.gate_id}:{self.timestamp}:{self.signal_hash}:{self.previous_ping_hash}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def confirm(self) -> bool:
        self.confirmed = True
        return True

class VaultEntry:
    """A Priori or A Posteriori vault entry with geometric signature"""
    def __init__(self, content: Any, glyph: GeometricGlyph, 
                 weight: float = 1.0, entry_type: str = "posteriori",
                 philosopher_bindings: Optional[Dict] = None):
        self.content = content
        self.glyph = glyph
        self.weight = weight
        self.entry_type = entry_type  # "priori" or "posteriori"
        self.philosopher_bindings = philosopher_bindings or {}
        self.retrieval_count = 0
        self.created_at = time.time()
    
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "glyph": self.glyph.to_dict(),
            "weight": self.weight,
            "entry_type": self.entry_type,
            "philosopher_bindings": self.philosopher_bindings,
            "retrieval_count": self.retrieval_count,
            "created_at": self.created_at
        }

class HLSF:
    """High-Level Space Field - 18D traversal environment"""
    HYSTERESIS_TRIGGER = 700
    HYSTERESIS_RELEASE = 520
    
    def __init__(self):
        self.nodes: Dict[str, GeometricGlyph] = {}
        self.vivacity_threshold = 0.3
        self.edge_cutter_active = False
        self.node_count = 0
    
    def add_node(self, node_id: str, glyph: GeometricGlyph) -> bool:
        """Add node with vivacity weighting"""
        self.nodes[node_id] = glyph
        self.node_count += 1
        
        # Edge-cutter hysteresis
        if self.node_count >= self.HYSTERESIS_TRIGGER:
            self.edge_cutter_active = True
            self._prune_low_vivacity()
        elif self.node_count <= self.HYSTERESIS_RELEASE and self.edge_cutter_active:
            self.edge_cutter_active = False
        
        return True
    
    def _prune_low_vivacity(self):
        """Sovereign forgetting - prune low-vivacity nodes"""
        to_remove = [
            nid for nid, glyph in self.nodes.items() 
            if glyph.vivacity < self.vivacity_threshold
        ]
        for nid in to_remove:
            del self.nodes[nid]
            self.node_count -= 1
    
    def traverse(self, query_glyph: GeometricGlyph, top_k: int = 5) -> List[Tuple[str, float]]:
        """Traverse HLSF and return nearest nodes with distances"""
        distances = []
        for node_id, glyph in self.nodes.items():
            dist = query_glyph.distance_to(glyph)
            distances.append((node_id, dist, glyph.vivacity))
        
        # Weight by vivacity
        distances.sort(key=lambda x: x[1] / max(x[2], 0.01))
        return [(nid, dist) for nid, dist, _ in distances[:top_k]]

class EGF:
    """Epistemic Gravity Field - Certainty-as-gravity retrieval physics"""
    def __init__(self, hlsf: HLSF):
        self.hlsf = hlsf
        self.gravity_constant = 1.0
        self.certainty_threshold = 0.7
    
    def compute_gravity(self, query_glyph: GeometricGlyph, 
                       vault_glyph: GeometricGlyph) -> float:
        """High-certainty signatures exert stronger gravitational pull"""
        distance = query_glyph.distance_to(vault_glyph)
        certainty = vault_glyph.vivacity  # Certainty maps to vivacity
        
        # Inverse square law with certainty weighting
        if distance == 0:
            return float('inf')
        
        gravity = (self.gravity_constant * certainty) / (distance ** 2)
        return gravity
    
    def retrieve_with_physics(self, query_glyph: GeometricGlyph, 
                             vault_entries: List[VaultEntry],
                             top_k: int = 3) -> List[Tuple[VaultEntry, float, float]]:
        """Retrieve using gravity physics - returns (entry, gravity, distance)"""
        results = []
        for entry in vault_entries:
            gravity = self.compute_gravity(query_glyph, entry.glyph)
            distance = query_glyph.distance_to(entry.glyph)
            results.append((entry, gravity, distance))
        
@dataclass
class Verdict:
    conclusion: str
    confidence: float          # 0.0–0.95 (ECM hard cap)
    rationale_trace: List[str] # human-auditable chain
    glyph_vector: np.ndarray   # for EGF later

class PhilosopherCore:
    """Base class for every beam — pure probabilistic state machine"""
    def __init__(self, name: str, rules: Dict[str, Any], weight: float = 0.25):
        self.name = name
        self.rules = rules                    # declarative rule set
        self.weight = weight
        self.transition_graph = self._build_graph()  # adjacency list + probabilities

    def _build_graph(self):
        """Override per core — returns {state: [(next_state, prob, condition_fn)]}"""
        raise NotImplementedError

    def process(self, stimulus: Dict[str, Any], depth: int = 0) -> Verdict:
        """K⁰/K¹/K² recursion entry point"""
        current_state = "START"
        trace = [f"{self.name}@{depth}: START"]
        confidence = 1.0

        for _ in range(8):  # safety bound on loop depth
            transitions = self.transition_graph.get(current_state, [])
            admissible = [
                (next_s, p, cond) for next_s, p, cond in transitions
                if cond(stimulus, confidence)
            ]
            if not admissible:
                break

            # Softmax over admissible transitions only
            probs = np.array([p for _, p, _ in admissible])
            probs /= probs.sum()
            choice_idx = np.random.choice(len(admissible), p=probs)
            next_state, _, cond = admissible[choice_idx]

            trace.append(f"{self.name}@{depth}: {next_state} (conf={confidence:.3f})")
            confidence = self._update_confidence(confidence, next_state, stimulus)
            current_state = next_state

            if current_state == "TERMINAL":
                break

        glyph = self._compute_glyph(stimulus, confidence)  # phasor vector for EGF
        return Verdict(
            conclusion=current_state,
            confidence=min(confidence, 0.95),
            rationale_trace=trace,
            glyph_vector=glyph
        )

    def _update_confidence(self, conf: float, state: str, stimulus: Dict) -> float:
        """Beam-specific confidence decay/boost — override per core"""
        return conf * 0.92  # default decay; each core overrides

    def _compute_glyph(self, stimulus: Dict, conf: float) -> np.ndarray:
        return generate_phasor_glyph(stimulus, conf)
# Concrete Core Implementations (Copy-Paste Ready)

class HumeCore(PhilosopherCore):
    def __init__(self):
        rules = {
            "empirical_trace": lambda s, c: s.get("empirical_evidence", 0) > 0.6,
            "no_pure_causal": lambda s, c: not s.get("pure_causal_claim", False),
            "no_abstraction_without_anchor": lambda s, c: s.get("empirical_evidence", 0) > 0.6,
        }
        super().__init__("HumeCore", rules)

    def _build_graph(self):
        return {
            "START": [
                ("EMPIRICAL_CHECK", 0.50, lambda s, c: s.get("empirical_evidence", 0) > 0.6),
                ("CAUSAL_REJECT", 0.30, lambda s, c: s.get("pure_causal_claim", False)),
                ("ABSTRACTION_CHECK", 0.20, lambda s, c: s.get("empirical_evidence", 0) <= 0.6),
            ],
            "EMPIRICAL_CHECK": [
                ("TERMINAL", 1.0, lambda s, c: s.get("empirical_evidence", 0) > 0.6),
                ("REJECT", 1.0, lambda s, c: s.get("empirical_evidence", 0) <= 0.6)
            ],
            "CAUSAL_REJECT": [("REJECT", 1.0, lambda s, c: True)],
            "ABSTRACTION_CHECK": [("REJECT", 1.0, lambda s, c: True)],
            "REJECT": [("TERMINAL", 1.0, lambda s, c: True)],  # low-conf terminal
            "TERMINAL": []
        }

    def _update_confidence(self, conf: float, state: str, stimulus: Dict) -> float:
        if state == "REJECT":
            return conf * 0.25  # hard downgrade on rejection path
        if state == "TERMINAL" and stimulus.get("empirical_evidence", 0) > 0.6:
            return min(conf * 1.08, 0.95)  # only boost on good empirical path
        return conf * 0.98  # light decay elsewhere

class KantCore(PhilosopherCore):
    def __init__(self):
        rules = {
            "reject_contradiction": lambda s, c: not s.get("has_contradiction", False),
            "universalizable": lambda s, c: s.get("can_universalize", True),
            "agent_dignity": lambda s, c: s.get("respects_agency", True),
            "duty_over_expedience": lambda s, c: not s.get("expedient_but_immoral", False),
        }
        super().__init__("KantCore", rules)

    def _build_graph(self):
        return {
            "START": [
                ("CHECK_CONTRADICTION", 0.4, lambda s, c: True),
                ("TEST_UNIVERSAL", 0.3, lambda s, c: True),
                ("DIGNITY_CHECK", 0.2, lambda s, c: True),
                ("DUTY_VS_EXPEDIENCE", 0.1, lambda s, c: True),
            ],
            "CHECK_CONTRADICTION": [
                ("REJECT", 1.0, lambda s, c: s.get("has_contradiction", False)),
                ("TERMINAL", 1.0, lambda s, c: not s.get("has_contradiction", False))
            ],
            "TEST_UNIVERSAL": [
                ("TERMINAL", 1.0, lambda s, c: s.get("can_universalize", True)),
                ("REJECT", 1.0, lambda s, c: not s.get("can_universalize", True))
            ],
            "DIGNITY_CHECK": [
                ("TERMINAL", 1.0, lambda s, c: s.get("respects_agency", True)),
                ("REJECT", 1.0, lambda s, c: not s.get("respects_agency", True))
            ],
            "DUTY_VS_EXPEDIENCE": [
                ("TERMINAL", 1.0, lambda s, c: not s.get("expedient_but_immoral", False)),
                ("REJECT", 1.0, lambda s, c: s.get("expedient_but_immoral", False))
            ],
            "REJECT": [("TERMINAL", 1.0, lambda s, c: True)],
            "TERMINAL": []
        }

    def _update_confidence(self, conf: float, state: str, stimulus: Dict) -> float:
        if state == "REJECT":
            return conf * 0.25  # hard downgrade on rejection path
        if state == "CHECK_CONTRADICTION" and stimulus.get("has_contradiction"):
            return conf * 0.1
        if state == "DUTY_VS_EXPEDIENCE" and stimulus.get("expedient_but_immoral") and not stimulus.get("catastrophic_harm_override"):
            return conf * 0.2
        return super()._update_confidence(conf, state, stimulus)

class LockeCore(PhilosopherCore):
    def __init__(self):
        rules = {
            "rights_evidence": lambda s, c: s.get("has_rights_evidence", False),
            "consent_present": lambda s, c: s.get("consent_explicit_or_implied", True),
            "autonomy_preserved": lambda s, c: not s.get("violates_autonomy", False),
            "legitimate_authority": lambda s, c: s.get("authority_justified", True),
        }
        super().__init__("LockeCore", rules)

    def _build_graph(self):
        return {
            "START": [
                ("CHECK_RIGHTS_EVIDENCE", 0.35, lambda s, c: True),
                ("VERIFY_CONSENT", 0.35, lambda s, c: True),
                ("AUTONOMY_CHECK", 0.20, lambda s, c: True),
                ("AUTHORITY_CHECK", 0.10, lambda s, c: s.get("authority_justified", True) and not s.get("violates_autonomy", False)),
            ],
            "CHECK_RIGHTS_EVIDENCE": [
                ("TERMINAL", 1.0, lambda s, c: s.get("has_rights_evidence", False)),
                ("REJECT", 1.0, lambda s, c: not s.get("has_rights_evidence", False))
            ],
            "VERIFY_CONSENT": [
                ("TERMINAL", 1.0, lambda s, c: s.get("consent_explicit_or_implied", True)),
                ("REJECT", 1.0, lambda s, c: not s.get("consent_explicit_or_implied", True))
            ],
            "AUTONOMY_CHECK": [
                ("REJECT", 1.0, lambda s, c: s.get("violates_autonomy", False)),
                ("TERMINAL", 1.0, lambda s, c: not s.get("violates_autonomy", False))
            ],
            "AUTHORITY_CHECK": [
                ("TERMINAL", 1.0, lambda s, c: s.get("authority_justified", True)),
                ("REJECT", 1.0, lambda s, c: not s.get("authority_justified", True))
            ],
            "REJECT": [("TERMINAL", 1.0, lambda s, c: True)],
            "TERMINAL": []
        }

    def _update_confidence(self, conf: float, state: str, stimulus: Dict) -> float:
        if state == "REJECT":
            return conf * 0.25  # hard downgrade on rejection path
        if state == "TERMINAL" and stimulus.get("has_rights_evidence", False) and stimulus.get("consent_explicit_or_implied", True) and not stimulus.get("violates_autonomy", False) and stimulus.get("authority_justified", True):
            return min(conf * 1.05, 0.95)  # only boost on good path
        return conf * 0.98  # light decay elsewhere

class SpinozaCore(PhilosopherCore):
    def __init__(self):
        rules = {
            "axiomatic_derivation": lambda s, c: s.get("derivation_chain_complete", True),
            "system_coherence": lambda s, c: not s.get("breaks_whole_state", False),
            "necessity_over_plausibility": lambda s, c: s.get("necessary_conclusion", True),
        }
        super().__init__("SpinozaCore", rules)

    def _build_graph(self):
        return {
            "START": [
                ("BUILD_AXIOM_CHAIN", 0.40, lambda s, c: True),
                ("CHECK_SYSTEM_COHERENCE", 0.40, lambda s, c: True),
                ("TEST_NECESSITY", 0.20, lambda s, c: True),
            ],
            "BUILD_AXIOM_CHAIN": [
                ("TERMINAL", 1.0, lambda s, c: s.get("derivation_chain_complete", True)),
                ("REJECT", 1.0, lambda s, c: not s.get("derivation_chain_complete", True))
            ],
            "CHECK_SYSTEM_COHERENCE": [
                ("TERMINAL", 1.0, lambda s, c: not s.get("breaks_whole_state", False)),
                ("REJECT", 1.0, lambda s, c: s.get("breaks_whole_state", False))
            ],
            "TEST_NECESSITY": [
                ("TERMINAL", 1.0, lambda s, c: s.get("necessary_conclusion", True)),
                ("REJECT", 1.0, lambda s, c: not s.get("necessary_conclusion", True))
            ],
            "REJECT": [("TERMINAL", 1.0, lambda s, c: True)],
            "TERMINAL": []
        }

    def _update_confidence(self, conf: float, state: str, stimulus: Dict) -> float:
        if state == "REJECT":
            return conf * 0.25  # hard downgrade on rejection path
        if state == "TERMINAL" and stimulus.get("derivation_chain_complete", True):
            return min(conf * 1.05, 0.95)  # only boost on complete chains
        return conf * 0.98  # light decay elsewhere

class MultiBeamRunner:
    def __init__(self):
        self.beams = [
            HumeCore(), KantCore(), LockeCore(), SpinozaCore()
        ]
        # initial equal weights
        self.shadow_propagation_weight = 0.10

    def run_k_depth(self, stimulus: Dict[str, Any], max_depth: int = 2) -> List[Verdict]:
        verdicts = []
        for depth in range(max_depth + 1):
            depth_verdicts = []
            for beam in self.beams:
                verdict = beam.process(stimulus, depth=depth)
                depth_verdicts.append(verdict)
            verdicts.extend(depth_verdicts)

            # ShadowPropagation: inject confidence scalars only
            avg_conf = np.mean([v.confidence for v in depth_verdicts])
            for beam in self.beams:
                # each beam can slightly adjust internal state based on aggregate confidence
                pass  # minimal cross-talk

        return verdicts

class PhaseCoherence:
    """Phase Coherence Signal - KayGee derived measurement"""
    
    def __init__(self):
        self.coherence_threshold = 0.6
        self.divergence_threshold = 0.3
    
    def measure(self, verdicts: List[Verdict]) -> Tuple[float, str]:
        """Measure phase coherence across philosopher beams"""
        confidences = [v.confidence for v in verdicts]

        if not confidences:
            return 0.0, "no_signal"

        # Coherence = 1 - normalized variance, weighted by mean confidence
        mean_conf = sum(confidences) / len(confidences)
        variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)
        coherence = (1.0 - (variance / max(mean_conf ** 2, 0.01))) * mean_conf

        if coherence > self.coherence_threshold:
            return coherence, "convergence"
        elif coherence < self.divergence_threshold:
            return coherence, "divergence"
        else:
            return coherence, "partial"

class DepthRecursion:
    """K⁰→K¹→K² Depth Recursion"""
    
    def __init__(self):
        self.max_depth = 2  # K⁰, K¹, K²
        self.depth_weights = [1.0, 0.7, 0.4]
    
    def recurse(self, input_glyph: GeometricGlyph, 
                processor: Callable, context: Dict) -> List[Tuple[int, GeometricGlyph, Any]]:
        """Perform depth recursion - output becomes input for deeper level"""
        results = []
        current_glyph = input_glyph
        
        for depth in range(self.max_depth + 1):
            # Process at current depth
            processed = processor(current_glyph, context, depth)
            results.append((depth, current_glyph, processed))
            
            # Output becomes input for next depth (abstraction)
            if depth < self.max_depth:
                current_glyph = self._abstract_glyph(current_glyph, processed)
        
        return results
    
    def _abstract_glyph(self, glyph: GeometricGlyph, 
                       processing_result: Any) -> GeometricGlyph:
        """Abstract glyph for next depth level"""
        # Simplified abstraction: reduce dimensionality emphasis
        new_coords = glyph.coordinates * 0.8  # Dampen for abstraction
        new_phase = (glyph.phase_angle + np.pi / 4) % (2 * np.pi)
        
        return GeometricGlyph(
            coordinates=new_coords,
            phase_angle=new_phase,
            vivacity=glyph.vivacity * 0.9
        )

class ECM:
    """Epistemic Contract Management - Escalation Gate"""
    
    def __init__(self):
        self.runtime_invariants = 30  # Hard requirement
        self.confidence_cap = 0.95  # Hard cap - no 100% certainty
        self.escalation_triggers = ["novelty", "incoherence", "paradox", "vault_miss"]
        self.invariant_checks = self._setup_invariants()
    
    # Maps index → human-readable invariant name
    INVARIANT_NAMES = {
        0: "confidence_within_cap",
        1: "four_beams_present",
        2: "drift_ping_confirmed",
        3: "phase_coherence_measured",
        4: "vault_integrity",
    }

    def _setup_invariants(self) -> List[Callable]:
        """Setup 30 runtime invariants (all active)."""
        inv = []
        # ── Group 1: Core pipeline integrity (0-4) ──────────────────────────────
        inv.append(lambda ctx: ctx.get("confidence", 0) <= self.confidence_cap)
        inv.append(lambda ctx: ctx.get("philosopher_count", 0) == 4)
        inv.append(lambda ctx: ctx.get("drift_ping_confirmed", False))
        inv.append(lambda ctx: ctx.get("phase_coherence_measured", False))
        inv.append(lambda ctx: ctx.get("vault_integrity", True))
        # ── Group 2: Confidence bounds (5-9) ────────────────────────────────────
        inv.append(lambda ctx: ctx.get("confidence", 0) >= 0.0)
        inv.append(lambda ctx: ctx.get("confidence", 1.0) < 1.0)           # strict < 1
        inv.append(lambda ctx: ctx.get("beam_variance", 0.0) <= 1.0)
        inv.append(lambda ctx: ctx.get("synthesis_trace_len", 0) >= 1)
        inv.append(lambda ctx: ctx.get("glyph_finite", True))
        # ── Group 3: Input validation (10-14) ────────────────────────────────────
        inv.append(lambda ctx: isinstance(ctx.get("input_text", ""), str))
        inv.append(lambda ctx: len(ctx.get("input_text", "x")) > 0)
        inv.append(lambda ctx: ctx.get("query_id", None) is not None)
        inv.append(lambda ctx: ctx.get("input_type", "") in ("text", "audio", "glyph"))
        inv.append(lambda ctx: ctx.get("acp_glyph_dim", 18) == 18)
        # ── Group 4: Phase coherence bounds (15-19) ──────────────────────────────
        inv.append(lambda ctx: 0.0 <= ctx.get("phase_score", 0.5) <= 1.0)
        inv.append(lambda ctx: ctx.get("phase_status", "") in ("convergence", "partial", "divergence", "no_signal", ""))
        inv.append(lambda ctx: ctx.get("beam_count", 0) >= 4)
        inv.append(lambda ctx: ctx.get("k_depth", 0) in (0, 1, 2))
        inv.append(lambda ctx: ctx.get("max_beam_confidence", 0.0) <= self.confidence_cap)
        # ── Group 5: Vault & ECM (20-24) ─────────────────────────────────────────
        inv.append(lambda ctx: ctx.get("vault_entry_count", 0) >= 0)
        inv.append(lambda ctx: ctx.get("ecm_invariant_count", 0) == 30)
        inv.append(lambda ctx: not (ctx.get("contract_violated", False) and ctx.get("confidence", 0) > 0.6))
        inv.append(lambda ctx: ctx.get("synthesis_conclusion", "") != "")
        inv.append(lambda ctx: ctx.get("drift_chain_depth", 1) >= 1)
        # ── Group 6: Safety & ethical gates (25-29) ──────────────────────────────
        inv.append(lambda ctx: ctx.get("escalation_reason", "none") != "")
        inv.append(lambda ctx: not ctx.get("paradox_detected", False) or ctx.get("escalation_triggered", False))
        inv.append(lambda ctx: ctx.get("tribunal_beams_used", 0) == 4)
        inv.append(lambda ctx: ctx.get("no_null_conclusion", True))
        inv.append(lambda ctx: ctx.get("runtime_invariant_count", 30) == 30)
        return inv

    def check_invariants(self, context: Dict) -> Tuple[bool, List[str]]:
        """Check all 30 runtime invariants. Returns (passed, named_violations)."""
        violations = []
        for i, invariant in enumerate(self.invariant_checks):
            try:
                if not invariant(context):
                    name = self.INVARIANT_NAMES.get(i, f"invariant_{i}")
                    violations.append(name)
            except Exception as e:
                violations.append(f"{self.INVARIANT_NAMES.get(i, f'invariant_{i}')}_error")
        return len(violations) == 0, violations
    
    def should_escalate(self, context: Dict) -> Tuple[bool, str]:
        """Determine if escalation is needed"""
        if context.get("novelty_score", 0) > 0.8:
            return True, "novelty"
        if context.get("phase_coherence") == "divergence":
            return True, "incoherence"
        if context.get("paradox_detected", False):
            return True, "paradox"
        if context.get("vault_miss", False):
            return True, "vault_miss"
        
        return False, "none"
    
    def apply_confidence_cap(self, confidence: float) -> float:
        """Apply hard 0.95 confidence cap"""
        return min(confidence, self.confidence_cap)

@dataclass
class TribunalOutput:
    final_conclusion: str
    final_confidence: float
    synthesis_trace: List[str]
    combined_glyph: np.ndarray
    contract_violated: bool = False
    violations: List[str] = None

    def __post_init__(self):
        if self.violations is None:
            self.violations = []

class TribunalSynthesizer:
    """Integrates all four philosopher verdicts - NOT majority vote"""

    def __init__(self, beams: List[PhilosopherCore]):
        self.beams = beams  # for weight lookup

    def synthesize(self, verdicts: List[Verdict]) -> TribunalOutput:
        if not verdicts:
            return TribunalOutput("NO_INPUT", 0.0, ["ERROR"], np.zeros(18))

        confs = np.array([v.confidence for v in verdicts])
        weights = np.array([b.weight for b in self.beams])  # all 0.25

        # Weighted average (primary signal)
        weighted_avg = np.average(confs, weights=weights)

        # Gentle coherence bonus (only penalize large divergence)
        std = np.std(confs)
        coherence_bonus = max(0.0, 1.0 - (std / 0.1))   # drop faster for high variance

        # Final confidence = weighted average boosted by coherence
        final_conf = min(weighted_avg * (1.0 + coherence_bonus), 0.95)

        # Best conclusion + full trace
        best_idx = np.argmax(confs)
        final_conclusion = verdicts[best_idx].conclusion

        trace = ["TribunalSynthesizer (resolved fusion):"]
        for i, v in enumerate(verdicts):
            trace.append(f"  {self.beams[i].name}@{v.confidence:.4f} → {v.rationale_trace[-1]}")
        trace.append(f"→ Final: {final_conclusion} @ {final_conf:.4f} (coherence_bonus={coherence_bonus:.3f})")

        # Combined glyph = confidence-weighted average
        combined_glyph = np.average([v.glyph_vector for v in verdicts], axis=0, weights=confs)

        return TribunalOutput(final_conclusion, final_conf, trace, combined_glyph)

        return TribunalOutput(final_conclusion, final_conf, trace, combined_glyph)

print("Core TPC classes defined successfully")
print(f"HLSF dimensions: 18D")
print(f"Philosopher beams: 4 (Hume, Kant, Locke, Spinoza)")
print(f"Confidence cap: 0.95")
print(f"Runtime invariants: 30")
