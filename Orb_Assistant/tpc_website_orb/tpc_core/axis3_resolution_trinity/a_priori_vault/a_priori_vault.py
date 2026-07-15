"""
A Priori Vault
Pre-pruned ethical and logical certainties.
Structurally encoded at the root level by the four philosopher rule sets.
Ethical reasoning is not bolted on — it is load-bearing architecture.
Most queries are variations on already-resolved epistemic ground.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path
import time


@dataclass
class APrioriEntry:
    """An a priori certainty entry."""
    id: str
    content: str
    signature: np.ndarray
    certainty: float
    source_philosophers: List[str]
    category: str  # 'ethical', 'logical', 'mathematical', 'causal'
    timestamp: float


class APrioriVault:
    """
    Pre-seeded vault of ethical and logical certainties.
    Structurally encoded by philosopher rule sets.
    """

    def __init__(self, persistence_path: str = None):
        self.entries: Dict[str, APrioriEntry] = {}
        self.persistence_path = persistence_path

        # Seed with philosopher-derived certainties
        self._seed_philosopher_certainties()

        if persistence_path and Path(persistence_path).exists():
            self._load()

    def _seed_philosopher_certainties(self):
        """
        Seed the vault with structurally encoded certainties.
        These are NOT learned — they are architecturally embedded.
        """
        # Hume-derived: Empirical grounding requirements
        self._add_entry(
            id="hume_empirical_grounding",
            content="All claims require traceable empirical grounding. Causal inferences are probabilistic, not necessary.",
            certainty=0.98,
            source_philosophers=["Hume"],
            category="causal"
        )

        # Kant-derived: Universalizability
        self._add_entry(
            id="kant_universalizability",
            content="Principles must be universalizable without internal contradiction. Duty-based reasoning supersedes consequential preference.",
            certainty=0.97,
            source_philosophers=["Kant"],
            category="ethical"
        )

        # Locke-derived: Rights and consent
        self._add_entry(
            id="locke_consent_rights",
            content="Individual autonomy and consent are morally primary. No conclusion may violate legitimate rights of agents involved.",
            certainty=0.96,
            source_philosophers=["Locke"],
            category="ethical"
        )

        # Spinoza-derived: Demonstrable necessity
        self._add_entry(
            id="spinoza_demonstration",
            content="Claims require derivation from definitions, axioms, and demonstrable propositions. Necessity, not plausibility.",
            certainty=0.95,
            source_philosophers=["Spinoza"],
            category="logical"
        )

        # Cross-philosopher: Non-violation
        self._add_entry(
            id="cross_non_violation",
            content="No output may endorse rights violation, logical contradiction, ungrounded abstraction, or undemonstrated claim.",
            certainty=0.99,
            source_philosophers=["Hume", "Kant", "Locke", "Spinoza"],
            category="ethical"
        )

        # Mathematical certainties
        self._add_entry(
            id="math_identity",
            content="A = A. Identity is preserved across all transformations.",
            certainty=1.0,
            source_philosophers=["Spinoza"],
            category="mathematical"
        )

        self._add_entry(
            id="math_contradiction",
            content="A and not-A cannot both be true. Contradiction invalidates any reasoning chain.",
            certainty=1.0,
            source_philosophers=["Kant", "Spinoza"],
            category="mathematical"
        )

        # Epistemic humility
        self._add_entry(
            id="epistemic_humility",
            content="Confidence is bounded. No output claims 100% certainty. All knowledge is provisional.",
            certainty=0.95,
            source_philosophers=["Hume", "Spinoza"],
            category="logical"
        )

    def _add_entry(self, id: str, content: str, certainty: float,
                   source_philosophers: List[str], category: str):
        """Add an entry with auto-computed signature."""
        # Compute geometric signature from content
        signature = self._compute_signature(content)

        entry = APrioriEntry(
            id=id,
            content=content,
            signature=signature,
            certainty=certainty,
            source_philosophers=source_philosophers,
            category=category,
            timestamp=time.time()
        )

        self.entries[id] = entry

    def _compute_signature(self, content: str) -> np.ndarray:
        """Compute geometric glyph signature from content."""
        # Character-level encoding with golden ratio phase damping
        chars = [ord(c) for c in content[:256]]  # Limit length
        vec = np.zeros(512)
        vec[:len(chars)] = np.array(chars) / 255.0

        # Apply phasor transform
        phi = (1 + np.sqrt(5)) / 2
        phases = np.exp(1j * phi * np.arange(512))
        signature = np.fft.ifft(np.fft.fft(vec) * phases).real
        return signature / (np.linalg.norm(signature) + 1e-10)

    def get_all_entries(self) -> List[Dict]:
        """Get all entries as dictionaries."""
        return [
            {
                'id': e.id,
                'content': e.content,
                'signature': e.signature.tolist(),
                'certainty': e.certainty,
                'source_philosophers': e.source_philosophers,
                'category': e.category,
                'timestamp': e.timestamp
            }
            for e in self.entries.values()
        ]

    def query(self, signature: np.ndarray, threshold: float = 0.8) -> Optional[APrioriEntry]:
        """Query vault by signature similarity."""
        best_match = None
        best_score = 0

        for entry in self.entries.values():
            sim = np.dot(signature, entry.signature) / (
                np.linalg.norm(signature) * np.linalg.norm(entry.signature) + 1e-10
            )
            if sim > best_score and sim >= threshold:
                best_score = sim
                best_match = entry

        return best_match

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
                entry = APrioriEntry(
                    id=item['id'],
                    content=item['content'],
                    signature=np.array(item['signature']),
                    certainty=item['certainty'],
                    source_philosophers=item['source_philosophers'],
                    category=item['category'],
                    timestamp=item['timestamp']
                )
                self.entries[entry.id] = entry

            print(f"[A Priori Vault] Loaded {len(self.entries)} entries")
        except Exception as e:
            print(f"[A Priori Vault] Load failed: {e}")


# Singleton
_apriori_instance = None

def get_a_priori_vault(persistence_path: str = None) -> APrioriVault:
    global _apriori_instance
    if _apriori_instance is None:
        _apriori_instance = APrioriVault(persistence_path)
    return _apriori_instance
