import json
import time
import hashlib
import numpy as np
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from tpc_cubed import GeometricGlyph, VaultEntry, DriftPing


class ACP:
    """Adaptive Cochlear Processor - Unified input synthesis"""
    
    def __init__(self):
        self.audio_path_enabled = True
        self.text_path_enabled = True
        self.cochlear_shape_factor = 1.618  # Golden ratio
    
    def process_text(self, text: str) -> GeometricGlyph:
        """Process text through cochlear-like signal shaping"""
        # Text normalization mimicking cochlear signal shaping
        # Convert text to frequency-like representation
        
        # Character frequency analysis (simplified cochlear mapping)
        char_freq = defaultdict(int)
        for char in text.lower():
            char_freq[char] += 1
        
        # Map to 18D HLSF coordinates
        coords = np.zeros(18)
        for i, (char, count) in enumerate(sorted(char_freq.items())):
            idx = i % 18
            coords[idx] += count * (ord(char) / 255.0)
        
        # Normalize
        coords = coords / (np.linalg.norm(coords) + 1e-10)
        
        # Apply cochlear-like shaping (logarithmic scaling)
        coords = np.sign(coords) * np.log1p(np.abs(coords) * self.cochlear_shape_factor)
        
        # Compute phase angle from text characteristics
        phase = (len(text) % 360) * (np.pi / 180)
        
        return GeometricGlyph(
            coordinates=coords,
            phase_angle=phase,
            vivacity=min(len(text) / 1000.0, 1.0)
        )
    
    def process_audio(self, audio_data: np.ndarray) -> GeometricGlyph:
        """Process audio through Cochlear 3.0 AdaptiveCochlearProcessor."""
        if len(audio_data) == 0:
            return self._empty_glyph()

        import sys, os
        cochlear_dir = os.path.join(os.path.dirname(__file__), "cochlear_processor_3.0")
        if cochlear_dir not in sys.path:
            sys.path.insert(0, cochlear_dir)
        from processor import AdaptiveCochlearProcessor

        proc = AdaptiveCochlearProcessor()
        result = proc.process_audio(audio_data)

        # AdaptiveCochlearProcessor returns a dict with 'features' (18D) and 'phase'
        features = np.array(result.get("features", np.zeros(18)), dtype=float)
        if features.shape[0] != 18:
            tmp = np.zeros(18)
            tmp[: min(18, len(features))] = features[: min(18, len(features))]
            features = tmp

        phase = float(result.get("phase", 0.0))
        vivacity = float(result.get("vivacity", min(np.mean(np.abs(features)) * 2, 1.0)))

        return GeometricGlyph(
            coordinates=features,
            phase_angle=phase,
            vivacity=vivacity,
        )
    
    def _empty_glyph(self) -> GeometricGlyph:
        return GeometricGlyph(
            coordinates=np.zeros(18),
            phase_angle=0.0,
            vivacity=0.0
        )
    
    def synthesize(self, input_data: Any, input_type: str = "text") -> GeometricGlyph:
        """Unified synthesis - both audio and text arrive as normalized epistemic stimulus"""
        if input_type == "text":
            return self.process_text(str(input_data))
        elif input_type == "audio":
            return self.process_audio(input_data)
        else:
            raise ValueError(f"Unknown input type: {input_type}")

