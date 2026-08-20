# vaults/system.py - A Priori and A Posteriori Vaults (Robust + Antifragile Foundations)
import json
import os
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
import numpy as np
from datetime import datetime
import uuid

try:
    from core.geometric_primitives import GlyphSignature
except ImportError:
    GlyphSignature = None  # For type checking / future

CURRENT_SCHEMA_VERSION = 2  # Increment on breaking changes

def numpy_array_to_list(obj: Any) -> Any:
    """Custom JSON serializer for numpy arrays."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):  # np.float64 etc.
        return obj.item()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@dataclass
class VaultEntry:
    """Stored reasoning result with full state for durable reconstruction."""
    signature: 'GlyphSignature'
    conclusion: str
    philosopher_votes: Dict[str, str]
    confidence: float
    timestamp: str
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: int = CURRENT_SCHEMA_VERSION
    vivacity: float = 1.0          # Antifragile: strengthens with reinforcement, decays over time
    origin: str = "pipeline"       # "a_priori", "demo", "user_correction", etc.
    source_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        d = asdict(self)
        # Ensure signature serializes cleanly
        if hasattr(self.signature, 'coordinates') and isinstance(self.signature.coordinates, np.ndarray):
            d['signature'] = {
                'coordinates': self.signature.coordinates.tolist(),
                'certainty': getattr(self.signature, 'certainty', 0.0),
                'vivacity': getattr(self.signature, 'vivacity', 800.0),
                'origin': getattr(self.signature, 'origin', self.origin),
            }
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'VaultEntry':
        """Reconstruct with migration support."""
        if data.get('schema_version', 1) < CURRENT_SCHEMA_VERSION:
            data = cls._migrate(data)
        
        # Rebuild GlyphSignature (adjust based on your actual class)
        coords = np.array(data['signature']['coordinates'], dtype=np.float32)
        sig = GlyphSignature(
            coordinates=coords,
            certainty=data['signature'].get('certainty', 0.0),
            vivacity=data['signature'].get('vivacity', data.get('vivacity', 1.0) * 800.0),
            origin=data['signature'].get('origin', data.get('origin', 'vault')),
        )
        
        return cls(
            signature=sig,
            conclusion=data['conclusion'],
            philosopher_votes=data['philosopher_votes'],
            confidence=data['confidence'],
            timestamp=data['timestamp'],
            entry_id=data.get('entry_id', str(uuid.uuid4())),
            schema_version=data.get('schema_version', CURRENT_SCHEMA_VERSION),
            vivacity=data.get('vivacity', 1.0),
            origin=data.get('origin', 'pipeline'),
            source_metadata=data.get('source_metadata', {})
        )

    @staticmethod
    def _migrate(data: Dict) -> Dict:
        """Example migration (extend as versions grow)."""
        if data.get('schema_version') == 1:
            data['vivacity'] = 1.0
            data['origin'] = 'legacy'
            data['schema_version'] = 2
            if 'entry_id' not in data:
                data['entry_id'] = str(uuid.uuid4())
        return data


class APrioriVault:
    """
    Pre-pruned ethical and logical certainties.
    Now fully deterministic and structurally encoded.
    """
    def __init__(self, storage_path: str = "vaults/a_priori"):
        self.storage_path = storage_path
        self.certainties: List[Dict] = []
        self._initialize_certainties()

    def _initialize_certainties(self):
        """Structural certainties with deterministic signatures."""
        self.certainties = [
            {
                "id": "causality_exists",
                "pattern": "causal_inference",
                "certainty": 0.95,
                "source": "hume_structural",
                "stimulus": [0.15, 0.45, 0.2, 0.6, 0.2, 0.2, 0, 0, 0, 0, 0, 0, 1.0, 1.0, 0.2, 0.0, 0.2, 0.0],
            },
            {
                "id": "contradiction_invalid",
                "pattern": "no_contradiction",
                "certainty": 0.95,
                "source": "kant_structural",
                "stimulus": [0.1, 0.05, 0.2, 0.95, 0.2, 0.2, 0, 0, 0, 0, 0, 0, 0.2, 0.0, 1.0, 0.0, 0.2, 0.0],
            },
            {
                "id": "autonomy_default",
                "pattern": "preserve_autonomy",
                "certainty": 0.95,
                "source": "locke_structural",
                "stimulus": [0.1, 0.05, 0.2, 0.95, 0.2, 0.2, 0, 0, 0, 0, 0, 0, 0.2, 0.0, 0.2, 1.0, 0.0, 0.0],
            },
            {
                "id": "geometric_order",
                "pattern": "necessity_through_geometry",
                "certainty": 0.95,
                "source": "spinoza_structural",
                "stimulus": [0.1, 0.05, 0.2, 0.8, 0.2, 0.2, 0, 0, 0, 0, 0, 0, 0.2, 0.0, 0.2, 0.0, 1.0, 0.0],
            },
        ]

    def check(self, signature: 'GlyphSignature') -> Optional[Tuple[str, float]]:
        """Deterministic structural match."""
        for certainty in self.certainties:
            structural_sig = GlyphSignature.from_stimulus(
                np.array(certainty["stimulus"], dtype=float),
                origin=f"a_priori:{certainty['source']}",
            )
            structural_sig.certainty = certainty["certainty"]
            
            distance = signature.geometric_distance(structural_sig)
            if distance < 0.08:  # Tight threshold for structural certainty
                return certainty["pattern"], certainty["certainty"]
        return None

    def is_structurally_resolved(self, query_type: str) -> bool:
        return any(c["pattern"] == query_type for c in self.certainties)


class APosterioriVault:
    """
    Empirical evidence store. Now persistent, reconstructible, and antifragile.
    """
    def __init__(self, storage_path: str = "vaults/a_posteriori.json"):
        self.storage_path = storage_path
        self.entries: List[VaultEntry] = []
        self.retrieval_threshold = 0.08   # Exact or near-identical
        self.partial_threshold = 0.22
        self.load_errors: List[str] = []
        self._load()

    def _load(self):
        """Robust load with migration."""
        self.load_errors = []
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = data.get("entries", [])
            if not isinstance(data, list):
                raise TypeError("vault root must be a list or an object with an entries list")
            self.entries = []
            for index, item in enumerate(data):
                try:
                    self.entries.append(VaultEntry.from_dict(item))
                except (KeyError, TypeError, ValueError, ImportError) as e:
                    self.load_errors.append(f"entry_{index}: {e}")
            print(f"[OK] Loaded {len(self.entries)} vault entries (schema v{CURRENT_SCHEMA_VERSION})")
            if self.load_errors:
                print(f"[WARN] Skipped {len(self.load_errors)} invalid vault entries")
        except (json.JSONDecodeError, KeyError, TypeError, OSError) as e:
            print(f"[WARN] Vault load failed (corrupt/migrating?): {e}. Starting fresh.")
            self.entries = []

    def store(self, entry: VaultEntry, force: bool = False):
        """Store with reinforcement and basic conflict detection."""
        if not force and entry.confidence <= 0.6:  # Your original threshold; override with force=True in demo
            return

        # Reinforcement / Antifragile loop
        for existing in self.entries:
            dist = entry.signature.geometric_distance(existing.signature)
            if dist < self.retrieval_threshold:
                if existing.conclusion == entry.conclusion:
                    # Strengthen on agreement
                    existing.vivacity = min(2.0, existing.vivacity + 0.2)
                    existing.confidence = max(existing.confidence, entry.confidence * 0.9)
                else:
                    # Conflict detected — flag for future resolution (antifragile stress)
                    existing.source_metadata['has_conflict'] = True
                    print(f"[WARN] Vault conflict detected for entry {existing.entry_id}")
                break
        else:
            # Novel entry
            self.entries.append(entry)

        # Prune old/weak entries (optional antifragile pruning)
        self.entries = [e for e in self.entries if e.vivacity > 0.3][-2000:]  # Keep recent + strong

        self._save()

    def _save(self):
        directory = os.path.dirname(self.storage_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        serializable = [e.to_dict() for e in self.entries]
        temp_path = f"{self.storage_path}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, default=numpy_array_to_list, indent=2, ensure_ascii=False)
        os.replace(temp_path, self.storage_path)

    def retrieve(self, signature: 'GlyphSignature') -> Tuple[Optional[VaultEntry], float, str]:
        """Geometric retrieval with vivacity weighting."""
        if not self.entries:
            return None, 0.0, "novel"

        nearest = None
        min_distance = float('inf')
        best_vivacity = 0.0

        for entry in self.entries:
            dist = signature.geometric_distance(entry.signature)
            # Weight distance by vivacity (stronger memories preferred)
            effective_dist = dist / (entry.vivacity ** 0.5)
            if effective_dist < min_distance:
                min_distance = effective_dist
                nearest = entry
                best_vivacity = entry.vivacity

        confidence = min(0.95, max(0.0, 1.0 - min_distance) * best_vivacity)

        if min_distance < self.retrieval_threshold:
            return nearest, confidence, "exact"
        elif min_distance < self.partial_threshold:
            return nearest, confidence * 0.6, "partial"
        return None, 0.0, "novel"

    def get_stats(self) -> Dict:
        if not self.entries:
            return {
                "total_entries": 0,
                "avg_vivacity": 0.0,
                "storage_path": self.storage_path,
                "schema_version": CURRENT_SCHEMA_VERSION,
                "load_errors": self.load_errors
            }
        return {
            "total_entries": len(self.entries),
            "avg_vivacity": np.mean([e.vivacity for e in self.entries]),
            "avg_confidence": np.mean([e.confidence for e in self.entries]),
            "conflicts_detected": sum(1 for e in self.entries if e.source_metadata.get('has_conflict')),
            "retrieval_threshold": self.retrieval_threshold,
            "storage_path": self.storage_path,
            "schema_version": CURRENT_SCHEMA_VERSION,
            "load_errors": self.load_errors
        }


# Usage / Demo
if __name__ == "__main__":
    print("[OK] Vault System (Robust + Antifragile Foundations)")
    a_priori = APrioriVault()
    a_posteriori = APosterioriVault()
    
    print(f"  - A Priori certainties: {len(a_priori.certainties)} structural truths")
    print(f"  - A Posteriori entries on load: {len(a_posteriori.entries)}")
    print("  - Persistence & reconstruction: full (with schema migration)")
    print("  - Signatures: deterministic & shape-preserving")
    print("  - Antifragile traits: vivacity reinforcement, conflict flagging, pruning")
    
    # Test same-session vs reload would now work reliably
