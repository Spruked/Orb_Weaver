"""Evidence-labelled website intelligence dossier compiled from one crawl.

The dossier deliberately separates OBSERVED, INFERRED, VERIFIED, UNKNOWN and
UNAVAILABLE states. A missing observation never becomes a confident negative.
"""

from __future__ import annotations

import asyncio
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.analytics.search_console import retrieve_search_console


PLATFORM_MARKERS: Dict[str, Tuple[str, ...]] = {
    "WordPress": ("wp-content/", "wp-includes/", "wp-json", "wordpress ›", "name=\"generator\" content=\"wordpress"),
    "Shopify": ("cdn.shopify.com", "shopify.theme", "myshopify.com", "shopify-section"),
    "Wix": ("wixstatic.com", "wix-code", "wix.com/website-template"),
    "Squarespace": ("static1.squarespace.com", "squarespace.com", "sqs-block"),
    "Webflow": ("webflow.js", "webflow.css", "data-wf-page", "data-wf-site"),
    "Framer": ("framerusercontent.com", "data-framer-", "framer.app"),
    "HubSpot CMS": ("hs-sites.com", "hs_cos_wrapper", "hubspotusercontent"),
    "Drupal": ("drupalsettings", "/sites/default/files/", "drupal.org"),
    "Joomla": ("option=com_", "joomla!", "/media/system/js/"),
    "Ghost": ("ghost.io", "ghost-url", "content=\"ghost"),
    "Next.js": ("__next_data__", "/_next/static/", "next-route-announcer"),
    "Vite": ("/@vite/", "/assets/index-", "vite/client"),
    "React": ("react-dom", "data-reactroot", "createroot("),
}

ASSISTANT_VENDOR_MARKERS: Dict[str, Tuple[str, ...]] = {
    "Digiium.AI": ("digiium.ai", "powered by digiium", "digiium"),
    "Intercom": ("intercom", "intercomcdn"),
    "HubSpot Chat": ("hubspot-messages", "hs-scripts", "hubspot conversations"),
    "Zendesk": ("zendesk", "zdassets", "zopim"),
    "Drift": ("drift.com", "drift-widget", "driftt"),
    "Tawk.to": ("tawk.to", "tawkchat"),
    "Crisp": ("crisp.chat", "$crisp", "crisp-client"),
    "LiveChat": ("livechatinc", "livechat.com"),
    "Salesforce": ("embeddedservice", "einstein bot"),
    "GoHighLevel": ("leadconnectorhq", "msgsndr.com"),
}

CONVERSION_RULES = (
    (re.compile(r"\b(try|start).{0,24}\bfree\b", re.I), "free_trial", "Self-service trial"),
    (re.compile(r"\bcontact\s+(sales|us)\b", re.I), "contact_sales", "Sales-assisted conversion"),
    (re.compile(r"\b(get|request).{0,18}\b(quote|estimate|estimator)\b", re.I), "quote_request", "Lead / estimate request"),
    (re.compile(r"\b(schedule|book).{0,18}\b(call|demo|inspection|appointment|consultation)?\b", re.I), "schedule", "Scheduled conversion"),
    (re.compile(r"\b(call|phone)\s+(now|us|today)\b", re.I), "phone", "Phone conversion"),
    (re.compile(r"\b(buy|purchase|checkout|order)\b", re.I), "transaction", "Direct transaction"),
    (re.compile(r"\b(sign\s*up|register|create account|get started)\b", re.I), "signup", "Account / onboarding conversion"),
    (re.compile(r"\b(demo|request demo|see a demo)\b", re.I), "demo", "Demo conversion"),
)


def _normalize_url(url: str) -> str:
    value = (url or "").split("#", 1)[0].rstrip("/")
    return value or url


