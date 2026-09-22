from __future__ import annotations

from pathlib import Path
from .storage import canonical_vault_root, require_vault_path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
COMPILED_ORB_ROOT = require_vault_path(canonical_vault_root() / "payload", "compiled runtime payload")
SITE_WORLD_PATH = COMPILED_ORB_ROOT / "site_world.json"
POINTER_MAP_PATH = COMPILED_ORB_ROOT / "pointers.json"
RUNTIME_LANGUAGE_PATH = COMPILED_ORB_ROOT / "runtime_language.json"
TOOL_CACHE_PATH = COMPILED_ORB_ROOT / "tool_cache.json"


DEFAULT_ROUTE = "/"
