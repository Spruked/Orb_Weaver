"""Shared route policy for public marketing and claim extraction."""

from __future__ import annotations

from urllib.parse import urlparse


SENSITIVE_ROUTE_PREFIXES = (
    "/admin",
    "/cart",
    "/checkout",
    "/dashboard",
    "/account",
    "/login",
    "/signup",
)


def is_sensitive_route(url: str) -> bool:
    """Return whether a route must be excluded from public/marketing evidence."""
    path = urlparse(str(url or "")).path.lower().rstrip("/") or "/"
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in SENSITIVE_ROUTE_PREFIXES)

