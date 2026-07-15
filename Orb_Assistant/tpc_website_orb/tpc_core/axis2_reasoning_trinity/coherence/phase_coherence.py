"""
Phase Coherence Signal
A lightweight KayGee-derived measurement.
If philosopher loops are oscillating chaotically, phase coherence drops.
System health signal indicating genuine novelty or paradox.
Convergence = defensible answer.
Divergence = genuinely contested terrain.
Oscillation in a pattern = self-referential or paradoxical.
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class CoherenceState(Enum):
    HIGH = "high"           # Strong convergence, defensible answer
    MODERATE = "moderate"    # Partial convergence, some uncertainty
    LOW = "low"             # Divergence, contested terrain
    CHAOTIC = "chaotic"     # Oscillation, paradox or novelty


@dataclass
class CoherenceReading:
    """A phase coherence measurement."""
    coherence_score: float  # 0-1
    phase_alignment: float  # How well phases align
    oscillation_frequency: float
    state: CoherenceState
    interpretation: str


class PhaseCoherenceMonitor:
    """
    Monitors phase coherence across philosopher beams.
    Derived from KayGee measurement principles.
    """

    def __init__(self, history_size: int = 50):
        self.history_size = history_size
        self.phase_history: List[Dict[str, np.ndarray]] = []
        self.coherence_history: List[float] = []

    def measure(self, verdicts: Dict[str, 'PhilosopherVerdict']) -> CoherenceReading:
        """
        Measure phase coherence from current philosopher verdicts.
        """
        # Extract output vectors
        vectors = {name: v.output_vector for name, v in verdicts.items()}

        # Store in history
        self.phase_history.append(vectors)
        if len(self.phase_history) > self.history_size:
            self.phase_history.pop(0)

        # Compute phase alignment (how similar are the beam outputs?)
        phase_alignment = self._compute_phase_alignment(vectors)

        # Compute oscillation frequency
        oscillation_freq = self._compute_oscillation_frequency()

        # Overall coherence score
        coherence = phase_alignment * (1.0 - min(1.0, oscillation_freq))

        self.coherence_history.append(coherence)

        # Determine state
        state, interpretation = self._interpret(coherence, oscillation_freq, phase_alignment)

        return CoherenceReading(
            coherence_score=coherence,
            phase_alignment=phase_alignment,
            oscillation_frequency=oscillation_freq,
            state=state,
            interpretation=interpretation
        )

    def _compute_phase_alignment(self, vectors: Dict[str, np.ndarray]) -> float:
        """
        Compute how well the philosopher beam outputs align.
        Uses pairwise cosine similarity.
        """
        names = list(vectors.keys())
        if len(names) < 2:
            return 1.0

        similarities = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                v1 = vectors[names[i]]
                v2 = vectors[names[j]]

                # Cosine similarity
                dot = np.dot(v1, v2)
                norm = np.linalg.norm(v1) * np.linalg.norm(v2)
                sim = dot / (norm + 1e-10)
                similarities.append(sim)

        return np.mean(similarities) if similarities else 1.0

    def _compute_oscillation_frequency(self) -> float:
        """
        Detect oscillation patterns in phase history.
        """
        if len(self.phase_history) < 3:
            return 0.0

        # Track a representative vector's movement
        # Use first beam's vector as representative
        first_beam = list(self.phase_history[0].keys())[0]

        trajectory = []
        for history_entry in self.phase_history:
            if first_beam in history_entry:
                trajectory.append(history_entry[first_beam])

        if len(trajectory) < 3:
            return 0.0

        # Compute direction changes
        direction_changes = 0
        for i in range(2, len(trajectory)):
            prev_dir = trajectory[i-1] - trajectory[i-2]
            curr_dir = trajectory[i] - trajectory[i-1]

            # Check if direction reversed
            if np.dot(prev_dir, curr_dir) < 0:
                direction_changes += 1

        # Frequency = changes per observation
        freq = direction_changes / max(1, len(trajectory) - 2)
        return freq

    def _interpret(self, coherence: float, oscillation: float, 
                   alignment: float) -> Tuple[CoherenceState, str]:
        """
        Interpret coherence reading into human-readable state.
        """
        if coherence > 0.8:
            return CoherenceState.HIGH, (
                "Strong convergence across all philosopher beams. "
                "Output is defensible with high confidence."
            )
        elif coherence > 0.5:
            return CoherenceState.MODERATE, (
                "Partial convergence. Some beams diverge but majority align. "
                "Output is reasonable but not strongly defensible."
            )
        elif oscillation > 0.3:
            return CoherenceState.CHAOTIC, (
                "Oscillation pattern detected. Input may be self-referential, "
                "paradoxical, or genuinely novel. Requires deeper analysis."
            )
        else:
            return CoherenceState.LOW, (
                "Divergence across philosopher beams. "
                "Genuinely contested terrain. No clear consensus."
            )

    def get_trend(self) -> str:
        """Get coherence trend over recent history."""
        if len(self.coherence_history) < 5:
            return "insufficient_data"

        recent = self.coherence_history[-5:]
        if recent[-1] > recent[0]:
            return "improving"
        elif recent[-1] < recent[0]:
            return "declining"
        else:
            return "stable"
