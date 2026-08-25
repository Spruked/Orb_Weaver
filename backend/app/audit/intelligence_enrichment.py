"""Website Intelligence Dossier enrichment for the canonical audit engine."""

from __future__ import annotations

from typing import Any, Dict, List


def _issue(severity: str, category: str, title: str, description: str, recommendation: str, impact: int, urls=None) -> Dict[str, Any]:
    return {
        "severity": severity,
        "category": category,
        "title": title,
        "description": description,
        "affected_urls": list(urls or []),
        "recommendation": recommendation,
        "impact_score": impact,
    }


def _pointer_truth(stats: Dict[str, Any]) -> Dict[str, Any]:
    pointer_map = stats.get("pointer_map") or {}
    records = [row for row in pointer_map.get("records") or [] if isinstance(row, dict)]
    live = [row for row in records if row.get("pointer_class") == "live_guidance"]
    verified = [
        row for row in live
        if str(row.get("confidence_class") or "") in {"VERIFIED", "STABLE"}
        and (row.get("runtime_policy") or {}).get("may_point") is True
        and (row.get("confidence_evidence") or {}).get("verification_resolution") not in {None, "", "not_run"}
    ]
    unverified = [row for row in live if row not in verified]
    return {
        "extracted_targets": len(records),
        "live_guidance_candidates": len(live),
        "independently_verified_guidance_targets": len(verified),
        "unverified_guidance_candidates": len(unverified),
        "evidence_state": "VERIFIED" if live and not unverified else "REQUIRES_VERIFICATION",
    }


