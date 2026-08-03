"""Persist analytics-tag findings inside the existing crawl data contract.

The analytics scanner writes its aggregate record into crawl stats. This
adapter also copies each page's finding into semantic_analysis, an existing
CrawledPage JSON field, so Site Scan datasets, lifecycle evidence, reports,
and generated customer intelligence packages retain route-level tag evidence
without adding a parallel database or storage path.
"""

from __future__ import annotations

from typing import List, Optional


def install_analytics_persistence(crawler_type) -> None:
    if getattr(crawler_type, "_orb_analytics_persistence_installed", False):
        return

    original_crawl = crawler_type.crawl

    async def persistence_crawl(self, start_url: str, seed_urls: Optional[List[str]] = None):
        pages = await original_crawl(self, start_url, seed_urls)
        for page in pages:
            finding = getattr(page, "analytics_tags", None)
            if not isinstance(finding, dict):
                continue
            page.semantic_analysis = {
                **(page.semantic_analysis or {}),
                "analytics_tags": finding,
            }
        return pages

    crawler_type.crawl = persistence_crawl
    crawler_type._orb_analytics_persistence_installed = True
