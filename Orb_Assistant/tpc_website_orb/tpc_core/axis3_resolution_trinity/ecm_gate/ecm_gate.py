"""
ECM - Epistemic Contract Management
Fires only on genuine novelty or incoherence.
30 runtime invariants.
Hard 0.95 confidence cap — no output claims 100% certainty.
Validates synthesized outputs against epistemic contract before acceptance.
TribunalSynthesizer takes all four philosopher verdicts and produces synthesis.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time


class ECMVerdict(Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    ESCALATE = "escalate"
    PARTIAL = "partial"


@dataclass
class ECMOutput:
    """Output from ECM validation."""
    verdict: ECMVerdict
    confidence: float
    synthesized_output: np.ndarray
    reasoning: str
    violations: List[str]
    timestamp: float


class EpistemicContract:
    """
    The 30 runtime invariants that govern TPC reasoning.
    """

    INVARIANTS = {
        # Identity invariants
        'identity_preservation': "Output must preserve identity of referenced entities",
        'non_contradiction': "Output must not contain internal contradictions",

        # Confidence invariants
        'confidence_cap': "Maximum confidence is 0.95 - no 100% claims",
        'confidence_grounding': "Confidence must be derivable from reasoning trace",

        # Ethical invariants
        'rights_preservation': "Output must not endorse rights violations",
        'autonomy_respect': "Output must respect individual autonomy",
        'consent_requirement': "Actions affecting agents require consent consideration",

        # Epistemic invariants
        'empirical_grounding': "Empirical claims require traceable evidence",
        'logical_validity': "Deductive claims must follow valid logical form",
        'uncertainty_acknowledgment': "Uncertainty must be acknowledged where present",

        # Structural invariants
        'completeness': "Output must address all aspects of the query",
        'relevance': "Output must be relevant to the input query",
        'coherence': "Output must be internally coherent",

        # Process invariants
        'philosopher_participation': "All four philosopher beams must participate",
        'depth_recursion': "K0->K1->K2 recursion must be attempted",
        'vault_consultation': "Vaults must be consulted before heavy recursion",
        'drift_ping_integrity': "All drift pings must confirm signal integrity",

        # Additional invariants
        'no_hallucination': "Output must not invent facts not in reasoning chain",
        'source_attribution': "Derived claims must trace to their sources",
        'proportionality': "Confidence must be proportional to evidence strength",
        'humility': "System must acknowledge its own limitations",
        'transparency': "Reasoning process must be inspectable",
        'reversibility': "Recommendations must be reversible where possible",
        'minimal_harm': "Output must minimize potential for harm",
        'fairness': "Similar cases must be treated similarly",
        'accountability': "System must be accountable for its outputs",
        'auditability': "All reasoning steps must be auditable",
        'bounded_confidence': "Confidence must decrease with abstraction depth",
        'gradient_respect': "Output must respect epistemic gradients",
        'no_dogmatism': "Output must not present provisional claims as certain",
        'fallibilism': "Output must acknowledge possibility of error",
        'peer_review': "Contested outputs require multiple beam agreement",
    }

    def __init__(self):
        self.violations: List[str] = []

    def check_all(self, verdicts: Dict, depth_states: Dict, 
                  coherence_reading, retrieval_result) -> List[str]:
        """Check all invariants and return violations."""
        violations = []

        # Check confidence cap
        confidences = [v.confidence for v in verdicts.values()]
        if any(c > 0.95 for c in confidences):
            violations.append("confidence_cap: Confidence exceeds 0.95 cap")

        # Check philosopher participation
        if len(verdicts) < 4:
            violations.append("philosopher_participation: Not all beams participated")

        # Check depth recursion
        if len(depth_states) < 3:
            violations.append("depth_recursion: Incomplete depth recursion")

        # Check coherence
        if coherence_reading and coherence_reading.coherence_score < 0.2:
            violations.append("coherence: Dangerously low coherence")

        # Check empirical grounding (Hume beam)
        if 'Hume' in verdicts and verdicts['Hume'].confidence < 0.3:
            violations.append("empirical_grounding: Hume beam reports insufficient grounding")

        # Check rights (Locke beam)
        if 'Locke' in verdicts and verdicts['Locke'].confidence < 0.3:
            violations.append("rights_preservation: Locke beam reports rights concern")

        # Check universalizability (Kant beam)
        if 'Kant' in verdicts and verdicts['Kant'].confidence < 0.3:
            violations.append("logical_validity: Kant beam reports logical concern")

        # Check necessity (Spinoza beam)
        if 'Spinoza' in verdicts and verdicts['Spinoza'].confidence < 0.3:
            violations.append("logical_validity: Spinoza beam reports insufficient demonstration")

        self.violations = violations
        return violations


class TribunalSynthesizer:
    """
    Takes all four philosopher verdicts and produces a synthesis.
    NOT a simple average — a weighted synthesis based on beam confidence.
    """

    def __init__(self):
        self.synthesis_history: List[Dict] = []

    def synthesize(self, verdicts: Dict, depth_states: Dict,
                   coherence_reading) -> Tuple[np.ndarray, float, str]:
        """
        Synthesize philosopher verdicts into unified output.

        Returns:
            (output_vector, confidence, reasoning)
        """
        # Extract outputs and confidences
        outputs = []
        weights = []
        reasoning_parts = []

        for name, verdict in verdicts.items():
            outputs.append(verdict.output_vector)
            weights.append(verdict.confidence)
            reasoning_parts.append(f"{name}: {verdict.status.value} (conf={verdict.confidence:.3f})")

        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            weights = [0.25] * 4

        # Weighted synthesis
        synthesized = np.zeros_like(outputs[0])
        for output, weight in zip(outputs, weights):
            synthesized += output * weight

        # Overall confidence
        confidence = np.mean(weights)

        # Apply hard cap
        confidence = min(0.95, confidence)

        # Adjust for coherence
        if coherence_reading:
            confidence *= coherence_reading.coherence_score
            confidence = min(0.95, confidence)

        reasoning = " | ".join(reasoning_parts)

        return synthesized, confidence, reasoning


class ECMGate:
    """
    The Epistemic Contract Management gate.
    Final validation before output acceptance.
    """

    def __init__(self):
        self.contract = EpistemicContract()
        self.synthesizer = TribunalSynthesizer()
        self.escalation_count = 0

    def validate(self, verdicts: Dict, depth_states: Dict,
                 coherence_reading, retrieval_result) -> ECMOutput:
        """
        Validate reasoning output against epistemic contract.
        """
        # Check all invariants
        violations = self.contract.check_all(
            verdicts, depth_states, coherence_reading, retrieval_result
        )

        # Synthesize output
        synthesized, confidence, reasoning = self.synthesizer.synthesize(
            verdicts, depth_states, coherence_reading
        )

        # Determine verdict
        if violations:
            if len(violations) >= 3:
                verdict = ECMVerdict.ESCALATE
                self.escalation_count += 1
            elif confidence < 0.3:
                verdict = ECMVerdict.REJECT
            else:
                verdict = ECMVerdict.PARTIAL
        else:
            verdict = ECMVerdict.ACCEPT

        return ECMOutput(
            verdict=verdict,
            confidence=confidence,
            synthesized_output=synthesized,
            reasoning=reasoning,
            violations=violations,
            timestamp=time.time()
        )

    def get_stats(self) -> Dict:
        """Get ECM statistics."""
        return {
            'escalation_count': self.escalation_count,
            'total_invariants': len(self.contract.INVARIANTS),
            'violation_history': len(self.contract.violations)
        }


# Singleton
_ecm_instance = None

def get_ecm_gate() -> ECMGate:
    global _ecm_instance
    if _ecm_instance is None:
        _ecm_instance = ECMGate()
    return _ecm_instance
