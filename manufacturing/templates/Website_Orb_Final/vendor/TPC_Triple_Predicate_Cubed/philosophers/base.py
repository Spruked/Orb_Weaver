# philosophers/base.py
#
# STATUS: citation layer — deferred integration
#
# This module implements HumeBeam, KantBeam, LockeBeam, SpinozaBeam backed
# by the seed JSON vaults (philosophers/seed_*.json). These are richer
# implementations than the inline beams in tpc_cubed.py: they load empirical
# parameters, performance metrics, and reasoning entries from the vault files.
#
# DEFERRED BECAUSE: the live API pipeline uses tpc_cubed.py beams directly.
# Wiring this module in requires replacing the MultiBeamRunner beam list with
# these vault-backed classes — a scoped refactor, not a quick swap.
#
# INTEGRATION PATH (when ready):
#   1. Replace tpc_cubed.MultiBeamRunner.beams with instances from this module
#   2. Verify PhilosopherVerdict fields match tpc_cubed.Verdict interface
#   3. Run demo_test.run_all_tests() — all 10 must still PASS
#
# Do not delete. Do not use as runtime import until the step above is complete.
# See ARCHITECTURE_REGISTRY.md § Philosophers (seed data)

import json
import numpy as np
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass

try:
    from core.geometric_primitives import PHI
except ImportError:
    PHI = (1 + np.sqrt(5)) / 2

PHILOSOPHER_DIR = Path(__file__).resolve().parent


def _load_seed_vault(seed_name: str) -> Dict[str, Any]:
    """Load a philosopher seed JSON from the local philosophers folder."""
    path = PHILOSOPHER_DIR / f"seed_{seed_name}.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            vault = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "vault_id": f"seed_{seed_name}",
            "philosopher": seed_name.title(),
            "reasoning_type": "fallback",
            "entries": [],
            "learning_principles": [],
            "parameters": {},
            "operations": {},
            "performance_metrics": {},
            "loaded": False,
            "load_error": str(exc),
            "path": str(path),
        }

    vault["loaded"] = True
    vault["load_error"] = None
    vault["path"] = str(path)
    return vault


def _build_rule_set(seed_name: str, runtime_rules: Dict[str, Any]) -> Dict[str, Any]:
    """Merge runtime beam switches with the immutable seed vault."""
    seed_vault = _load_seed_vault(seed_name)
    entries = seed_vault.get("entries", [])
    entry_index = {
        entry.get("id"): entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("id")
    }

    return {
        **runtime_rules,
        "seed_vault": {
            "vault_id": seed_vault.get("vault_id"),
            "vault_name": seed_vault.get("vault_name"),
            "version": seed_vault.get("version"),
            "philosopher": seed_vault.get("philosopher"),
            "reasoning_type": seed_vault.get("reasoning_type"),
            "description": seed_vault.get("description"),
            "index": seed_vault.get("index", {}),
            "entries": entries,
            "entry_index": entry_index,
            "learning_principles": seed_vault.get("learning_principles", []),
            "parameters": seed_vault.get("parameters", {}),
            "operations": seed_vault.get("operations", {}),
            "performance_metrics": seed_vault.get("performance_metrics", {}),
            "loaded": seed_vault.get("loaded", False),
            "load_error": seed_vault.get("load_error"),
            "path": seed_vault.get("path"),
        },
    }

@dataclass
class PhilosopherVerdict:
    """Output from a philosopher beam"""
    confidence: float      # 0.0 to 1.0
    coherence: float       # Phase alignment
    verdict: str          # "admit", "reject", "suspend"
    reasoning: str        # Explanation
    beam_weight: float    # Current weight (starts at 0.25)

class PhilosopherBeam(ABC):
    """Base class for the Four-Beam Constraint Architecture"""
    
    def __init__(self, name: str):
        self.name = name
        self.beam_weight = 0.25  # Equal initial weights
        self.rule_set = self._initialize_rules()
        
    @abstractmethod
    def _initialize_rules(self) -> Dict:
        """Load the philosopher's rule set"""
        pass
    
    @abstractmethod
    def reason(self, stimulus: np.ndarray, depth: int) -> PhilosopherVerdict:
        """Pure probabilistic state machine - no LLM"""
        pass
    
    def softmax_confidence(self, logits: np.ndarray) -> float:
        """Softmax probability loop for confidence scoring"""
        exp_logits = np.exp(logits - np.max(logits))  # Numerical stability
        probs = exp_logits / np.sum(exp_logits)
        return float(np.max(probs))  # Confidence = max probability

    @property
    def seed_vault(self) -> Dict[str, Any]:
        return self.rule_set.get("seed_vault", {})

    def seed_parameter(self, key: str, default: Any = None) -> Any:
        return self.seed_vault.get("parameters", {}).get(key, default)

    def seed_metric(self, key: str, default: Any = None) -> Any:
        return self.seed_vault.get("performance_metrics", {}).get(key, default)

    def seed_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "vault_id": self.seed_vault.get("vault_id"),
            "reasoning_type": self.seed_vault.get("reasoning_type"),
            "entries": len(self.seed_vault.get("entries", [])),
            "loaded": self.seed_vault.get("loaded", False),
            "load_error": self.seed_vault.get("load_error"),
        }


