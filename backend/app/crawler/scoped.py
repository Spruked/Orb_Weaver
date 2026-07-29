"""Deterministic scan-scope support for Orb Weaver crawls.

The public CrawlConfig already carries owner-provided seed_urls. This module
adds an internal marker protocol so the existing crawl endpoint can perform a
true section or exact-page refresh without widening into a full-site crawl.
Scoped refreshes merge their newly measured pages into the last authoritative
crawl snapshot, carrying every untouched page forward.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse

import aiohttp

from app.core.storage import client_root

SCOPE_PREFIX = "orb-scope:"
VALID_SCOPES = {"full", "section", "exact", "changed"}


def _scope_and_seeds(seed_urls: Optional[Sequence[str]]) -> Tuple[str, List[str]]:
    scope = "full"
    clean: List[str] = []
    for raw in seed_urls or []:
        value = (raw or "").strip()
        if not value:
            continue
        if value.lower().startswith(SCOPE_PREFIX):
            candidate = value[len(SCOPE_PREFIX):].strip().lower()
            if candidate in VALID_SCOPES:
                scope = candidate
            continue
        clean.append(value)
    return scope, clean


def _path_matches_prefix(url: str, prefixes: Iterable[str]) -> bool:
    path = urlparse(url).path.rstrip("/") or "/"
    for raw_prefix in prefixes:
        prefix = raw_prefix.rstrip("/") or "/"
        if prefix == "/" or path == prefix or path.startswith(prefix + "/"):
            return True
    return False


def _page_from_dict(page_type, payload: dict):
    allowed = page_type.__dataclass_fields__.keys()
    values = {key: payload[key] for key in allowed if key in payload}
    return page_type(**values)


def _baseline_pages(page_type, domain: str) -> List:
    latest = client_root(domain) / "current" / "latest_crawl.json"
    if not latest.is_file():
        return []
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = ((payload.get("crawl") or {}).get("pages") or [])
    return [
        _page_from_dict(page_type, row)
        for row in rows
        if isinstance(row, dict) and row.get("url")
    ]


def _deduplicate_pages(crawler, pages: Sequence) -> List:
    by_url = {}
    order: List[str] = []
    for page in pages:
        key = crawler._normalize_url(page.url)
        if key not in by_url:
            order.append(key)
        by_url[key] = page
    return [by_url[key] for key in order]


def _recalculate_duplicate_risk(pages: Sequence) -> None:
    counts = Counter(page.content_hash for page in pages if page.content_hash)
    for page in pages:
        page.duplicate_content_risk = bool(page.content_hash and counts[page.content_hash] > 1)


def install_scope_support(crawler_type) -> None:
    """Patch the canonical crawler class once, before main imports it."""
    if getattr(crawler_type, "_orb_scope_support_installed", False):
        return

    original_crawl = crawler_type.crawl
    original_extract_links = crawler_type._extract_links
    original_get_stats = crawler_type.get_crawl_stats

    def scoped_extract_links(self, soup, base_url):
        internal, external, targets = original_extract_links(self, soup, base_url)
        prefixes: Set[str] = getattr(self, "_orb_allowed_prefixes", set())
        if not prefixes:
            return internal, external, targets
        filtered_internal = {url for url in internal if _path_matches_prefix(url, prefixes)}
        filtered_targets = [row for row in targets if row.get("url") in filtered_internal]
        return filtered_internal, external, filtered_targets

    async def scoped_crawl(self, start_url: str, seed_urls: Optional[List[str]] = None):
        scope, clean_seeds = _scope_and_seeds(seed_urls)
        self._orb_scan_scope = scope
        self._orb_pages_scanned_this_run = 0
        self._orb_baseline_pages_carried = 0

        if scope == "full":
            return await original_crawl(self, start_url, clean_seeds)

        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        self.domain_key = self._domain_key(parsed.netloc)

        # PageData is discoverable from the original crawl method without a
        # circular import back into the crawler package.
        page_type = original_crawl.__globals__["PageData"]
        baseline = _baseline_pages(page_type, self.domain)
        context_seeds = self._resolve_seed_urls(start_url, clean_seeds)
        if not context_seeds:
            raise ValueError("A scoped scan requires at least one same-domain page or section URL")

        exact_urls = {self._normalize_url(url) for url in context_seeds}
        prefixes = {urlparse(url).path.rstrip("/") or "/" for url in context_seeds}
        if scope == "section":
            self._orb_allowed_prefixes = prefixes
        else:
            self._orb_allowed_prefixes = set()
            self.max_depth = 0

        async with aiohttp.ClientSession(
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
        ) as session:
            robots_url = self._check_robots_txt(start_url)
            try:
                async with session.get(robots_url, ssl=False) as response:
                    if response.status == 200:
                        self.robots_rules = await response.text()
            except Exception:
                pass

            for seed_url in context_seeds:
                if self.total_pages_scraped >= self.max_pages:
                    self.max_page_limit_hit = True
                    break
                await self._crawl_page(session, seed_url, 0)
            self._emit_progress(force=True)

        scanned = list(self.crawled_data)
        self._orb_pages_scanned_this_run = len(scanned)
        for page in scanned:
            page.has_robots_txt = self.robots_rules is not None

        if scope in {"exact", "changed"}:
            untouched = [
                page for page in baseline
                if self._normalize_url(page.url) not in exact_urls
            ]
        else:
            untouched = [
                page for page in baseline
                if not _path_matches_prefix(page.url, prefixes)
            ]

        merged = _deduplicate_pages(self, [*untouched, *scanned])
        _recalculate_duplicate_risk(merged)
        self._orb_baseline_pages_carried = len(untouched)
        self.crawled_data = merged
        return merged

    def scoped_get_stats(self):
        stats = original_get_stats(self)
        scope = getattr(self, "_orb_scan_scope", "full")
        if scope != "full":
            stats.update({
                "scan_scope": scope,
                "pages_scanned_this_run": int(getattr(self, "_orb_pages_scanned_this_run", 0)),
                "baseline_pages_carried_forward": int(getattr(self, "_orb_baseline_pages_carried", 0)),
                "authoritative_page_count": len(self.crawled_data),
                "scope_widening_blocked": True,
            })
        return stats

    crawler_type._extract_links = scoped_extract_links
    crawler_type.crawl = scoped_crawl
    crawler_type.get_crawl_stats = scoped_get_stats
    crawler_type._orb_scope_support_installed = True