def install_audit_intelligence_enrichment(auditor_type) -> None:
    if getattr(auditor_type, "_orb_intelligence_enrichment_installed", False):
        return

    original_audit = auditor_type.audit

    def enriched_audit(self, pages, stats):
        result = original_audit(self, pages, stats)
        site_intel = stats.get("site_intelligence") or {}
        browser = stats.get("browser_observation") or site_intel.get("browser_observation") or {}
        google = site_intel.get("google_intelligence") or {}
        architecture = site_intel.get("content_architecture") or {}
        dispositions = site_intel.get("url_disposition") or {}
        platform = site_intel.get("platform") or {}
        builder = site_intel.get("site_builder") or {}
        assistant = site_intel.get("existing_conversational_interface") or {}
        pointer_truth = _pointer_truth(stats)

        warnings: List[Dict[str, Any]] = result["issues"]["warnings"]
        opportunities: List[Dict[str, Any]] = result["issues"]["opportunities"]

        browser_status = str(browser.get("status") or "NOT_RUN")
        if browser_status != "VERIFIED_FULL":
            warnings.append(_issue(
                "warning", "runtime_verification", "Rendered Browser Observation Incomplete",
                "The source crawl completed, but the visitor-visible runtime was not independently observed on every eligible route. Dynamic widgets, injected assistants, overlays or controls may therefore be missing from the source-only inventory.",
                "Complete the rendered-browser observation before claiming runtime controls or conversational interfaces are absent.",
                92,
                browser.get("unobserved_routes") or browser.get("failed_routes") or [],
            ))

        unresolved = int(dispositions.get("unresolved_count") or 0)
        if unresolved:
            warnings.append(_issue(
                "warning", "crawl_integrity", "Unresolved URL Dispositions",
                f"{unresolved} discovered URL(s) do not yet have a proven final crawl disposition.",
                "Resolve every discovered URL as fetched, blocked by policy, depth-limited, redirected/canonicalized, or explicitly unresolved before final release.",
                82,
                [row.get("url") for row in dispositions.get("rows") or [] if row.get("disposition") == "UNRESOLVED_NOT_FETCHED"],
            ))

        if architecture.get("homepage_concentrated"):
            opportunities.append(_issue(
                "opportunity", "content_architecture", "Homepage-Dominant Content Architecture",
                f"The homepage carries approximately {float(architecture.get('homepage_word_share') or 0) * 100:.0f}% of measured site copy while supporting routes are comparatively thin.",
                "Move important commercial and topical coverage into durable, internally linked destination pages where visitor intent and search intent justify separate routes.",
                68,
            ))

        artifacts = architecture.get("public_artifact_candidates") or []
        if artifacts:
            warnings.append(_issue(
                "warning", "content_integrity", "Public Development or Legacy Content Artifacts",
                f"{len(artifacts)} public route(s) match deterministic default, test-like, misspelled, or legacy-template patterns.",
                "Review these routes manually; remove, redirect, rename, noindex, or update them when they are not intentional public content.",
                72,
                [row.get("url") for row in artifacts],
            ))

        search_console = google.get("search_console") or {}
        ranking_ops = search_console.get("ranking_opportunities") or []
        low_ctr_ops = search_console.get("low_ctr_opportunities") or []
        if search_console.get("status") == "RETRIEVED" and (ranking_ops or low_ctr_ops):
            opportunities.append(_issue(
                "opportunity", "search_performance", "Google Search Performance Opportunities",
                f"Search Console identified {len(ranking_ops)} ranking opportunity query set(s) and {len(low_ctr_ops)} low-CTR opportunity query set(s) in the authenticated reporting window.",
                "Prioritize high-impression queries near page-one positions and improve titles/snippets for high-impression low-CTR queries.",
                78,
            ))

        summary = result.setdefault("summary", {})
        raw_load = float(summary.get("avg_load_time") or 0)
        summary["avg_load_time_ms"] = raw_load
        summary["avg_load_time_unit"] = "ms"
        summary["browser_observation_status"] = browser_status
        summary["platform"] = platform.get("platform")
        summary["site_builder_status"] = builder.get("status")
        summary["existing_assistant_status"] = assistant.get("status")
        summary["verified_guidance_targets"] = pointer_truth["independently_verified_guidance_targets"]

        total_images = int(stats.get("total_images") or 0)
        missing_alt = int(stats.get("images_missing_alt") or 0)
        public_pages = int(summary.get("public_pages") or summary.get("total_pages") or 0)
        schema_pages = int(stats.get("schema_pages") or 0)
        indexable = int(stats.get("indexable_pages") or 0)
        result["deep_seo"] = {
            "schema": "orb_weaver.deep_seo.v1",
            "technical": {
                "public_pages": public_pages,
                "indexable_pages": indexable,
                "indexable_ratio": round(indexable / public_pages, 4) if public_pages else None,
                "duplicate_content_pages": int(stats.get("duplicate_content_pages") or 0),
                "schema_pages": schema_pages,
                "schema_coverage": round(schema_pages / public_pages, 4) if public_pages else None,
            },
            "accessibility": {
                "images": total_images,
                "images_missing_alt": missing_alt,
                "alt_coverage": round((total_images - missing_alt) / total_images, 4) if total_images else None,
            },
            "semantic": {
                "thin_pages": int(stats.get("thin_semantic_pages") or summary.get("orb_context_thin_content_pages") or 0),
                "homepage_word_share": architecture.get("homepage_word_share"),
                "homepage_concentrated": architecture.get("homepage_concentrated"),
            },
            "search_performance": search_console,
            "analytics": google.get("ga4") or {},
        }
        result["site_intelligence"] = site_intel
        result["browser_observation"] = browser
        result["pointer_truth"] = pointer_truth
        result["assurance"] = {
            **(site_intel.get("assurance") or {}),
            "pointer_truth": pointer_truth,
            "audit_release_state": "BLOCKED_VERIFICATION_REQUIRED"
            if pointer_truth["evidence_state"] != "VERIFIED" or browser_status != "VERIFIED_FULL"
            else (site_intel.get("assurance") or {}).get("release_state", "REQUIRES_FINAL_RESCAN"),
        }

        all_issues = [
            *result["issues"]["critical"],
            *result["issues"]["warnings"],
            *result["issues"]["opportunities"],
        ]
        summary["total_issues"] = len(all_issues)
        summary["critical_count"] = len(result["issues"]["critical"])
        summary["warning_count"] = len(result["issues"]["warnings"])
        summary["opportunity_count"] = len(result["issues"]["opportunities"])
        result["top_issues"] = sorted(all_issues, key=lambda item: int(item.get("impact_score") or 0), reverse=True)[:10]
        return result

    auditor_type.audit = enriched_audit
    auditor_type._orb_intelligence_enrichment_installed = True


__all__ = ["install_audit_intelligence_enrichment"]
