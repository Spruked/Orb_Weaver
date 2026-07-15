"""Compatibility import for legacy Orb_Assistant callers.

The canonical implementation and all stored records now live in the
repository-root vault_system package.
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vault_system.manager import VaultManager

__all__ = ["VaultManager"]
