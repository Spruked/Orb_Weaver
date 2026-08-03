"""Automatic public analytics-tag discovery and authenticated GA4 retrieval.

This module extends the canonical crawler without creating a parallel data store.
Per-page findings are serialized with PageData, and the aggregate resolution/
traffic record is returned through get_crawl_stats so existing Vault crawl
snapshots and client packages preserve it automatically.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from app.analytics.ga4 import GA4Connector
from app.core.config import settings

GA4_PATTERN = re.compile(r"(?<![A-Z0-9-])G-[A-Z0-9]{6,}(?![A-Z0-9])", re.I)
GTM_PATTERN = re.compile(r"(?<![A-Z0-9-])GTM-[A-Z0-9]{4,}(?![A-Z0-9])", re.I)
ADS_PATTERN = re.compile(r"(?<![A-Z0-9-])AW-\d{5,}(?!\d)", re.I)
UA_PATTERN = re.compile(r"(?<![A-Z0-9-])UA-\d{4,}-\d+(?!\d)", re.I)

GOOGLE_SCRIPT_MARKERS = (
    "googletagmanager.com/gtag/js",
    "googletagmanager.com/gtm.js",
    "google-analytics.com/analytics.js",
    "google-analytics.com/collect",
)


def _sorted_ids(pattern: re.Pattern[str], value: str) -> List[str]:
    return sorted({match.upper() for match in pattern.findall(value or "")})


def analyze_analytics_tags(html: str, route: str) -> Dict[str, Any]:
    """Extract public analytics identifiers and static implementation signals."""
    source = html or ""
    lower = source.lower()

    ga4_ids = _sorted_ids(GA4_PATTERN, source)
    gtm_ids = _sorted_ids(GTM_PATTERN, source)
    ads_ids = _sorted_ids(ADS_PATTERN, source)
    ua_ids = _sorted_ids(UA_PATTERN, source)

    occurrences = {
        identifier: len(re.findall(re.escape(identifier), source, flags=re.I))
        for identifier in [*ga4_ids, *gtm_ids, *ads_ids, *ua_ids]
    }
    duplicate_ids = sorted(identifier for identifier, count in occurrences.items() if count > 1)

    script_markers = [marker for marker in GOOGLE_SCRIPT_MARKERS if marker in lower]
    has_data_layer = "datalayer" in lower
    has_gtag_call = bool(re.search(r"\bgtag\s*\(", source, flags=re.I))
    has_config_call = bool(
        re.search(
            r"\bgtag\s*\(\s*['\"]config['\"]\s*,\s*['\"](?:G-|AW-|UA-)",
            source,
            flags=re.I,
        )
    )
    consent_signals = sorted(
        signal
        for signal in ("analytics_storage", "ad_storage", "ad_user_data", "ad_personalization")
        if signal in lower
    )
    has_consent_mode = bool(
        consent_signals
        or re.search(r"\bgtag\s*\(\s*['\"]consent['\"]", source, flags=re.I)
    )

    detected = bool(ga4_ids or gtm_ids or ads_ids or ua_ids or script_markers)
    sources: List[str] = []
    if script_markers:
        sources.append("script_url")
    if ga4_ids or gtm_ids or ads_ids or ua_ids:
        sources.append("page_source")
    if has_gtag_call:
        sources.append("gtag_call")
    if has_data_layer:
        sources.append("data_layer")

    return {
        "route": route,
        "detected": detected,
        "ga4_measurement_ids": ga4_ids,
        "gtm_container_ids": gtm_ids,
        "google_ads_ids": ads_ids,
        "legacy_ua_ids": ua_ids,
        "identifier_occurrences": occurrences,
        "duplicate_ids": duplicate_ids,
        "duplicate_tag": bool(duplicate_ids),
        "tag_sources": sources,
        "script_markers": script_markers,
        "gtag_call_detected": has_gtag_call,
        "gtag_config_detected": has_config_call,
        "data_layer_detected": has_data_layer,
        "consent_mode_detected": has_consent_mode,
        "consent_signals": consent_signals,
        "static_activity_status": "implementation_detected" if detected else "not_detected",
        "network_activity_status": "not_verified_by_static_crawl",
        "confidence": 0.99 if ga4_ids or gtm_ids or ads_ids or ua_ids else (0.75 if script_markers else 0.0),
    }


def summarize_analytics_tags(page_findings: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    findings = [row for row in page_findings if isinstance(row, dict)]
    ga4 = sorted({item for row in findings for item in row.get("ga4_measurement_ids", [])})
    gtm = sorted({item for row in findings for item in row.get("gtm_container_ids", [])})
    ads = sorted({item for row in findings for item in row.get("google_ads_ids", [])})
    ua = sorted({item for row in findings for item in row.get("legacy_ua_ids", [])})
    detected_routes = [row.get("route") for row in findings if row.get("detected")]
    missing_routes = [row.get("route") for row in findings if not row.get("detected")]
    per_id_routes: Dict[str, List[str]] = {}
    for row in findings:
        route = row.get("route")
        for identifier in [
            *row.get("ga4_measurement_ids", []),
            *row.get("gtm_container_ids", []),
            *row.get("google_ads_ids", []),
            *row.get("legacy_ua_ids", []),
        ]:
            per_id_routes.setdefault(identifier, []).append(route)

    issues: List[Dict[str, Any]] = []
    if detected_routes and missing_routes:
        issues.append({"code": "analytics_missing_on_routes", "severity": "warning", "routes": missing_routes})
    if len(ga4) > 1:
        issues.append({"code": "multiple_ga4_measurement_ids", "severity": "warning", "identifiers": ga4})
    if ua and ga4:
        issues.append({"code": "legacy_and_ga4_tags_together", "severity": "warning", "legacy_ids": ua, "ga4_ids": ga4})
    duplicate_routes = [row.get("route") for row in findings if row.get("duplicate_tag")]
    if duplicate_routes:
        issues.append({"code": "duplicate_analytics_tag", "severity": "warning", "routes": duplicate_routes})
    detected_consent_values = {bool(row.get("consent_mode_detected")) for row in findings if row.get("detected")}
    if len(detected_consent_values) > 1:
        issues.append({"code": "consent_mode_inconsistent", "severity": "warning"})

    return {
        "scan_version": "analytics-tags-v1",
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "pages_scanned": len(findings),
        "pages_with_analytics": len(detected_routes),
        "pages_without_analytics": len(missing_routes),
        "ga4_measurement_ids": ga4,
        "gtm_container_ids": gtm,
        "google_ads_ids": ads,
        "legacy_ua_ids": ua,
        "identifier_routes": per_id_routes,
        "detected_routes": detected_routes,
        "missing_routes": missing_routes,
        "issues": issues,
        "property_resolution": {
            "status": "not_attempted",
            "property_id": None,
            "measurement_id": ga4[0] if len(ga4) == 1 else None,
            "verified": False,
        },
        "traffic_retrieval": {"status": "not_attempted", "retrieved_at": None, "error": None},
        "traffic": None,
    }


def _credentials():
    path = getattr(settings, "GA4_CREDENTIALS_PATH", None)
    if not path:
        return None
    from google.oauth2 import service_account

    scopes = getattr(settings, "GA4_SCOPES", ["https://www.googleapis.com/auth/analytics.readonly"])
    return service_account.Credentials.from_service_account_file(path, scopes=scopes)


def _iter_property_names(admin_client) -> Iterable[str]:
    seen = set()
    for summary in admin_client.list_account_summaries():
        for prop in getattr(summary, "property_summaries", []):
            name = str(getattr(prop, "property", "") or "")
            if name and name not in seen:
                seen.add(name)
                yield name


def resolve_ga4_property(measurement_id: str) -> Dict[str, Any]:
    """Resolve a public G- ID to its authenticated GA4 property and web stream."""
    normalized = (measurement_id or "").upper().strip()
    if not normalized:
        return {"status": "measurement_id_missing", "measurement_id": None, "property_id": None, "verified": False}
    if not getattr(settings, "GA4_CREDENTIALS_PATH", None):
        return {"status": "authentication_required", "measurement_id": normalized, "property_id": None, "verified": False}

    try:
        from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
    except ImportError as exc:
        return {
            "status": "admin_api_dependency_missing",
            "measurement_id": normalized,
            "property_id": None,
            "verified": False,
            "error": str(exc),
        }

    try:
        client = AnalyticsAdminServiceClient(credentials=_credentials())
        matches: List[Dict[str, Any]] = []
        for property_name in _iter_property_names(client):
            for stream in client.list_data_streams(parent=property_name):
                web = getattr(stream, "web_stream_data", None)
                found = str(getattr(web, "measurement_id", "") or "").upper()
                if found != normalized:
                    continue
                property_id = property_name.rsplit("/", 1)[-1]
                stream_name = str(getattr(stream, "name", "") or "")
                matches.append({
                    "measurement_id": normalized,
                    "property_id": property_id,
                    "property_name": property_name,
                    "stream_id": stream_name.rsplit("/", 1)[-1] if stream_name else None,
                    "stream_name": stream_name or None,
                    "display_name": str(getattr(stream, "display_name", "") or "") or None,
                    "default_uri": str(getattr(web, "default_uri", "") or "") or None,
                })

        if not matches:
            return {"status": "no_accessible_property_match", "measurement_id": normalized, "property_id": None, "verified": False}
        if len(matches) > 1:
            return {
                "status": "ambiguous_property_match",
                "measurement_id": normalized,
                "property_id": None,
                "verified": False,
                "matches": matches,
            }
        return {"status": "verified", "verified": True, **matches[0]}
    except Exception as exc:
        return {
            "status": "resolution_failed",
            "measurement_id": normalized,
            "property_id": None,
            "verified": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def retrieve_ga4_traffic(property_id: str) -> Dict[str, Any]:
    try:
        report = GA4Connector(property_id=property_id).get_full_report(days=30)
        return {
            "status": "retrieved",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
            "traffic": report,
        }
    except Exception as exc:
        return {
            "status": "retrieval_failed",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "error": f"{type(exc).__name__}: {exc}",
            "traffic": None,
        }


def enrich_with_google_data(summary: Dict[str, Any]) -> Dict[str, Any]:
    measurement_ids = summary.get("ga4_measurement_ids") or []
    if not measurement_ids:
        summary["property_resolution"] = {
            "status": "no_ga4_measurement_id_detected",
            "property_id": None,
            "measurement_id": None,
            "verified": False,
        }
        summary["traffic_retrieval"]["status"] = "blocked_no_measurement_id"
        return summary
    if len(measurement_ids) > 1:
        summary["property_resolution"] = {
            "status": "blocked_conflicting_measurement_ids",
            "property_id": None,
            "measurement_id": None,
            "verified": False,
            "candidates": measurement_ids,
        }
        summary["traffic_retrieval"]["status"] = "blocked_conflicting_measurement_ids"
        return summary

    resolution = resolve_ga4_property(measurement_ids[0])
    summary["property_resolution"] = resolution
    if not resolution.get("verified") or not resolution.get("property_id"):
        summary["traffic_retrieval"]["status"] = "blocked_property_unresolved"
        summary["traffic_retrieval"]["error"] = resolution.get("error")
        return summary

    traffic = retrieve_ga4_traffic(str(resolution["property_id"]))
    summary["traffic_retrieval"] = {key: traffic.get(key) for key in ("status", "retrieved_at", "error")}
    summary["traffic"] = traffic.get("traffic")
    return summary


def install_analytics_tag_support(crawler_type, page_type) -> None:
    """Patch the canonical crawler once; existing persistence consumes the result."""
    if getattr(crawler_type, "_orb_analytics_tag_support_installed", False):
        return

    original_fetch_page = crawler_type._fetch_page
    original_render_page_dom = crawler_type._render_page_dom
    original_crawl = crawler_type.crawl
    original_get_stats = crawler_type.get_crawl_stats
    original_to_dict = page_type.to_dict

    async def capturing_fetch_page(self, session, url):
        result = await original_fetch_page(self, session, url)
        html = result[0]
        if html:
            captured = getattr(self, "_orb_analytics_html", None)
            if captured is None:
                captured = {}
                self._orb_analytics_html = captured
            captured[self._normalize_url(url)] = html
        return result

    async def capturing_render_page_dom(self, url):
        html = await original_render_page_dom(self, url)
        if html:
            captured = getattr(self, "_orb_analytics_html", None)
            if captured is None:
                captured = {}
                self._orb_analytics_html = captured
            captured[self._normalize_url(url)] = html
        return html

    async def analytics_crawl(self, start_url: str, seed_urls: Optional[List[str]] = None):
        self._orb_analytics_html = {}
        pages = await original_crawl(self, start_url, seed_urls)
        findings = []
        for page in pages:
            normalized = self._normalize_url(page.url)
            html = self._orb_analytics_html.get(normalized, "")
            route = urlparse(page.url).path or "/"
            finding = analyze_analytics_tags(html, route)
            page.analytics_tags = finding
            findings.append(finding)

        summary = summarize_analytics_tags(findings)
        self._orb_analytics_summary = await asyncio.to_thread(enrich_with_google_data, summary)
        return pages

    def analytics_get_stats(self):
        stats = original_get_stats(self)
        stats["analytics_tag_scan"] = getattr(self, "_orb_analytics_summary", summarize_analytics_tags([]))
        return stats

    def analytics_to_dict(self):
        payload = original_to_dict(self)
        payload["analytics_tags"] = getattr(
            self,
            "analytics_tags",
            analyze_analytics_tags("", urlparse(self.url).path or "/"),
        )
        return payload

    crawler_type._fetch_page = capturing_fetch_page
    crawler_type._render_page_dom = capturing_render_page_dom
    crawler_type.crawl = analytics_crawl
    crawler_type.get_crawl_stats = analytics_get_stats
    page_type.to_dict = analytics_to_dict
    crawler_type._orb_analytics_tag_support_installed = True
