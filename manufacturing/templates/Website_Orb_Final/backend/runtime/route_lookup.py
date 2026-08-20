from __future__ import annotations

from typing import Any, Dict, Tuple

from .site_world import SiteWorld, normalize_route


def lookup_route(world: SiteWorld, route: str) -> Tuple[str, Dict[str, Any]]:
    normalized = normalize_route(route)
    routes = world.routes
    if normalized in routes:
        return normalized, routes[normalized]

    alias = world.route_aliases.get(normalized)
    if alias and alias in routes:
        return alias, routes[alias]

    segments = [part for part in normalized.split("/") if part]
    while segments:
        candidate = "/" + "/".join(segments)
        if candidate in routes:
            return candidate, routes[candidate]
        segments.pop()

    return "/", routes.get("/", {})

