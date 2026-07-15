"""Compatibility shim for historical Orb_Assistant imports.

The canonical VaultManager implementation and all persisted records live in
repository-root vault_system.
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vault_system.manager import VaultManager

__all__ = ["VaultManager"]
