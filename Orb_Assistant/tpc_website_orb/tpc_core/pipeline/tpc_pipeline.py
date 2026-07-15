"""
TPC Full Pipeline Orchestrator

Input (audio or text)
↓
Gate 1 STT gateway — Faster-Whisper primary, Qwen STT optional
↓
HLSF — traversal + vivacity weighting
↓
K0→K1→K2 depth recursion mechanic
↓
Four Philosopher ML Loops (softmax, simultaneous)
↓
Phase Coherence Check
↓
EGF — certainty gravity (vault retrieval physics)
↓
A Priori Vault + A Posteriori Vault
Geometric Glyph Signatures (phasor coordinates)
↓
ECM — fires only on genuine novelty or incoherence
↓
Output — ethically pre-pruned, geometrically verified

Drift Ping embedded between every gate transition.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import time
import asyncio

# Core imports
from Orb_Assistant.tpc_website_orb.tpc_core.axis1_input_trinity.input_gateway.faster_whisper_gateway import get_input_gateway
from Orb_Assistant.tpc_website_orb.tpc_core.axis1_input_trinity.hlsf.hlsf_engine import get_hlsf
from Orb_Assistant.tpc_website_orb.tpc_core.axis1_input_trinity.egf.egf_engine import get_egf
from Orb_Assistant.tpc_website_orb.tpc_core.axis2_reasoning_trinity.depth_recursion.depth_engine import DepthLevel, DepthRecursionEngine
from Orb_Assistant.tpc_website_orb.tpc_core.axis2_reasoning_trinity.coherence.phase_coherence import PhaseCoherenceMonitor
from Orb_Assistant.tpc_website_orb.tpc_core.axis3_resolution_trinity.a_priori_vault.a_priori_vault import APrioriVault, get_a_priori_vault
from Orb_Assistant.tpc_website_orb.tpc_core.axis3_resolution_trinity.a_posteriori_vault.a_posteriori_vault import APosterioriVault, get_a_posteriori_vault
from Orb_Assistant.tpc_website_orb.tpc_core.axis3_resolution_trinity.ecm_gate.ecm_gate import ECMGate, get_ecm_gate
from Orb_Assistant.tpc_website_orb.tpc_core.four_beam.hume_beam.hume_beam import HumeBeam, get_hume_beam
from Orb_Assistant.tpc_website_orb.tpc_core.four_beam.kant_beam.kant_beam import KantBeam, get_kant_beam
from Orb_Assistant.tpc_website_orb.tpc_core.four_beam.locke_beam.locke_beam import LockeBeam, get_locke_beam
from Orb_Assistant.tpc_website_orb.tpc_core.four_beam.spinoza_beam.spinoza_beam import SpinozaBeam, get_spinoza_beam
from Orb_Assistant.tpc_website_orb.tpc_core.geometric_glyph.signatures.glyph_signatures import GlyphSignatureEngine, get_glyph_engine
from Orb_Assistant.tpc_website_orb.tpc_core.geometric_glyph.retrieval.geometric_retrieval import GeometricRetrieval, get_geometric_retrieval
from Orb_Assistant.tpc_website_orb.tpc_core.drift_ping.drift_ping import DriftPingChain, get_drift_ping_chain


class PipelineStatus(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"
    ESCALATED = "escalated"


@dataclass
class PipelineResult:
    status: PipelineStatus
    output_text: str
    confidence: float
    philosopher_verdicts: Dict[str, Any]
    coherence_reading: Dict
    vault_retrieval: Dict
    ecm_output: Dict
    drift_report: Dict
    processing_time_ms: float
    glyph_signature: str
    depth_trace: List[str]


class TPCPipeline:
    """
    The full Triple Predicate Cubed pipeline.
    Orchestrates all 3 axes, 4 beams, vaults, and ECM gate.
    """

    def __init__(self, vector_dim: int = 512, hlsf_dimensions: int = 18):
        self.vector_dim = vector_dim
        self.hlsf_dimensions = hlsf_dimensions

        # Axis 3: Resolution Trinity
        self.a_priori = get_a_priori_vault()
        self.a_posteriori = get_a_posteriori_vault()
        self.ecm = get_ecm_gate()

        # Axis 1: Input Trinity
        self.input_gateway = get_input_gateway(vector_dim)
        self.hlsf = get_hlsf()
        self.egf = get_egf(self.a_priori, self.a_posteriori)

        # Axis 2: Reasoning Trinity
        self.depth_engine = DepthRecursionEngine(feature_dim=vector_dim)
        self.coherence_monitor = PhaseCoherenceMonitor()

        # Individual philosopher beams
        self.hume = get_hume_beam(vector_dim)
        self.kant = get_kant_beam(vector_dim)
        self.locke = get_locke_beam(vector_dim)
        self.spinoza = get_spinoza_beam(vector_dim)

        # Geometric Glyph
        self.glyph_engine = get_glyph_engine(dimensions=hlsf_dimensions)
        self.retrieval = get_geometric_retrieval()

        # Drift Ping
        self.drift = get_drift_ping_chain()

        # Register all pipeline gates for drift ping
        self._register_gates()

        # Pipeline state
        self.session_history: List[Dict] = []
        self.stats = {
            'total_queries': 0,
            'vault_hits': 0,
            'philosopher_recursions': 0,
            'ecm_escalations': 0,
            'avg_processing_time_ms': 0
        }

    def _register_gates(self):
        """Register all pipeline gates with drift ping system."""
        gates = [
            ("stt_gateway", "faster_whisper_input_gateway"),
            ("hlsf_gate", "traversal_weighting"),
            ("depth_k0", "surface_reasoning"),
            ("depth_k1", "abstract_reasoning"),
            ("depth_k2", "deep_reasoning"),
            ("philosopher_beams", "four_beam_reasoning"),
            ("coherence_check", "phase_coherence"),
            ("egf_gate", "certainty_gravity"),
            ("vault_retrieval", "geometric_retrieval"),
            ("ecm_gate", "epistemic_validation"),
            ("output_gate", "final_output")
        ]
        for gate_id, gate_type in gates:
            self.drift.register_gate(gate_id, gate_type)

    async def process(self, input_data: str, input_type: str = "text",
                     session_id: str = None) -> PipelineResult:
        """
        Process input through the full TPC pipeline.

        Args:
            input_data: Raw input (text string or audio path)
            input_type: "text" or "audio"
            session_id: Optional session identifier

        Returns:
            PipelineResult with full reasoning trace
        """
        start_time = time.time()
        session_id = session_id or f"tpc_{int(start_time * 1000)}"
        depth_trace = []

        try:
            # === GATE 1: STT Gateway — Faster-Whisper primary, Qwen STT optional ===
            gate1_stimulus = self.input_gateway.process(input_data, input_type)
            gate1_signal = gate1_stimulus.signal
            gate1_ping = self.drift.emit_ping("stt_gateway", "input_source", gate1_signal)
            confirmed = self.drift.confirm_ping(gate1_ping, gate1_signal)
            if confirmed.status.value != "confirmed":
                return self._error_result("Gate 1 input drift detected", start_time)
            depth_trace.append("Gate 1: Faster-Whisper input gateway normalized signal")

            # === GATE 2: HLSF — Traversal + Vivacity Weighting ===
            hlsf_node = self.hlsf.create_node(
                coordinates=self._to_hlsf_coordinates(gate1_signal),
                depth_level=0,
                source_beam="gate1_stt_gateway",
                vivacity=gate1_stimulus.confidence,
            )
            self.hlsf.traverse(hlsf_node.id)
            hlsf_signal = gate1_signal
            hlsf_ping = self.drift.emit_ping("hlsf_gate", "stt_gateway", hlsf_signal)
            confirmed = self.drift.confirm_ping(hlsf_ping, hlsf_signal)
            if confirmed.status.value != "confirmed":
                return self._error_result("HLSF drift detected", start_time)
            depth_trace.append("HLSF: 18D traversal complete")

            # === GATE 3: K0→K1→K2 Depth Recursion ===
            beam_processors = self._beam_processors()

            # K0: Surface reasoning
            k0_state = self.depth_engine.k0_surface(hlsf_signal, beam_processors)
            k0_signal = k0_state.output_vector
            k0_ping = self.drift.emit_ping("depth_k0", "hlsf_gate", k0_signal)
            self.drift.confirm_ping(k0_ping, k0_signal)
            depth_trace.append("K0: surface reasoning complete")

            # K1: Abstract reasoning
            k1_state = self.depth_engine.k1_abstraction(k0_state, beam_processors)
            k1_signal = k1_state.output_vector
            k1_ping = self.drift.emit_ping("depth_k1", "depth_k0", k1_signal)
            self.drift.confirm_ping(k1_ping, k1_signal)
            depth_trace.append("K1: abstract reasoning complete")

            # K2: Deep reasoning
            k2_state = self.depth_engine.k2_deep(k1_state, beam_processors)
            k2_signal = k2_state.output_vector
            k2_ping = self.drift.emit_ping("depth_k2", "depth_k1", k2_signal)
            self.drift.confirm_ping(k2_ping, k2_signal)
            depth_states = {
                DepthLevel.K0: k0_state,
                DepthLevel.K1: k1_state,
                DepthLevel.K2: k2_state,
            }
            depth_trace.append("K2: deep reasoning complete")

            # === GATE 4: Four Philosopher Beams (Simultaneous) ===
            philosopher_verdicts = await self._run_philosopher_beams(k2_signal, depth_states)
            beam_ping = self.drift.emit_ping("philosopher_beams", "depth_k2", k2_signal)
            self.drift.confirm_ping(beam_ping, k2_signal)
            depth_trace.append("4-Beam: simultaneous reasoning complete")

            # === GATE 5: Phase Coherence Check ===
            coherence = self.coherence_monitor.measure(philosopher_verdicts)
            coherence_ping = self.drift.emit_ping("coherence_check", "philosopher_beams", k2_signal)
            self.drift.confirm_ping(coherence_ping, k2_signal)
            depth_trace.append(f"Coherence: {coherence.coherence_score:.3f}")

            # === GATE 6: EGF — Certainty Gravity ===
            certainty = np.mean([v.confidence for v in philosopher_verdicts.values()])
            self.egf.retrieve(k2_signal)
            egf_ping = self.drift.emit_ping("egf_gate", "coherence_check", k2_signal)
            self.drift.confirm_ping(egf_ping, k2_signal)
            depth_trace.append(f"EGF: certainty={certainty:.3f}")

            # === GATE 7: Geometric Glyph + Vault Retrieval ===
            glyph_sig = self.glyph_engine.generate(k2_signal, certainty, source="tpc_pipeline")
            retrieval_result = self.retrieval.retrieve(k2_signal, certainty)
            vault_ping = self.drift.emit_ping("vault_retrieval", "egf_gate", k2_signal)
            self.drift.confirm_ping(vault_ping, k2_signal)
            depth_trace.append(f"Vault: {retrieval_result.result.value}")

            # === GATE 8: ECM — Epistemic Contract Validation ===
            ecm_output = self.ecm.validate(
                verdicts=philosopher_verdicts,
                depth_states=depth_states,
                coherence_reading=coherence,
                retrieval_result=retrieval_result
            )
            ecm_ping = self.drift.emit_ping("ecm_gate", "vault_retrieval", ecm_output.synthesized_output)
            self.drift.confirm_ping(ecm_ping, ecm_output.synthesized_output)
            depth_trace.append(f"ECM: {ecm_output.verdict.value} (conf={ecm_output.confidence:.3f})")

            # === GATE 9: Output Generation ===
            output_text = self._synthesize_output(
                ecm_output, philosopher_verdicts, retrieval_result
            )
            output_ping = self.drift.emit_ping("output_gate", "ecm_gate", ecm_output.synthesized_output)
            self.drift.confirm_ping(output_ping, ecm_output.synthesized_output)
            depth_trace.append("Output: synthesized")

            # Update stats
            self.stats['total_queries'] += 1
            if retrieval_result.result.value in ['exact', 'partial']:
                self.stats['vault_hits'] += 1
            if retrieval_result.result.value == 'novel':
                self.stats['philosopher_recursions'] += 1
            if ecm_output.verdict.value == 'escalate':
                self.stats['ecm_escalations'] += 1

            processing_time = (time.time() - start_time) * 1000

            result = PipelineResult(
                status=PipelineStatus.COMPLETE,
                output_text=output_text,
                confidence=float(ecm_output.confidence),
                philosopher_verdicts={k: {
                    'status': v.status.value if hasattr(v, 'status') else str(v.status),
                    'confidence': float(v.confidence)
                } for k, v in philosopher_verdicts.items()},
                coherence_reading={
                    'score': coherence.coherence_score,
                    'status': coherence.state.value
                },
                vault_retrieval={
                    'result': retrieval_result.result.value,
                    'confidence': float(retrieval_result.confidence),
                    'recommendation': retrieval_result.recommendation
                },
                ecm_output={
                    'verdict': ecm_output.verdict.value,
                    'confidence': float(ecm_output.confidence),
                    'violations': ecm_output.violations
                },
                drift_report=self.drift.get_drift_report(),
                processing_time_ms=float(processing_time),
                glyph_signature=self.glyph_engine._hash_signature(glyph_sig),
                depth_trace=depth_trace
            )

            self.session_history.append({
                'session_id': session_id,
                'input_type': input_type,
                'output': output_text[:200],
                'confidence': float(ecm_output.confidence),
                'processing_time_ms': processing_time,
                'timestamp': time.time()
            })

            return result

        except Exception as e:
            return self._error_result(str(e), start_time)

    async def _run_philosopher_beams(self, signal: np.ndarray, 
                                      depth_states: Dict) -> Dict:
        """Run all four philosopher beams simultaneously."""
        # Run beams in parallel
        hume_future = asyncio.create_task(
            asyncio.to_thread(self.hume.reason, signal, "K2")
        )
        kant_future = asyncio.create_task(
            asyncio.to_thread(self.kant.reason, signal, "K2")
        )
        locke_future = asyncio.create_task(
            asyncio.to_thread(self.locke.reason, signal, "K2")
        )
        spinoza_future = asyncio.create_task(
            asyncio.to_thread(self.spinoza.reason, signal, "K2")
        )

        verdicts = {
            'Hume': await hume_future,
            'Kant': await kant_future,
            'Locke': await locke_future,
            'Spinoza': await spinoza_future
        }

        return verdicts

    def _beam_processors(self):
        return [
            lambda signal, depth=0: self.hume.reason(signal, f"K{depth}").output_vector,
            lambda signal, depth=0: self.kant.reason(signal, f"K{depth}").output_vector,
            lambda signal, depth=0: self.locke.reason(signal, f"K{depth}").output_vector,
            lambda signal, depth=0: self.spinoza.reason(signal, f"K{depth}").output_vector,
        ]

    def _to_hlsf_coordinates(self, signal: np.ndarray) -> np.ndarray:
        coords = np.asarray(signal, dtype=float).flatten()[:self.hlsf_dimensions]
        if coords.size < self.hlsf_dimensions:
            coords = np.pad(coords, (0, self.hlsf_dimensions - coords.size))
        norm = np.linalg.norm(coords)
        if norm > 0:
            coords = coords / norm
        return coords

    def _synthesize_output(self, ecm_output, philosopher_verdicts, 
                            retrieval_result) -> str:
        """Synthesize human-readable output from pipeline results."""
        verdict = ecm_output.verdict.value
        confidence = ecm_output.confidence

        parts = []
        parts.append(f"[TPC Output | Confidence: {confidence:.1%}]")
        parts.append(f"ECM Verdict: {verdict.upper()}")

        if ecm_output.violations:
            parts.append(f"Violations: {', '.join(ecm_output.violations[:3])}")

        parts.append(f"Philosopher Consensus: " + 
                    " | ".join([f"{k}={v.confidence:.2f}" 
                               for k, v in philosopher_verdicts.items()]))

        parts.append(f"Vault: {retrieval_result.result.value} " +
                    f"(confidence: {retrieval_result.confidence:.2f})")

        parts.append(f"Drift: {self.drift.get_drift_report()['status']}")

        return "\n".join(parts)

    def _error_result(self, error_msg: str, start_time: float) -> PipelineResult:
        """Generate error result."""
        return PipelineResult(
            status=PipelineStatus.ERROR,
            output_text=f"[TPC ERROR] {error_msg}",
            confidence=0.0,
            philosopher_verdicts={},
            coherence_reading={},
            vault_retrieval={},
            ecm_output={},
            drift_report=self.drift.get_drift_report(),
            processing_time_ms=(time.time() - start_time) * 1000,
            glyph_signature="",
            depth_trace=[f"ERROR: {error_msg}"]
        )

    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        return self.stats.copy()

    def get_session_history(self, limit: int = 10) -> List[Dict]:
        """Get recent session history."""
        return self.session_history[-limit:]


# Singleton
_pipeline_instance = None

def get_tpc_pipeline(vector_dim: int = 512, hlsf_dim: int = 18) -> TPCPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = TPCPipeline(vector_dim, hlsf_dim)
    return _pipeline_instance