class VaultSystem:
    """A Priori and A Posteriori Vault management"""
    
    def __init__(self):
        self.a_priori_vault: List[VaultEntry] = []
        self.a_posteriori_vault: List[VaultEntry] = []
        self.geometric_index: Dict[str, List[VaultEntry]] = defaultdict(list)
        self.retrieval_threshold = 0.7  # Cosine similarity threshold
        self.partial_threshold = 0.4
    
    def seed_a_priori(self, ethical_certainties: List[Dict]):
        """Seed a priori vault with structurally encoded ethical/logical certainties"""
        for certainty in ethical_certainties:
            glyph = self._certainty_to_glyph(certainty)
            entry = VaultEntry(
                content=certainty,
                glyph=glyph,
                weight=1.0,
                entry_type="priori",
                philosopher_bindings=certainty.get("philosopher_bindings", {})
            )
            self.a_priori_vault.append(entry)
            self._index_entry(entry)
    
    def add_a_posteriori(self, evidence: Any, glyph: GeometricGlyph, 
                        weight: float = 1.0,
                        philosopher_bindings: Optional[Dict] = None):
        """Add empirical evidence to a posteriori vault"""
        entry = VaultEntry(
            content=evidence,
            glyph=glyph,
            weight=weight,
            entry_type="posteriori",
            philosopher_bindings=philosopher_bindings or {}
        )
        self.a_posteriori_vault.append(entry)
        self._index_entry(entry)
    
    def _certainty_to_glyph(self, certainty: Dict) -> GeometricGlyph:
        """Convert ethical certainty to geometric signature"""
        # Deterministic encoding of certainty content
        content_str = json.dumps(certainty, sort_keys=True)
        hash_bytes = hashlib.sha256(content_str.encode()).digest()
        
        # Map hash to 18D coordinates
        coords = np.array([b / 255.0 for b in hash_bytes[:18]])
        
        # Apply golden ratio phase
        phase = (sum(hash_bytes[18:22]) / 1024.0) * 2 * np.pi
        
        return GeometricGlyph(coordinates=coords, phase_angle=phase, vivacity=1.0)
    
    def _index_entry(self, entry: VaultEntry):
        """Index entry by geometric region for fast retrieval"""
        # Simple grid-based indexing
        region = self._get_region(entry.glyph)
        self.geometric_index[region].append(entry)
    
    def _get_region(self, glyph: GeometricGlyph) -> str:
        """Determine geometric region for indexing"""
        # Quantize coordinates to grid cells
        quantized = np.round(glyph.coordinates * 10).astype(int)
        return "_".join(map(str, quantized[:3]))  # Use first 3 dims for coarse indexing
    
    def retrieve(self, query_glyph: GeometricGlyph, 
                vault_type: str = "both") -> Tuple[str, Optional[VaultEntry], float]:
        """
        Retrieve from vaults using geometric signatures
        Returns: (status, entry, confidence)
        status: "exact", "partial", "novel", "orthogonal"
        """
        entries_to_search = []
        if vault_type in ["both", "priori"]:
            entries_to_search.extend(self.a_priori_vault)
        if vault_type in ["both", "posteriori"]:
            entries_to_search.extend(self.a_posteriori_vault)
        
        if not entries_to_search:
            return "novel", None, 0.0
        
        # Find nearest entry
        best_entry = None
        best_similarity = -1
        best_distance = float('inf')
        
        for entry in entries_to_search:
            sim = query_glyph.cosine_similarity(entry.glyph)
            dist = query_glyph.distance_to(entry.glyph)
            
            if sim > best_similarity:
                best_similarity = sim
                best_distance = dist
                best_entry = entry
        
        # Determine retrieval status
        if best_similarity >= self.retrieval_threshold:
            status = "exact"
            confidence = best_similarity
            best_entry.retrieval_count += 1
        elif best_similarity >= self.partial_threshold:
            status = "partial"
            confidence = best_similarity * 0.7  # Weighted partial confidence
        elif best_distance > np.sqrt(18):  # Roughly orthogonal in 18D
            status = "orthogonal"
            confidence = 0.0
        else:
            status = "novel"
            confidence = 0.0
        
        return status, best_entry, confidence
    
    def get_stats(self) -> Dict:
        return {
            "a_priori_count": len(self.a_priori_vault),
            "a_posteriori_count": len(self.a_posteriori_vault),
            "total_entries": len(self.a_priori_vault) + len(self.a_posteriori_vault),
            "index_regions": len(self.geometric_index)
        }

class DriftPingChain:
    """Forward-only confirmation handshake chain"""
    
    def __init__(self):
        self.pings: List[DriftPing] = []
        self.confirmation_threshold = 1.0  # seconds
        self.gate_sequence = [
            "acp", "hlsf", "depth_recursion", "philosopher_loops",
            "phase_coherence", "egf", "vault_retrieval", "ecm", "output"
        ]
    
    def create_ping(self, gate_id: str, signal_data: Any) -> DriftPing:
        """Create new ping in chain"""
        signal_hash = hashlib.sha256(str(signal_data).encode()).hexdigest()[:16]
        previous_hash = self.pings[-1].compute_hash() if self.pings else None
        
        ping = DriftPing(
            gate_id=gate_id,
            timestamp=time.time(),
            signal_hash=signal_hash,
            previous_ping_hash=previous_hash
        )
        self.pings.append(ping)
        return ping
    
    def confirm_ping(self, ping: DriftPing) -> bool:
        """Confirm ping receipt"""
        return ping.confirm()
    
    def verify_chain(self) -> Tuple[bool, List[str]]:
        """Verify entire chain integrity"""
        issues = []
        
        for i, ping in enumerate(self.pings):
            # Check confirmation
            if not ping.confirmed:
                issues.append(f"Gate {ping.gate_id}: unconfirmed")
            
            # Check chain linkage
            if i > 0:
                expected_prev = self.pings[i-1].compute_hash()
                if ping.previous_ping_hash != expected_prev:
                    issues.append(f"Gate {ping.gate_id}: chain break")
            
            # Check timing
            if i > 0:
                time_diff = ping.timestamp - self.pings[i-1].timestamp
                if time_diff > self.confirmation_threshold:
                    issues.append(f"Gate {ping.gate_id}: timeout")
        
        return len(issues) == 0, issues
    
    def get_stats(self) -> Dict:
        confirmed = sum(1 for p in self.pings if p.confirmed)
        return {
            "total_pings": len(self.pings),
            "confirmed": confirmed,
            "integrity": confirmed / len(self.pings) if self.pings else 0
        }

print("ACP, Vault System, and Drift Ping Chain defined")
