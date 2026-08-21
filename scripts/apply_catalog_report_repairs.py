#!/usr/bin/env python3
"""One-shot guarded patch for the Aug 20 catalog/report integration.

Every transformation validates its source anchor. If yesterday's wiring no
longer matches, the patch fails instead of guessing and corrupting the repo.
"""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "backend" / "main.py"
LANDING = ROOT / "frontend" / "src" / "landing" / "LandingPage.tsx"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, found {count}")
    return updated


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "from app.crawler.engine import OrbWeaverCrawler, PageData\n",
        "from app.crawler.engine import OrbWeaverCrawler, PageData\n"
        "from app.catalog.compiler import compile_commercial_catalog\n"
        "from app.reporting.audit_reporting import build_audit_pdf, enrich_audit_report\n",
        "main imports",
    )

    # Index the catalog beside every other persisted Website ORB context artifact.
    text = replace_once(
        text,
        '("scan_stage_execution", "scan_stage_execution.json"),\n                )\n                if (payload.get("website_orb_context") or {}).get(key) is not None',
        '("scan_stage_execution", "scan_stage_execution.json"),\n                    ("commercial_catalog", "commercial_catalog.json"),\n                )\n                if (payload.get("website_orb_context") or {}).get(key) is not None',
        "client context index catalog",
    )

    text = replace_once(
        text,
        '    config = crawl_job.config or {}\n    page_knowledge = [',
        '    config = crawl_job.config or {}\n    commercial_catalog = config.get("commercial_catalog") or compile_commercial_catalog(pages)\n    page_knowledge = [',
        "client crawl pack catalog compile",
    )

    text = replace_once(
        text,
        '            "scan_stage_execution": config.get("scan_stage_execution"),\n            "competitor_gap": crawl_payload.get("competitor_gap"),',
        '            "scan_stage_execution": config.get("scan_stage_execution"),\n            "commercial_catalog": commercial_catalog,\n            "competitor_gap": crawl_payload.get("competitor_gap"),',
        "website context catalog",
    )

    # The current crawl pack's top level also exposes the same artifact explicitly.
    text = replace_once(
        text,
        '        "pointer_plot_map": pointer_plot_map,\n        "website_orb_context": {',
        '        "pointer_plot_map": pointer_plot_map,\n        "commercial_catalog": commercial_catalog,\n        "website_orb_context": {',
        "client crawl top-level catalog",
    )

    # Persist commercial_catalog.json beside lexical/retrieval/source artifacts.
    text = replace_once(
        text,
        '("scan_stage_execution", "scan_stage_execution.json"),\n        ):\n            artifact = payload["website_orb_context"].get(key)',
        '("scan_stage_execution", "scan_stage_execution.json"),\n            ("commercial_catalog", "commercial_catalog.json"),\n        ):\n            artifact = payload["website_orb_context"].get(key)',
        "client artifact persistence catalog",
    )

    # Make the catalog a first-class scan stage from the moment the job starts.
    text = replace_once(
        text,
        '"page_content_scan", "content_structure_extraction", "schema_extraction", "mobile_ux_analysis",\n                    "semantic_indexing", "lexical_indexing", "entity_extraction", "relationship_mapping",',
        '"page_content_scan", "content_structure_extraction", "schema_extraction", "commercial_catalog_extraction",\n                    "commercial_catalog_index_build", "mobile_ux_analysis", "semantic_indexing", "lexical_indexing",\n                    "entity_extraction", "relationship_mapping",',
        "initial catalog stages",
    )

    # Compile once from persisted page evidence; the summary is small enough for stats,
    # while the complete deterministic artifact remains in crawl.config.
    text = replace_once(
        text,
        '        source_validation = _build_source_validation(stored_pages, knowledge_chunks)\n        if source_validation["status"] != "COMPLETE":',
        '        source_validation = _build_source_validation(stored_pages, knowledge_chunks)\n'
        '        commercial_catalog = compile_commercial_catalog(stored_pages)\n'
        '        commercial_catalog_summary = {\n'
        '            key: int(commercial_catalog.get(key) or 0)\n'
        '            for key in (\n'
        '                "entry_count", "product_count", "service_count", "priced_entry_count",\n'
        '                "sku_model_count", "availability_count", "variant_count",\n'
        '                "specification_count", "source_page_count",\n'
        '            )\n'
        '        }\n'
        '        stats["commercial_catalog"] = commercial_catalog_summary\n'
        '        if source_validation["status"] != "COMPLETE":',
        "compile commercial catalog",
    )

    text = replace_once(
        text,
        '            "schema_extraction": evidence("COMPLETE", len(stored_pages), int(stats.get("schema_pages") or 0), "db:crawled_pages.schema_markup"),\n            "mobile_ux_analysis":',
        '            "schema_extraction": evidence("COMPLETE", len(stored_pages), int(stats.get("schema_pages") or 0), "db:crawled_pages.schema_markup"),\n'
        '            "commercial_catalog_extraction": evidence("COMPLETE", len(stored_pages), int(commercial_catalog.get("entry_count") or 0), "crawl.config.commercial_catalog"),\n'
        '            "commercial_catalog_index_build": evidence("COMPLETE", int(commercial_catalog.get("entry_count") or 0), len((commercial_catalog.get("indexes") or {}).get("by_name") or {}), "crawl.config.commercial_catalog.indexes"),\n'
        '            "mobile_ux_analysis":',
        "catalog stage evidence",
    )

    text = replace_once(
        text,
        '            "source_validation": source_validation,\n            "scan_stage_execution": scan_stage_execution,',
        '            "source_validation": source_validation,\n            "commercial_catalog": commercial_catalog,\n            "catalog_summary": commercial_catalog_summary,\n            "scan_stage_execution": scan_stage_execution,',
        "crawl config catalog artifacts",
    )

    # Assembly status: catalog stages now participate in ORB readiness and are visible
    # on the Crawl Job page through the existing dynamic stage renderer.
    text = replace_once(
        text,
        '    route_categories = (stats.get("route_category_counts") or (crawl_job.config or {}).get("route_category_counts") or {})\n    route_count =',
        '    catalog_summary = (crawl_job.config or {}).get("catalog_summary") or stats.get("commercial_catalog") or {}\n'
        '    route_categories = (stats.get("route_category_counts") or (crawl_job.config or {}).get("route_category_counts") or {})\n    route_count =',
        "assembly catalog summary",
    )

    text = replace_once(
        text,
        '        "page_content_scan", "content_structure_extraction", "schema_extraction", "mobile_ux_analysis",\n        "semantic_indexing", "lexical_indexing", "entity_extraction",',
        '        "page_content_scan", "content_structure_extraction", "schema_extraction",\n        "commercial_catalog_extraction", "commercial_catalog_index_build", "mobile_ux_analysis",\n        "semantic_indexing", "lexical_indexing", "entity_extraction",',
        "required catalog stages",
    )

    text = replace_once(
        text,
        '            _scan_stage("mobile_ux_analysis", "Mobile / UX Analysis", stage_status("mobile_ux_analysis"), [',
        '            _scan_stage("commercial_catalog_extraction", "Commercial Catalog Extraction", stage_status("commercial_catalog_extraction"), [\n'
        '                {"label": "catalog entries", "value": int(catalog_summary.get("entry_count") or 0)},\n'
        '                {"label": "products", "value": int(catalog_summary.get("product_count") or 0)},\n'
        '                {"label": "services", "value": int(catalog_summary.get("service_count") or 0)},\n'
        '                {"label": "priced entries", "value": int(catalog_summary.get("priced_entry_count") or 0)},\n'
        '                {"label": "SKU/model records", "value": int(catalog_summary.get("sku_model_count") or 0)},\n'
        '            ], execution_note),\n'
        '            _scan_stage("commercial_catalog_index_build", "Catalog Lookup Index Build", stage_status("commercial_catalog_index_build"), [\n'
        '                {"label": "availability records", "value": int(catalog_summary.get("availability_count") or 0)},\n'
        '                {"label": "variants", "value": int(catalog_summary.get("variant_count") or 0)},\n'
        '                {"label": "specifications", "value": int(catalog_summary.get("specification_count") or 0)},\n'
        '                {"label": "source pages", "value": int(catalog_summary.get("source_page_count") or 0)},\n'
        '            ], execution_note),\n'
        '            _scan_stage("mobile_ux_analysis", "Mobile / UX Analysis", stage_status("mobile_ux_analysis"), [',
        "assembly catalog stage cards",
    )

    # Surface a compact catalog summary in the crawl API without forcing the UI to
    # download the complete catalog artifact on every refresh.
    text = replace_once(
        text,
        '        "planned_tool_calls": _planned_tool_calls(pointer_summary, stats),\n        "historical": config.get("historical"),',
        '        "planned_tool_calls": _planned_tool_calls(pointer_summary, stats),\n        "commercial_catalog_summary": config.get("catalog_summary") or stats.get("commercial_catalog") or {},\n        "historical": config.get("historical"),',
        "serialize catalog summary",
    )

    # Add a dedicated full-catalog endpoint. This keeps exact deterministic facts
    # available to the ORB/runtime and owner UI without bloating polling responses.
    catalog_endpoint = '''\n\n@app.get("/api/crawl-jobs/{job_id}/commercial-catalog")\nasync def get_crawl_commercial_catalog(\n    job_id: str,\n    db: Session = Depends(get_db),\n    customer: Customer = Depends(get_current_customer),\n):\n    crawl_job = _owned_crawl_job(job_id, customer, db)\n    catalog = (crawl_job.config or {}).get("commercial_catalog")\n    if not isinstance(catalog, dict):\n        pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job.id).all()\n        catalog = compile_commercial_catalog(pages)\n    return {\n        "crawl_id": str(crawl_job.id),\n        "project_id": str(crawl_job.project_id),\n        **catalog,\n    }\n'''
    text = replace_once(
        text,
        '\n\n@app.get("/api/crawl-jobs/{job_id}/export/csv")\nasync def export_crawl_csv',
        catalog_endpoint + '\n\n@app.get("/api/crawl-jobs/{job_id}/export/csv")\nasync def export_crawl_csv',
        "catalog endpoint",
    )

    # Audit uses the full completed crawl config (not just recomputed page basics),
    # then enriches report JSON with catalog, stage ledger, crawl coverage, and narrative.
    text = replace_once(
        text,
        '        stats = _compute_stats(pages)\n\n        auditor = SEOAuditor()\n        report_payload = auditor.audit(page_data, stats)\n        report_payload["pointer_summary"] = stats.get("pointer_summary") or _pointer_summary_from_pages(pages)\n        report_payload["planned_tool_calls"] = stats.get("planned_tool_calls") or _planned_tool_calls(report_payload["pointer_summary"], stats)\n\n        audit.report_data = report_payload',
        '        crawl_config = crawl_job.config or {}\n'
        '        stats = {**_compute_stats(pages), **(crawl_config.get("stats") or {})}\n\n'
        '        auditor = SEOAuditor()\n'
        '        report_payload = auditor.audit(page_data, stats)\n'
        '        report_payload["pointer_summary"] = _pointer_summary_with_execution(_pointer_summary_from_pages(pages), crawl_config)\n'
        '        report_payload["planned_tool_calls"] = _planned_tool_calls(report_payload["pointer_summary"], stats)\n'
        '        report_payload = enrich_audit_report(report_payload, crawl_config=crawl_config, pages=page_data)\n\n'
        '        audit.report_data = report_payload',
        "enrich audit report",
    )

    # Replace the tiny score-card PDF with the shared human-readable report compiler.
    pdf_pattern = r'@app\.get\("/api/audit-reports/\{audit_id\}/export/pdf"\)\nasync def export_audit_pdf\(.*?\n\n(?=@app\.get\("/api/projects/\{project_id\}/report-compiler"\))'
    pdf_replacement = '''@app.get("/api/audit-reports/{audit_id}/export/pdf")\nasync def export_audit_pdf(audit_id: str, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):\n    report = _owned_audit_report(audit_id, customer, db)\n    if not report.report_data:\n        raise HTTPException(status_code=404, detail="Audit report not found")\n    try:\n        buf = build_audit_pdf(report.report_data, str(audit_id))\n    except RuntimeError as exc:\n        raise HTTPException(status_code=500, detail=str(exc))\n    headers = {"Content-Disposition": f"attachment; filename=audit_{audit_id}.pdf"}\n    return StreamingResponse(buf, media_type="application/pdf", headers=headers)\n\n'''
    text = regex_once(text, pdf_pattern, pdf_replacement, "replace audit PDF compiler")

    MAIN.write_text(text, encoding="utf-8")


