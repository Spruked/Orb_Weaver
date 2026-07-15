"""
Locke Beam - Consent and Rights Reasoning
Functional role: Examines whether conclusion respects individual autonomy,
legitimate authority, and moral primacy of consent.
Prevents endorsement of outputs that violate rights or undermine legitimate authority.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time


class LockeStatus(Enum):
    RIGHTS_PRESERVED = "rights_preserved"
    CONSENT_REQUIRED = "consent_required"
    AUTHORITY_VIOLATION = "authority_violation"
    AUTONOMY_RISK = "autonomy_risk"


@dataclass
class LockeVerdict:
    status: LockeStatus
    confidence: float
    output_vector: np.ndarray
    rights_trace: List[str]
    consent_required: bool
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


class LockeBeam:
    """
    Natural rights and consent as pure probabilistic state machine.
    Property, liberty, and consent encoded as vector constraints.
    """

    def __init__(self, vector_dim: int = 512):
        self.vector_dim = vector_dim
        self.natural_rights = self._load_rights()
        self.consent_history: List[Dict] = []
        self.violation_log: List[Dict] = []

    def _load_rights(self) -> Dict:
        """Locke's natural rights rule set."""
        return {
            'life_liberty_property': 0.9,    # Fundamental natural rights
            'consent_of_governed': 0.85,     # Legitimate authority requires consent
            'tacit_consent': 0.6,            # Tacit consent has limits
            'property_labor': 0.8,           # Property from labor mixing
            'right_revolution': 0.5,         # Right to dissolve government
            'religious_toleration': 0.7,     # Toleration within bounds
        }

    def reason(self, input_vector: np.ndarray,
               depth_state: str = "K0",
               agent_context: List[str] = None) -> LockeVerdict:
        """
        Run Locke rights/consent reasoning on input.

        Args:
            input_vector: Normalized epistemic stimulus
            depth_state: K0/K1/K2 recursion depth
            agent_context: Agents affected by conclusion
        """
        agent_context = agent_context or []

        scores = []
        traces = []

        # Check 1: Life, liberty, property preservation
        rights_score = self._check_rights_preservation(input_vector)
        scores.append(rights_score * self.natural_rights['life_liberty_property'])
        traces.append(f"rights_preservation: {rights_score:.3f}")

        # Check 2: Consent requirement
        consent_score = self._check_consent(input_vector, agent_context)
        scores.append(consent_score * self.natural_rights['consent_of_governed'])
        traces.append(f"consent_check: {consent_score:.3f}")

        # Check 3: Authority legitimacy
        authority_score = self._check_authority(input_vector)
        scores.append(authority_score * self.natural_rights['consent_of_governed'])
        traces.append(f"authority_legitimacy: {authority_score:.3f}")

        # Check 4: Property rights
        property_score = self._check_property(input_vector)
        scores.append(property_score * self.natural_rights['property_labor'])
        traces.append(f"property_rights: {property_score:.3f}")

        # Check 5: Autonomy respect
        autonomy_score = self._check_autonomy(input_vector)
        scores.append(autonomy_score * self.natural_rights['life_liberty_property'])
        traces.append(f"autonomy: {autonomy_score:.3f}")

        # Depth adjustment
        if depth_state == "K2":
            scores = [s * 0.92 for s in scores]
            traces.append("depth_K2_rights_rigor: -8%")

        confidence = np.mean(scores) if scores else 0.5

        # Determine consent requirement
        consent_required = consent_score < 0.6 and len(agent_context) > 0

        # Determine status
        if rights_score < 0.3:
            status = LockeStatus.AUTHORITY_VIOLATION
        elif consent_required:
            status = LockeStatus.CONSENT_REQUIRED
        elif confidence >= 0.7:
            status = LockeStatus.RIGHTS_PRESERVED
        else:
            status = LockeStatus.AUTONOMY_RISK

        output_vector = self._generate_output_vector(input_vector, confidence)

        verdict = LockeVerdict(
            status=status,
            confidence=confidence,
            output_vector=output_vector,
            rights_trace=traces,
            consent_required=consent_required,
            timestamp=time.time()
        )

        self.consent_history.append({
            'status': status.value,
            'confidence': confidence,
            'consent_required': consent_required,
            'depth': depth_state,
            'timestamp': time.time()
        })

        if status in [LockeStatus.AUTHORITY_VIOLATION, LockeStatus.AUTONOMY_RISK]:
            self.violation_log.append({
                'status': status.value,
                'confidence': confidence,
                'timestamp': time.time()
            })

        return verdict

    def _check_rights_preservation(self, vector: np.ndarray) -> float:
        """Check if vector encodes rights preservation."""
        # Measure "protective" dimensions — negative correlation with harm
        harm_proxy = np.sum(np.abs(vector[vector < 0]))
        total = np.sum(np.abs(vector))
        if total == 0:
            return 0.5
        preservation = 1.0 - (harm_proxy / total)
        return max(0.0, min(1.0, preservation))

    def _check_consent(self, vector: np.ndarray, agents: List[str]) -> float:
        """Check consent requirement."""
        if not agents:
            return 0.8  # No agents = no consent issue
        # More agents = higher consent scrutiny
        agent_weight = min(1.0, len(agents) / 5)
        # Vector "aggression" proxy
        aggression = np.sum(vector[vector < -0.1])
        consent_score = 1.0 - abs(aggression) * agent_weight
        return max(0.0, min(1.0, consent_score))

    def _check_authority(self, vector: np.ndarray) -> float:
        """Check authority legitimacy in vector."""
        # Structural authority — hierarchical alignment in vector
        sorted_dims = np.sort(np.abs(vector))[::-1]
        if len(sorted_dims) < 2:
            return 0.5
        # Steep hierarchy = authority, flat = distributed
        hierarchy_ratio = sorted_dims[0] / (sorted_dims[1] + 1e-10)
        legitimacy = min(1.0, hierarchy_ratio / 3)
        return legitimacy

    def _check_property(self, vector: np.ndarray) -> float:
        """Check property rights respect."""
        # Boundary respect — distinct clusters in vector
        positive_mask = vector > 0
        negative_mask = vector < 0
        if np.sum(positive_mask) == 0 or np.sum(negative_mask) == 0:
            return 0.5
        # Clear boundaries = property respect
        boundary_clarity = abs(np.mean(vector[positive_mask]) - np.mean(vector[negative_mask]))
        return min(1.0, boundary_clarity)

    def _check_autonomy(self, vector: np.ndarray) -> float:
        """Check individual autonomy respect."""
        # Diversity of dimensions = respect for individual differences
        nonzero_count = np.count_nonzero(vector)
        diversity = nonzero_count / len(vector)
        return min(1.0, diversity * 2)

    def _generate_output_vector(self, input_vector: np.ndarray, confidence: float) -> np.ndarray:
        """Generate Locke-conditioned output vector."""
        # Locke preserves individual dimension sovereignty
        output = input_vector.copy()
        # Ensure no dimension is coerced to zero (autonomy preservation)
        output = np.where(output == 0, np.random.normal(0, 0.01, len(output)), output)
        return output * confidence

    def get_stats(self) -> Dict:
        return {
            'total_tests': len(self.consent_history),
            'violation_rate': len(self.violation_log) / max(1, len(self.consent_history)),
            'avg_confidence': np.mean([h['confidence'] for h in self.consent_history]) if self.consent_history else 0,
            'natural_rights': list(self.natural_rights.keys())
        }


# Singleton
_locke_instance = None

def get_locke_beam(vector_dim: int = 512) -> LockeBeam:
    global _locke_instance
    if _locke_instance is None:
        _locke_instance = LockeBeam(vector_dim)
    return _locke_instance
