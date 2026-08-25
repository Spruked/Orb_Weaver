"""Mandatory rendered-browser observation for Website ORB truth assurance.

A successful HTTP crawl proves source availability, not the visitor-visible
runtime. Every manageable customer scan therefore receives a second rendered
observation pass. Injected chat widgets, overlays, iframes and controls are
recorded separately from ordinary JavaScript-shell recovery so absence is never
claimed from static HTML alone.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup


VENDOR_MARKERS = {
    "digiium.ai": ("digiium.ai", "digiium", "powered by digiium"),
    "intercom": ("intercom", "intercomcdn", "intercom-frame"),
    "hubspot": ("hubspot", "hs-scripts", "hubspot-messages"),
    "zendesk": ("zendesk", "zdassets", "zopim"),
    "drift": ("drift.com", "driftt", "drift-widget"),
    "tawk.to": ("tawk.to", "tawk_", "tawkchat"),
    "crisp": ("crisp.chat", "$crisp", "crisp-client"),
    "livechat": ("livechatinc", "livechat.com", "__lc"),
    "salesforce": ("embeddedservice", "salesforce.com", "einstein bot"),
    "gohighlevel": ("leadconnectorhq", "msgsndr.com", "gohighlevel"),
}

CHAT_TERMS = (
    "live chat", "chat with us", "start chat", "message us", "ask us",
    "how can i help", "how may i help", "sms/email", "voice", "chat now",
)

CONTROL_SELECTOR = "button, input, select, textarea, form, [role='button'], [role='dialog'], [contenteditable='true']"
FLOAT_HINTS = ("chat", "widget", "launcher", "bubble", "messenger", "assistant", "bot", "support", "floating", "sticky")


def _route(url: str) -> str:
    return urlparse(url).path or "/"


def _digest(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8", errors="ignore")).hexdigest()


def inspect_rendered_html(html: str, url: str, static_pointer_count: int = 0) -> Dict[str, Any]:
    soup = BeautifulSoup(html or "", "lxml")
    corpus = (html or "").lower()
    scripts = [str(tag.get("src") or "").strip() for tag in soup.find_all("script") if tag.get("src")]
    iframes = [str(tag.get("src") or "").strip() for tag in soup.find_all("iframe") if tag.get("src")]
    controls = soup.select(CONTROL_SELECTOR)

    detected_vendors: List[str] = []
    for vendor, markers in VENDOR_MARKERS.items():
        if any(marker in corpus for marker in markers):
            detected_vendors.append(vendor)

    floating_candidates: List[Dict[str, Any]] = []
    for tag in soup.find_all(True):
        attrs = " ".join([
            str(tag.get("id") or ""),
            " ".join(str(item) for item in (tag.get("class") or [])),
            str(tag.get("aria-label") or ""),
            str(tag.get("role") or ""),
            str(tag.get("style") or ""),
        ]).lower()
        if not any(hint in attrs for hint in FLOAT_HINTS):
            continue
        text = re.sub(r"\s+", " ", tag.get_text(" ", strip=True))[:180]
        floating_candidates.append({
            "tag": tag.name,
            "id": tag.get("id"),
            "class": list(tag.get("class") or [])[:8],
            "aria_label": tag.get("aria-label"),
            "text": text,
        })
        if len(floating_candidates) >= 40:
            break

    visible_text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).lower()
    chat_terms = sorted({term for term in CHAT_TERMS if term in visible_text or term in corpus})
    conversational = bool(detected_vendors or chat_terms or floating_candidates)
    rendered_control_count = len(controls)

    return {
        "schema": "orb_weaver.browser_route_observation.v1",
        "url": url,
        "route": _route(url),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "dom_sha256": _digest(html),
        "rendered_control_count": rendered_control_count,
        "static_pointer_count": int(static_pointer_count or 0),
        "additional_runtime_control_signal": max(0, rendered_control_count - int(static_pointer_count or 0)),
        "script_sources": scripts[:100],
        "iframe_sources": iframes[:50],
        "floating_control_candidates": floating_candidates,
        "chat_terms": chat_terms,
        "assistant_vendors": sorted(set(detected_vendors)),
        "conversational_interface_detected": conversational,
    }


def install_browser_observation_support(crawler_type) -> None:
    if getattr(crawler_type, "_orb_browser_observation_installed", False):
        return

    original_crawl = crawler_type.crawl
    original_get_stats = crawler_type.get_crawl_stats

    async def browser_observed_crawl(self, start_url: str, seed_urls: Optional[List[str]] = None):
        pages = await original_crawl(self, start_url, seed_urls)
        html_pages = [
            page for page in pages
            if not self._is_crawl_control_resource(str(getattr(page, "url", "") or ""))
            and int(getattr(page, "status_code", 0) or 0) < 400
        ]
        cap = max(1, int(os.environ.get("ORB_BROWSER_OBSERVATION_MAX_ROUTES", "50") or 50))
        planned = html_pages[:cap]
        observations: List[Dict[str, Any]] = []
        failures: List[str] = []
        browser = self._chrome_executable()

        if browser:
            for page in planned:
                url = str(getattr(page, "url", "") or "")
                try:
                    rendered = await self._render_page_dom(url)
                except Exception:
                    rendered = None
                if not rendered:
                    failures.append(url)
                    continue
                static_records = (getattr(page, "semantic_analysis", None) or {}).get("pointer_plot_records") or []
                observation = inspect_rendered_html(rendered, url, len(static_records))
                observations.append(observation)
                page.semantic_analysis = {
                    **(getattr(page, "semantic_analysis", None) or {}),
                    "browser_observation": observation,
                }

        observed_urls = {row["url"] for row in observations}
        unobserved = [str(getattr(page, "url", "") or "") for page in html_pages if str(getattr(page, "url", "") or "") not in observed_urls]
        vendors = sorted({vendor for row in observations for vendor in row.get("assistant_vendors", [])})
        conversational_routes = [row["url"] for row in observations if row.get("conversational_interface_detected")]
        dynamic_signal = sum(int(row.get("additional_runtime_control_signal") or 0) for row in observations)

        if not browser:
            status = "BLOCKED_BROWSER_UNAVAILABLE"
        elif failures:
            status = "PARTIAL"
        elif len(html_pages) > cap:
            status = "PARTIAL_ROUTE_CAP"
        elif len(observations) == len(html_pages):
            status = "VERIFIED_FULL"
        else:
            status = "PARTIAL"

        self._orb_browser_observation = {
            "schema": "orb_weaver.browser_observation.v1",
            "status": status,
            "evidence_state": "VERIFIED" if status == "VERIFIED_FULL" else "REQUIRES_VERIFICATION",
            "browser_available": bool(browser),
            "browser_executable": browser,
            "route_cap": cap,
            "routes_total": len(html_pages),
            "routes_planned": len(planned),
            "routes_observed": len(observations),
            "failed_routes": failures,
            "unobserved_routes": unobserved,
            "dynamic_control_signal_count": dynamic_signal,
            "assistant_vendors": vendors,
            "conversational_interface_detected": bool(conversational_routes),
            "conversational_routes": conversational_routes,
            "observations": observations,
        }
        return pages

    def browser_observed_stats(self):
        stats = original_get_stats(self)
        stats["browser_observation"] = getattr(self, "_orb_browser_observation", {
            "schema": "orb_weaver.browser_observation.v1",
            "status": "NOT_RUN",
            "evidence_state": "REQUIRES_VERIFICATION",
            "routes_total": 0,
            "routes_observed": 0,
            "assistant_vendors": [],
            "conversational_interface_detected": False,
            "observations": [],
        })
        return stats

    crawler_type.crawl = browser_observed_crawl
    crawler_type.get_crawl_stats = browser_observed_stats
    crawler_type._orb_browser_observation_installed = True


__all__ = ["inspect_rendered_html", "install_browser_observation_support"]