def patch_landing_intro() -> None:
    text = LANDING.read_text(encoding="utf-8")
    old = '''            <h2>Meet Weaver.</h2>\n            <div className="ow-cut-encounter-steps" aria-label="Weaver communication orientation">\n              <p data-orb-target="speak_naturally"><strong>Just talk.</strong> Use the words you would use with a person who knows the site.</p>\n              <p data-orb-target="pause_when_finished"><strong>Finish the thought, then pause.</strong> Weaver takes the turn when your voice settles.</p>\n              <p data-orb-target="watch_weaver_guide"><strong>Watch the page.</strong> When showing is clearer, Weaver moves and points to the verified target.</p>\n            </div>'''
    new = '''            <h2>Meet Weaver.</h2>\n            <div className="ow-cut-encounter-steps" aria-label="Weaver communication orientation">\n              <p data-orb-target="what_weaver_does"><strong>What does Weaver do?</strong> It understands this website, answers from its verified knowledge, and guides you to the right place when showing is faster than explaining.</p>\n              <p data-orb-target="what_to_say"><strong>What do I say?</strong> Anything you would ask a person who knows the site. Click Weaver, speak naturally, finish your thought, and pause.</p>\n              <p data-orb-target="interrupt_or_guide"><strong>You stay in control.</strong> Click Weaver while it is talking to stop it. Click again when you want help. When pointing is useful, Weaver guides only to a verified target.</p>\n            </div>'''
    text = replace_once(text, old, new, "landing first-encounter copy")
    LANDING.write_text(text, encoding="utf-8")


def main() -> int:
    patch_main()
    patch_landing_intro()
    print("Applied guarded catalog/report/intro repairs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
