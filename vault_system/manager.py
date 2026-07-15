from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class VaultManager:
    """Canonical Orb Weaver vault manager.

    Source code and all persisted records resolve from the repository-root
    vault_system. Callers may pass another root only for isolated tests.
    """

    def __init__(self, base_path: str | Path | None = None):
        self.base_path = (
            Path(base_path).expanduser().resolve()
            if base_path is not None
            else Path(__file__).resolve().parent
        )
        self.apriori_path = self.base_path / "apriori" / "apriori_core.json"
        self.posteriori_dir = self.base_path / "posteriori"
        self.canonical_truths = self._load_apriori()
        self.posteriori_cache: dict[str, Any] = {}

    def _load_apriori(self) -> list[dict[str, Any]]:
        if not self.apriori_path.exists():
            return []
        with self.apriori_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return list(payload.get("canonical_truths", []))

    @staticmethod
    def _stimulus_string(stimulus_text: Any) -> str:
        if isinstance(stimulus_text, dict):
            return json.dumps(stimulus_text, sort_keys=True)
        return str(stimulus_text)

    def lightning_query(self, stimulus_text: Any) -> dict[str, Any] | None:
        stimulus_string = self._stimulus_string(stimulus_text)

        for truth in self.canonical_truths:
            truth_id = str(truth.get("id", ""))
            if truth_id and truth_id in stimulus_string.upper():
                return {
                    "status": "DETERMINISTIC",
                    "source": "APRIORI",
                    "predicate": truth.get("predicate"),
                }

        stimulus_hash = hashlib.sha256(stimulus_string.encode("utf-8")).hexdigest()
        posteriori_path = self.posteriori_dir / f"{stimulus_hash}.json"
        if posteriori_path.exists():
            with posteriori_path.open("r", encoding="utf-8") as handle:
                return {
                    "status": "DETERMINISTIC",
                    "source": "POSTERIORI",
                    "data": json.load(handle),
                }

        return None

    def crystallize(self, stimulus_text: Any, resolved_predicate: Any) -> None:
        self.posteriori_dir.mkdir(parents=True, exist_ok=True)
        stimulus_string = self._stimulus_string(stimulus_text)
        stimulus_hash = hashlib.sha256(stimulus_string.encode("utf-8")).hexdigest()
        posteriori_path = self.posteriori_dir / f"{stimulus_hash}.json"

        temporary_path = posteriori_path.with_suffix(".json.tmp")
        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(resolved_predicate, handle, indent=2)
            handle.flush()
        temporary_path.replace(posteriori_path)

        self.posteriori_cache[stimulus_string] = resolved_predicate
