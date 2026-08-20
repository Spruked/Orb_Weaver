"""Customer-safe crawl seed and browser-rendering diagnostics.

Historically the Projects UI submitted Orb Weaver's own route bundle to every
Map Crawl. This module prevents those platform-specific paths from leaking into
customer projects while preserving genuine owner-provided seeds.

It also records whether JavaScript rendering was available and successful so a
200 response containing only an empty SPA shell is never silently presented as
a fully analyzed page.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Set
from urllib.parse import urlparse


ORB_WEAVER_PLATFORM_HOSTS: Set[str] = {
    "orbweaver.spruked.com",
    "campaign.orbweaver.spruked.com",
}

ORB_WEAVER_CONTEXT_SEED_BUNDLE: Set[str] = {
    "/",
    "/admin",
    "/admin/customers",
    "/dashboard",
    "/account",
    "/cart",
    "/checkout",
    "/checkout/success",
    "/login",
    "/signup",
    "/privacy",
    "/terms",
    "/sitemap.xml",
    "/robots.txt",
}

ORB_WEAVER_BUNDLE_MARKERS: Set[str] = {
    "/admin/customers",
    "/dashboard",
    "/account",
    "/checkout/success",
}

CUSTOMER_NEUTRAL_SEEDS: Set[str] = {
    "/",
    "/sitemap.xml",
    "/robots.txt",
}


def _seed_path(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://seed.invalid/{raw.lstrip('/')}")
    return (parsed.path or "/").rstrip("/") or "/"


def _looks_like_platform_seed_bundle(seed_urls: Sequence[str]) -> bool:
    paths = {_seed_path(seed) for seed in seed_urls if str(seed or "").strip()}
    marker_count = len(paths & ORB_WEAVER_BUNDLE_MARKERS)
    bundle_count = len(paths & ORB_WEAVER_CONTEXT_SEED_BUNDLE)
    return ORB_WEAVER_BUNDLE_MARKERS.issubset(paths) or (
        marker_count >= 3 and bundle_count >= 8
    )


def install_customer_seed_contract(crawler_type) -> None:
    """Install customer-safe seed filtering and render diagnostics once."""

    if getattr(crawler_type, "_orb_customer_seed_contract_installed", False):
        return

    original_resolve_seed_urls = crawler_type._resolve_seed_urls
    original_get_stats = crawler_type.get_crawl_stats
    original_looks_like_spa_shell = crawler_type._looks_like_spa_shell
    original_render_page_dom_sync = crawler_type._render_page_dom_sync

    def resolve_customer_seed_urls(self, start_url: str, seed_urls: Optional[List[str]] = None):
        submitted = [str(seed).strip() for seed in (seed_urls or []) if str(seed or "").strip()]
        domain_key = str(getattr(self, "domain_key", "") or "").lower()
        filtered = submitted
        filtered_platform_bundle = False

        if domain_key not in ORB_WEAVER_PLATFORM_HOSTS and _looks_like_platform_seed_bundle(submitted):
            filtered = [seed for seed in submitted if _seed_path(seed) in CUSTOMER_NEUTRAL_SEEDS]
            filtered_platform_bundle = True

        self._orb_seed_contract = {
            "domain": domain_key,
            "submitted_seed_count": len(submitted),
            "effective_owner_seed_count": len(filtered),
            "platform_seed_bundle_filtered": filtered_platform_bundle,
            "filtered_seed_paths": sorted(
                {
                    _seed_path(seed)
                    for seed in submitted
                    if seed not in filtered and _seed_path(seed)
                }
            ),
        }
        return original_resolve_seed_urls(self, start_url, filtered)

    def robust_spa_shell_detection(self, html: str) -> bool:
        if original_looks_like_spa_shell(self, html):
            return True
        compact = re.sub(r"\s+", "", str(html or "").lower())
        empty_mount = any(
            marker in compact
            for marker in (
                '<divid="root"></div>',
                "<divid='root'></div>",
                '<divid="app"></div>',
                "<divid='app'></div>",
                '<mainid="root"></main>',
                "<mainid='root'></main>",
            )
        )
        javascript_bundle = bool(
            re.search(r"<script[^>]+src=[\"'][^\"']+\.(?:js|mjs)(?:\?[^\"']*)?[\"']", compact)
        )
        return empty_mount and javascript_bundle

    def render_page_dom_sync_with_diagnostics(self, url: str):
        self._orb_browser_render_attempted = int(
            getattr(self, "_orb_browser_render_attempted", 0)
        ) + 1
        chrome = self._chrome_executable()
        self._orb_browser_available = bool(chrome)
        if not chrome:
            self._orb_browser_render_failures = int(
                getattr(self, "_orb_browser_render_failures", 0)
            ) + 1
            self._orb_last_browser_render_error = "Chromium executable not available"
            return None

        rendered = original_render_page_dom_sync(self, url)
        if rendered:
            self._orb_browser_render_succeeded = int(
                getattr(self, "_orb_browser_render_succeeded", 0)
            ) + 1
            self._orb_last_browser_render_error = None
        else:
            self._orb_browser_render_failures = int(
                getattr(self, "_orb_browser_render_failures", 0)
            ) + 1
            self._orb_last_browser_render_error = "Chromium returned no usable rendered DOM"
        return rendered

    def get_stats_with_contract(self) -> Dict:
        stats = original_get_stats(self)
        stats["seed_contract"] = getattr(
            self,
            "_orb_seed_contract",
            {
                "submitted_seed_count": 0,
                "effective_owner_seed_count": 0,
                "platform_seed_bundle_filtered": False,
                "filtered_seed_paths": [],
            },
        )
        stats["browser_rendering"] = {
            "available": bool(
                getattr(self, "_orb_browser_available", False)
                or self._chrome_executable()
            ),
            "attempted": int(getattr(self, "_orb_browser_render_attempted", 0)),
            "succeeded": int(getattr(self, "_orb_browser_render_succeeded", 0)),
            "failed": int(getattr(self, "_orb_browser_render_failures", 0)),
            "last_error": getattr(self, "_orb_last_browser_render_error", None),
        }
        return stats

    crawler_type._resolve_seed_urls = resolve_customer_seed_urls
    crawler_type._looks_like_spa_shell = robust_spa_shell_detection
    crawler_type._render_page_dom_sync = render_page_dom_sync_with_diagnostics
    crawler_type.get_crawl_stats = get_stats_with_contract
    crawler_type._orb_customer_seed_contract_installed = True
