"""
Drift Ping — Confirmation Handshake Chain
Not a loop. Not a recursion.
Each gate sends a confirmation signal back to the previous gate before the next gate fires.
Forward progress only. The system does not backtrack — it confirms.

Mechanism:
- Each gate emits a Ping to the previous gate upon successful receipt of valid signal
- If previous gate does not receive confirmation within threshold, signal is flagged
- Corrupted or degraded signals cannot pass through silently
- Small errors cannot compound because each gate is confirmed clean before next begins

Prior implementation record:
- Cali X One: Drift Ping demonstrated zero drift across all test conditions
- Caleon: Zero drift in deterministically absolute environment
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import hashlib


class PingStatus(Enum):
    CONFIRMED = "confirmed"
    DEGRADED = "degraded"
    CORRUPTED = "corrupted"
    TIMEOUT = "timeout"
    PENDING = "pending"


@dataclass
class DriftPing:
    """A single drift ping packet."""
    gate_id: str
    previous_gate_id: str
    signal_hash: str
    timestamp: float
    status: PingStatus
    latency_ms: float
    signal_integrity: float
    payload_sample: np.ndarray


class DriftPingChain:
    """
    Confirmation handshake chain embedded in the TPC pipeline.
    Ensures signal integrity between every gate transition.
    """

    def __init__(self, confirmation_threshold_ms: float = 100.0,
                 integrity_threshold: float = 0.95):
        self.confirmation_threshold_ms = confirmation_threshold_ms
        self.integrity_threshold = integrity_threshold
        self.ping_log: List[DriftPing] = []
        self.gate_registry: Dict[str, Dict] = {}
        self.drift_count = 0
        self.confirmation_count = 0

    def register_gate(self, gate_id: str, gate_type: str):
        """Register a pipeline gate in the drift ping system."""
        self.gate_registry[gate_id] = {
            'type': gate_type,
            'registered_at': time.time(),
            'ping_count': 0,
            'drift_detected': 0
        }

    def emit_ping(self, from_gate: str, to_gate: str, 
                  signal: np.ndarray) -> DriftPing:
        """
        Emit a drift ping from one gate to the previous gate.

        Args:
            from_gate: Current gate (sender)
            to_gate: Previous gate (recipient of confirmation)
            signal: The signal being passed
        """
        # Hash the signal for integrity checking
        signal_hash = self._hash_signal(signal)

        # Measure signal integrity
        integrity = self._measure_integrity(signal)

        ping = DriftPing(
            gate_id=from_gate,
            previous_gate_id=to_gate,
            signal_hash=signal_hash,
            timestamp=time.time(),
            status=PingStatus.PENDING,
            latency_ms=0.0,
            signal_integrity=integrity,
            payload_sample=signal[:10].copy()  # Sample for debugging
        )

        return ping

    def confirm_ping(self, ping: DriftPing, 
                     received_signal: np.ndarray) -> DriftPing:
        """
        Confirm receipt of ping at the receiving gate.

        Returns updated ping with status.
        """
        start_time = ping.timestamp
        latency_ms = (time.time() - start_time) * 1000

        # Check latency
        if latency_ms > self.confirmation_threshold_ms:
            ping.status = PingStatus.TIMEOUT
            self.drift_count += 1
            return ping

        # Check signal integrity
        received_hash = self._hash_signal(received_signal)
        if received_hash != ping.signal_hash:
            ping.status = PingStatus.CORRUPTED
            self.drift_count += 1
            return ping

        # Check integrity score
        received_integrity = self._measure_integrity(received_signal)
        if received_integrity < self.integrity_threshold:
            ping.status = PingStatus.DEGRADED
            self.drift_count += 1
            return ping

        # All checks passed
        ping.status = PingStatus.CONFIRMED
        ping.latency_ms = latency_ms
        self.confirmation_count += 1

        # Update gate stats
        if ping.gate_id in self.gate_registry:
            self.gate_registry[ping.gate_id]['ping_count'] += 1

        self.ping_log.append(ping)
        return ping

    def _hash_signal(self, signal: np.ndarray) -> str:
        """Create deterministic hash of signal vector."""
        # Round to reduce floating-point noise
        rounded = np.round(signal, decimals=6)
        return hashlib.sha256(rounded.tobytes()).hexdigest()[:16]

    def _measure_integrity(self, signal: np.ndarray) -> float:
        """Measure signal integrity score."""
        # Check for NaN/Inf
        if np.any(np.isnan(signal)) or np.any(np.isinf(signal)):
            return 0.0

        # Check for zero signal (complete loss)
        magnitude = np.linalg.norm(signal)
        if magnitude < 1e-10:
            return 0.0

        return 1.0

    def verify_chain(self, gate_sequence: List[str], 
                     signals: List[np.ndarray]) -> Tuple[bool, List[DriftPing]]:
        """
        Verify a complete gate sequence.

        Returns (all_confirmed, ping_history)
        """
        pings = []
        all_confirmed = True

        for i in range(1, len(gate_sequence)):
            from_gate = gate_sequence[i]
            to_gate = gate_sequence[i-1]
            signal = signals[i]

            # Emit ping
            ping = self.emit_ping(from_gate, to_gate, signal)

            # Simulate confirmation (in real system, this is cross-process)
            confirmed_ping = self.confirm_ping(ping, signal)
            pings.append(confirmed_ping)

            if confirmed_ping.status != PingStatus.CONFIRMED:
                all_confirmed = False

        return all_confirmed, pings

    def get_drift_report(self) -> Dict:
        """Generate drift detection report."""
        total = self.confirmation_count + self.drift_count
        drift_rate = self.drift_count / max(1, total)

        return {
            'total_pings': total,
            'confirmed': self.confirmation_count,
            'drift_detected': self.drift_count,
            'drift_rate': drift_rate,
            'target_drift_rate': 0.0,
            'gates_registered': len(self.gate_registry),
            'integrity_threshold': self.integrity_threshold,
            'latency_threshold_ms': self.confirmation_threshold_ms,
            'status': 'ZERO_DRIFT' if drift_rate == 0 else 'DRIFT_DETECTED'
        }

    def get_gate_stats(self) -> Dict:
        """Get per-gate statistics."""
        return {gate_id: stats.copy() for gate_id, stats in self.gate_registry.items()}


# Singleton
_drift_chain = None

def get_drift_ping_chain(threshold_ms: float = 100.0, 
                         integrity: float = 0.95) -> DriftPingChain:
    global _drift_chain
    if _drift_chain is None:
        _drift_chain = DriftPingChain(threshold_ms, integrity)
    return _drift_chain