def _domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _walk_json(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            if isinstance(child, (Mapping, list)):
                yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _page_html(crawler, page: Any) -> str:
    cache = getattr(crawler, "_orb_analytics_html", {}) or {}
    url = str(getattr(page, "url", "") or "")
    return str(cache.get(crawler._normalize_url(url), "") or "")


def detect_platform(pages: Iterable[Any], html_by_url: Dict[str, str]) -> Dict[str, Any]:
    evidence: Dict[str, List[str]] = defaultdict(list)
    scores: Counter[str] = Counter()
    for page in pages:
        url = str(getattr(page, "url", "") or "")
        corpus = (html_by_url.get(url, "") + " " + str(getattr(page, "title", "") or "")).lower()
        for platform, markers in PLATFORM_MARKERS.items():
            matched = sorted({marker for marker in markers if marker in corpus})
            if matched:
                scores[platform] += len(matched)
                evidence[platform].extend(f"{url}: {marker}" for marker in matched[:4])

    if not scores:
        return {
            "status": "UNKNOWN",
            "evidence_state": "UNKNOWN",
            "platform": None,
            "confidence": 0.0,
            "evidence": [],
            "message": "No deterministic platform fingerprint was found; platform is not guessed.",
        }
    platform, score = scores.most_common(1)[0]
    confidence = min(0.99, 0.72 + 0.08 * score)
    return {
        "status": "IDENTIFIED",
        "evidence_state": "VERIFIED" if score >= 2 else "OBSERVED",
        "platform": platform,
        "confidence": round(confidence, 2),
        "evidence": list(dict.fromkeys(evidence[platform]))[:12],
        "alternates": [{"platform": name, "score": count} for name, count in scores.most_common()[1:5]],
    }


def detect_builder(pages: Iterable[Any], html_by_url: Dict[str, str]) -> Dict[str, Any]:
    patterns = re.compile(r"\b(?:website|site)\s+(?:designed|developed|built|created)\s+by\b|\b(?:designed|developed|built)\s+by\b", re.I)
    candidates: List[Dict[str, str]] = []
    for page in pages:
        url = str(getattr(page, "url", "") or "")
        html = html_by_url.get(url, "")
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        for footer in soup.find_all(["footer", "small"]):
            text = re.sub(r"\s+", " ", footer.get_text(" ", strip=True))
            match = patterns.search(text)
            if not match:
                continue
            nearby = text[match.start(): match.end() + 120].strip()
            link = footer.find("a", href=True)
            candidates.append({"source_url": url, "evidence": nearby[:220], "link": str(link.get("href")) if link else ""})
    if not candidates:
        return {
            "status": "NOT_IDENTIFIED",
            "evidence_state": "UNKNOWN",
            "builder": None,
            "evidence": [],
            "message": "Site builder/agency not identified from available evidence.",
        }
    return {
        "status": "ATTRIBUTION_OBSERVED",
        "evidence_state": "OBSERVED",
        "builder": candidates[0]["evidence"],
        "evidence": candidates[:10],
        "message": "Attribution text was observed; owner verification is recommended before treating it as contractual authorship.",
    }


def detect_business_identity(pages: Iterable[Any]) -> Dict[str, Any]:
    organizations: Dict[str, Dict[str, Any]] = {}
    for page in pages:
        page_url = str(getattr(page, "url", "") or "")
        for wrapper in getattr(page, "schema_markup", None) or []:
            payload = wrapper.get("data") if isinstance(wrapper, Mapping) and wrapper.get("type") == "json-ld" else wrapper
            for node in _walk_json(payload):
                types = node.get("@type") if isinstance(node, Mapping) else None
                type_values = types if isinstance(types, list) else [types]
                if not any(str(value or "").lower() in {"organization", "localbusiness", "corporation", "professionalservice", "store"} or str(value or "").lower().endswith("business") for value in type_values):
                    continue
                name = str(node.get("name") or "").strip()
                if not name:
                    continue
                key = name.lower()
                record = organizations.setdefault(key, {"name": name, "types": [], "phones": [], "emails": [], "urls": [], "source_pages": []})
                record["types"] = list(dict.fromkeys([*record["types"], *[str(v) for v in type_values if v]]))
                for field, target in (("telephone", "phones"), ("email", "emails"), ("url", "urls")):
                    value = node.get(field)
                    values = value if isinstance(value, list) else [value]
                    record[target] = list(dict.fromkeys([*record[target], *[str(v) for v in values if v]]))
                record["source_pages"] = list(dict.fromkeys([*record["source_pages"], page_url]))
    rows = list(organizations.values())
    return {
        "status": "IDENTIFIED" if rows else "UNKNOWN",
        "evidence_state": "OBSERVED" if rows else "UNKNOWN",
        "organizations": rows[:25],
    }


def detect_conversions(pages: Iterable[Any], html_by_url: Dict[str, str]) -> List[Dict[str, Any]]:
    found: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for page in pages:
        page_url = str(getattr(page, "url", "") or "")
        html = html_by_url.get(page_url, "")
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        for element in soup.select("a, button, [role='button'], input[type='submit']"):
            text = re.sub(r"\s+", " ", element.get_text(" ", strip=True) or str(element.get("value") or "")).strip()
            if not text or len(text) > 160:
                continue
            for pattern, kind, purpose in CONVERSION_RULES:
                if not pattern.search(text):
                    continue
                destination = str(element.get("href") or element.get("formaction") or "")
                key = (kind, text.lower(), destination)
                found[key] = {
                    "kind": kind,
                    "label": text,
                    "purpose": purpose,
                    "source_page": page_url,
                    "destination": destination or None,
                    "evidence_state": "OBSERVED",
                }
                break
    return list(found.values())[:100]


def detect_assistant(html_by_url: Dict[str, str], browser_observation: Dict[str, Any]) -> Dict[str, Any]:
    corpus = "\n".join(html_by_url.values()).lower()
    static_vendors = sorted({
        vendor for vendor, markers in ASSISTANT_VENDOR_MARKERS.items()
        if any(marker in corpus for marker in markers)
    })
    runtime_vendors = [str(item) for item in browser_observation.get("assistant_vendors") or []]
    vendors = sorted(set([*static_vendors, *runtime_vendors]))
    browser_status = str(browser_observation.get("status") or "NOT_RUN")
    runtime_detected = bool(browser_observation.get("conversational_interface_detected"))

    if runtime_detected or runtime_vendors:
        return {
            "status": "DETECTED",
            "evidence_state": "VERIFIED" if browser_status == "VERIFIED_FULL" else "OBSERVED",
            "providers": vendors,
            "runtime_detected": True,
            "browser_status": browser_status,
        }
    if browser_status == "VERIFIED_FULL":
        return {
            "status": "VERIFIED_NOT_DETECTED",
            "evidence_state": "VERIFIED",
            "providers": vendors,
            "runtime_detected": False,
            "browser_status": browser_status,
        }
    if static_vendors:
        return {
            "status": "IMPLEMENTATION_SIGNAL_DETECTED_RUNTIME_UNVERIFIED",
            "evidence_state": "REQUIRES_VERIFICATION",
            "providers": static_vendors,
            "runtime_detected": False,
            "browser_status": browser_status,
        }
    return {
        "status": "UNKNOWN_REQUIRES_BROWSER_VERIFICATION",
        "evidence_state": "REQUIRES_VERIFICATION",
        "providers": [],
        "runtime_detected": False,
        "browser_status": browser_status,
        "message": "No static signal was found, but absence is not claimed without a complete browser observation.",
    }


def content_architecture(pages: Iterable[Any]) -> Dict[str, Any]:
    rows = []
    total_words = 0
    for page in pages:
        url = str(getattr(page, "url", "") or "")
        if not url or urlparse(url).path.lower().endswith(("robots.txt", "sitemap.xml")):
            continue
        words = int(getattr(page, "word_count", 0) or 0)
        total_words += words
        rows.append({"url": url, "words": words, "thin": words < 300})
    homepage = next((row for row in rows if (urlparse(row["url"]).path or "/").rstrip("/") in {"", "/"}), None)
    share = (homepage["words"] / total_words) if homepage and total_words else 0.0
    thin_count = sum(1 for row in rows if row["thin"])
    artifacts = []
    for row in rows:
        path = urlparse(row["url"]).path.lower()
        reasons = []
        if "hello-world" in path:
            reasons.append("default_wordpress_hello_world")
        if "/category/uncategorized" in path:
            reasons.append("default_uncategorized_archive")
        if "/author/" in path and any(token in path for token in ("test", "gmail", "email")):
            reasons.append("test_like_author_archive")
        if "/testimomial/" in path:
            reasons.append("testimonial_route_spelling_anomaly")
        if any(token in path for token in ("usemotion", "/motion-", "motion-has-", "motion-the-")):
            reasons.append("legacy_template_slug_candidate")
        if reasons:
            artifacts.append({"url": row["url"], "reasons": reasons, "evidence_state": "OBSERVED"})
    return {
        "page_count": len(rows),
        "total_words": total_words,
        "homepage_word_share": round(share, 4),
        "homepage_concentrated": bool(share >= 0.50 and len(rows) >= 4),
        "thin_page_count": thin_count,
        "thin_page_ratio": round(thin_count / len(rows), 4) if rows else 0.0,
        "top_pages_by_words": sorted(rows, key=lambda row: row["words"], reverse=True)[:20],
        "public_artifact_candidates": artifacts,
    }


def url_dispositions(crawler, pages: Iterable[Any]) -> Dict[str, Any]:
    fetched = {_normalize_url(str(getattr(page, "url", "") or "")) for page in pages}
    robots = {_normalize_url(str(url)) for url in getattr(crawler, "robots_blocked_urls", set())}
    discovered = sorted({_normalize_url(str(url)) for url in getattr(crawler, "discovered_urls", set()) if url})
    depth_map = getattr(crawler, "current_depth", {}) or {}
    rows = []
    counts: Counter[str] = Counter()
    for url in discovered:
        if url in fetched:
            disposition = "FETCHED"
        elif url in robots:
            disposition = "ROBOTS_BLOCKED"
        elif int(depth_map.get(url, 0) or 0) > int(getattr(crawler, "max_depth", 0) or 0):
            disposition = "DEPTH_LIMITED"
        else:
            disposition = "UNRESOLVED_NOT_FETCHED"
        counts[disposition] += 1
        rows.append({"url": url, "disposition": disposition})
    return {
        "schema": "orb_weaver.url_disposition.v1",
        "discovered_count": len(discovered),
        "counts": dict(counts),
        "unresolved_count": counts.get("UNRESOLVED_NOT_FETCHED", 0),
        "rows": rows,
        "evidence_state": "VERIFIED" if counts.get("UNRESOLVED_NOT_FETCHED", 0) == 0 else "REQUIRES_VERIFICATION",
    }


def install_site_intelligence_support(crawler_type) -> None:
    if getattr(crawler_type, "_orb_site_intelligence_installed", False):
        return

    original_crawl = crawler_type.crawl
    original_get_stats = crawler_type.get_crawl_stats

    async def intelligence_crawl(self, start_url: str, seed_urls: Optional[List[str]] = None):
        pages = await original_crawl(self, start_url, seed_urls)
        html_by_url = {str(getattr(page, "url", "") or ""): _page_html(self, page) for page in pages}
        browser_observation = getattr(self, "_orb_browser_observation", {}) or {}
        analytics = getattr(self, "_orb_analytics_summary", {}) or {}
        domain = _domain(start_url) or str(getattr(self, "domain", "") or "")
        search_console = await asyncio.to_thread(retrieve_search_console, domain)

        platform = detect_platform(pages, html_by_url)
        builder = detect_builder(pages, html_by_url)
        assistant = detect_assistant(html_by_url, browser_observation)
        conversions = detect_conversions(pages, html_by_url)
        architecture = content_architecture(pages)
        dispositions = url_dispositions(self, pages)
        identity = detect_business_identity(pages)

        analytics_resolution = analytics.get("property_resolution") or {}
        traffic_retrieval = analytics.get("traffic_retrieval") or {}
        google_intelligence = {
            "analytics_tag_scan": analytics,
            "ga4": {
                "status": traffic_retrieval.get("status") or "UNAVAILABLE",
                "evidence_state": "VERIFIED" if traffic_retrieval.get("status") == "retrieved" else "UNAVAILABLE",
                "measurement_ids": analytics.get("ga4_measurement_ids") or [],
                "gtm_container_ids": analytics.get("gtm_container_ids") or [],
                "property_id": analytics_resolution.get("property_id"),
                "traffic": analytics.get("traffic"),
                "message": None if traffic_retrieval.get("status") == "retrieved" else "GA4 traffic is not reported as zero when property access is unavailable.",
            },
            "search_console": search_console,
        }

        assurance_checks = {
            "source_crawl": "PASS" if pages else "FAIL",
            "browser_observation": "PASS" if browser_observation.get("status") == "VERIFIED_FULL" else "REQUIRES_VERIFICATION",
            "platform_attribution": "PASS" if platform.get("status") == "IDENTIFIED" else "UNKNOWN_ACCEPTABLE",
            "builder_attribution": "PASS" if builder.get("status") != "NOT_IDENTIFIED" else "UNKNOWN_ACCEPTABLE",
            "google_analytics": "PASS" if traffic_retrieval.get("status") == "retrieved" else "NOT_CONNECTED_OR_UNAVAILABLE",
            "search_console": "PASS" if search_console.get("status") == "RETRIEVED" else "NOT_CONNECTED_OR_UNAVAILABLE",
            "url_disposition": "PASS" if dispositions.get("unresolved_count") == 0 else "REQUIRES_VERIFICATION",
            "pointer_verification": "NOT_RUN",
            "final_orb_rescan": "NOT_RUN",
        }
        blocking = [key for key, value in assurance_checks.items() if value in {"FAIL", "REQUIRES_VERIFICATION", "NOT_RUN"}]

        self._orb_site_intelligence = {
            "schema": "orb_weaver.website_intelligence_dossier.v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "evidence_vocabulary": ["OBSERVED", "INFERRED", "VERIFIED", "UNKNOWN", "UNAVAILABLE", "REQUIRES_VERIFICATION"],
            "business_identity": identity,
            "platform": platform,
            "site_builder": builder,
            "existing_conversational_interface": assistant,
            "conversion_paths": conversions,
            "content_architecture": architecture,
            "url_disposition": dispositions,
            "browser_observation": browser_observation,
            "google_intelligence": google_intelligence,
            "assurance": {
                "doctrine": "Find broadly. Claim conservatively. Verify independently. Rescan before release.",
                "checks": assurance_checks,
                "blocking_checks": blocking,
                "release_state": "BLOCKED_VERIFICATION_REQUIRED" if blocking else "VERIFIED_FOR_RELEASE",
            },
        }
        return pages

    def intelligence_stats(self):
        stats = original_get_stats(self)
        stats["site_intelligence"] = getattr(self, "_orb_site_intelligence", {
            "schema": "orb_weaver.website_intelligence_dossier.v1",
            "assurance": {"release_state": "BLOCKED_VERIFICATION_REQUIRED", "blocking_checks": ["site_intelligence_not_run"]},
        })
        return stats

    crawler_type.crawl = intelligence_crawl
    crawler_type.get_crawl_stats = intelligence_stats
    crawler_type._orb_site_intelligence_installed = True


__all__ = [
    "content_architecture",
    "detect_assistant",
    "detect_builder",
    "detect_business_identity",
    "detect_conversions",
    "detect_platform",
    "install_site_intelligence_support",
    "url_dispositions",
]
