"""Deterministic scan-scope and full-weave support for Orb Weaver crawls."""

from __future__ import annotations

import json
from collections import Counter
from typing import Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse

import aiohttp

from app.core.storage import client_root
from app.crawler.tesseract_weave import (
    build_lidar_candidate_inventory,
    collect_tesseract_candidates,
    summarize_weaves,
)

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
    return [_page_from_dict(page_type, row) for row in rows if isinstance(row, dict) and row.get("url")]


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
    """Patch the canonical crawler once with scope, Tesseract, LiDAR, and live activity support."""
    if getattr(crawler_type, "_orb_scope_support_installed", False):
        return

    original_crawl = crawler_type.crawl
    original_crawl_page = crawler_type._crawl_page
    original_extract_links = crawler_type._extract_links
    original_get_stats = crawler_type.get_crawl_stats

    def set_activity(self, stage_id: str, label: str, detail: str, page_url: Optional[str] = None, force: bool = False):
        self._orb_current_scan_activity = {
            "stage_id": stage_id,
            "label": label,
            "detail": detail,
            "page_url": page_url,
            "pages_processed": len(getattr(self, "crawled_data", [])),
            "pages_discovered": len(getattr(self, "discovered_urls", [])),
        }
        self._emit_progress(force=force)

    def weave_extract_links(self, soup, base_url):
        self._orb_latest_soup_by_url = getattr(self, "_orb_latest_soup_by_url", {})
        self._orb_latest_soup_by_url[self._normalize_url(base_url)] = soup
        set_activity(self, "dom_mapping", "Mapping page structure", "Reading links, controls, and page relationships", base_url)
        return original_extract_links(self, soup, base_url)

    async def weave_crawl_page(self, session, url, depth=0):
        set_activity(self, "page_fetch", "Opening website page", "Retrieving and rendering the current page", url, force=True)
        page = await original_crawl_page(self, session, url, depth)
        if page is None:
            return None

        soup_map = getattr(self, "_orb_latest_soup_by_url", {})
        source_soup = soup_map.pop(self._normalize_url(page.url), None)
        semantic = dict(page.semantic_analysis or {})

        set_activity(
            self,
            "tesseract_weave",
            "Tesseract Visual Surface Weave",
            "Identifying images, documents, canvas, SVG, and other surfaces that may contain visible text",
            page.url,
            force=True,
        )
        if source_soup is not None:
            semantic["tesseract_weave"] = collect_tesseract_candidates(source_soup, page.url)
        else:
            semantic["tesseract_weave"] = {
                "status": "not_measured",
                "page_url": page.url,
                "resource_count": 0,
                "resources": [],
                "ocr_execution_status": "source_dom_unavailable",
                "note": "The page DOM was unavailable; no OCR claim was made.",
            }

        set_activity(
            self,
            "lidar_weave",
            "LiDAR Spatial Mapping Weave",
            "Preparing occupancy, target identity, stacking, and coordinate-cache inputs",
            page.url,
            force=True,
        )
        semantic["lidar_weave"] = build_lidar_candidate_inventory(
            page.url,
            semantic.get("pointer_plot_records") or [],
        )
        page.semantic_analysis = semantic

        set_activity(
            self,
            "page_complete",
            "Page weave complete",
            "The page has been added to the measured website model",
            page.url,
            force=True,
        )
        return page

    def scoped_extract_links(self, soup, base_url):
        internal, external, targets = weave_extract_links(self, soup, base_url)
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
        set_activity(self, "scan_start", "Beginning website weave", "Discovering pages and establishing scan boundaries", start_url, force=True)

        if scope == "full":
            pages = await original_crawl(self, start_url, clean_seeds)
            set_activity(self, "scan_finalize", "Compiling full scan results", "Combining all measured weaves into the ORB knowledge base", start_url, force=True)
            return pages

        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        self.domain_key = self._domain_key(parsed.netloc)
        page_type = original_crawl.__globals__["PageData"]
        baseline = _baseline_pages(page_type, self.domain)
        baseline_has_sitemap = any(page.has_sitemap for page in baseline)
        self.has_sitemap_file = baseline_has_sitemap
        self.include_admin_sections = False
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

        async with aiohttp.ClientSession(timeout=self.timeout, headers={"User-Agent": self.user_agent}) as session:
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
            page.has_sitemap = baseline_has_sitemap
            page.has_robots_txt = self.robots_rules is not None

        if scope in {"exact", "changed"}:
            untouched = [page for page in baseline if self._normalize_url(page.url) not in exact_urls]
        else:
            untouched = [page for page in baseline if not _path_matches_prefix(page.url, prefixes)]

        merged = _deduplicate_pages(self, [*untouched, *scanned])
        _recalculate_duplicate_risk(merged)
        self._orb_baseline_pages_carried = len(untouched)
        self.crawled_data = merged
        set_activity(self, "scan_finalize", "Compiling scoped scan results", "Merging refreshed pages with the authoritative website model", start_url, force=True)
        return merged

    def scoped_get_stats(self):
        stats = original_get_stats(self)
        scope = getattr(self, "_orb_scan_scope", "full")
        stats.update(summarize_weaves(list(self.crawled_data)))
        stats["current_scan_activity"] = getattr(self, "_orb_current_scan_activity", {
            "stage_id": "waiting",
            "label": "Preparing scan",
            "detail": "Waiting for the next measured scan operation",
            "page_url": None,
            "pages_processed": len(self.crawled_data),
            "pages_discovered": len(self.discovered_urls),
        })
        if scope != "full":
            stats.update({
                "scan_scope": scope,
                "pages_scanned_this_run": int(getattr(self, "_orb_pages_scanned_this_run", 0)),
                "baseline_pages_carried_forward": int(getattr(self, "_orb_baseline_pages_carried", 0)),
                "authoritative_page_count": len(self.crawled_data),
                "scope_widening_blocked": True,
            })
        return stats

    crawler_type._set_scan_activity = set_activity
    crawler_type._extract_links = scoped_extract_links
    crawler_type._crawl_page = weave_crawl_page
    crawler_type.crawl = scoped_crawl
    crawler_type.get_crawl_stats = scoped_get_stats
    crawler_type._orb_scope_support_installed = True
