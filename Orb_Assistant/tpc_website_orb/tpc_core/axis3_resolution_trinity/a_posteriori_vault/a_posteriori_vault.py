"""
A Posteriori Vault
Empirical evidence store with weighted geometric glyph signatures.
Vaulted prior returns. Pattern-matched retrieval via cosine similarity.
Distance threshold determines vault hit, partial hit, or escalation.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path
import time


@dataclass
class APosterioriEntry:
    """An a posteriori empirical entry."""
    id: str
    input_signature: np.ndarray
    output_signature: np.ndarray
    content: str
    certainty: float
    retrieval_count: int = 0
    last_accessed: float = 0.0
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()
        if self.last_accessed == 0:
            self.last_accessed = self.timestamp


class APosterioriVault:
    """
    Empirical evidence store.
    Grows from experience. Weighted by retrieval frequency and certainty.
    """

    def __init__(self, persistence_path: str = None, max_entries: int = 10000):
        self.entries: Dict[str, APosterioriEntry] = {}
        self.persistence_path = persistence_path
        self.max_entries = max_entries
        self.access_log: List[Dict] = []

        if persistence_path and Path(persistence_path).exists():
            self._load()

    def store(self, input_signature: np.ndarray, output_signature: np.ndarray,
              content: str, certainty: float) -> str:
        """
        Store a new empirical observation.
        Returns the vault entry ID.
        """
        entry_id = f"apost_{int(time.time() * 1000)}_{len(self.entries)}"

        entry = APosterioriEntry(
            id=entry_id,
            input_signature=input_signature,
            output_signature=output_signature,
            content=content,
            certainty=certainty,
            timestamp=time.time()
        )

        self.entries[entry_id] = entry

        # Prune if over max
        if len(self.entries) > self.max_entries:
            self._prune_oldest()

        self._save()
        return entry_id

    def retrieve(self, query_signature: np.ndarray, 
                 top_k: int = 5,
                 distance_threshold: float = 0.3) -> List[Tuple[APosterioriEntry, float]]:
        """
        Retrieve entries by cosine similarity to query signature.
        Returns list of (entry, confidence_score) tuples.
        """
        if not self.entries:
            return []

        scored = []
        for entry in self.entries.values():
            # Compare against input signatures
            sim = np.dot(query_signature, entry.input_signature) / (
                np.linalg.norm(query_signature) * np.linalg.norm(entry.input_signature) + 1e-10
            )

            # Convert similarity to distance
            distance = 1.0 - sim

            if distance <= distance_threshold:
                # Weight by certainty and access frequency
                confidence = sim * entry.certainty * (1 + 0.1 * entry.retrieval_count)
                scored.append((entry, confidence))

        # Sort by confidence
        scored.sort(key=lambda x: x[1], reverse=True)

        # Update access counts
        for entry, _ in scored[:top_k]:
            entry.retrieval_count += 1
            entry.last_accessed = time.time()

        return scored[:top_k]

    def _prune_oldest(self):
        """Remove least-accessed entries when vault is full."""
        # Sort by (retrieval_count, last_accessed) ascending
        sorted_entries = sorted(
            self.entries.items(),
            key=lambda x: (x[1].retrieval_count, x[1].last_accessed)
        )

        # Remove bottom 10%
        remove_count = max(1, len(self.entries) // 10)
        for entry_id, _ in sorted_entries[:remove_count]:
            del self.entries[entry_id]

        print(f"[A Posteriori Vault] Pruned {remove_count} entries. Remaining: {len(self.entries)}")

    def get_all_entries(self) -> List[Dict]:
        """Get all entries as dictionaries."""
        return [
            {
                'id': e.id,
                'input_signature': e.input_signature.tolist(),
                'output_signature': e.output_signature.tolist(),
                'content': e.content,
                'certainty': e.certainty,
                'retrieval_count': e.retrieval_count,
                'timestamp': e.timestamp
            }
            for e in self.entries.values()
        ]

    def get_stats(self) -> Dict:
        """Get vault statistics."""
        if not self.entries:
            return {'total_entries': 0, 'avg_certainty': 0, 'avg_retrievals': 0}

        certainties = [e.certainty for e in self.entries.values()]
        retrievals = [e.retrieval_count for e in self.entries.values()]

        return {
            'total_entries': len(self.entries),
            'avg_certainty': np.mean(certainties),
            'avg_retrievals': np.mean(retrievals),
            'max_retrievals': max(retrievals),
            'oldest_entry': min(e.timestamp for e in self.entries.values()),
            'newest_entry': max(e.timestamp for e in self.entries.values())
        }

    def _save(self):
        """Persist vault to disk."""
        if not self.persistence_path:
            return

        data = self.get_all_entries()
        Path(self.persistence_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.persistence_path, 'w') as f:
            json.dump(data, f)

    def _load(self):
        """Load vault from disk."""
        try:
            with open(self.persistence_path, 'r') as f:
                data = json.load(f)

            for item in data:
                entry = APosterioriEntry(
                    id=item['id'],
                    input_signature=np.array(item['input_signature']),
                    output_signature=np.array(item['output_signature']),
                    content=item['content'],
                    certainty=item['certainty'],
                    retrieval_count=item.get('retrieval_count', 0),
                    timestamp=item['timestamp']
                )
                self.entries[entry.id] = entry

            print(f"[A Posteriori Vault] Loaded {len(self.entries)} entries")
        except Exception as e:
            print(f"[A Posteriori Vault] Load failed: {e}")


# Singleton
_aposteriori_instance = None

def get_a_posteriori_vault(persistence_path: str = None) -> APosterioriVault:
    global _aposteriori_instance
    if _aposteriori_instance is None:
        _aposteriori_instance = APosterioriVault(persistence_path)
    return _aposteriori_instance
