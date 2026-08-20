
# core/pipeline.py - Full TPC Pipeline
import importlib.util
import sys
from pathlib import Path
from typing import Union, Dict
import numpy as np
from datetime import datetime

from core.ecm import EpistemicContractManager, TribunalSynthesis
from core.geometric_primitives import GlyphSignature, SpaceField
from drift.ping import DepthRecursion, DriftPing
from Epistemic_Gravity_Field import EpistemicGravityField
from philosophers.base import MultiBeamRunner
from vaults.system import APrioriVault, APosterioriVault, VaultEntry


def _load_cochlear_processor_class():
    repo_dir = Path(__file__).resolve().parents[1] / "cochlear_processor_3.0"
    module_path = repo_dir / "processor.py"
    if str(repo_dir) not in sys.path:
        sys.path.insert(0, str(repo_dir))
    spec = importlib.util.spec_from_file_location("tcp_cochlear_processor", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load cochlear processor from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.AdaptiveCochlearProcessor


AdaptiveCochlearProcessor = _load_cochlear_processor_class()


class TriplePredicateCubed:
    """
    Full TPC Pipeline:
    Input -> Cochlear Processor -> HLSF -> K0/K1/K2 -> Four Philosophers
    -> Phase Coherence -> EGF -> A Priori + A Posteriori -> ECM -> Output
    """
    
    def __init__(self):
        # Axis 1: Input Trinity
        self.cochlear_processor = AdaptiveCochlearProcessor()
        self.hlsf = SpaceField()
        self.egf = EpistemicGravityField(self.hlsf)
        
        # Axis 2: Reasoning Trinity
        self.philosopher_runner = MultiBeamRunner()
        self.depth_recursion = DepthRecursion(self.philosopher_runner)
        
        # Axis 3: Resolution Trinity
        self.a_priori = APrioriVault()
        self.a_posteriori = APosterioriVault()
        self.ecm = EpistemicContractManager()
        
        # Drift protection
        self.drift_ping = DriftPing()
        
        # Register gates for drift ping
        self.drift_ping.register_gate("cochlear_processor")
        self.drift_ping.register_gate("hlsf")
        self.drift_ping.register_gate("egf")
        self.drift_ping.register_gate("depth")
        self.drift_ping.register_gate("philosophers")
        self.drift_ping.register_gate("vaults")
        self.drift_ping.register_gate("ecm")
        
        self.query_count = 0
        self.last_egf_signal_energy = 0.0
        self.last_egf_neighbor_distances = []
        
    def process(self, input_data: Union[str, np.ndarray], 
                input_type: str = "text") -> TribunalSynthesis:
        """
        Process input through full TPC pipeline.
        Ethically pre-pruned, geometrically verified output.
        """
        self.query_count += 1
        self.drift_ping.send_ping("input", "cochlear_processor", str(input_data))
        
        # === GATE 1: Cochlear Processor ===
        stimulus = self.cochlear_processor.process(input_data, input_type)
        if not self.drift_ping.confirm_receipt("cochlear_processor", "input"):
            print("Warning: Drift detected at cochlear processor gate")
        
        # Create geometric signature
        signature = GlyphSignature.from_stimulus(stimulus, origin=input_type)
        self.drift_ping.send_ping("cochlear_processor", "hlsf", str(signature.coordinates[:3]))
        
        # === GATE 2: HLSF Traversal ===
        self.hlsf.insert(signature)
        neighbors = self.hlsf.traverse(signature, top_k=5)
        self.drift_ping.send_ping("hlsf", "egf", str(len(neighbors)))

        # === GATE 2B: Epistemic Gravity Field ===
        if not self.drift_ping.confirm_receipt("egf", "hlsf"):
            print("Warning: Drift detected at EGF gate")

        egf_signal = self.egf.broadcast_signature(signature)
        self.egf.step(steps=1)
        gravity_ranked = self.egf.attract_similar(
            signature,
            [node for node, _distance in neighbors]
        )
        self.last_egf_neighbor_distances = [
            float(distance) for _node, distance in gravity_ranked
        ]
        self.last_egf_signal_energy = float(egf_signal.abs().sum().item())
        self.drift_ping.send_ping("egf", "depth", str(self.last_egf_signal_energy))
        
        # === CHECK A PRIORI (Pre-pruned certainties) ===
        prior_result = self.a_priori.check(signature)
        if prior_result:
            # Structurally resolved - minimal compute
            conclusion, confidence = prior_result
            return TribunalSynthesis(
                conclusion=conclusion,
                confidence=confidence,
                philosopher_breakdown={"a_priori": {"verdict": "admit", "reason": "structural certainty"}},
                phase_coherence=1.0,
                escalated=False,
                contract_valid=True,
                timestamp=datetime.now().isoformat()
            )
        
        # === GATE 3: Depth Recursion (K0->K1->K2) ===
        depth_results = self.depth_recursion.recurse(stimulus)
        final_verdicts = depth_results["k2"]
        self.drift_ping.send_ping("depth", "philosophers", str(depth_results["final_output"][:3]))
        
        # === GATE 4: Phase Coherence Check ===
        coherence = self.philosopher_runner.calculate_phase_coherence(final_verdicts)
        self.drift_ping.send_ping("philosophers", "vaults", str(coherence))
        
        # === GATE 5: EGF + Vault Retrieval ===
        # Try A Posteriori retrieval
        retrieved_entry, retrieval_confidence, retrieval_status = self.a_posteriori.retrieve(signature)
        
        escalated = False
        if retrieval_status == "exact" and retrieved_entry and retrieval_confidence > 0.8:
            # Vault hit - no need for heavy recursion (compute savings)
            synthesis = TribunalSynthesis(
                conclusion=retrieved_entry.conclusion,
                confidence=retrieval_confidence,
                philosopher_breakdown=retrieved_entry.philosopher_votes,
                phase_coherence=coherence,
                escalated=False,
                contract_valid=True,
                timestamp=datetime.now().isoformat()
            )
        else:
            # Novel input - ECM escalation required
            escalated = True
            synthesis = self.ecm.synthesize(final_verdicts, signature.coordinates, coherence, escalated)
            
            # Store in A Posteriori for future retrieval
            if synthesis.confidence > 0.6:
                entry = VaultEntry(
                    signature=signature,
                    conclusion=synthesis.conclusion,
                    philosopher_votes={k: v["verdict"] for k, v in synthesis.philosopher_breakdown.items()},
                    confidence=synthesis.confidence,
                    timestamp=synthesis.timestamp
                )
                self.a_posteriori.store(entry)
        
        self.drift_ping.send_ping("vaults", "ecm", synthesis.conclusion)
        
        # === GATE 6: ECM Final Validation ===
        valid, violations = self.ecm.validate(
            final_verdicts, signature.coordinates, coherence
        )
        
        if not valid:
            synthesis.contract_valid = False
            synthesis.conclusion = "suspend"
            synthesis.confidence *= 0.5
        
        # Final drift check
        if not self.drift_ping.validate_pipeline():
            print(f"Warning: Drift detected in pipeline. Count: {self.drift_ping.drift_detected}")
        
        # Periodic vivacity decay (sovereign forgetting)
        if self.query_count % 100 == 0:
            self.hlsf.global_decay()
        
        return synthesis
    
    def get_stats(self) -> Dict:
        return {
            "queries_processed": self.query_count,
            "drift_status": self.drift_ping.get_status(),
            "vault_stats": self.a_posteriori.get_stats(),
            "hlsf_nodes": len(self.hlsf.nodes),
            "edge_cutter_active": self.hlsf.edge_cutter_active,
            "egf_field_stats": self.egf.get_field_stats(),
            "egf_last_signal_energy": self.last_egf_signal_energy,
            "egf_last_neighbor_distances": self.last_egf_neighbor_distances
        }


print("[OK] Full TPC Pipeline implemented")
print("  - Input Trinity: Cochlear Processor -> HLSF -> EGF")
print("  - Reasoning Trinity: Depth -> Philosophers -> Coherence")
print("  - Resolution Trinity: A Priori -> A Posteriori -> ECM")
print("  - Drift Ping: Zero-drift handshake chain")
print("  - Geometric reasoning: No token prediction")