class HumeBeam(PhilosopherBeam):
    """Empirical Skepticism: Claims require sensory evidence"""
    
    def _initialize_rules(self) -> Dict:
        return _build_rule_set("hume", {
            "requires_impression": True,
            "causal_skepticism": True,
            "reject_abstract_groundless": True,
            "probability_not_necessity": True
        })
    
    def reason(self, stimulus: np.ndarray, depth: int) -> PhilosopherVerdict:
        # Hume: Check for empirical grounding in stimulus
        # Higher variance = more empirical complexity = more skepticism needed
        variance = np.var(stimulus)
        mean_val = np.mean(np.abs(stimulus))
        
        # Grounded if there's clear signal structure
        empirical_threshold = 0.1
        if self.seed_parameter("knowledge_basis") == "impressions_only":
            empirical_threshold = 0.12
        is_grounded = variance > empirical_threshold and mean_val > 0.01
        
        # Depth affects skepticism (deeper = more scrutiny)
        skepticism = 0.3 + (depth * 0.2)
        if self.seed_metric("skepticism_level") == "radical":
            skepticism += 0.05
        if self.seed_parameter("induction_status") == "unjustified":
            skepticism += 0.02 * depth
        skepticism = min(skepticism, 0.95)
        
        if not is_grounded:
            confidence = 0.1
            verdict = "reject"
            reasoning = "No empirical impression detected in stimulus"
        else:
            # Confidence based on signal clarity
            logits = np.array([variance * 2, 1 - variance, skepticism])
            confidence = self.softmax_confidence(logits)
            verdict = "admit" if confidence > 0.6 else "suspend"
            reasoning = (
                f"Empirical variance {variance:.3f}; "
                f"{self.seed_vault.get('reasoning_type')} seed active"
            )
        
        return PhilosopherVerdict(
            confidence=confidence,
            coherence=1.0 - skepticism,
            verdict=verdict,
            reasoning=reasoning,
            beam_weight=self.beam_weight
        )


class KantBeam(PhilosopherBeam):
    """Categorical Reasoning: Universalizability without contradiction"""
    
    def _initialize_rules(self) -> Dict:
        return _build_rule_set("kant", {
            "universalizability_test": True,
            "no_contradiction": True,
            "duty_based": True,
            "preference_independent": True
        })
    
    def reason(self, stimulus: np.ndarray, depth: int) -> PhilosopherVerdict:
        # Kant: Check structural consistency across stimulus dimensions
        # Universalizability = pattern consistency across all 18 dims
        
        # Test if principle applies consistently (no internal contradiction)
        dims = len(stimulus) if len(stimulus) < 18 else 18
        consistency = 1.0 - np.std(stimulus[:dims]) / (np.mean(np.abs(stimulus[:dims])) + 1e-10)
        
        # Categorical imperative simulation: would this scale?
        scaling_test = np.all(np.diff(stimulus[:dims]) < np.mean(stimulus[:dims]))
        
        admit_threshold = 0.7
        suspend_threshold = 0.4
        if self.seed_parameter("certainty_level") == "necessary_for_experience":
            admit_threshold = 0.65
        if self.seed_parameter("knowledge_domain") == "phenomena_only":
            suspend_threshold = 0.35

        if consistency > admit_threshold and scaling_test:
            confidence = min(consistency * 0.95, 0.95)
            verdict = "admit"
            reasoning = f"Universalizable structure ({self.seed_vault.get('reasoning_type')}, consistency: {consistency:.3f})"
        elif consistency > suspend_threshold:
            confidence = consistency * 0.5
            verdict = "suspend"
            reasoning = "Partial universalizability within phenomenal bounds"
        else:
            confidence = 0.15
            verdict = "reject"
            reasoning = "Contradiction detected in categorical structure"
        
        return PhilosopherVerdict(
            confidence=confidence,
            coherence=consistency,
            verdict=verdict,
            reasoning=reasoning,
            beam_weight=self.beam_weight
        )


