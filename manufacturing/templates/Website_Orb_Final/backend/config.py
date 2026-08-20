from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
COMPILED_ORB_ROOT = PACKAGE_ROOT / "compiled_orb"
SITE_WORLD_PATH = COMPILED_ORB_ROOT / "site_world.json"
POINTER_MAP_PATH = COMPILED_ORB_ROOT / "pointer_plot_map.json"
RUNTIME_LANGUAGE_PATH = COMPILED_ORB_ROOT / "runtime_language.json"
TOOL_CACHE_PATH = COMPILED_ORB_ROOT / "tool_cache.json"


DEFAULT_ROUTE = "/"

