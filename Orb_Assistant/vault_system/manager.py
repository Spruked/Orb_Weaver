import json
import os
import hashlib


class VaultManager:
    def __init__(self, base_path="vault_system"):
        self.apriori_path = os.path.join(base_path, "apriori_core.json")
        self.posteriori_dir = os.path.join(base_path, "posteriori")
        self.canonical_truths = self._load_apriori()
        self.posteriori_cache = {}

    def _load_apriori(self):
        if os.path.exists(self.apriori_path):
            with open(self.apriori_path, "r", encoding="utf-8") as f:
                return json.load(f).get("canonical_truths", [])
        return []

    def lightning_query(self, stimulus_text):
        """The Deterministic Bypass: Checks Vaults for instant resolution."""
        # Normalize stimulus to string for matching and hashing
        if isinstance(stimulus_text, dict):
            stimulus_str = json.dumps(stimulus_text, sort_keys=True)
        else:
            stimulus_str = str(stimulus_text)

        # 1. Check Apriori (Hard-coded laws)
        for truth in self.canonical_truths:
            if truth["id"] in stimulus_str.upper():
                return {
                    "status": "DETERMINISTIC",
                    "source": "APRIORI",
                    "predicate": truth["predicate"],
                }

        # 2. Check Posteriori (Learned experience)
        stimulus_hash = hashlib.sha256(stimulus_str.encode()).hexdigest()
        p_path = os.path.join(self.posteriori_dir, f"{stimulus_hash}.json")
        if os.path.exists(p_path):
            with open(p_path, "r", encoding="utf-8") as f:
                return {
                    "status": "DETERMINISTIC",
                    "source": "POSTERIORI",
                    "data": json.load(f),
                }

        return None  # No bypass available, proceed to Four-Mind Tribunal

    def crystallize(self, stimulus_text, resolved_predicate):
        """Saves a resolved thought into the Posteriori Vault for future bypass."""
        os.makedirs(self.posteriori_dir, exist_ok=True)
        if isinstance(stimulus_text, dict):
            stimulus_str = json.dumps(stimulus_text, sort_keys=True)
        else:
            stimulus_str = str(stimulus_text)
        stimulus_hash = hashlib.sha256(stimulus_str.encode()).hexdigest()
        p_path = os.path.join(self.posteriori_dir, f"{stimulus_hash}.json")
        with open(p_path, "w", encoding="utf-8") as f:
            json.dump(resolved_predicate, f, indent=4)
        # Cache in-memory for faster habit lookups using the raw key
        self.posteriori_cache[str(stimulus_text)] = resolved_predicate
