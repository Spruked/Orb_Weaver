"""Truth-preserving compatibility adapter for human audit surfaces.

The legacy AuditReport UI expects pointer_summary.record_count to mean
"Verified Targets" and summary.avg_load_time to be seconds.  The underlying
crawl contract stores mapped target count and milliseconds.  This adapter keeps
both machine facts while making the existing human surface impossible to
mislabel.
"""

from __future__ import annotations

from typing import Any, Dict


def install_reporting_truth_adapter(reporting_module) -> None:
    if getattr(reporting_module, "_orb_reporting_truth_adapter_installed", False):
        return

    original_enrich = reporting_module.enrich_audit_report

    def truth_enrich(report: Dict[str, Any], *, crawl_config, pages):
        # Let the canonical report builder create its narrative from the original
        # mapped/extracted counts first.  Then adapt legacy display fields.
        enriched = original_enrich(report, crawl_config=crawl_config, pages=pages)

        pointer = enriched.get("pointer_summary") if isinstance(enriched.get("pointer_summary"), dict) else {}
        pointer_truth = enriched.get("pointer_truth") if isinstance(enriched.get("pointer_truth"), dict) else {}
        mapped = int(pointer.get("record_count") or 0)
        verified = int(pointer_truth.get("independently_verified_guidance_targets") or 0)
        candidates = int(pointer_truth.get("live_guidance_candidates") or 0)
        unverified = int(pointer_truth.get("unverified_guidance_candidates") or max(candidates - verified, 0))

        if pointer:
            pointer["mapped_record_count"] = mapped
            pointer["verified_target_count"] = verified
            pointer["unverified_guidance_candidate_count"] = unverified
            # Backward-compatible human UI: it labels record_count "Verified Targets".
            # Until that UI is migrated, feed it only actual independently verified targets.
            pointer["record_count"] = verified
            pointer["verification_evidence_state"] = pointer_truth.get("evidence_state") or "REQUIRES_VERIFICATION"

        summary = enriched.setdefault("summary", {})
        raw_ms_value = summary.get("avg_load_time_ms")
        if raw_ms_value is None:
            raw_ms_value = summary.get("avg_load_time", 0)
        try:
            raw_ms = float(raw_ms_value or 0)
        except (TypeError, ValueError):
            raw_ms = 0.0
        summary["avg_load_time_ms"] = raw_ms
        # Backward-compatible human UI appends "s" to avg_load_time.
        summary["avg_load_time"] = raw_ms / 1000.0
        summary["avg_load_time_unit"] = "seconds"
        summary["mapped_pointer_targets"] = mapped
        summary["verified_pointer_targets"] = verified
        summary["unverified_guidance_candidates"] = unverified

        narrative = enriched.get("audit_narrative") if isinstance(enriched.get("audit_narrative"), dict) else None
        site_intel = enriched.get("site_intelligence") if isinstance(enriched.get("site_intelligence"), dict) else {}
        if narrative is not None and site_intel:
            platform = site_intel.get("platform") or {}
            builder = site_intel.get("site_builder") or {}
            assistant = site_intel.get("existing_conversational_interface") or {}
            browser = site_intel.get("browser_observation") or {}
            google = site_intel.get("google_intelligence") or {}
            ga4 = google.get("ga4") or {}
            gsc = google.get("search_console") or {}
            assurance = site_intel.get("assurance") or {}
            providers = ", ".join(str(item) for item in assistant.get("providers") or []) or "none verified"
            platform_name = platform.get("platform") or "not identified"
            builder_name = builder.get("builder") or "not identified"
            browser_status = browser.get("status") or "NOT_RUN"
            narrative.setdefault("sections", []).insert(1, {
                "id": "website_identity_and_runtime_truth",
                "title": "Website Identity and Runtime Verification",
                "narrative": (
                    f"Platform: {platform_name} ({platform.get('evidence_state') or 'UNKNOWN'}). "
                    f"Builder/agency: {builder_name} ({builder.get('evidence_state') or 'UNKNOWN'}). "
                    f"Existing conversational interface: {assistant.get('status') or 'UNKNOWN'}; providers: {providers}. "
                    f"Rendered-browser verification: {browser_status}. "
                    f"GA4: {ga4.get('status') or 'UNAVAILABLE'}. Search Console: {gsc.get('status') or 'UNAVAILABLE'}. "
                    f"ORB release assurance: {assurance.get('release_state') or 'BLOCKED_VERIFICATION_REQUIRED'}."
                ),
            })

        return enriched

    reporting_module.enrich_audit_report = truth_enrich
    reporting_module._orb_reporting_truth_adapter_installed = True


__all__ = ["install_reporting_truth_adapter"]
