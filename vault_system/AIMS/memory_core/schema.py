"""Deterministic local schema marker for A.I.M.S. derived stores."""

from __future__ import annotations

import json
import os
from pathlib import Path


SCHEMA_VERSION = 1


class SchemaManager:
    def __init__(self, root: Path):
        self.path = Path(root) / "aims_schema.json"
        self.version = self._migrate()

    def _migrate(self) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        current = 0
        if self.path.exists():
            current = int(json.loads(self.path.read_text(encoding="utf-8")).get("schema_version", 0))
        if current > SCHEMA_VERSION:
            raise RuntimeError("AIMS store schema is newer than this runtime")
        # Version 1 has no destructive conversion: legacy ledgers are replayed
        # with backward-compatible defaults for new fields.
        while current < SCHEMA_VERSION:
            current += 1
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"schema_version": current}, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)
        return current
