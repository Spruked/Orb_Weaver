"""Paid customer review-package export for completed Orb Weaver projects.

Package 1 ($49) and Package 2 ($99) unlock the full customer review bundle.
The bundle is generated only from authoritative Vault/database evidence and is
stored beneath the project's canonical client Vault.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import canonical_database_url, client_root, require_vault_path
from app.models.database import (
    AuditReport,
    CheckoutOrder,
    CrawlJob,
    CrawledPage,
    Customer,
    CustomerSession,
    Project,
    get_engine,
    get_session_maker,
)
from app.orb.pointer_plot import pointer_plot_map_from_pages


router = APIRouter(tags=["customer-review-package"])

PACKAGE_PRICE_TIERS = {
    4900: "package_1",
    9900: "package_2",
}
PACKAGE_SCHEMA = "orb_weaver.customer_review_package.v1"

_DATABASE_URL = canonical_database_url(settings.DATABASE_URL)
_ENGINE = get_engine(
    _DATABASE_URL,
    **({"connect_args": {"check_same_thread": False}} if _DATABASE_URL.startswith("sqlite") else {}),
)
SessionLocal = get_session_maker(_ENGINE)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_current_customer(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Customer:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Login required")
    token_hash = _hash_token(authorization.split(" ", 1)[1].strip())
    session = db.query(CustomerSession).filter(CustomerSession.token_hash == token_hash).first()
    if not session or session.revoked_at:
        raise HTTPException(status_code=401, detail="Invalid session")
    if session.expires_at and session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired")
    customer = db.get(Customer, session.customer_id)
    if not customer or customer.status != "active":
        raise HTTPException(status_code=401, detail="Customer account unavailable")
    return customer


def _owned_project(project_id: str, customer: Customer, db: Session) -> Project:
    try:
        parsed_id = int(project_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Project not found")
    project = db.get(Project, parsed_id)
    if not project or project.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _line_item_paid_tier(line_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        unit_amount = int(line_item.get("unit_amount_cents") or 0)
        quantity = int(line_item.get("quantity") or 1)
    except (TypeError, ValueError):
        return None
    if quantity < 1 or unit_amount not in PACKAGE_PRICE_TIERS:
        return None
    return {
        "tier": PACKAGE_PRICE_TIERS[unit_amount],
        "price_cents": unit_amount,
        "sku": line_item.get("sku"),
        "name": line_item.get("name"),
    }


def _paid_review_entitlement(customer: Customer, project: Project, db: Session) -> Optional[Dict[str, Any]]:
    orders = (
        db.query(CheckoutOrder)
        .filter(
            CheckoutOrder.customer_id == customer.id,
            CheckoutOrder.payment_verified_at.isnot(None),
        )
        .order_by(CheckoutOrder.payment_verified_at.desc(), CheckoutOrder.id.desc())
        .all()
    )
    for order in orders:
        if order.project_id is not None and order.project_id != project.id:
            continue
        for item in order.line_items or []:
            if not isinstance(item, dict):
                continue
            paid_tier = _line_item_paid_tier(item)
            if paid_tier:
                return {
                    **paid_tier,
                    "checkout_order_id": str(order.id),
                    "payment_verified_at": order.payment_verified_at.isoformat() if order.payment_verified_at else None,
                }
        if int(order.amount_cents or 0) in PACKAGE_PRICE_TIERS:
            return {
                "tier": PACKAGE_PRICE_TIERS[int(order.amount_cents)],
                "price_cents": int(order.amount_cents),
                "sku": None,
                "name": None,
                "checkout_order_id": str(order.id),
                "payment_verified_at": order.payment_verified_at.isoformat() if order.payment_verified_at else None,
            }
    return None


def _page_record(page: CrawledPage) -> Dict[str, Any]:
    return {
        "url": page.url,
        "title": page.title,
        "meta_description": page.meta_description,
        "h1": page.h1,
        "h2_tags": page.h2_tags or [],
        "word_count": page.word_count,
        "status_code": page.status_code,
        "load_time_ms": page.load_time_ms,
        "canonical_url": page.canonical_url,
        "robots_meta": page.robots_meta,
        "schema_markup": page.schema_markup or [],
        "internal_links": page.internal_links,
        "external_links": page.external_links,
        "images_count": page.images_count,
        "images_without_alt": page.images_without_alt,
        "has_sitemap": page.has_sitemap,
        "has_robots_txt": page.has_robots_txt,
        "mobile_friendly": page.mobile_friendly,
        "ssl_enabled": page.ssl_enabled,
        "content_hash": page.content_hash,
        "semantic_analysis": page.semantic_analysis or {},
        "schema_analysis": page.schema_analysis or {},
        "internal_link_targets": page.internal_link_targets or [],
        "entity_analysis": page.entity_analysis or {},
        "mobile_ux_analysis": page.mobile_ux_analysis or {},
        "template_signature": page.template_signature,
        "crawl_depth": page.crawl_depth,
        "created_at": page.created_at.isoformat() if page.created_at else None,
    }


def _json_read(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not path.is_file():
        return fallback
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
    return payload if isinstance(payload, dict) else fallback


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _write_crawl_csv(path: Path, pages: Iterable[CrawledPage]) -> None:
    columns = [
        "url", "title", "meta_description", "h1", "word_count", "status_code",
        "load_time_ms", "canonical_url", "robots_meta", "internal_links",
        "external_links", "images_count", "images_without_alt", "has_sitemap",
        "has_robots_txt", "mobile_friendly", "ssl_enabled", "crawl_depth",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for page in pages:
            record = _page_record(page)
            writer.writerow({key: record.get(key) for key in columns})


def _audit_issue_rows(report_data: Dict[str, Any]) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    issues = report_data.get("issues") or {}
    for bucket, items in issues.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            rows.append({
                "severity": item.get("severity") or bucket,
                "category": item.get("category"),
                "title": item.get("title"),
                "description": item.get("description"),
                "recommendation": item.get("recommendation"),
                "impact_score": item.get("impact_score"),
                "affected_urls": " | ".join(str(value) for value in (item.get("affected_urls") or [])),
            })
    return rows


def _write_audit_csv(path: Path, report_data: Dict[str, Any]) -> None:
    columns = ["severity", "category", "title", "description", "recommendation", "impact_score", "affected_urls"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(_audit_issue_rows(report_data))


def _fallback_context(project: Project, crawl: CrawlJob, pages: list[CrawledPage]) -> Dict[str, Any]:
    return {
        "schema": "orb_weaver.website_context.review.v1",
        "generated_at": datetime.utcnow().isoformat(),
        "project": {"id": str(project.id), "name": project.name, "domain": project.domain},
        "source_crawl_id": str(crawl.id),
        "page_count": len(pages),
        "routes": [page.url for page in pages],
        "titles": [page.title for page in pages if page.title],
        "note": "Generated customer-review context because no canonical latest_context.json was available.",
    }


def _render_html_report(
    project: Project,
    crawl: CrawlJob,
    audit: AuditReport,
    pages: list[CrawledPage],
    entitlement: Dict[str, Any],
) -> str:
    report_data = audit.report_data or {}
    summary = report_data.get("summary") or {}
    scores = report_data.get("scores") or {}
    issue_rows = _audit_issue_rows(report_data)
    top_issue_rows = issue_rows[:20]

    score_cards = "".join(
        f"<div class='metric'><span>{html.escape(str(name).replace('_', ' ').title())}</span><strong>{html.escape(str(value))}</strong></div>"
        for name, value in scores.items()
    ) or "<div class='metric'><span>Audit score</span><strong>See audit.json</strong></div>"

    issues_html = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('severity') or ''))}</td>"
        f"<td>{html.escape(str(row.get('title') or ''))}</td>"
        f"<td>{html.escape(str(row.get('recommendation') or ''))}</td>"
        "</tr>"
        for row in top_issue_rows
    ) or "<tr><td colspan='3'>No audit issues were recorded.</td></tr>"

    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Orb Weaver Review — {html.escape(project.name)}</title>
<style>
body{{font-family:Inter,system-ui,sans-serif;margin:0;background:#f8fafc;color:#0f172a}}
main{{max-width:1100px;margin:0 auto;padding:40px 24px 64px}}
h1{{margin-bottom:4px}} .muted{{color:#64748b}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:24px 0}}
.metric,section{{background:white;border:1px solid #e2e8f0;border-radius:14px;padding:18px}} .metric span{{display:block;color:#64748b;font-size:13px}} .metric strong{{display:block;font-size:24px;margin-top:5px}}
table{{width:100%;border-collapse:collapse}} th,td{{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #e2e8f0}} code{{background:#e2e8f0;padding:2px 5px;border-radius:4px}}
</style>
</head>
<body><main>
<p class='muted'>Orb Weaver customer review package · {html.escape(entitlement['tier'])} · ${(int(entitlement['price_cents']) / 100):.0f} verified purchase</p>
<h1>{html.escape(project.name)}</h1>
<p class='muted'>{html.escape(project.domain)} · Crawl #{crawl.id} · Audit #{audit.id}</p>
<div class='grid'>
<div class='metric'><span>Pages crawled</span><strong>{len(pages)}</strong></div>
<div class='metric'><span>Issues found</span><strong>{html.escape(str(summary.get('total_issues', audit.issues_found or 0)))}</strong></div>
<div class='metric'><span>Critical</span><strong>{html.escape(str(summary.get('critical_count', 0)))}</strong></div>
<div class='metric'><span>Warnings</span><strong>{html.escape(str(summary.get('warning_count', audit.warnings_found or 0)))}</strong></div>
</div>
<section><h2>Scores</h2><div class='grid'>{score_cards}</div></section>
<section style='margin-top:18px'><h2>Priority findings</h2><table><thead><tr><th>Severity</th><th>Finding</th><th>Recommended action</th></tr></thead><tbody>{issues_html}</tbody></table></section>
<section style='margin-top:18px'><h2>Package contents</h2><p>This human-readable report is accompanied by raw CSV exports and structured JSON for crawl evidence, audit findings, Website ORB context, and the Pointer Plot Map. See <code>manifest.json</code> for hashes and provenance.</p></section>
</main></body></html>"""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_package(project: Project, customer: Customer, db: Session, entitlement: Dict[str, Any]) -> Dict[str, Any]:
    crawl = (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project.id, CrawlJob.status == "completed")
        .order_by(CrawlJob.id.desc())
        .first()
    )
    if not crawl:
        return {"ready": False, "reason": "completed_crawl_required"}

    audit = (
        db.query(AuditReport)
        .filter(AuditReport.project_id == project.id, AuditReport.crawl_job_id == crawl.id)
        .order_by(AuditReport.id.desc())
        .first()
        or db.query(AuditReport).filter(AuditReport.project_id == project.id).order_by(AuditReport.id.desc()).first()
    )
    if not audit or not audit.report_data:
        return {"ready": False, "reason": "completed_audit_required", "crawl_id": str(crawl.id)}

    pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl.id).order_by(CrawledPage.id.asc()).all()
    package_root = require_vault_path(
        client_root(project.domain) / "customer_review_packages" / f"crawl_{crawl.id}_audit_{audit.id}",
        "customer review package",
    )
    package_root.mkdir(parents=True, exist_ok=True)

    context_root = client_root(project.domain) / "website_orb_context"
    context_payload = _json_read(
        context_root / "latest_context.json",
        _fallback_context(project, crawl, pages),
    )
    pointer_payload = _json_read(
        context_root / "pointer_plot_map.json",
        pointer_plot_map_from_pages(pages),
    )

    crawl_payload = {
        "schema": "orb_weaver.customer_crawl_export.v1",
        "project": {"id": str(project.id), "name": project.name, "domain": project.domain},
        "crawl": {
            "id": str(crawl.id),
            "status": crawl.status,
            "pages_crawled": crawl.pages_crawled,
            "pages_found": crawl.pages_found,
            "errors_count": crawl.errors_count,
            "start_time": crawl.start_time.isoformat() if crawl.start_time else None,
            "end_time": crawl.end_time.isoformat() if crawl.end_time else None,
            "config": crawl.config or {},
        },
        "pages": [_page_record(page) for page in pages],
    }
    audit_payload = {
        "schema": "orb_weaver.customer_audit_export.v1",
        "project_id": str(project.id),
        "crawl_id": str(crawl.id),
        "audit_id": str(audit.id),
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
        "report": audit.report_data or {},
    }

    files = {
        "report.html": package_root / "report.html",
        "crawl.csv": package_root / "crawl.csv",
        "crawl.json": package_root / "crawl.json",
        "audit.csv": package_root / "audit.csv",
        "audit.json": package_root / "audit.json",
        "website_context.json": package_root / "website_context.json",
        "pointer_map.json": package_root / "pointer_map.json",
    }

    files["report.html"].write_text(
        _render_html_report(project, crawl, audit, pages, entitlement),
        encoding="utf-8",
    )
    _write_crawl_csv(files["crawl.csv"], pages)
    _write_json(files["crawl.json"], crawl_payload)
    _write_audit_csv(files["audit.csv"], audit.report_data or {})
    _write_json(files["audit.json"], audit_payload)
    _write_json(files["website_context.json"], context_payload)
    _write_json(files["pointer_map.json"], pointer_payload)

    manifest = {
        "schema": PACKAGE_SCHEMA,
        "generated_at": datetime.utcnow().isoformat(),
        "customer_id": str(customer.id),
        "project": {"id": str(project.id), "name": project.name, "domain": project.domain},
        "source": {"crawl_id": str(crawl.id), "audit_id": str(audit.id)},
        "entitlement": entitlement,
        "files": [
            {
                "name": name,
                "sha256": _file_sha256(path),
                "bytes": path.stat().st_size,
            }
            for name, path in files.items()
        ],
        "manifest_note": "manifest.json is the integrity index and therefore does not self-hash.",
    }
    manifest_path = package_root / "manifest.json"
    _write_json(manifest_path, manifest)

    zip_path = require_vault_path(package_root / f"orb-weaver-review-{project.id}.zip", "customer review package archive")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in [
            "report.html", "manifest.json", "crawl.csv", "crawl.json",
            "audit.csv", "audit.json", "website_context.json", "pointer_map.json",
        ]:
            archive.write(package_root / name, arcname=name)

    return {
        "ready": True,
        "crawl_id": str(crawl.id),
        "audit_id": str(audit.id),
        "package_dir": str(package_root),
        "archive_path": str(zip_path),
        "files": [
            "report.html", "manifest.json", "crawl.csv", "crawl.json",
            "audit.csv", "audit.json", "website_context.json", "pointer_map.json",
        ],
    }


