"""Rendered-DOM recovery for JavaScript application shells.

The canonical crawler performs a fast HTTP fetch first. That is correct for
ordinary server-rendered pages, but some applications return only a bootstrap
shell and populate navigation, controls, text, and images in the browser. This
module broadens shell detection beyond the legacy Create React App signature,
uses an available Chromium-family browser to capture the live DOM, and records
render failures so an empty shell cannot be mistaken for a completed ORB scan.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from bs4 import BeautifulSoup


APP_ROOT_SELECTORS = (
    "#root",
    "#app",
    "#__next",
    "[data-reactroot]",
    "[data-react-app]",
    "[data-v-app]",
    "[ng-version]",
)

FRAMEWORK_MARKERS = (
    "/static/js/",
    "/_next/",
    "/assets/",
    "vite",
    "webpack",
    "react-dom",
    "createapp(",
    "createRoot(",
    "hydrateRoot(",
    "new Vue(",
)

BROWSER_NAMES = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "microsoft-edge",
    "microsoft-edge-stable",
)

BROWSER_PATHS = (
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/microsoft-edge",
    "/usr/bin/microsoft-edge-stable",
    "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
    "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe",
    "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)


def _word_count(value: str) -> int:
    return len(re.findall(r"\b[\w][\w'’-]*\b", value or "", flags=re.UNICODE))


def summarize_dom_signals(html: str) -> Dict[str, Any]:
    """Return deterministic signals used to decide whether rendering is needed."""
    source = html or ""
    soup = BeautifulSoup(source, "lxml")

    script_sources = [
        str(tag.get("src") or "").strip().lower()
        for tag in soup.find_all("script")
        if tag.get("src")
    ]
    inline_scripts = " ".join(
        str(tag.string or tag.get_text(" ", strip=True) or "")
        for tag in soup.find_all("script")
        if not tag.get("src")
    ).lower()
    script_corpus = " ".join([*script_sources, inline_scripts, source.lower()[:20000]])

    visible_soup = BeautifulSoup(source, "lxml")
    for node in visible_soup.find_all(["script", "style", "noscript", "template", "svg"]):
        node.decompose()
    visible_text = visible_soup.get_text(" ", strip=True)

    has_app_root = any(soup.select_one(selector) is not None for selector in APP_ROOT_SELECTORS)
    has_module_script = any(
        str(tag.get("type") or "").strip().lower() == "module"
        for tag in soup.find_all("script")
    )
    framework_markers = sorted(marker for marker in FRAMEWORK_MARKERS if marker.lower() in script_corpus)

    return {
        "word_count": _word_count(visible_text),
        "link_count": len(soup.select("a[href]")),
        "control_count": len(soup.select("button, input, select, textarea, form, [role='button']")),
        "heading_count": len(soup.select("h1, h2, h3")),
        "paragraph_count": len(soup.select("p, article, main")),
        "image_count": len(soup.select("img, picture, video")),
        "script_count": len(soup.find_all("script")),
        "has_app_root": has_app_root,
        "has_module_script": has_module_script,
        "framework_markers": framework_markers,
        "framework_bootstrap": bool(has_module_script or framework_markers),
    }


def looks_like_unrendered_app_shell(html: str) -> bool:
    """Identify low-signal HTML that is expected to become useful after JS runs."""
    if not html:
        return False

    compact = re.sub(r"\s+", "", html.lower())
    if '<divid="root"></div>' in compact and "/static/js/" in compact:
        return True

    signals = summarize_dom_signals(html)
    interactive = int(signals["link_count"]) + int(signals["control_count"])
    semantic_blocks = int(signals["heading_count"]) + int(signals["paragraph_count"])
    word_count = int(signals["word_count"])

    if signals["has_app_root"] and signals["framework_bootstrap"]:
        return word_count < 120 and interactive == 0 and semantic_blocks <= 2

    if signals["framework_bootstrap"]:
        return (
            word_count < 45
            and interactive == 0
            and int(signals["heading_count"]) <= 1
            and int(signals["image_count"]) == 0
        )

    if signals["has_app_root"]:
        return word_count < 30 and interactive == 0 and semantic_blocks <= 1

    return False


def _browser_candidates() -> Iterable[str]:
    for env_name in ("CHROME_PATH", "CHROME_BIN", "CHROMIUM_PATH", "EDGE_PATH"):
        value = (os.environ.get(env_name) or "").strip()
        if value:
            yield value
    yield from BROWSER_NAMES
    yield from BROWSER_PATHS


def resolve_browser_executable(original: Optional[str] = None) -> Optional[str]:
    """Resolve Chromium/Chrome/Edge across Linux, Windows, WSL, and containers."""
    candidates = [original] if original else []
    candidates.extend(_browser_candidates())
    seen = set()

    for raw in candidates:
        if not raw:
            continue
        candidate = str(raw).strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)

        path = Path(candidate)
        if path.is_absolute() and path.exists():
            return str(path)

        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    return None


def install_rendered_dom_support(crawler_type) -> None:
    """Patch the canonical crawler once without creating a parallel crawler."""
    if getattr(crawler_type, "_orb_rendered_dom_support_installed", False):
        return

    original_looks_like_shell = crawler_type._looks_like_spa_shell
    original_chrome_executable = crawler_type._chrome_executable
    original_render_page_dom = crawler_type._render_page_dom
    original_crawl = crawler_type.crawl
    original_get_stats = crawler_type.get_crawl_stats

    def enhanced_shell_detection(self, html: str) -> bool:
        return bool(original_looks_like_shell(self, html) or looks_like_unrendered_app_shell(html))

    def enhanced_chrome_executable(self) -> Optional[str]:
        return resolve_browser_executable(original_chrome_executable(self))

    async def measured_render_page_dom(self, url: str) -> Optional[str]:
        self._orb_render_attempts = int(getattr(self, "_orb_render_attempts", 0)) + 1
        rendered = await original_render_page_dom(self, url)
        unresolved = getattr(self, "_orb_unresolved_app_shell_urls", None)
        if unresolved is None:
            unresolved = set()
            self._orb_unresolved_app_shell_urls = unresolved

        if not rendered or looks_like_unrendered_app_shell(rendered):
            self._orb_render_failures = int(getattr(self, "_orb_render_failures", 0)) + 1
            unresolved.add(self._normalize_url(url))
            return None

        self._orb_render_successes = int(getattr(self, "_orb_render_successes", 0)) + 1
        unresolved.discard(self._normalize_url(url))
        return rendered

    async def rendered_dom_crawl(self, start_url: str, seed_urls=None):
        self._orb_render_attempts = 0
        self._orb_render_successes = 0
        self._orb_render_failures = 0
        self._orb_unresolved_app_shell_urls = set()
        return await original_crawl(self, start_url, seed_urls)

    def rendered_dom_get_stats(self):
        stats = original_get_stats(self)
        attempted = int(getattr(self, "_orb_render_attempts", 0))
        succeeded = int(getattr(self, "_orb_render_successes", 0))
        failed = int(getattr(self, "_orb_render_failures", 0))
        unresolved = sorted(getattr(self, "_orb_unresolved_app_shell_urls", set()))
        browser = self._chrome_executable()

        if unresolved:
            status = "failed_unresolved_application_shell"
        elif attempted and succeeded == attempted:
            status = "rendered"
        elif attempted:
            status = "partial"
        else:
            status = "not_required"

        stats["rendered_dom"] = {
            "status": status,
            "browser_available": bool(browser),
            "browser_executable": browser,
            "attempted": attempted,
            "succeeded": succeeded,
            "failed": failed,
            "unresolved_app_shell_count": len(unresolved),
            "unresolved_app_shell_urls": unresolved[:50],
        }
        return stats

    crawler_type._looks_like_spa_shell = enhanced_shell_detection
    crawler_type._chrome_executable = enhanced_chrome_executable
    crawler_type._render_page_dom = measured_render_page_dom
    crawler_type.crawl = rendered_dom_crawl
    crawler_type.get_crawl_stats = rendered_dom_get_stats
    crawler_type._orb_rendered_dom_support_installed = True
