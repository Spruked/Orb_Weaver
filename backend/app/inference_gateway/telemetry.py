from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class VaultTelemetry:
    """Append-only runtime telemetry inside Orb Weaver's sole canonical Vault."""

    def __init__(self, path: Path, max_bytes: int = 10 * 1024 * 1024) -> None:
        self.path = path
        self.max_bytes = max_bytes
        self._lock = asyncio.Lock()

    async def record(self, event: Dict[str, Any]) -> None:
        payload = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            **event,
        }
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        async with self._lock:
            await asyncio.to_thread(self._append_sync, line)

    def _append_sync(self, line: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_size >= self.max_bytes:
            rotated = self.path.with_suffix(self.path.suffix + ".1")
            try:
                rotated.unlink(missing_ok=True)
            except TypeError:
                if rotated.exists():
                    rotated.unlink()
            os.replace(self.path, rotated)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