@router.get("/api/projects/{project_id}/customer-review-package")
async def customer_review_package_status(
    project_id: str,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    project = _owned_project(project_id, customer, db)
    entitlement = _paid_review_entitlement(customer, project, db)
    if not entitlement:
        return {
            "schema": PACKAGE_SCHEMA,
            "eligible": False,
            "ready": False,
            "required_paid_packages": [
                {"tier": "package_1", "price_cents": 4900},
                {"tier": "package_2", "price_cents": 9900},
            ],
        }
    result = _build_package(project, customer, db, entitlement)
    return {
        "schema": PACKAGE_SCHEMA,
        "eligible": True,
        "entitlement": entitlement,
        **{key: value for key, value in result.items() if key != "archive_path" and key != "package_dir"},
    }


@router.get("/api/projects/{project_id}/customer-review-package/download")
async def download_customer_review_package(
    project_id: str,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    project = _owned_project(project_id, customer, db)
    entitlement = _paid_review_entitlement(customer, project, db)
    if not entitlement:
        raise HTTPException(
            status_code=403,
            detail="Full Review Package requires a verified Package 1 ($49) or Package 2 ($99) purchase.",
        )
    result = _build_package(project, customer, db, entitlement)
    if not result.get("ready"):
        raise HTTPException(status_code=409, detail=result.get("reason") or "Review package is not ready")
    archive_path = Path(str(result["archive_path"]))
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=f"orb-weaver-review-{project.domain}.zip",
    )