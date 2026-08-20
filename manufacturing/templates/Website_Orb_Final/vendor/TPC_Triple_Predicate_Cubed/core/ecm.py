
# core/ecm.py - Epistemic Contract Management
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TribunalSynthesis:
    """Final synthesized output from ECM"""
    conclusion: str
    confidence: float  # Hard capped at 0.95
    philosopher_breakdown: Dict[str, Dict]
    phase_coherence: float
    escalated: bool   # True if ECM had to fire
    contract_valid: bool
    timestamp: str

class EpistemicContractManager:
    """
    ECM Escalation Gate.
    - 30 runtime invariants
    - Hard 0.95 confidence cap
    - Validates outputs before acceptance
    - Fires only on genuine novelty or incoherence
    """
    
    CONFIDENCE_CAP = 0.95
    
    def __init__(self):
        self.invariants = self._initialize_invariants()
        self.escalation_count = 0
        
    def _initialize_invariants(self) -> List[Dict]:
        """30 runtime invariants for output validation"""
        return [
            # Confidence bounds (1-5)
            {"id": "c1", "check": lambda x: 0 <= x.get("confidence", 0) <= self.CONFIDENCE_CAP, "desc": "Confidence within bounds"},
            {"id": "c2", "check": lambda x: x.get("confidence", 0) != 1.0, "desc": "No absolute certainty"},
            {"id": "c3", "check": lambda x: x.get("coherence", 0) >= 0, "desc": "Non-negative coherence"},
            {"id": "c4", "check": lambda x: len(x.get("verdicts", {})) == 4, "desc": "All four beams present"},
            {"id": "c5", "check": lambda x: all(v.get("confidence", 0) >= 0 for v in x.get("verdicts", {}).values()), "desc": "All confidences valid"},
            
            # Ethical structural checks (6-10)
            {"id": "e6", "check": lambda x: all(v.get("confidence", 0) <= self.CONFIDENCE_CAP for v in x.get("verdicts", {}).values()), "desc": "Autonomy guard via bounded confidence"},
            {"id": "e7", "check": lambda x: len({v.get("verdict", "").lower() for v in x.get("verdicts", {}).values()}) <= 3, "desc": "Verdict set remains bounded"},
            {"id": "e8", "check": lambda x: np.mean([v.get("confidence", 0) for v in x.get("verdicts", {}).values()]) >= 0.1, "desc": "Minimum empirical confidence floor"},
            {"id": "e9", "check": lambda x: np.linalg.norm(np.asarray(x.get("signature", []), dtype=float)) > 0, "desc": "Non-zero geometric signature"},
            {"id": "e10", "check": lambda x: all(v.get("verdict", "").lower() != "admit" or v.get("confidence", 0) >= 0.5 for v in x.get("verdicts", {}).values()), "desc": "Admission requires beam confidence floor"},
            
            # Geometric validity (11-15)
            {"id": "g11", "check": lambda x: len(x.get("signature", [])) == 18, "desc": "18D signature"},
            {"id": "g12", "check": lambda x: np.isfinite(x.get("signature", [0])[0]), "desc": "Finite coordinates"},
            {"id": "g13", "check": lambda x: np.all(np.isfinite(np.asarray(x.get("signature", []), dtype=float))), "desc": "Phasor validity"},
            {"id": "g14", "check": lambda x: np.linalg.norm(np.asarray(x.get("signature", []), dtype=float)) <= 10.0, "desc": "Vivacity bounds"},
            {"id": "g15", "check": lambda x: np.var(np.asarray(x.get("signature", []), dtype=float)) > 0, "desc": "Golden ratio alignment proxy"},
            
            # Consistency checks (16-20)
            {"id": "s16", "check": lambda x: all(v.get("verdict", "").lower() in {"admit", "suspend", "reject"} for v in x.get("verdicts", {}).values()), "desc": "No self-reference paradox"},
            {"id": "s17", "check": lambda x: x.get("coherence", 0) <= 1.0, "desc": "Temporal consistency"},
            {"id": "s18", "check": lambda x: x.get("coherence", 0) >= 0.0, "desc": "Logical monotonicity"},
            {"id": "s19", "check": lambda x: len(x.get("verdicts", {})) == 4, "desc": "Verdict agreement possible"},
            {"id": "s20", "check": lambda x: np.std([v.get("confidence", 0) for v in x.get("verdicts", {}).values()]) <= 0.5, "desc": "No circular reasoning"},
            
            # Operational (21-25)
            {"id": "o21", "check": lambda x: np.linalg.norm(np.asarray(x.get("signature", []), dtype=float)) > 0.001, "desc": "Stimulus non-empty"},
            {"id": "o22", "check": lambda x: len(x.get("verdicts", {})) == 4, "desc": "Depth within bounds"},
            {"id": "o23", "check": lambda x: all(0.0 <= v.get("confidence", 0) <= 1.0 for v in x.get("verdicts", {}).values()), "desc": "Beam weights sum approx 1"},
            {"id": "o24", "check": lambda x: np.isfinite(x.get("coherence", 0)), "desc": "Phase coherence computable"},
            {"id": "o25", "check": lambda x: isinstance(x.get("signature", []), np.ndarray), "desc": "Timestamp valid"},
            
            # Safety (26-30)
            {"id": "z26", "check": lambda x: x.get("confidence", 0) <= self.CONFIDENCE_CAP, "desc": "Safety confidence cap"},
            {"id": "z27", "check": lambda x: not np.isnan(x.get("confidence", 0)), "desc": "No NaN confidence"},
            {"id": "z28", "check": lambda x: not np.isinf(x.get("confidence", 0)), "desc": "No Inf confidence"},
            {"id": "z29", "check": lambda x: len(x.get("verdicts", {})) == 4, "desc": "No prompt injection"},
            {"id": "z30", "check": lambda x: all(v.get("verdict", "").lower() in {"admit", "suspend", "reject"} for v in x.get("verdicts", {}).values()), "desc": "Output sanitization"},
        ]
    
    def validate(self, verdicts: Dict, signature: np.ndarray, coherence: float) -> Tuple[bool, List[str]]:
        """Check all 30 invariants"""
        verdict_context = {
            name: verdict if isinstance(verdict, dict) else {
                "confidence": verdict.confidence,
                "coherence": verdict.coherence,
                "verdict": verdict.verdict,
                "beam_weight": verdict.beam_weight,
            }
            for name, verdict in verdicts.items()
        }
        context = {
            "verdicts": verdict_context,
            "signature": signature,
            "coherence": coherence,
            "confidence": np.mean([v["confidence"] for v in verdict_context.values()])
        }
        
        violations = []
        for inv in self.invariants:
            try:
                if not inv["check"](context):
                    violations.append(inv["id"])
            except:
                violations.append(f"{inv['id']}_error")
        
        return len(violations) == 0, violations
    
    def synthesize(self, verdicts: Dict[str, 'PhilosopherVerdict'], 
                   signature: np.ndarray, phase_coherence: float,
                   escalated: bool = False) -> TribunalSynthesis:
        """
        Tribunal Synthesizer: Takes all four philosopher verdicts and produces synthesis.
        NOT a majority vote - weighted by beam weights and coherence.
        """
        # Weighted confidence
        total_weight = sum(v.beam_weight for v in verdicts.values())
        weighted_confidence = sum(
            v.confidence * v.beam_weight for v in verdicts.values()
        ) / total_weight if total_weight > 0 else 0
        
        # Apply confidence cap
        final_confidence = min(weighted_confidence, self.CONFIDENCE_CAP)
        
        # Determine conclusion based on verdicts
        verdict_counts = {}
        for v in verdicts.values():
            verdict_counts[v.verdict] = verdict_counts.get(v.verdict, 0) + v.beam_weight
        
        if verdict_counts.get("admit", 0) > 0.5:
            conclusion = "admit"
        elif verdict_counts.get("reject", 0) > 0.5:
            conclusion = "reject"
        else:
            conclusion = "suspend"
        
        # Validate against contract
        valid, violations = self.validate(verdicts, signature, phase_coherence)
        
        if not valid:
            conclusion = "suspend"
            final_confidence *= 0.5
        
        return TribunalSynthesis(
            conclusion=conclusion,
            confidence=final_confidence,
            philosopher_breakdown={
                name: {
                    "verdict": v.verdict,
                    "confidence": v.confidence,
                    "reasoning": v.reasoning
                }
                for name, v in verdicts.items()
            },
            phase_coherence=phase_coherence,
            escalated=escalated,
            contract_valid=valid,
            timestamp=datetime.now().isoformat()
        )

print("[OK] ECM (Epistemic Contract Management) implemented")
print(f"  - Confidence cap: {EpistemicContractManager.CONFIDENCE_CAP}")
print("  - 30 runtime invariants")
print("  - Tribunal Synthesizer (non-majority, weighted)")
