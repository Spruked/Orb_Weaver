"""Compatibility import for legacy Orb_Assistant callers.

The canonical implementation and all stored records now live in the
repository-root vault_system package.
"""

from vault_system.manager import VaultManager

__all__ = ["VaultManager"]
