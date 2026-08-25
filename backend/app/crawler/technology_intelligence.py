"""Technology, integration and local-SEO enrichment for Website Intelligence."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup


TECH_MARKERS: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "Elementor": ("site_builder", ("elementor", "elementor-widget", "elementor-frontend")),
    "Divi": ("site_builder", ("et_pb_", "divi", "elegantthemes")),
    "WPBakery": ("site_builder", ("wpb_wrapper", "vc_row", "js_composer")),
    "Beaver Builder": ("site_builder", ("fl-builder", "fl-row", "bb-plugin")),
    "Bricks": ("site_builder", ("bricks-element", "bricks-is-frontend")),
    "WooCommerce": ("commerce", ("woocommerce", "wc-ajax", "wc-block")),
    "Stripe": ("payments", ("js.stripe.com", "stripe.com/v3", "stripe-checkout")),
    "PayPal": ("payments", ("paypal.com/sdk", "paypalobjects.com", "paypal-buttons")),
    "Square": ("payments", ("squarecdn.com", "squareup.com", "web-payments-sdk")),
    "Calendly": ("booking", ("calendly.com", "calendly-inline-widget")),
    "HubSpot": ("crm_marketing", ("hubspot", "hs-scripts", "hsforms")),
    "Salesforce": ("crm", ("salesforce.com", "force.com", "embeddedservice")),
    "Twilio": ("communications", ("twilio", "twilio.com")),
    "Google Tag Manager": ("analytics", ("googletagmanager.com/gtm.js", "gtm-")),
    "Google Analytics": ("analytics", ("googletagmanager.com/gtag/js", "google-analytics.com", "gtag(")),
    "Google Ads": ("advertising", ("googleadservices.com", "aw-")),
    "Meta Pixel": ("advertising", ("connect.facebook.net", "fbq(")),
    "Hotjar": ("analytics", ("hotjar.com", "hj(")),
    "Cloudflare": ("cdn_security", ("cdn-cgi/", "cloudflareinsights.com", "cf-ray")),
    "reCAPTCHA": ("security", ("google.com/recaptcha", "grecaptcha")),
}


def _walk_json(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            if isinstance(child, (Mapping, list)):
                yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _html_cache(crawler, pages: Iterable[Any]) -> Dict[str, str]:
    cache = getattr(crawler, "_orb_analytics_html", {}) or {}
    result: Dict[str, str] = {}
    for page in pages:
        url = str(getattr(page, "url", "") or "")
        normalized = crawler._normalize_url(url)
        result[url] = str(cache.get(normalized, "") or "")
    return result


def detect_technology_stack(html_by_url: Dict[str, str], platform: Dict[str, Any], browser: Dict[str, Any]) -> Dict[str, Any]:
    evidence: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for url, html in html_by_url.items():
        corpus = (html or "").lower()
        for technology, (category, markers) in TECH_MARKERS.items():
            for marker in markers:
                if marker.lower() in corpus:
                    evidence[technology].append({"source_url": url, "marker": marker})
                    break

    for vendor in browser.get("assistant_vendors") or []:
        label = str(vendor)
        evidence[label].append({"source_url": "rendered_browser_observation", "marker": "runtime assistant vendor"})

    rows = []
    for technology, rows_evidence in evidence.items():
        category = TECH_MARKERS.get(technology, ("conversational_ai", ()))[0]
        rows.append({
            "technology": technology,
            "category": category,
            "evidence_state": "VERIFIED" if rows_evidence and rows_evidence[0]["source_url"] == "rendered_browser_observation" else "OBSERVED",
            "evidence": rows_evidence[:10],
        })
    rows.sort(key=lambda row: (row["category"], row["technology"]))
    return {
        "status": "IDENTIFIED" if rows or platform.get("platform") else "UNKNOWN",
        "evidence_state": "OBSERVED" if rows else platform.get("evidence_state", "UNKNOWN"),
        "platform": platform.get("platform"),
        "technologies": rows,
        "hosting_provider": {
            "status": "UNKNOWN",
            "evidence_state": "UNKNOWN",
            "provider": None,
            "message": "Hosting provider is not guessed from weak public signals. CDN/proxy technology is reported separately when observed.",
        },
    }


def local_seo_intelligence(pages: Iterable[Any], html_by_url: Dict[str, str]) -> Dict[str, Any]:
    local_types = []
    names = []
    phones = []
    emails = []
    addresses = []
    areas_served = []
    geo = []
    source_pages = []

    for page in pages:
        url = str(getattr(page, "url", "") or "")
        for wrapper in getattr(page, "schema_markup", None) or []:
            payload = wrapper.get("data") if isinstance(wrapper, Mapping) and wrapper.get("type") == "json-ld" else wrapper
            for node in _walk_json(payload):
                raw_type = node.get("@type")
                types = raw_type if isinstance(raw_type, list) else [raw_type]
                normalized_types = [str(value or "") for value in types if value]
                is_local = any(
                    value.lower() == "localbusiness"
                    or value.lower().endswith("business")
                    or value.lower() in {"professionalservice", "homeandconstructionbusiness", "roofingcontractor"}
                    for value in normalized_types
                )
                if not is_local:
                    continue
                local_types.extend(normalized_types)
                source_pages.append(url)
                if node.get("name"):
                    names.append(str(node.get("name")))
                if node.get("telephone"):
                    phones.append(str(node.get("telephone")))
                if node.get("email"):
                    emails.append(str(node.get("email")))
                address = node.get("address")
                if isinstance(address, Mapping):
                    formatted = ", ".join(str(address.get(key) or "").strip() for key in ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry") if address.get(key))
                    if formatted:
                        addresses.append(formatted)
                elif address:
                    addresses.append(str(address))
                area = node.get("areaServed")
                values = area if isinstance(area, list) else [area]
                for value in values:
                    if isinstance(value, Mapping):
                        label = value.get("name") or value.get("@id")
                        if label:
                            areas_served.append(str(label))
                    elif value:
                        areas_served.append(str(value))
                geo_value = node.get("geo")
                if isinstance(geo_value, Mapping) and (geo_value.get("latitude") or geo_value.get("longitude")):
                    geo.append({"latitude": geo_value.get("latitude"), "longitude": geo_value.get("longitude")})

    maps_links = []
    for url, html in html_by_url.items():
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "")
            host = (urlparse(href).hostname or "").lower()
            if host.endswith("google.com") and ("maps" in href.lower() or "place" in href.lower()):
                maps_links.append({"source_url": url, "href": href})
            elif host.endswith("goo.gl") and "maps" in href.lower():
                maps_links.append({"source_url": url, "href": href})

    return {
        "status": "LOCAL_SCHEMA_OBSERVED" if local_types else "LOCAL_SCHEMA_NOT_OBSERVED",
        "evidence_state": "OBSERVED" if local_types else "UNKNOWN",
        "local_business_schema_types": sorted(set(local_types)),
        "names": sorted(set(names)),
        "phones": sorted(set(phones)),
        "emails": sorted(set(emails)),
        "addresses": sorted(set(addresses)),
        "areas_served": sorted(set(areas_served)),
        "geo": geo[:10],
        "google_maps_links": maps_links[:20],
        "source_pages": sorted(set(source_pages)),
        "nap_completeness": {
            "name": bool(names),
            "address": bool(addresses),
            "phone": bool(phones),
            "complete": bool(names and addresses and phones),
        },
    }


def install_technology_intelligence_support(crawler_type) -> None:
    if getattr(crawler_type, "_orb_technology_intelligence_installed", False):
        return

    original_crawl = crawler_type.crawl
    original_get_stats = crawler_type.get_crawl_stats

    async def technology_crawl(self, start_url: str, seed_urls: Optional[List[str]] = None):
        pages = await original_crawl(self, start_url, seed_urls)
        dossier = getattr(self, "_orb_site_intelligence", {}) or {}
        browser = getattr(self, "_orb_browser_observation", {}) or {}
        html_by_url = _html_cache(self, pages)
        platform = dossier.get("platform") or {}
        technology = detect_technology_stack(html_by_url, platform, browser)
        local_seo = local_seo_intelligence(pages, html_by_url)

        pointer_verification = browser.get("pointer_verification") or {}
        runtime_rescan = browser.get("runtime_rescan") or {}
        candidate_count = int(pointer_verification.get("candidate_count") or 0)
        verified_count = int(pointer_verification.get("verified_and_reverified_count") or 0)
        pointer_check = (
            "PASS_SAFE_SUBSET" if verified_count > 0
            else "NO_GUIDANCE_TARGETS" if candidate_count == 0
            else "REQUIRES_VERIFICATION"
        )
        runtime_rescan_check = "PASS" if runtime_rescan.get("status") == "VERIFIED" else "REQUIRES_VERIFICATION"

        dossier["technology_stack"] = technology
        dossier["local_seo"] = local_seo
        assurance = dict(dossier.get("assurance") or {})
        checks = dict(assurance.get("checks") or {})
        checks["pointer_verification"] = pointer_check
        checks["rendered_runtime_rescan"] = runtime_rescan_check
        # Full Audit is a separate independent crawl/reconciliation lifecycle and
        # remains required before production release even when the rendered
        # two-pass rescan succeeds.
        checks["final_orb_rescan"] = "REQUIRES_FULL_AUDIT"
        blocking = [
            key for key, value in checks.items()
            if value in {"FAIL", "REQUIRES_VERIFICATION", "NOT_RUN", "REQUIRES_FULL_AUDIT"}
        ]
        assurance.update({
            "checks": checks,
            "blocking_checks": blocking,
            "release_state": "BLOCKED_VERIFICATION_REQUIRED" if blocking else "VERIFIED_FOR_RELEASE",
            "pointer_guidance_policy": "only independently verified subset may point; quarantined candidates may be repaired later",
        })
        dossier["assurance"] = assurance
        self._orb_site_intelligence = dossier
        return pages

    def technology_stats(self):
        stats = original_get_stats(self)
        dossier = getattr(self, "_orb_site_intelligence", {}) or {}
        stats["site_intelligence"] = dossier
        stats["technology_stack"] = dossier.get("technology_stack") or {}
        stats["local_seo"] = dossier.get("local_seo") or {}
        return stats

    crawler_type.crawl = technology_crawl
    crawler_type.get_crawl_stats = technology_stats
    crawler_type._orb_technology_intelligence_installed = True


__all__ = ["detect_technology_stack", "install_technology_intelligence_support", "local_seo_intelligence"]
