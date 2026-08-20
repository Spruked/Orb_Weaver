"""
orb/vault/shared/confidence.py
Confidence calculation, decay, reinforcement, and cap enforcement.
All confidence operations in both vaults route through this engine.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .types import Confidence, VerificationSignal, DegradationSignal, KnowledgeState


class ConfidenceEngine:
    """
    Deterministic confidence calculator.
    No learning. No mutation of self. Pure function behavior.
    """

    # Signal weights for verification
    VERIFICATION_WEIGHTS: Dict[VerificationSignal, float] = {
        VerificationSignal.REPETITION: 0.15,
        VerificationSignal.OUTCOME_SUCCESS: 0.25,
        VerificationSignal.SOURCE_CONSISTENT: 0.10,
        VerificationSignal.OWNER_APPROVED: 0.35,
        VerificationSignal.CROSS_REFERENCE: 0.20,
    }

    # Signal weights for degradation
    DEGRADATION_WEIGHTS: Dict[DegradationSignal, float] = {
        DegradationSignal.CONTRADICTION: -0.30,
        DegradationSignal.STALENESS: -0.10,
        DegradationSignal.SOURCE_CHANGED: -0.25,
        DegradationSignal.LOW_USEFULNESS: -0.15,
        DegradationSignal.DUPLICATION: -0.10,
        DegradationSignal.POOR_OUTCOME: -0.35,
        DegradationSignal.CONFIDENCE_DECAY: -0.05,
    }

    # Reinforcement per successful use
    REINFORCEMENT_DELTA: float = 0.03
    MAX_REINFORCEMENT: float = 0.15  # Cap total reinforcement from usage

    # Decay parameters
    DECAY_HALF_LIFE_DAYS: float = 30.0
    DECAY_MINIMUM: float = 0.10

    @classmethod
    def calculate_verification_confidence(
        cls,
        signals: Dict[VerificationSignal, int],
        base_confidence: float = 0.0,
        cap: float = 0.95
    ) -> Confidence:
        """
        Calculate confidence from accumulated verification signals.
        Each signal occurrence adds diminishing returns.
        """
        total = base_confidence
        for signal, count in signals.items():
            weight = cls.VERIFICATION_WEIGHTS.get(signal, 0.0)
            # Diminishing returns: sqrt(count) scaling
            import math
            effective_count = math.sqrt(count)
            total += weight * effective_count

        # Hard cap
        total = min(total, cap)
        # Floor
        total = max(total, 0.0)

        provenance = [f"ver:{s.name}:{c}" for s, c in signals.items()]
        return Confidence(value=total, cap=cap, provenance=provenance)

    @classmethod
    def calculate_degradation_penalty(
        cls,
        signals: Dict[DegradationSignal, int],
        current_confidence: float
    ) -> float:
        """Calculate total confidence penalty from degradation signals."""
        total_penalty = 0.0
        for signal, count in signals.items():
            weight = cls.DEGRADATION_WEIGHTS.get(signal, 0.0)
            import math
            effective_count = math.sqrt(count)
            total_penalty += abs(weight) * effective_count

        return min(total_penalty, current_confidence)  # Cannot go below 0

    @classmethod
    def reinforce(
        cls,
        current: Confidence,
        success: bool,
        streak: int = 1
    ) -> Confidence:
        """
        Reinforce confidence based on usage outcome.
        Success increases, failure decreases.
        Streak multipliers apply.
        """
        import math
        if success:
            # Diminishing returns on repeated reinforcement
            delta = cls.REINFORCEMENT_DELTA * (1.0 / math.sqrt(streak + 1))
            delta = min(delta, cls.MAX_REINFORCEMENT)
            return current.adjust(delta, f"reinforce:success:streak_{streak}")
        else:
            # Failure penalty is sharper
            delta = -cls.REINFORCEMENT_DELTA * 2.0
            return current.adjust(delta, f"reinforce:failure:streak_{streak}")

    @classmethod
    def apply_time_decay(
        cls,
        current: Confidence,
        days_since_last_access: float
    ) -> Confidence:
        """
        Apply time-based confidence decay.
        Uses exponential decay with floor.
        """
        import math
        if days_since_last_access <= 0:
            return current

        decay_factor = math.exp(-0.693 * days_since_last_access / cls.DECAY_HALF_LIFE_DAYS)
        new_value = max(current.value * decay_factor, cls.DECAY_MINIMUM)

        if new_value < current.value:
            return Confidence(
                value=new_value,
                cap=current.cap,
                provenance=current.provenance + [f"decay:{days_since_last_access:.1f}d"]
            )
        return current

    @classmethod
    def cap_under_tension(cls, current: Confidence, tension_level: float = 0.0) -> Confidence:
        """
        Apply confidence cap under peer tension.
        tension_level: 0.0 = no tension, 1.0 = maximum tension
        """
        if tension_level <= 0:
            return current

        # Under tension, cap drops to 0.75
        tension_cap = 0.75
        if current.cap > tension_cap:
            return current.set_cap(tension_cap, f"tension:{tension_level:.2f}")
        return current

    @classmethod
    def promotion_threshold_met(
        cls,
        signals: Dict[VerificationSignal, int],
        min_signals: int = 2,
        min_confidence: float = 0.60
    ) -> bool:
        """Check if a candidate has enough verification to be promoted."""
        conf = cls.calculate_verification_confidence(signals, cap=0.95)
        signal_diversity = len([s for s, c in signals.items() if c > 0])
        return conf.value >= min_confidence and signal_diversity >= min_signals

    @classmethod
    def prune_threshold_met(
        cls,
        confidence: float,
        degradation_signals: Dict[DegradationSignal, int],
        access_count: int,
        days_since_access: float
    ) -> tuple[bool, str]:
        """
        Determine if knowledge should be pruned.
        Returns (should_prune, reason).
        """
        # High-confidence, recently used knowledge is never pruned
        if confidence > 0.80 and days_since_access < 7:
            return False, "active_high_confidence"

        # Check degradation severity
        total_degradation = sum(degradation_signals.values())
        if total_degradation >= 5 and confidence < 0.30:
            return True, f"severe_degradation:{total_degradation}"

        # Low usefulness + old
        if access_count < 3 and days_since_access > 90 and confidence < 0.40:
            return True, "low_use_stale"

        # Source changed + low confidence
        if degradation_signals.get(DegradationSignal.SOURCE_CHANGED, 0) > 0 and confidence < 0.35:
            return True, "source_changed_weak"

        # Contradiction with low confidence
        if degradation_signals.get(DegradationSignal.CONTRADICTION, 0) >= 2 and confidence < 0.45:
            return True, "contradicted_weak"

        return False, "retain"
