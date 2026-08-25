"""Truth-preserving Google Search Console retrieval.

Search performance is only reported when an authorized property can actually be
queried. Missing credentials or inaccessible properties are explicit
UNAVAILABLE states; they are never converted into zero traffic.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from app.core.config import settings


GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


def _normalized_domain(domain: str) -> str:
    value = (domain or "").strip().lower()
    value = value.removeprefix("https://").removeprefix("http://").split("/", 1)[0]
    return value[4:] if value.startswith("www.") else value


def _credentials(path: str):
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_file(path, scopes=[GSC_SCOPE])


def _property_candidates(domain: str) -> List[str]:
    canonical = _normalized_domain(domain)
    if not canonical:
        return []
    return [
        f"sc-domain:{canonical}",
        f"https://{canonical}/",
        f"https://www.{canonical}/",
        f"http://{canonical}/",
        f"http://www.{canonical}/",
    ]


def _query_property(session, property_name: str, start_date: str, end_date: str, row_limit: int) -> Dict[str, Any]:
    endpoint = (
        "https://searchconsole.googleapis.com/webmasters/v3/sites/"
        f"{quote(property_name, safe='')}/searchAnalytics/query"
    )
    payload = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query", "page", "device", "country"],
        "rowLimit": row_limit,
        "dataState": "final",
    }
    response = session.post(endpoint, json=payload, timeout=30)
    if response.status_code in {401, 403, 404}:
        return {"accessible": False, "status_code": response.status_code, "rows": []}
    response.raise_for_status()
    body = response.json() if response.content else {}
    return {"accessible": True, "status_code": response.status_code, "rows": body.get("rows") or []}


def _summarize_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    clicks = sum(float(row.get("clicks") or 0) for row in rows)
    impressions = sum(float(row.get("impressions") or 0) for row in rows)
    weighted_position = (
        sum(float(row.get("position") or 0) * float(row.get("impressions") or 0) for row in rows) / impressions
        if impressions else None
    )
    ctr = clicks / impressions if impressions else None

    query_rollup: Dict[str, Dict[str, float]] = {}
    page_rollup: Dict[str, Dict[str, float]] = {}
    for row in rows:
        keys = row.get("keys") or []
        query = str(keys[0]) if len(keys) > 0 else ""
        page = str(keys[1]) if len(keys) > 1 else ""
        row_clicks = float(row.get("clicks") or 0)
        row_impressions = float(row.get("impressions") or 0)
        row_position = float(row.get("position") or 0)
        for bucket, key in ((query_rollup, query), (page_rollup, page)):
            if not key:
                continue
            current = bucket.setdefault(key, {"clicks": 0.0, "impressions": 0.0, "position_weight": 0.0})
            current["clicks"] += row_clicks
            current["impressions"] += row_impressions
            current["position_weight"] += row_position * row_impressions

    def finish(bucket: Dict[str, Dict[str, float]], key_name: str) -> List[Dict[str, Any]]:
        output = []
        for key, values in bucket.items():
            imps = values["impressions"]
            clicks_value = values["clicks"]
            output.append({
                key_name: key,
                "clicks": round(clicks_value, 2),
                "impressions": round(imps, 2),
                "ctr": round(clicks_value / imps, 4) if imps else None,
                "position": round(values["position_weight"] / imps, 2) if imps else None,
            })
        return sorted(output, key=lambda item: (item["impressions"], item["clicks"]), reverse=True)

    queries = finish(query_rollup, "query")
    pages = finish(page_rollup, "page")
    opportunities = [
        item for item in queries
        if item.get("impressions", 0) >= 25
        and item.get("position") is not None
        and 4 <= float(item["position"]) <= 20
    ][:50]
    low_ctr = [
        item for item in queries
        if item.get("impressions", 0) >= 50
        and item.get("ctr") is not None
        and float(item["ctr"]) < 0.02
    ][:50]

    return {
        "totals": {
            "clicks": round(clicks, 2),
            "impressions": round(impressions, 2),
            "ctr": round(ctr, 4) if ctr is not None else None,
            "average_position": round(weighted_position, 2) if weighted_position is not None else None,
        },
        "top_queries": queries[:100],
        "top_pages": pages[:100],
        "ranking_opportunities": opportunities,
        "low_ctr_opportunities": low_ctr,
    }


def retrieve_search_console(domain: str, days: int = 28, row_limit: int = 25000) -> Dict[str, Any]:
    credentials_path = getattr(settings, "GA4_CREDENTIALS_PATH", None)
    canonical = _normalized_domain(domain)
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=max(1, days) - 1)
    date_range = {"start_date": start.isoformat(), "end_date": end.isoformat(), "days": days}

    if not canonical:
        return {"schema": "orb_weaver.search_console.v1", "status": "UNAVAILABLE_DOMAIN_MISSING", "evidence_state": "UNAVAILABLE", "date_range": date_range}
    if not credentials_path:
        return {
            "schema": "orb_weaver.search_console.v1",
            "status": "UNAVAILABLE_AUTH_REQUIRED",
            "evidence_state": "UNAVAILABLE",
            "domain": canonical,
            "date_range": date_range,
            "message": "Search Console credentials are not configured; zero traffic is not inferred.",
        }

    try:
        from google.auth.transport.requests import AuthorizedSession
        session = AuthorizedSession(_credentials(credentials_path))
    except Exception as exc:
        return {
            "schema": "orb_weaver.search_console.v1",
            "status": "UNAVAILABLE_AUTH_FAILED",
            "evidence_state": "UNAVAILABLE",
            "domain": canonical,
            "date_range": date_range,
            "error": f"{type(exc).__name__}: {exc}",
        }

    attempts = []
    for property_name in _property_candidates(canonical):
        try:
            result = _query_property(session, property_name, start.isoformat(), end.isoformat(), row_limit)
        except Exception as exc:
            attempts.append({"property": property_name, "status": "request_failed", "error": f"{type(exc).__name__}: {exc}"})
            continue
        attempts.append({"property": property_name, "status": "accessible" if result["accessible"] else "not_accessible", "status_code": result["status_code"]})
        if not result["accessible"]:
            continue
        summary = _summarize_rows(result["rows"])
        return {
            "schema": "orb_weaver.search_console.v1",
            "status": "RETRIEVED",
            "evidence_state": "VERIFIED",
            "domain": canonical,
            "property": property_name,
            "date_range": date_range,
            "row_count": len(result["rows"]),
            **summary,
            "property_attempts": attempts,
        }

    return {
        "schema": "orb_weaver.search_console.v1",
        "status": "UNAVAILABLE_NO_ACCESSIBLE_PROPERTY",
        "evidence_state": "UNAVAILABLE",
        "domain": canonical,
        "date_range": date_range,
        "property_attempts": attempts,
        "message": "No authorized Search Console property matched this domain; zero search traffic is not inferred.",
    }


__all__ = ["retrieve_search_console", "_summarize_rows"]
