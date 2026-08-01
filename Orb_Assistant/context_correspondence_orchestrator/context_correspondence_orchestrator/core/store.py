"""
Context & Correspondence Orchestrator - Handle Store
Manages context handle persistence and lifecycle.
"""

import os
import json
import glob
from datetime import datetime, timedelta
from typing import Optional, List
from ..models import OrchestrationMetadata
from ..config import config


class HandleStore:
    """File-based handle store with TTL support."""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or config.HANDLE_STORE_PATH
        os.makedirs(self.base_path, exist_ok=True)

    def save(self, metadata: OrchestrationMetadata) -> None:
        """Save crystal metadata to disk."""
        filepath = os.path.join(self.base_path, f"{metadata.handle}.json")

        # Convert datetime to ISO format for JSON
        data = metadata.dict()
        data["created_at"] = metadata.created_at.isoformat()
        data["last_accessed"] = metadata.last_accessed.isoformat()

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def get(self, handle: str) -> Optional[OrchestrationMetadata]:
        """Retrieve crystal metadata by handle."""
        filepath = os.path.join(self.base_path, f"{handle}.json")

        if not os.path.exists(filepath):
            return None

        with open(filepath, "r") as f:
            data = json.load(f)

        # Check TTL
        created = datetime.fromisoformat(data["created_at"])
        ttl = data.get("ttl_seconds", config.DEFAULT_TTL_SECONDS)
        if datetime.utcnow() > created + timedelta(seconds=ttl):
            # Expired
            os.remove(filepath)
            return None

        # Reconstruct metadata
        data["created_at"] = created
        data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])

        return OrchestrationMetadata(**data)

    def delete(self, handle: str) -> bool:
        """Delete a crystal handle."""
        filepath = os.path.join(self.base_path, f"{handle}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    def list_all(self) -> List[str]:
        """List all active handles."""
        handles = []
        for filepath in glob.glob(os.path.join(self.base_path, "ctx_*.json")):
            handle = os.path.basename(filepath).replace(".json", "")
            if self.get(handle):  # Validates TTL
                handles.append(handle)
        return handles

    def cleanup_expired(self) -> int:
        """Remove expired handles. Returns count removed."""
        removed = 0
        for filepath in glob.glob(os.path.join(self.base_path, "ctx_*.json")):
            with open(filepath, "r") as f:
                data = json.load(f)

            created = datetime.fromisoformat(data["created_at"])
            ttl = data.get("ttl_seconds", config.DEFAULT_TTL_SECONDS)

            if datetime.utcnow() > created + timedelta(seconds=ttl):
                os.remove(filepath)
                removed += 1

        return removed

    def stats(self) -> dict:
        """Return store statistics."""
        handles = self.list_all()
        total_original = 0
        total_crystal = 0

        for handle in handles:
            meta = self.get(handle)
            if meta:
                total_original += meta.original_tokens
                total_crystal += meta.crystal_tokens

        return {
            "active_handles": len(handles),
            "total_original_tokens": total_original,
            "total_crystal_tokens": total_crystal,
            "overall_compression_ratio": total_original / max(total_crystal, 1),
            "store_path": self.base_path
        }
