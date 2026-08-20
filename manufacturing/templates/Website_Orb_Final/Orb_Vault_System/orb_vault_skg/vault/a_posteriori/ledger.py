"""
orb/vault/a_posteriori/ledger.py
Immutable append-only experience ledger.
Every interaction is recorded here permanently.
No deletions. No mutations. Only appends.
"""

from __future__ import annotations
import json
import os
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Iterator
from pathlib import Path

from ..shared.types import Experience, VaultTimestamp, VerificationSignal
from ..shared.constants import VaultConstants


class ExperienceLedger:
    """
    Immutable append-only ledger for all experiences.
    Writes are atomic. Reads are sequential.
    """

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.current_file: Optional[Path] = None
        self._current_count = 0
        self._file_index = 0
        self._open_current_file()

    def _open_current_file(self):
        """Open or create the current ledger segment."""
        # Find highest existing file index
        existing = sorted(self.data_dir.glob("ledger_*.jsonl"))
        if existing:
            latest = existing[-1]
            self._file_index = int(latest.stem.split("_")[1])
            self.current_file = latest
            # Count entries
            with open(latest, "r") as f:
                self._current_count = sum(1 for _ in f)
        else:
            self._file_index = 0
            self.current_file = self.data_dir / "ledger_00000.jsonl"
            self._current_count = 0

    def _rotate_if_needed(self):
        """Rotate to new file if current is at capacity."""
        if self._current_count >= VaultConstants.LEDGER_MAX_ENTRIES_PER_FILE:
            self._file_index += 1
            self.current_file = self.data_dir / f"ledger_{self._file_index:05d}.jsonl"
            self._current_count = 0

    def append(self, experience: Experience) -> str:
        """
        Append an experience to the ledger.
        Returns the ledger hash (proof of append).
        """
        self._rotate_if_needed()

        record = {
            "experience_id": experience.experience_id,
            "timestamp": experience.timestamp.to_dict(),
            "query_text": experience.query_text,
            "detected_intent": experience.detected_intent.name,
            "detected_entities": experience.detected_entities,
            "resolution_path": experience.resolution_path,
            "resolution_result": experience.resolution_result,
            "outcome_success": experience.outcome_success,
            "user_feedback": experience.user_feedback,
            "session_id": experience.session_id,
            "source_signals": [s.name for s in experience.source_signals],
            "fingerprint": experience.fingerprint(),
        }

        line = json.dumps(record, ensure_ascii=False) + "\n"

        # Atomic append
        with open(self.current_file, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())

        self._current_count += 1

        # Return hash of this record for verification
        return hashlib.sha256(line.encode()).hexdigest()[:16]

    def read_all(self) -> Iterator[Dict[str, Any]]:
        """Iterate all ledger entries in chronological order."""
        files = sorted(self.data_dir.glob("ledger_*.jsonl"))
        for file_path in files:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        yield json.loads(line)

    def read_since(self, timestamp: float) -> Iterator[Dict[str, Any]]:
        """Read entries since a given unix timestamp."""
        for record in self.read_all():
            if record["timestamp"]["unix"] >= timestamp:
                yield record

    def read_by_intent(self, intent_name: str) -> Iterator[Dict[str, Any]]:
        """Read entries matching a specific intent."""
        for record in self.read_all():
            if record["detected_intent"] == intent_name:
                yield record

    def read_by_entity(self, entity_id: str) -> Iterator[Dict[str, Any]]:
        """Read entries involving a specific entity."""
        for record in self.read_all():
            if entity_id in record.get("detected_entities", []):
                yield record

    def get_stats(self) -> Dict[str, Any]:
        """Ledger statistics."""
        files = list(self.data_dir.glob("ledger_*.jsonl"))
        total_entries = 0
        success_count = 0
        intent_counts: Dict[str, int] = {}

        for record in self.read_all():
            total_entries += 1
            if record["outcome_success"]:
                success_count += 1
            intent = record["detected_intent"]
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        return {
            "total_entries": total_entries,
            "success_count": success_count,
            "success_rate": success_count / total_entries if total_entries > 0 else 0,
            "file_count": len(files),
            "intent_distribution": intent_counts,
            "data_dir": str(self.data_dir),
        }

    def verify_integrity(self) -> bool:
        """Verify ledger integrity by re-hashing entries."""
        for record in self.read_all():
            stored_fp = record.get("fingerprint")
            # Reconstruct for hash check
            payload = f"{record['query_text']}:{record['detected_intent']}:{record['resolution_path']}:{record['outcome_success']}"
            computed_fp = hashlib.sha256(payload.encode()).hexdigest()[:16]
            if stored_fp != computed_fp:
                return False
        return True
