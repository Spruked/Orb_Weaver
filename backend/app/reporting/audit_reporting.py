"""Human-readable audit enrichment and PDF compilation.

This module keeps the audit JSON and PDF sourced from the same evidence so the
compact PDF is a readable explanation of the weave, not a separate score card.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from app.catalog.compiler import compile_commercial_catalog


CATALOG_SUMMARY_KEYS = (
    "entry_count",
    "product_count",
    "service_count",
    "priced_entry_count",
    "sku_model_count",
    "availability_count",
    "variant_count",
    "specification_count",
    "source_page_count",
)


def _number(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _score(value: Any) -> str:
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "not scored"


def _catalog_summary(catalog: Mapping[str, Any]) -> Dict[str, int]:
    return {key: _number(catalog.get(key)) for key in CATALOG_SUMMARY_KEYS}


def _crawl_coverage_sentence(stats: Mapping[str, Any]) -> str:
    crawled = _number(stats.get("total_pages"))
    discovered = _number(stats.get("discovered_urls"))
    max_pages = _number(stats.get("max_pages_configured"))
    depth = _number(stats.get("max_depth_configured"))
    if not discovered:
        return f"The weave analyzed {crawled} stored pages."
    remainder = max(discovered - crawled, 0)
    limit_note = ""
    if stats.get("max_page_limit_hit") or stats.get("depth_limit_hit"):
        reasons = []
        if stats.get("max_page_limit_hit"):
            reasons.append(f"the {max_pages or 'configured'}-page ceiling")
        if stats.get("depth_limit_hit"):
            reasons.append(f"depth {depth or 'limit'}")
        limit_note = f" The frontier was not exhausted because {' and '.join(reasons)} was reached."
    return (
        f"ORB Weaver discovered {discovered} URLs and retained analysis for {crawled} pages; "
        f"{remainder} discovered URLs were not represented by a stored crawl page.{limit_note}"
    )


def build_audit_narrative(report: Mapping[str, Any]) -> Dict[str, Any]:
    scores = report.get("scores") or {}
    summary = report.get("summary") or {}
    stats = report.get("crawl_stats") or {}
    catalog = report.get("commercial_catalog") or {}
    catalog_summary = _catalog_summary(catalog)
    pointer = report.get("pointer_summary") or {}
    stages = report.get("scan_stage_execution") or {}

    critical = _number(summary.get("critical_count"))
    warnings = _number(summary.get("warning_count"))
    opportunities = _number(summary.get("opportunity_count"))
    overall = _score(scores.get("overall"))

    executive = (
        f"This report explains what ORB Weaver found, what the findings mean, and what remains before a Website ORB "
        f"can safely guide visitors. The current overall audit score is {overall}. The audit contains {critical} critical "
        f"issues, {warnings} warnings, and {opportunities} opportunities. {_crawl_coverage_sentence(stats)}"
    )

    catalog_text = (
        f"The commercial catalog contains {catalog_summary['entry_count']} deterministic entries: "
        f"{catalog_summary['product_count']} product-like records and {catalog_summary['service_count']} service records. "
        f"{catalog_summary['priced_entry_count']} entries carry direct price evidence, {catalog_summary['sku_model_count']} "
        f"carry SKU/model identifiers, {catalog_summary['availability_count']} expose availability, and the weave captured "
        f"{catalog_summary['variant_count']} variants plus {catalog_summary['specification_count']} specifications. "
        "These facts are kept separate from general semantic retrieval so exact commercial questions can use direct evidence first."
    ) if catalog_summary["entry_count"] else (
        "No deterministic commercial catalog entries were confirmed in this crawl. That does not prove the site has no products or "
        "services; it means the current crawl evidence did not provide enough structured or extracted commercial identity to publish a direct catalog record."
    )

    pointer_count = _number(pointer.get("record_count"))
    guidance_count = _number(pointer.get("guidance_eligible_count") or pointer.get("safe_pointer_count"))
    conflicts = _number(pointer.get("route_locator_conflicts") or pointer.get("route_locator_conflict_count"))
    pointer_status = str(pointer.get("status") or ("ready" if pointer_count and guidance_count == pointer_count else "needs review"))
    pointer_text = (
        f"Pointer extraction identified {pointer_count} physical targets. {guidance_count} are currently guidance-eligible. "
        f"{conflicts} route/locator conflicts were reported. Runtime pointing status is {pointer_status}. "
        "ORB Weaver deliberately blocks uncertain physical guidance rather than pointing at a target it cannot verify."
    )

    intelligence_text = (
        f"The intelligence weave indexed {_number(stats.get('semantic_sections') or stats.get('content_sections'))} explicit semantic sections when available, "
        f"{_number(stats.get('canonical_terms') or stats.get('lexical_canonical_terms'))} canonical lexical terms, "
        f"{_number(stats.get('entity_count') or stats.get('unique_entities'))} entities, and "
        f"{_number(stats.get('relationship_count') or stats.get('relationships'))} mapped relationships. "
        f"Schema was present on {_number(stats.get('schema_pages'))} pages with {_number(stats.get('schema_errors'))} extraction errors."
    )

    completed_stages = sum(1 for item in stages.values() if isinstance(item, Mapping) and str(item.get("status", "")).upper() == "COMPLETE")
    blocked_stages = [name for name, item in stages.items() if isinstance(item, Mapping) and str(item.get("status", "")).upper() in {"BLOCKED", "FAILED"}]
    stage_text = (
        f"The persisted stage ledger records {completed_stages} completed stages. "
        + (f"Stages still blocked or failed: {', '.join(blocked_stages)}." if blocked_stages else "No persisted stage is currently marked blocked or failed.")
    )

    return {
        "schema": "orb_weaver.audit_narrative.v1",
        "executive_summary": executive,
        "sections": [
            {"id": "crawl_coverage", "title": "Crawl Coverage", "narrative": _crawl_coverage_sentence(stats)},
            {"id": "commercial_catalog", "title": "Commercial Catalog", "narrative": catalog_text},
            {"id": "website_intelligence", "title": "Website Intelligence", "narrative": intelligence_text},
            {"id": "pointer_guidance", "title": "ORB Pointer Guidance", "narrative": pointer_text},
            {"id": "stage_evidence", "title": "Weave Stage Evidence", "narrative": stage_text},
        ],
    }


def enrich_audit_report(
    report: Dict[str, Any],
    *,
    crawl_config: Mapping[str, Any] | None,
    pages: Sequence[Any],
) -> Dict[str, Any]:
    config = dict(crawl_config or {})
    stored_catalog = config.get("commercial_catalog")
    catalog = stored_catalog if isinstance(stored_catalog, Mapping) else compile_commercial_catalog(pages)
    stats = dict(config.get("stats") or {})

    report["crawl_stats"] = stats
    report["scan_stage_execution"] = dict(config.get("scan_stage_execution") or {})
    report["commercial_catalog"] = dict(catalog)
    report["commercial_catalog_summary"] = _catalog_summary(catalog)
    report["audit_narrative"] = build_audit_narrative(report)
    return report


def _issue_rows(report: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    issues = report.get("issues") or {}
    rows: List[Mapping[str, Any]] = []
    for bucket in ("critical", "warnings", "opportunities"):
        for issue in issues.get(bucket) or []:
            if isinstance(issue, Mapping):
                rows.append({**issue, "severity_bucket": bucket})
    rows.sort(key=lambda row: _number(row.get("impact_score")), reverse=True)
    return rows


def build_audit_pdf(report: Mapping[str, Any], audit_id: str) -> BytesIO:
    """Build a compact but substantive human-readable audit PDF."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            KeepTogether,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except Exception as exc:  # pragma: no cover - dependency failure is handled by endpoint
        raise RuntimeError(f"PDF export dependency missing: {exc}") from exc

    enriched = dict(report)
    if not enriched.get("audit_narrative"):
        enriched["audit_narrative"] = build_audit_narrative(enriched)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=f"ORB Weaver Audit Report #{audit_id}",
        author="ORB Weaver",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="OWBody", parent=styles["BodyText"], fontSize=9.5, leading=13, spaceAfter=7))
    styles.add(ParagraphStyle(name="OWSmall", parent=styles["BodyText"], fontSize=8, leading=10.5, spaceAfter=4))
    styles.add(ParagraphStyle(name="OWIssue", parent=styles["BodyText"], fontSize=8.7, leading=11.5, spaceAfter=3))
    styles.add(ParagraphStyle(name="OWHeading", parent=styles["Heading2"], fontSize=13, leading=16, spaceBefore=8, spaceAfter=6))
    styles.add(ParagraphStyle(name="OWTitle", parent=styles["Title"], fontSize=19, leading=22, alignment=TA_LEFT, spaceAfter=10))

    story: List[Any] = []
    story.append(Paragraph(f"ORB Weaver Website Intelligence Audit #{audit_id}", styles["OWTitle"]))
    narrative = enriched.get("audit_narrative") or {}
    story.append(Paragraph(str(narrative.get("executive_summary") or "Audit evidence compiled."), styles["OWBody"]))

    scores = enriched.get("scores") or {}
    score_rows = [["Overall", "SEO", "Content", "Technical", "Performance", "Accessibility", "Mobile", "Security", "Authority", "Schema"]]
    score_rows.append([_score(scores.get(key)) for key in ("overall", "seo", "content", "technical", "performance", "accessibility", "mobile", "security", "authority", "schema")])
    table = Table(score_rows, repeatRows=1, colWidths=[0.69 * inch] * 10)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([table, Spacer(1, 8)])

    for section in narrative.get("sections") or []:
        story.append(Paragraph(str(section.get("title") or "Audit Section"), styles["OWHeading"]))
        story.append(Paragraph(str(section.get("narrative") or "No narrative evidence was recorded."), styles["OWBody"]))

    catalog = enriched.get("commercial_catalog") or {}
    entries = catalog.get("entries") or []
    story.append(Paragraph("Commercial Catalog Evidence", styles["OWHeading"]))
    if entries:
        rows = [["Name", "Type", "SKU / Model", "Price Evidence", "Availability", "Source"]]
        for entry in entries[:40]:
            offers = entry.get("offers") or []
            price_bits = []
            for offer in offers[:2]:
                currency = offer.get("currency") or ""
                price = offer.get("price") or (
                    f"{offer.get('low_price') or ''}-{offer.get('high_price') or ''}".strip("-")
                )
                if price:
                    price_bits.append(f"{currency} {price}".strip())
            rows.append([
                str(entry.get("name") or "")[:42],
                str(entry.get("kind") or "")[:20],
                str(entry.get("sku") or entry.get("gtin") or "")[:22],
                ", ".join(price_bits)[:28],
                str(entry.get("availability") or "")[:18],
                str(entry.get("source_page") or "")[:42],
            ])
        catalog_table = Table(rows, repeatRows=1, colWidths=[1.25*inch, .65*inch, .8*inch, .8*inch, .7*inch, 1.8*inch])
        catalog_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.2, colors.lightgrey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(catalog_table)
        if len(entries) > 40:
            story.append(Paragraph(f"The PDF shows the first 40 of {len(entries)} catalog entries; the full machine-readable audit retains all entries.", styles["OWSmall"]))
    else:
        story.append(Paragraph("No publishable catalog entries were confirmed in this weave.", styles["OWBody"]))

    story.append(PageBreak())
    story.append(Paragraph("Findings and Remediation", styles["OWHeading"]))
    issues = _issue_rows(enriched)
    if not issues:
        story.append(Paragraph("No audit issues were recorded.", styles["OWBody"]))
    for index, issue in enumerate(issues, start=1):
        severity = str(issue.get("severity") or issue.get("severity_bucket") or "finding").upper()
        affected = issue.get("affected_urls") or []
        source_examples = ", ".join(str(url) for url in affected[:3])
        pieces = [
            Paragraph(f"{index}. {severity}: {issue.get('title') or 'Finding'} (impact {_number(issue.get('impact_score'))})", styles["Heading3"]),
            Paragraph(str(issue.get("description") or "No description supplied."), styles["OWIssue"]),
            Paragraph(f"Recommended action: {issue.get('recommendation') or 'Review the recorded evidence and remediate the underlying condition.'}", styles["OWIssue"]),
        ]
        if affected:
            suffix = f"; examples: {source_examples}" if source_examples else ""
            pieces.append(Paragraph(f"Affected URLs: {len(affected)}{suffix}", styles["OWSmall"]))
        story.append(KeepTogether(pieces))
        story.append(Spacer(1, 5))

    planned = enriched.get("planned_tool_calls") or []
    story.append(Paragraph("ORB Assembly / Planned Tool Calls", styles["OWHeading"]))
    if planned:
        for item in planned:
            story.append(Paragraph(
                f"<b>{item.get('tool') or 'tool'}</b> — {item.get('status') or 'unknown'}; scope: {item.get('scope') or 'not specified'}",
                styles["OWSmall"],
            ))
    else:
        story.append(Paragraph("No planned ORB tool calls were recorded in this audit.", styles["OWSmall"]))

    story.append(Paragraph("Methodology and Limits", styles["OWHeading"]))
    story.append(Paragraph(
        "This PDF is a human-readable summary of persisted ORB Weaver crawl and audit evidence. Counts reflect the pages and stages actually completed in the cited crawl. "
        "A crawl limit, depth limit, robots policy, authentication boundary, failed render, unverified pointer, or missing structured commercial evidence can make a result incomplete. "
        "ORB Weaver therefore distinguishes discovered, crawled, verified, blocked, and not-started states rather than presenting incomplete evidence as complete.",
        styles["OWBody"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf
