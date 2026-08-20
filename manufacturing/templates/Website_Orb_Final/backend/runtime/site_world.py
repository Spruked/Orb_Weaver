from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return data


@dataclass(frozen=True)
class SiteWorld:
    site_world: Dict[str, Any]
    pointer_map: Dict[str, Any]
    runtime_language: Dict[str, Any]
    tool_cache: Dict[str, Any]
    pointer_by_route: Dict[str, List[Dict[str, Any]]]

    @classmethod
    def load(
        cls,
        site_world_path: Path,
        pointer_map_path: Path,
        runtime_language_path: Path,
        tool_cache_path: Path,
    ) -> "SiteWorld":
        site_world = _load_json(site_world_path)
        pointer_map = _load_json(pointer_map_path)
        runtime_language = _load_json(runtime_language_path)
        tool_cache = _load_json(tool_cache_path)
        pointer_by_route = _index_pointer_records(pointer_map)
        return cls(site_world, pointer_map, runtime_language, tool_cache, pointer_by_route)

    @property
    def routes(self) -> Dict[str, Dict[str, Any]]:
        routes = self.site_world.get("routes") or {}
        return routes if isinstance(routes, dict) else {}

    @property
    def route_aliases(self) -> Dict[str, str]:
        aliases = self.site_world.get("route_aliases") or {}
        return aliases if isinstance(aliases, dict) else {}

    def stats(self) -> Dict[str, Any]:
        return {
            "schema": self.site_world.get("schema"),
            "routes": len(self.routes),
            "pointer_records": self.pointer_map.get("record_count", len(self.pointer_map.get("records", []))),
            "tools": len(self.tool_cache.get("entries", [])),
            "runtime_contract": self.site_world.get("runtime_contract"),
        }


def _index_pointer_records(pointer_map: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    index: Dict[str, List[Dict[str, Any]]] = {}
    for record in pointer_map.get("records", []):
        if not isinstance(record, dict):
            continue
        route = normalize_route(
            record.get("page_route") or record.get("page_url") or record.get("route") or record.get("page") or "/"
        )
        index.setdefault(route, []).append(record)
    return index


def normalize_route(value: Any) -> str:
    raw = str(value or "/").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        raw = "/" + raw.split("/", 3)[3] if len(raw.split("/", 3)) > 3 else "/"
    if not raw.startswith("/"):
        raw = f"/{raw}"
    raw = raw.split("#", 1)[0].split("?", 1)[0]
    return raw.rstrip("/") or "/"