class LockeBeam(PhilosopherBeam):
    """Consent and Rights: Individual autonomy preservation"""
    
    def _initialize_rules(self) -> Dict:
        return _build_rule_set("locke", {
            "autonomy_preservation": True,
            "consent_required": True,
            "rights_primal": True,
            "authority_justification": True
        })
    
    def reason(self, stimulus: np.ndarray, depth: int) -> PhilosopherVerdict:
        # Locke: Check if reasoning preserves autonomy
        # Measure "rights violations" as extreme outliers (coercion signals)
        
        q75, q25 = np.percentile(stimulus, [75, 25])
        iqr = q75 - q25
        outliers = np.sum(np.abs(stimulus - np.median(stimulus)) > (1.5 * iqr))
        
        # Rights preserved if no extreme coercion (outliers)
        autonomy_score = 1.0 - (outliers / len(stimulus))
        if self.seed_parameter("innate_content") == "none":
            autonomy_score = min(1.0, autonomy_score + 0.02)
        
        # Check for legitimate authority (central tendency)
        legitimate_authority = np.median(stimulus) / (np.max(np.abs(stimulus)) + 1e-10)
        authority_threshold = 0.3
        if "reflection" in self.seed_parameter("knowledge_sources", []):
            authority_threshold = 0.25
        
        if autonomy_score > 0.8 and legitimate_authority > authority_threshold:
            confidence = autonomy_score * 0.9
            verdict = "admit"
            reasoning = f"Autonomy preserved ({self.seed_vault.get('reasoning_type')}, score: {autonomy_score:.3f})"
        elif autonomy_score > 0.5:
            confidence = autonomy_score * 0.6
            verdict = "suspend"
            reasoning = "Potential autonomy concerns - review consent mechanism"
        else:
            confidence = 0.1
            verdict = "reject"
            reasoning = "Autonomy violation detected - rights not preserved"
        
        return PhilosopherVerdict(
            confidence=confidence,
            coherence=autonomy_score,
            verdict=verdict,
            reasoning=reasoning,
            beam_weight=self.beam_weight
        )


class SpinozaBeam(PhilosopherBeam):
    """Geometric Determinism: Necessity through demonstrable chains"""
    
    def _initialize_rules(self) -> Dict:
        return _build_rule_set("spinoza", {
            "derive_from_axioms": True,
            "demonstrable_chain": True,
            "necessity_not_plausibility": True,
            "geometric_order": True
        })
    
    def reason(self, stimulus: np.ndarray, depth: int) -> PhilosopherVerdict:
        # Spinoza: Check for logical necessity through geometric derivation
        # Necessity = perfect alignment with axiomatic structure (smooth gradients)
        
        # Check for demonstrable chain (smooth derivatives)
        if len(stimulus) > 1:
            derivatives = np.diff(stimulus)
            smoothness = 1.0 - min(np.std(derivatives) * 2, 1.0)
        else:
            smoothness = 0.0
        
        # Axiomatic alignment (proximity to golden ratio proportions)
        phi_alignment = np.mean([1 - abs((x / PHI) - round(x / PHI)) for x in stimulus[:6]])
        
        necessity = (smoothness + phi_alignment) / 2
        admit_threshold = 0.75
        suspend_threshold = 0.4
        if self.seed_parameter("freedom_path") == "understanding_necessity":
            admit_threshold = 0.72
        if "reason" in self.seed_parameter("knowledge_hierarchy", []):
            suspend_threshold = 0.35
        
        if necessity > admit_threshold:
            confidence = necessity * 0.95
            verdict = "admit"
            reasoning = f"Geometric necessity proven ({self.seed_vault.get('reasoning_type')}, smoothness: {smoothness:.3f})"
        elif necessity > suspend_threshold:
            confidence = necessity * 0.6
            verdict = "suspend"
            reasoning = "Partial demonstration - chain incomplete"
        else:
            confidence = 0.2
            verdict = "reject"
            reasoning = "No demonstrable necessity - merely plausible"
        
        return PhilosopherVerdict(
            confidence=confidence,
            coherence=necessity,
            verdict=verdict,
            reasoning=reasoning,
            beam_weight=self.beam_weight
        )


class MultiBeamRunner:
    """Runs all four philosophers simultaneously"""
    
    def __init__(self):
        self.beams = {
            "hume": HumeBeam("Hume"),
            "kant": KantBeam("Kant"),
            "locke": LockeBeam("Locke"),
            "spinoza": SpinozaBeam("Spinoza")
        }
    
    def run_parallel(self, stimulus: np.ndarray, depth: int) -> Dict[str, PhilosopherVerdict]:
        """Execute all four beams - pure ML recursion, no LLM"""
        return {name: beam.reason(stimulus, depth) for name, beam in self.beams.items()}
    
    def calculate_phase_coherence(self, verdicts: Dict[str, PhilosopherVerdict]) -> float:
        """KayGee-derived measurement of philosopher alignment"""
        confidences = [v.confidence for v in verdicts.values()]
        # High variance = low coherence (chaotic oscillation)
        # Low variance = high coherence (convergence)
        mean_conf = np.mean(confidences)
        variance = np.var(confidences)
        coherence = max(0, 1 - (variance / (mean_conf + 1e-10)))
        return coherence

    def get_seed_status(self) -> Dict[str, Dict[str, Any]]:
        """Report philosopher seed JSON load status."""
        return {name: beam.seed_status() for name, beam in self.beams.items()}


print("[OK] Four-Beam Constraint Architecture implemented")
print("  - Hume: Empirical Skepticism")
print("  - Kant: Categorical Reasoning")
print("  - Locke: Consent & Rights")
print("  - Spinoza: Geometric Determinism")
print("  - MultiBeamRunner with Phase Coherence")
