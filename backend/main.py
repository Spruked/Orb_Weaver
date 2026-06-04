import csv
import hashlib
import io
import json
import re
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.analytics.ga4 import GA4Connector
from app.audit.engine import SEOAuditor
from app.core.config import settings
from app.crawler.engine import OrbWeaverCrawler, PageData
from app.models.database import (
    AuditReport,
    CrawlJob,
    CrawledPage,
    Customer,
    CustomerSession,
    Project,
    get_engine,
    get_session_maker,
    init_db,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORT_COMPILER_DIR = BASE_DIR / "report_compiler"
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORT_COMPILER_DIR.mkdir(parents=True, exist_ok=True)


def resolve_database_url() -> str:
    configured = settings.DATABASE_URL.strip()
    if not configured or configured == "postgresql://user:pass@localhost/orb_weaver":
        return "sqlite:///./data/orb_weaver.db"
    return configured


def build_engine():
    database_url = resolve_database_url()
    if database_url.startswith("sqlite"):
        return get_engine(database_url, connect_args={"check_same_thread": False})
    return get_engine(database_url)


engine = build_engine()
SessionLocal = get_session_maker(engine)
init_db(engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Website ORB intelligence engine with crawling, semantic analysis, and local-first reporting",
    version=settings.VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProjectCreate(BaseModel):
    name: Optional[str] = None
    domain: str
    ga4_property_id: Optional[str] = None


class CrawlConfig(BaseModel):
    max_pages: int = Field(default=100, ge=1, le=5000)
    delay: float = Field(default=1.0, ge=0.1, le=10.0)
    max_depth: int = Field(default=5, ge=1, le=10)
    competitor_domains: List[str] = Field(default_factory=list)


class GA4Config(BaseModel):
    property_id: str
    credentials_path: Optional[str] = None
    days: int = Field(default=30, ge=1, le=365)


class CustomerSignup(BaseModel):
    email: str
    password: str = Field(min_length=8)
    business_name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None


class CustomerLogin(BaseModel):
    email: str
    password: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), password_salt.encode("utf-8"), 120000)
    return f"pbkdf2_sha256${password_salt}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, digest = stored_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    return secrets.compare_digest(_hash_password(password, salt), stored_hash)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _serialize_customer(customer: Customer) -> Dict:
    return {
        "id": str(customer.id),
        "email": customer.email,
        "business_name": customer.business_name,
        "contact_name": customer.contact_name,
        "phone": customer.phone,
        "status": customer.status,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
    }


def _issue_customer_session(customer: Customer, db: Session) -> Dict:
    token = secrets.token_urlsafe(32)
    session = CustomerSession(
        customer_id=customer.id,
        token_hash=_hash_token(token),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    customer.last_login_at = datetime.utcnow()
    db.add(session)
    db.commit()
    return {"token": token, "customer": _serialize_customer(customer)}


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
    project = db.get(Project, int(project_id))
    if not project or project.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _owned_crawl_job(job_id: str, customer: Customer, db: Session) -> CrawlJob:
    job = db.get(CrawlJob, int(job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Crawl job not found")
    _owned_project(str(job.project_id), customer, db)
    return job


def _owned_audit_report(audit_id: str, customer: Customer, db: Session) -> AuditReport:
    report = db.get(AuditReport, int(audit_id))
    if not report:
        raise HTTPException(status_code=404, detail="Audit report not found")
    _owned_project(str(report.project_id), customer, db)
    return report


def normalize_domain(domain: str) -> str:
    return domain.strip().replace("http://", "").replace("https://", "").rstrip("/")


def default_project_name(domain: str) -> str:
    root = normalize_domain(domain)
    root = re.sub(r"^www\.", "", root)
    base = root.split("/")[0].split(":")[0]
    pieces = [p for p in re.split(r"[-_.]", base) if p]
    if not pieces:
        return root or "New Client"
    return " ".join(piece.capitalize() for piece in pieces)


def safe_folder_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9 _.-]", "", name).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "client"


def project_report_dir(project: Project) -> Path:
    folder = REPORT_COMPILER_DIR / f"{project.id}_{safe_folder_name(project.name)}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_report_compiler_snapshot(project: Project, payload: Dict, prefix: str) -> None:
    report_dir = project_report_dir(project)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out = report_dir / f"{prefix}_{stamp}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest = report_dir / f"{prefix}_latest.json"
    latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def page_to_dict(page: CrawledPage) -> Dict:
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
        "ssl_enabled": page.ssl_enabled,
        "content_hash": page.content_hash,
        "is_indexable": page.robots_meta != "noindex",
        "has_sitemap": page.has_sitemap,
        "has_robots_txt": page.has_robots_txt,
        "mobile_viewport": bool(page.mobile_friendly),
        "duplicate_content_risk": False,
        "open_graph": {},
        "twitter_cards": {},
        "heading_structure": [],
        "redirect_chain": [],
    }


def crawl_stats_from_pages(pages: List[CrawledPage]) -> Dict:
    total = len(pages)
    load_times = [p.load_time_ms for p in pages if p.load_time_ms is not None]
    return {
        "total_pages": total,
        "visited_urls": total,
        "sitemap_urls_found": 0,
        "has_robots_txt": any(p.has_robots_txt for p in pages),
        "has_sitemap": any(p.has_sitemap for p in pages),
        "avg_load_time": (sum(load_times) / len(load_times)) if load_times else 0,
        "ssl_pages": sum(1 for p in pages if p.ssl_enabled),
        "indexable_pages": sum(1 for p in pages if p.robots_meta != "noindex"),
        "duplicate_content_pages": 0,
        "total_images": sum(p.images_count or 0 for p in pages),
        "images_missing_alt": sum(p.images_without_alt or 0 for p in pages),
        "total_internal_links": sum(p.internal_links or 0 for p in pages),
        "total_external_links": sum(p.external_links or 0 for p in pages),
    }


def crawl_job_to_dict(job: CrawlJob, pages: Optional[List[CrawledPage]] = None) -> Dict:
    page_rows = pages if pages is not None else list(job.pages)
    stats = crawl_stats_from_pages(page_rows)
    payload = {
        "id": str(job.id),
        "project_id": str(job.project_id),
        "status": job.status,
        "config": job.config or {},
        "created_at": job.start_time.isoformat() if job.start_time else None,
        "start_time": job.start_time.isoformat() if job.start_time else None,
        "end_time": job.end_time.isoformat() if job.end_time else None,
        "pages_crawled": job.pages_crawled,
        "pages_found": job.pages_found,
        "errors_count": job.errors_count,
        "stats": stats,
    }
    error_message = (job.config or {}).get("error")
    if error_message:
        payload["error"] = error_message
    return payload


def project_to_dict(project: Project, db: Session) -> Dict:
    latest_crawl = (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project.id)
        .order_by(CrawlJob.id.desc())
        .first()
    )
    latest_audit = (
        db.query(AuditReport)
        .filter(AuditReport.project_id == project.id)
        .order_by(AuditReport.id.desc())
        .first()
    )
    return {
        "id": str(project.id),
        "name": project.name,
        "domain": project.domain,
        "ga4_property_id": project.ga4_property_id,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "latest_crawl_id": str(latest_crawl.id) if latest_crawl else None,
        "latest_crawl_status": latest_crawl.status if latest_crawl else "never_crawled",
        "latest_audit_id": str(latest_audit.id) if latest_audit else None,
        "folder_title": project.name,
    }


async def run_crawl_job(crawl_job_id: int, config: Dict):
    db = SessionLocal()
    try:
        crawl_job = db.get(CrawlJob, crawl_job_id)
        if not crawl_job:
            return
        project = db.get(Project, crawl_job.project_id)
        if not project:
            crawl_job.status = "failed"
            crawl_job.config = {**(crawl_job.config or {}), "error": "Project not found"}
            db.commit()
            return

        crawl_job.status = "running"
        crawl_job.start_time = datetime.utcnow()
        db.commit()

        crawler = OrbWeaverCrawler(
            max_pages=config.get("max_pages", 100),
            delay=config.get("delay", 1.0),
            max_depth=config.get("max_depth", 5),
        )

        start_url = f"https://{project.domain}" if not project.domain.startswith("http") else project.domain
        pages = await crawler.crawl(start_url)
        stats = crawler.get_crawl_stats()

        db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job.id).delete()
        for page in pages:
            db.add(
                CrawledPage(
                    crawl_job_id=crawl_job.id,
                    url=page.url,
                    title=page.title,
                    meta_description=page.meta_description,
                    h1=page.h1,
                    h2_tags=page.h2_tags,
                    word_count=page.word_count,
                    status_code=page.status_code,
                    load_time_ms=page.load_time_ms,
                    canonical_url=page.canonical_url,
                    robots_meta=page.robots_meta,
                    schema_markup=page.schema_markup,
                    internal_links=page.internal_links,
                    external_links=page.external_links,
                    images_count=page.images_count,
                    images_without_alt=page.images_without_alt,
                    has_sitemap=page.has_sitemap,
                    has_robots_txt=page.has_robots_txt,
                    mobile_friendly=page.mobile_viewport,
                    ssl_enabled=page.ssl_enabled,
                    content_hash=page.content_hash,
                )
            )

        crawl_job.status = "completed"
        crawl_job.end_time = datetime.utcnow()
        crawl_job.pages_crawled = len(pages)
        crawl_job.pages_found = int(stats.get("visited_urls", len(pages)))
        crawl_job.errors_count = 0
        crawl_job.config = {**(crawl_job.config or {}), "stats": stats}
        db.commit()

        write_report_compiler_snapshot(
            project,
            {
                "project_id": project.id,
                "crawl_job_id": crawl_job.id,
                "created_at": datetime.utcnow().isoformat(),
                "stats": stats,
                "pages": [p.to_dict() for p in pages],
            },
            "crawl_report",
        )
    except Exception as exc:
        crawl_job = db.get(CrawlJob, crawl_job_id)
        if crawl_job:
            crawl_job.status = "failed"
            crawl_job.end_time = datetime.utcnow()
            crawl_job.config = {**(crawl_job.config or {}), "error": str(exc)}
            db.commit()
    finally:
        db.close()


async def run_audit_job(audit_id: int, crawl_job_id: int):
    db = SessionLocal()
    try:
        crawl_job = db.get(CrawlJob, crawl_job_id)
        audit = db.get(AuditReport, audit_id)
        if not crawl_job or not audit or crawl_job.status != "completed":
            return

        page_rows = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job.id).all()
        pages = [PageData(**page_to_dict(page)) for page in page_rows]
        stats = crawl_stats_from_pages(page_rows)

        auditor = SEOAuditor()
        report = auditor.audit(pages, stats)

        audit.report_data = report
        audit.overall_score = report["scores"].get("overall")
        audit.seo_score = report["scores"].get("seo")
        audit.performance_score = report["scores"].get("performance")
        audit.accessibility_score = report["scores"].get("accessibility")
        audit.content_score = report["scores"].get("content")
        audit.technical_score = report["scores"].get("technical")
        audit.issues_found = report["summary"].get("critical_count", 0)
        audit.warnings_found = report["summary"].get("warning_count", 0)
        audit.opportunities_found = report["summary"].get("opportunity_count", 0)
        db.commit()

        project = db.get(Project, crawl_job.project_id)
        if project:
            write_report_compiler_snapshot(
                project,
                {
                    "project_id": project.id,
                    "crawl_job_id": crawl_job.id,
                    "audit_id": audit.id,
                    "created_at": datetime.utcnow().isoformat(),
                    "report": report,
                },
                "compiled_report",
            )
    finally:
        db.close()


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "operational",
    }


@app.post("/api/projects")
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    domain = normalize_domain(project.domain)
    name = (project.name or "").strip() or default_project_name(domain)

    existing = db.query(Project).filter(Project.domain == domain).first()
    if existing:
        existing.name = name
        existing.ga4_property_id = project.ga4_property_id
        db.commit()
        db.refresh(existing)
        return project_to_dict(existing, db)

    row = Project(name=name, domain=domain, ga4_property_id=project.ga4_property_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    project_report_dir(row)
    return project_to_dict(row, db)


@app.get("/api/projects")
async def list_projects(db: Session = Depends(get_db)):
    rows = db.query(Project).order_by(Project.id.asc()).all()
    return [project_to_dict(row, db) for row in rows]


@app.get("/api/projects/{project_id}")
async def get_project(project_id: int, db: Session = Depends(get_db)):
    row = db.get(Project, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_to_dict(row, db)


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    row = db.get(Project, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    crawl_ids = [job.id for job in db.query(CrawlJob).filter(CrawlJob.project_id == project_id).all()]
    if crawl_ids:
        db.query(CrawledPage).filter(CrawledPage.crawl_job_id.in_(crawl_ids)).delete(synchronize_session=False)
        db.query(CrawlJob).filter(CrawlJob.id.in_(crawl_ids)).delete(synchronize_session=False)
    db.query(AuditReport).filter(AuditReport.project_id == project_id).delete(synchronize_session=False)
    db.delete(row)
    db.commit()
    return {"status": "deleted", "project_id": str(project_id)}


@app.post("/api/projects/{project_id}/crawl")
async def start_crawl(
    project_id: int,
    config: CrawlConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = CrawlJob(
        project_id=project_id,
        status="pending",
        config=config.model_dump(),
        start_time=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_crawl_job, job.id, config.model_dump())
    return crawl_job_to_dict(job, [])


@app.get("/api/crawl-jobs/{job_id}")
async def get_crawl_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(CrawlJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Crawl job not found")
    pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == job.id).all()
    return crawl_job_to_dict(job, pages)


@app.get("/api/crawl-jobs/{job_id}/pages")
async def get_crawl_pages(
    job_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    job = db.get(CrawlJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Crawl job not found")

    query = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == job_id)
    total = query.count()
    pages = query.offset(skip).limit(limit).all()
    return {"total": total, "pages": [page_to_dict(page) for page in pages]}


@app.get("/api/crawl-jobs/{job_id}/export/csv")
async def export_crawl_csv(job_id: int, db: Session = Depends(get_db)):
    rows = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == job_id).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No crawled pages found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "url",
        "title",
        "status_code",
        "load_time_ms",
        "word_count",
        "internal_links",
        "external_links",
        "images_count",
        "images_without_alt",
        "ssl_enabled",
        "schema_count",
        "schema_errors",
        "semantic_depth",
        "internal_link_edges",
        "orb_semantic_score",
        "entity_count",
        "mobile_ux_score",
        "template_signature",
        "crawl_depth",
    ])
    for page in rows:
        writer.writerow([
            page.url,
            page.title or "",
            page.status_code or "",
            page.load_time_ms or "",
            page.word_count or 0,
            page.internal_links or 0,
            page.external_links or 0,
            page.images_count or 0,
            page.images_without_alt or 0,
            page.ssl_enabled,
            len(page.schema_markup or []),
            (page.schema_analysis or {}).get("invalid_count", 0),
            (page.semantic_analysis or {}).get("semantic_depth", ""),
            len(page.internal_link_targets or []),
            (page.semantic_analysis or {}).get("orb_semantic_score", {}).get("overall", ""),
            len((page.entity_analysis or {}).get("named_entities", [])),
            (page.mobile_ux_analysis or {}).get("score", ""),
            page.template_signature or "",
            page.crawl_depth or 0,
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=crawl_job_{job_id}.csv"},
    )


@app.post("/api/crawl-jobs/{job_id}/audit")
async def run_audit(job_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.get(CrawlJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Crawl job not found")

    audit = AuditReport(project_id=job.project_id, crawl_job_id=job.id, report_data={})
    db.add(audit)
    db.commit()
    db.refresh(audit)

    background_tasks.add_task(run_audit_job, audit.id, job.id)
    return {"audit_id": str(audit.id), "status": "started", "message": "Audit is running in background"}


@app.get("/api/audit-reports/{audit_id}")
async def get_audit_report(audit_id: int, db: Session = Depends(get_db)):
    report = db.get(AuditReport, audit_id)
    if not report:
        raise HTTPException(status_code=404, detail="Audit report not found")
    if not report.report_data:
        raise HTTPException(status_code=404, detail="Audit report not ready")

    return {
        "id": str(report.id),
        "crawl_job_id": str(report.crawl_job_id),
        "created_at": report.created_at.isoformat() if report.created_at else datetime.utcnow().isoformat(),
        "report": report.report_data,
    }


@app.get("/api/audit-reports/{audit_id}/export/csv")
async def export_audit_csv(audit_id: int, db: Session = Depends(get_db)):
    report = db.get(AuditReport, audit_id)
    if not report or not report.report_data:
        raise HTTPException(status_code=404, detail="Audit report not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["severity", "category", "title", "description", "impact_score", "recommendation"])
    for bucket in ("critical", "warnings", "opportunities"):
        for issue in report.report_data.get("issues", {}).get(bucket, []):
            writer.writerow([
                issue.get("severity", ""),
                issue.get("category", ""),
                issue.get("title", ""),
                issue.get("description", ""),
                issue.get("impact_score", ""),
                issue.get("recommendation", ""),
            ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_report_{audit_id}.csv"},
    )


@app.get("/api/audit-reports/{audit_id}/export/pdf")
async def export_audit_pdf(audit_id: int, db: Session = Depends(get_db)):
    report = db.get(AuditReport, audit_id)
    if not report or not report.report_data:
        raise HTTPException(status_code=404, detail="Audit report not found")

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF export dependency missing: {exc}")

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 50
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, f"SEO Audit Report #{audit_id}")
    y -= 30

    scores = report.report_data.get("scores", {})
    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, y, f"Overall Score: {scores.get('overall', '-')}")
    y -= 20

    summary = report.report_data.get("summary", {})
    pdf.drawString(40, y, f"Critical: {summary.get('critical_count', 0)}")
    y -= 16
    pdf.drawString(40, y, f"Warnings: {summary.get('warning_count', 0)}")
    y -= 16
    pdf.drawString(40, y, f"Opportunities: {summary.get('opportunity_count', 0)}")
    y -= 26

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, "Top Issues")
    y -= 20

    pdf.setFont("Helvetica", 10)
    for issue in report.report_data.get("top_issues", [])[:10]:
        title = (issue.get("title") or "")[:90]
        recommendation = (issue.get("recommendation") or "")[:95]
        pdf.drawString(44, y, f"- {title}")
        y -= 14
        pdf.drawString(52, y, f"Fix: {recommendation}")
        y -= 18
        if y < 60:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 10)

    pdf.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=audit_report_{audit_id}.pdf"},
    )


@app.get("/api/projects/{project_id}/report-compiler")
async def get_report_compiler(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    latest_crawl = (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project_id, CrawlJob.status == "completed")
        .order_by(CrawlJob.id.desc())
        .first()
    )
    latest_audit = (
        db.query(AuditReport)
        .filter(AuditReport.project_id == project_id)
        .order_by(AuditReport.id.desc())
        .first()
    )
    directory = project_report_dir(project)

    return {
        "project": project_to_dict(project, db),
        "latest_crawl": crawl_job_to_dict(latest_crawl, list(latest_crawl.pages)) if latest_crawl else None,
        "latest_audit": {
            "id": str(latest_audit.id),
            "report": latest_audit.report_data,
            "created_at": latest_audit.created_at.isoformat() if latest_audit.created_at else None,
        }
        if latest_audit and latest_audit.report_data
        else None,
        "files": [f.name for f in sorted(directory.glob("*.json"), reverse=True)],
    }


@app.post("/api/projects/{project_id}/recrawl")
async def recrawl_project(project_id: int, config: CrawlConfig, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return await start_crawl(project_id, config, background_tasks, db)


@app.post("/api/projects/{project_id}/reaudit")
async def reaudit_project(project_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    latest_crawl = (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project_id, CrawlJob.status == "completed")
        .order_by(CrawlJob.id.desc())
        .first()
    )
    if not latest_crawl:
        raise HTTPException(status_code=400, detail="No completed crawl found for this project")
    return await run_audit(latest_crawl.id, background_tasks, db)


@app.get("/api/combined/{project_id}/dashboard")
async def get_combined_dashboard(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    latest_crawl = (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project_id, CrawlJob.status == "completed")
        .order_by(CrawlJob.id.desc())
        .first()
    )
    latest_audit = (
        db.query(AuditReport)
        .filter(AuditReport.project_id == project_id)
        .order_by(AuditReport.id.desc())
        .first()
    )

    pages = list(latest_crawl.pages) if latest_crawl else []
    crawl_summary = crawl_stats_from_pages(pages) if latest_crawl else None

    ga4_data = None
    if project.ga4_property_id:
        try:
            connector = GA4Connector(property_id=project.ga4_property_id)
            ga4_data = connector.get_full_report(days=30)
        except Exception:
            ga4_data = None

    return {
        "project": project_to_dict(project, db),
        "crawl_summary": crawl_summary,
        "audit_scores": latest_audit.report_data.get("scores") if latest_audit and latest_audit.report_data else None,
        "audit_issues": latest_audit.report_data.get("summary") if latest_audit and latest_audit.report_data else None,
        "ga4_data": ga4_data,
        "top_issues": latest_audit.report_data.get("top_issues") if latest_audit and latest_audit.report_data else None,
    }


@app.post("/api/ga4/connect")
async def connect_ga4(config: GA4Config):
    try:
        connector = GA4Connector(property_id=config.property_id, credentials_path=config.credentials_path)
        overview = connector.get_traffic_overview(daysAgo="7daysAgo", end_date="today")
        return {"status": "connected", "property_id": config.property_id, "test_data": overview["totals"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"GA4 connection failed: {str(e)}")


@app.get("/api/ga4/{property_id}/overview")
async def get_ga4_overview(property_id: str, days: int = Query(30, ge=1, le=365)):
    try:
        connector = GA4Connector(property_id=property_id)
        return connector.get_full_report(days=days)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ga4/{property_id}/top-pages")
async def get_ga4_top_pages(property_id: str, days: int = Query(30, ge=1, le=365), limit: int = Query(50, ge=1, le=100)):
    try:
        connector = GA4Connector(property_id=property_id)
        start_date = (datetime.now() - __import__("datetime").timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        pages = connector.get_top_pages(start_date, end_date, limit)
        return {"pages": pages}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ga4/{property_id}/search-queries")
async def get_ga4_search_queries(property_id: str, days: int = Query(30, ge=1, le=365), limit: int = Query(100, ge=1, le=500)):
    try:
        connector = GA4Connector(property_id=property_id)
        start_date = (datetime.now() - __import__("datetime").timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        queries = connector.get_search_queries(start_date, end_date, limit)
        return {"queries": queries}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ga4/{property_id}/devices")
async def get_ga4_devices(property_id: str, days: int = Query(30, ge=1, le=365)):
    try:
        connector = GA4Connector(property_id=property_id)
        start_date = (datetime.now() - __import__("datetime").timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        devices = connector.get_device_breakdown(start_date, end_date)
        return {"devices": devices}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
from datetime import datetime, timedelta
from io import BytesIO, StringIO
import csv
import hashlib
import re
import secrets
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.analytics.ga4 import GA4Connector
from app.audit.engine import SEOAuditor
from app.core.config import settings
from app.crawler.engine import OrbWeaverCrawler, PageData
from app.models.database import (
    AuditReport,
    CrawlJob,
    CrawledPage,
    Customer,
    CustomerSession,
    Project,
    get_engine,
    get_session_maker,
    init_db,
)


app = FastAPI(
    title=settings.APP_NAME,
    description="Website ORB intelligence engine with crawling, semantic analysis, and local-first reporting",
    version=settings.VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_database_url() -> str:
    if settings.DATABASE_URL.strip() == "postgresql://user:pass@localhost/orb_weaver":
        return "sqlite:///./data/orb_weaver.db"
    return settings.DATABASE_URL


def _engine_kwargs(database_url: str) -> Dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


DATABASE_URL = _resolve_database_url()
if DATABASE_URL.startswith("sqlite"):
    Path("data").mkdir(parents=True, exist_ok=True)

ENGINE = get_engine(DATABASE_URL, **_engine_kwargs(DATABASE_URL))
SessionLocal = get_session_maker(ENGINE)
init_db(ENGINE)

REPORT_COMPILER_ROOT = Path("report_compiler")
REPORT_COMPILER_ROOT.mkdir(parents=True, exist_ok=True)

SUBSTRATE_ROOT = Path(settings.ORB_WEAVER_SUBSTRATE_ROOT)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ProjectCreate(BaseModel):
    name: Optional[str] = None
    domain: str
    ga4_property_id: Optional[str] = None


class CrawlConfig(BaseModel):
    max_pages: int = Field(default=100, ge=1, le=5000)
    delay: float = Field(default=1.0, ge=0.1, le=10.0)
    max_depth: int = Field(default=5, ge=1, le=10)
    competitor_domains: List[str] = Field(default_factory=list)


class GA4Config(BaseModel):
    property_id: str
    credentials_path: Optional[str] = None
    days: int = Field(default=30, ge=1, le=365)


class CustomerSignup(BaseModel):
    email: str
    password: str = Field(min_length=8)
    business_name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None


class CustomerLogin(BaseModel):
    email: str
    password: str


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), password_salt.encode("utf-8"), 120000)
    return f"pbkdf2_sha256${password_salt}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, _digest = stored_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    return secrets.compare_digest(_hash_password(password, salt), stored_hash)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _serialize_customer(customer: Customer) -> Dict:
    return {
        "id": str(customer.id),
        "email": customer.email,
        "business_name": customer.business_name,
        "contact_name": customer.contact_name,
        "phone": customer.phone,
        "status": customer.status,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
    }


def _issue_customer_session(customer: Customer, db: Session) -> Dict:
    token = secrets.token_urlsafe(32)
    db.add(
        CustomerSession(
            customer_id=customer.id,
            token_hash=_hash_token(token),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
    )
    customer.last_login_at = datetime.utcnow()
    db.commit()
    return {"token": token, "customer": _serialize_customer(customer)}


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
    project = db.get(Project, int(project_id))
    if not project or project.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _normalize_domain(raw_domain: str) -> str:
    return raw_domain.strip().replace("http://", "").replace("https://", "").rstrip("/")


def _default_project_name(domain: str) -> str:
    parts = [p for p in domain.split(".") if p and p not in {"www", "com", "net", "org", "io", "co"}]
    if not parts:
        return domain
    return " ".join([p.replace("-", " ").capitalize() for p in parts[:2]])


def _serialize_project(project: Project, db: Session) -> Dict:
    latest_crawl = (
        db.query(CrawlJob).filter(CrawlJob.project_id == project.id).order_by(CrawlJob.id.desc()).first()
    )
    latest_audit = (
        db.query(AuditReport).filter(AuditReport.project_id == project.id).order_by(AuditReport.id.desc()).first()
    )

    return {
        "id": str(project.id),
        "name": project.name,
        "domain": project.domain,
        "ga4_property_id": project.ga4_property_id,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "latest_crawl_id": str(latest_crawl.id) if latest_crawl else None,
        "latest_crawl_status": latest_crawl.status if latest_crawl else "never_crawled",
        "latest_pages_crawled": latest_crawl.pages_crawled if latest_crawl else None,
        "latest_audit_id": str(latest_audit.id) if latest_audit else None,
        "latest_audit_score": latest_audit.overall_score if latest_audit else None,
    }


def _project_report_dir(project: Project) -> Path:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", project.name.strip().lower()) or f"project_{project.id}"
    folder = REPORT_COMPILER_ROOT / f"{project.id}_{slug}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _safe_pack_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip().lower())
    return cleaned.strip("._-") or "unknown_site"


def _client_intelligence_root(project: Project) -> Path:
    return SUBSTRATE_ROOT / "clients" / _safe_pack_name(project.domain)


def _global_intelligence_root() -> Path:
    return SUBSTRATE_ROOT / "global_intelligence"


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _append_jsonl(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _ensure_client_pack(project: Project) -> Path:
    root = _client_intelligence_root(project)
    for name in (
        "current",
        "history",
        "recommendations",
        "website_orb_context",
        "dandy_sponsor_pack",
        "crm_context",
        "mail_context",
        "claims",
        "local_index",
        "reports",
        "visitor_questions",
        "owner_seed_changes",
        "approved_claims",
        "banned_claims",
        "dandy_packs",
    ):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def _client_index_path(project: Project) -> Path:
    return _client_intelligence_root(project) / "local_index" / "client_index.sqlite"


def _init_client_index(index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(index_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS pack_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS crawl_snapshots (
                crawl_id TEXT PRIMARY KEY,
                saved_at TEXT NOT NULL,
                status TEXT,
                total_pages INTEGER,
                avg_orb_semantic_score REAL,
                avg_mobile_ux_score REAL,
                avg_load_time REAL,
                json_path TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_snapshots (
                audit_id TEXT PRIMARY KEY,
                crawl_id TEXT,
                saved_at TEXT NOT NULL,
                overall_score REAL,
                total_issues INTEGER,
                critical_count INTEGER,
                warning_count INTEGER,
                opportunity_count INTEGER,
                json_path TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recommendation_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id TEXT NOT NULL,
                severity TEXT,
                category TEXT,
                title TEXT,
                impact_score INTEGER,
                status TEXT DEFAULT 'generated',
                json_path TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS context_documents (
                key TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                json_path TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )


def _index_pack_meta(project: Project, root: Path) -> None:
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(_client_index_path(project)) as connection:
        rows = {
            "pack_contract": "orb_weaver.client_pack.v0.1",
            "domain": project.domain,
            "project_id": str(project.id),
            "customer_id": str(project.customer_id) if project.customer_id else "",
            "root": str(root),
        }
        connection.executemany(
            "INSERT OR REPLACE INTO pack_meta(key, value, updated_at) VALUES (?, ?, ?)",
            [(key, value, now) for key, value in rows.items()],
        )


def _index_crawl_pack(project: Project, crawl_job: CrawlJob, payload: Dict, json_path: Path) -> None:
    stats = payload.get("crawl", {}).get("stats") or {}
    with sqlite3.connect(_client_index_path(project)) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO crawl_snapshots(
                crawl_id, saved_at, status, total_pages, avg_orb_semantic_score,
                avg_mobile_ux_score, avg_load_time, json_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(crawl_job.id),
                payload.get("saved_at"),
                crawl_job.status,
                int(stats.get("total_pages", 0) or 0),
                float(stats.get("avg_orb_semantic_score", 0) or 0),
                float(stats.get("avg_mobile_ux_score", 0) or 0),
                float(stats.get("avg_load_time", 0) or 0),
                str(json_path),
            ),
        )
        connection.execute(
            "INSERT OR REPLACE INTO context_documents(key, kind, json_path, updated_at) VALUES (?, ?, ?, ?)",
            ("latest_context", "website_orb_context", str(_client_intelligence_root(project) / "website_orb_context" / "latest_context.json"), payload.get("saved_at")),
        )


def _index_audit_pack(project: Project, audit: AuditReport, payload: Dict, json_path: Path, recommendations_path: Path) -> None:
    report = payload.get("audit", {}).get("report") or {}
    scores = report.get("scores") or {}
    summary = report.get("summary") or {}
    with sqlite3.connect(_client_index_path(project)) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO audit_snapshots(
                audit_id, crawl_id, saved_at, overall_score, total_issues,
                critical_count, warning_count, opportunity_count, json_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(audit.id),
                str(audit.crawl_job_id) if audit.crawl_job_id else None,
                payload.get("saved_at"),
                float(scores.get("overall", 0) or 0),
                int(summary.get("total_issues", 0) or 0),
                int(summary.get("critical_count", 0) or 0),
                int(summary.get("warning_count", 0) or 0),
                int(summary.get("opportunity_count", 0) or 0),
                str(json_path),
            ),
        )
        connection.execute("DELETE FROM recommendation_index WHERE audit_id = ?", (str(audit.id),))
        connection.executemany(
            """
            INSERT INTO recommendation_index(audit_id, severity, category, title, impact_score, json_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    str(audit.id),
                    item.get("severity"),
                    item.get("category"),
                    item.get("title"),
                    int(item.get("impact_score", 0) or 0),
                    str(recommendations_path),
                )
                for item in payload.get("recommendations", [])
            ],
        )


def _bucket_count(value: int) -> str:
    if value <= 1:
        return "1"
    if value <= 5:
        return "2-5"
    if value <= 25:
        return "6-25"
    if value <= 100:
        return "26-100"
    return "100+"


def _client_crawl_pack(project: Project, crawl_job: CrawlJob, pages: List[CrawledPage], db: Session) -> Dict:
    crawl_payload = _serialize_crawl_job(crawl_job, db, include_pages=True)
    return {
        "schema": "orb_weaver.client_crawl.v1",
        "saved_at": datetime.utcnow().isoformat(),
        "client": {
            "project_id": str(project.id),
            "domain": project.domain,
            "name": project.name,
            "customer_id": str(project.customer_id) if project.customer_id else None,
        },
        "site_profile": {
            "domain": project.domain,
            "latest_crawl_id": str(crawl_job.id),
            "page_count": len(pages),
            "has_ga4": bool(project.ga4_property_id),
        },
        "crawl": crawl_payload,
        "website_orb_context": {
            "orb_ready_score": crawl_payload.get("stats", {}).get("avg_orb_semantic_score", 0),
            "authority_flow": crawl_payload.get("authority_flow"),
            "knowledge_graph": crawl_payload.get("knowledge_graph"),
            "competitor_gap": crawl_payload.get("competitor_gap"),
            "template_detection": crawl_payload.get("template_detection"),
        },
    }


def _client_audit_pack(project: Project, crawl_job: CrawlJob, audit: AuditReport, db: Session) -> Dict:
    return {
        "schema": "orb_weaver.client_audit.v1",
        "saved_at": datetime.utcnow().isoformat(),
        "client": {
            "project_id": str(project.id),
            "domain": project.domain,
            "name": project.name,
            "customer_id": str(project.customer_id) if project.customer_id else None,
        },
        "crawl": _serialize_crawl_job(crawl_job, db, include_pages=False),
        "audit": _serialize_audit_report(audit),
        "recommendations": (audit.report_data or {}).get("top_issues", []),
        "safe_claims": [],
        "banned_claims": [],
        "customer_memory_eligibility": {
            "eligible": bool(audit.report_data),
            "reason": "audit_complete" if audit.report_data else "audit_not_ready",
        },
    }


def _global_crawl_pattern(project: Project, crawl_job: CrawlJob, stats: Dict, config: Dict) -> Dict:
    template_detection = config.get("template_detection") or {}
    competitor_gap = config.get("competitor_gap") or {}
    return {
        "schema": "orb_weaver.global_crawl_pattern.v1",
        "event": "crawl_completed",
        "saved_at": datetime.utcnow().isoformat(),
        "page_count_bucket": _bucket_count(int(stats.get("total_pages", 0) or 0)),
        "has_ga4": bool(project.ga4_property_id),
        "metric_buckets": {
            "avg_load_time_ms": round(float(stats.get("avg_load_time", 0) or 0), 2),
            "avg_orb_semantic_score": round(float(stats.get("avg_orb_semantic_score", 0) or 0), 2),
            "avg_mobile_ux_score": round(float(stats.get("avg_mobile_ux_score", 0) or 0), 2),
            "schema_pages": int(stats.get("schema_pages", 0) or 0),
            "low_orb_semantic_pages": int(stats.get("low_orb_semantic_pages", 0) or 0),
            "mobile_ux_problem_pages": int(stats.get("mobile_ux_problem_pages", 0) or 0),
        },
        "patterns": {
            "missing_questions": bool((competitor_gap.get("missing_questions") or [])),
            "missing_schema_types_count": len(competitor_gap.get("missing_schema_types") or []),
            "missing_internal_link_hubs_count": len(competitor_gap.get("missing_internal_link_hubs") or []),
            "repeated_layout_count": len(template_detection.get("repeated_layouts") or []),
            "duplicated_title_count": len(template_detection.get("duplicated_titles") or []),
            "duplicated_meta_description_count": len(template_detection.get("duplicated_meta_descriptions") or []),
        },
    }


def _global_audit_pattern(audit: AuditReport) -> Dict:
    report = audit.report_data or {}
    issues = report.get("issues") or {}
    category_counts: Dict[str, int] = {}
    recommendation_patterns = []
    for bucket, rows in issues.items():
        for issue in rows or []:
            category = issue.get("category") or "uncategorized"
            category_counts[category] = category_counts.get(category, 0) + 1
            recommendation_patterns.append({
                "severity": bucket,
                "category": category,
                "impact_bucket": _bucket_count(int(issue.get("impact_score", 0) or 0)),
                "title_pattern": issue.get("title", ""),
            })
    return {
        "schema": "orb_weaver.global_audit_pattern.v1",
        "event": "audit_completed",
        "saved_at": datetime.utcnow().isoformat(),
        "score_bucket": _bucket_count(int((report.get("scores") or {}).get("overall", 0) or 0)),
        "summary": report.get("summary") or {},
        "category_counts": category_counts,
        "recommendation_patterns": recommendation_patterns[:25],
    }


def preserve_client_crawl_intelligence(project: Project, crawl_job: CrawlJob, pages: List[CrawledPage], db: Session) -> None:
    try:
        root = _ensure_client_pack(project)
        _init_client_index(_client_index_path(project))
        _index_pack_meta(project, root)
        payload = _client_crawl_pack(project, crawl_job, pages, db)
        latest_path = root / "current" / "latest_crawl.json"
        history_path = root / "history" / f"crawl_{crawl_job.id}.json"
        _write_json(latest_path, payload)
        _write_json(history_path, payload)
        _write_json(root / "website_orb_context" / "latest_context.json", payload["website_orb_context"])
        _write_json(root / "crm_context" / "latest_context.json", {"schema": "orb_weaver.crm_context.v0.1", "status": "not_connected"})
        _write_json(root / "mail_context" / "latest_context.json", {"schema": "orb_weaver.mail_context.v0.1", "status": "not_connected"})
        _write_json(root / "dandy_sponsor_pack" / "latest_pack.json", {"schema": "orb_weaver.dandy_sponsor_pack.v0.1", "status": "not_configured"})
        _index_crawl_pack(project, crawl_job, payload, history_path)
        _append_jsonl(
            _global_intelligence_root() / "crawl_patterns.jsonl",
            _global_crawl_pattern(project, crawl_job, payload["crawl"].get("stats") or {}, crawl_job.config or {}),
        )
    except Exception as exc:
        config = crawl_job.config or {}
        config["substrate_preservation_error"] = str(exc)
        crawl_job.config = config


def preserve_client_audit_intelligence(project: Project, crawl_job: CrawlJob, audit: AuditReport, db: Session) -> None:
    try:
        root = _ensure_client_pack(project)
        _init_client_index(_client_index_path(project))
        _index_pack_meta(project, root)
        payload = _client_audit_pack(project, crawl_job, audit, db)
        latest_path = root / "current" / "latest_audit.json"
        history_path = root / "history" / f"audit_{audit.id}.json"
        recommendations_path = root / "recommendations" / f"audit_{audit.id}_recommendations.json"
        report_path = root / "reports" / f"audit_{audit.id}_report.json"
        _write_json(latest_path, payload)
        _write_json(history_path, payload)
        _write_json(recommendations_path, {"recommendations": payload["recommendations"]})
        _write_json(report_path, payload)
        _write_json(root / "claims" / "safe_claims.json", {"claims": payload["safe_claims"]})
        _write_json(root / "claims" / "banned_claims.json", {"claims": payload["banned_claims"]})
        _index_audit_pack(project, audit, payload, history_path, recommendations_path)
        _append_jsonl(_global_intelligence_root() / "audit_patterns.jsonl", _global_audit_pattern(audit))
    except Exception as exc:
        audit.report_data = {**(audit.report_data or {}), "substrate_preservation_error": str(exc)}


def _page_to_dict(page: CrawledPage) -> Dict:
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
        "ssl_enabled": page.ssl_enabled,
        "content_hash": page.content_hash,
        "is_indexable": True if page.robots_meta is None else "noindex" not in page.robots_meta.lower(),
        "has_sitemap": page.has_sitemap,
        "has_robots_txt": page.has_robots_txt,
        "mobile_viewport": bool(page.mobile_friendly),
        "open_graph": {},
        "twitter_cards": {},
        "heading_structure": [],
        "duplicate_content_risk": False,
        "semantic_analysis": page.semantic_analysis or {},
        "schema_analysis": page.schema_analysis or {},
        "internal_link_targets": page.internal_link_targets or [],
        "entity_analysis": page.entity_analysis or {},
        "mobile_ux_analysis": page.mobile_ux_analysis or {},
        "template_signature": page.template_signature,
        "crawl_depth": page.crawl_depth or 0,
    }


def _compute_stats(pages: List[CrawledPage]) -> Dict:
    if not pages:
        return {
            "total_pages": 0,
            "visited_urls": 0,
            "sitemap_urls_found": 0,
            "has_robots_txt": False,
            "avg_load_time": 0,
            "ssl_pages": 0,
            "indexable_pages": 0,
            "duplicate_content_pages": 0,
            "total_images": 0,
            "images_missing_alt": 0,
            "total_internal_links": 0,
            "total_external_links": 0,
            "schema_pages": 0,
            "schema_errors": 0,
            "semantic_thin_pages": 0,
            "internal_link_edges": 0,
            "avg_orb_semantic_score": 0,
            "low_orb_semantic_pages": 0,
            "avg_mobile_ux_score": 0,
            "mobile_ux_problem_pages": 0,
        }

    load_times = [p.load_time_ms for p in pages if p.load_time_ms is not None]
    content_hashes = [p.content_hash for p in pages if p.content_hash]
    duplicate_hashes = {h for h in content_hashes if content_hashes.count(h) > 1}
    return {
        "total_pages": len(pages),
        "visited_urls": len(pages),
        "sitemap_urls_found": 0,
        "has_robots_txt": any(p.has_robots_txt for p in pages),
        "has_sitemap": any(p.has_sitemap for p in pages),
        "avg_load_time": sum(load_times) / len(load_times) if load_times else 0,
        "ssl_pages": sum(1 for p in pages if p.ssl_enabled),
        "indexable_pages": sum(
            1 for p in pages if (p.robots_meta is None or "noindex" not in (p.robots_meta or "").lower())
        ),
        "duplicate_content_pages": sum(1 for p in pages if p.content_hash in duplicate_hashes),
        "total_images": sum(p.images_count for p in pages),
        "images_missing_alt": sum(p.images_without_alt for p in pages),
        "total_internal_links": sum(p.internal_links for p in pages),
        "total_external_links": sum(p.external_links for p in pages),
        "schema_pages": sum(1 for p in pages if p.schema_markup),
        "schema_errors": sum((p.schema_analysis or {}).get("invalid_count", 0) for p in pages),
        "semantic_thin_pages": sum(1 for p in pages if (p.semantic_analysis or {}).get("semantic_depth") == "thin"),
        "internal_link_edges": sum(len(p.internal_link_targets or []) for p in pages),
        "avg_orb_semantic_score": sum((p.semantic_analysis or {}).get("orb_semantic_score", {}).get("overall", 0) for p in pages) / len(pages),
        "low_orb_semantic_pages": sum(1 for p in pages if (p.semantic_analysis or {}).get("orb_semantic_score", {}).get("overall", 0) < 65),
        "avg_mobile_ux_score": sum((p.mobile_ux_analysis or {}).get("score", 0) for p in pages) / len(pages),
        "mobile_ux_problem_pages": sum(1 for p in pages if (p.mobile_ux_analysis or {}).get("score", 100) < 70),
    }


def _build_internal_link_graph(pages: List[CrawledPage]) -> Dict:
    known_urls = {page.url.rstrip("/") for page in pages}
    nodes = []
    edges = []
    incoming = {url: 0 for url in known_urls}

    for page in pages:
        source = page.url.rstrip("/")
        targets = page.internal_link_targets or []
        for target in targets:
            target_url = (target.get("url") or "").rstrip("/")
            if not target_url:
                continue
            edges.append({
                "source": page.url,
                "target": target.get("url"),
                "anchor": target.get("anchor", ""),
                "nofollow": bool(target.get("nofollow")),
            })
            if target_url in incoming:
                incoming[target_url] += 1

    for page in pages:
        normalized = page.url.rstrip("/")
        nodes.append({
            "url": page.url,
            "title": page.title,
            "inbound": incoming.get(normalized, 0),
            "outbound": len(page.internal_link_targets or []),
            "status_code": page.status_code,
        })

    return {
        "nodes": nodes,
        "edges": edges[:1000],
        "orphan_candidates": [node for node in nodes if node["inbound"] == 0 and node["status_code"] == 200],
    }


def _authority_flow(pages: List[CrawledPage], graph: Dict) -> Dict:
    urls = [page.url for page in pages]
    if not urls:
        return {"pages": [], "segments": {}, "insights": []}

    url_set = set(urls)
    outgoing = {url: [] for url in urls}
    incoming = {url: 0 for url in urls}
    depths = {page.url: page.crawl_depth or 0 for page in pages}
    for edge in graph.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if source in url_set and target in url_set:
            outgoing[source].append(target)
            incoming[target] += 1

    rank = {url: 1 / len(urls) for url in urls}
    damping = 0.85
    for _ in range(20):
        next_rank = {url: (1 - damping) / len(urls) for url in urls}
        for source, targets in outgoing.items():
            if not targets:
                continue
            share = rank[source] / len(targets)
            for target in targets:
                next_rank[target] += damping * share
        rank = next_rank

    page_rows = []
    segment_scores: Dict[str, List[float]] = {}
    for page in pages:
        segment = _url_segment(page.url)
        segment_scores.setdefault(segment, []).append(rank.get(page.url, 0))
        page_rows.append({
            "url": page.url,
            "title": page.title,
            "authority": round(rank.get(page.url, 0) * 100, 4),
            "link_depth": depths.get(page.url, 0),
            "crawl_depth": depths.get(page.url, 0),
            "inbound_links": incoming.get(page.url, 0),
            "outbound_links": len(outgoing.get(page.url, [])),
            "orphan_probability": 0.9 if incoming.get(page.url, 0) == 0 and depths.get(page.url, 0) > 0 else 0.2 if incoming.get(page.url, 0) <= 1 else 0.05,
            "dead_end": len(outgoing.get(page.url, [])) == 0,
            "segment": segment,
        })

    segments = {
        segment: {
            "avg_authority": round((sum(values) / len(values)) * 100, 4),
            "pages": len(values),
        }
        for segment, values in segment_scores.items()
    }
    insights = _authority_insights(segments)
    return {"pages": sorted(page_rows, key=lambda item: item["authority"], reverse=True), "segments": segments, "insights": insights}


def _url_segment(url: str) -> str:
    lower = url.lower()
    if "/blog" in lower or "/article" in lower or "/news" in lower:
        return "blog"
    if "/product" in lower or "/shop" in lower or "/store" in lower:
        return "product"
    if "/service" in lower:
        return "service"
    if lower.rstrip("/").count("/") <= 2:
        return "core"
    return "other"


def _authority_insights(segments: Dict) -> List[str]:
    blog = segments.get("blog", {}).get("avg_authority")
    product = segments.get("product", {}).get("avg_authority")
    if blog and product and product > 0 and product / max(blog, 0.0001) >= 4:
        return [f"Your blog posts receive {round(product / blog, 1)}x less internal authority than your product pages."]
    return []


def _knowledge_graph(pages: List[CrawledPage]) -> Dict:
    nodes: Dict[str, Dict] = {}
    edges = []
    for page in pages:
        page_id = page.url
        nodes[page_id] = {"id": page_id, "label": page.title or page.url, "type": "page", "url": page.url}
        entity_data = page.entity_analysis or {}
        for bucket, node_type in (
            ("named_entities", "entity"),
            ("people", "person"),
            ("organizations", "organization"),
            ("locations", "location"),
            ("product_names", "product"),
            ("schema_org_entities", "schema.org"),
        ):
            for entity in entity_data.get(bucket, [])[:25]:
                entity_id = f"{node_type}:{entity}"
                nodes.setdefault(entity_id, {"id": entity_id, "label": entity, "type": node_type})
                edges.append({"source": page_id, "target": entity_id, "relationship": "mentions"})

    entity_counts = Counter(edge["target"] for edge in edges)
    hubs = [
        {"id": entity_id, "label": nodes[entity_id]["label"], "mentions": count}
        for entity_id, count in entity_counts.most_common(20)
        if count >= 2
    ]
    missing_pillars = [
        {"entity": hub["label"], "reason": "Entity appears across multiple pages but no exact-title pillar page was found"}
        for hub in hubs
        if not any((page.title or "").lower() == hub["label"].lower() for page in pages)
    ][:10]
    topic_clusters = _topic_clusters(pages)
    return {
        "nodes": list(nodes.values())[:1000],
        "edges": edges[:2000],
        "hubs": hubs,
        "topic_clusters": topic_clusters,
        "missing_pillar_pages": missing_pillars,
        "internal_linking_suggestions": _knowledge_link_suggestions(pages, hubs),
    }


def _topic_clusters(pages: List[CrawledPage]) -> List[Dict]:
    clusters: Dict[str, List[str]] = {}
    for page in pages:
        terms = (page.semantic_analysis or {}).get("top_terms", [])
        cluster = terms[0]["term"] if terms else "uncategorized"
        clusters.setdefault(cluster, []).append(page.url)
    return [{"topic": topic, "pages": urls[:20], "page_count": len(urls)} for topic, urls in clusters.items()]


def _knowledge_link_suggestions(pages: List[CrawledPage], hubs: List[Dict]) -> List[Dict]:
    suggestions = []
    for hub in hubs[:10]:
        candidates = [
            page for page in pages
            if hub["label"].lower() in " ".join((page.entity_analysis or {}).get("named_entities", [])).lower()
        ]
        if len(candidates) > 1:
            source = min(candidates, key=lambda page: page.internal_links or 0)
            target = max(candidates, key=lambda page: page.internal_links or 0)
            if source.url != target.url:
                suggestions.append({
                    "entity": hub["label"],
                    "source": source.url,
                    "target": target.url,
                    "anchor": hub["label"],
                    "reason": "Pages share an entity but do not appear equally connected"
                })
    return suggestions


def _historical_delta(current_stats: Dict, previous_stats: Optional[Dict]) -> Dict:
    if not previous_stats:
        return {"has_previous": False, "deltas": {}}

    keys = [
        "total_pages",
        "avg_load_time",
        "indexable_pages",
        "duplicate_content_pages",
        "images_missing_alt",
        "schema_pages",
        "schema_errors",
        "semantic_thin_pages",
        "internal_link_edges",
    ]
    return {
        "has_previous": True,
        "previous_stats": {key: previous_stats.get(key, 0) for key in keys},
        "current_stats": {key: current_stats.get(key, 0) for key in keys},
        "deltas": {key: current_stats.get(key, 0) - previous_stats.get(key, 0) for key in keys},
    }


def _trend_model(current_stats: Dict, previous_jobs: List[CrawlJob], db: Session) -> Dict:
    snapshots = []
    for job in reversed(previous_jobs[-12:]):
        pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == job.id).all()
        stats = (job.config or {}).get("stats") or _compute_stats(pages)
        snapshots.append({"crawl_id": job.id, "date": job.end_time.isoformat() if job.end_time else None, "stats": stats})
    snapshots.append({"crawl_id": "current", "date": datetime.utcnow().isoformat(), "stats": current_stats})

    keys = ["avg_orb_semantic_score", "avg_mobile_ux_score", "schema_pages", "low_orb_semantic_pages", "mobile_ux_problem_pages"]
    trends = {}
    for key in keys:
        values = [float(item["stats"].get(key, 0) or 0) for item in snapshots]
        trends[key] = {
            "rolling_average": round(sum(values[-3:]) / len(values[-3:]), 2) if values else 0,
            "slope": round(_linear_slope(values), 4),
            "anomaly": _is_anomaly(values),
            "expected_next_month": round(values[-1] + _linear_slope(values), 2) if values else 0,
            "seasonality": "insufficient_data" if len(values) < 6 else "not_detected",
        }

    return {"snapshots": snapshots[-12:], "metrics": trends}


def _linear_slope(values: List[float]) -> float:
    n = len(values)
    if n < 2:
        return 0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum((idx - x_mean) * (value - y_mean) for idx, value in enumerate(values))
    denominator = sum((idx - x_mean) ** 2 for idx in range(n))
    return numerator / denominator if denominator else 0


def _is_anomaly(values: List[float]) -> bool:
    if len(values) < 4:
        return False
    baseline = values[:-1]
    mean = sum(baseline) / len(baseline)
    variance = sum((value - mean) ** 2 for value in baseline) / len(baseline)
    return abs(values[-1] - mean) > (variance ** 0.5) * 2 if variance else False


def _template_detection(pages: List[CrawledPage]) -> Dict:
    groups: Dict[str, List[CrawledPage]] = {}
    meta_titles = Counter((page.title or "").strip().lower() for page in pages if page.title)
    meta_desc = Counter((page.meta_description or "").strip().lower() for page in pages if page.meta_description)
    for page in pages:
        groups.setdefault(page.template_signature or "unknown", []).append(page)

    repeated = []
    for signature, group in groups.items():
        if len(group) < 2:
            continue
        hashes = [page.content_hash for page in group if page.content_hash]
        duplicate_ratio = max(Counter(hashes).values()) / len(group) if hashes else 0
        repeated.append({
            "signature": signature,
            "page_count": len(group),
            "duplicate_text_probability": round(duplicate_ratio * 100, 1),
            "pages": [page.url for page in group[:20]],
            "orb_statement": f"{_url_segment(group[0].url).capitalize()} pages share {round(duplicate_ratio * 100, 1)}% identical content signatures."
        })

    return {
        "repeated_layouts": sorted(repeated, key=lambda item: item["page_count"], reverse=True),
        "duplicated_titles": [{"title": title, "count": count} for title, count in meta_titles.items() if count > 1],
        "duplicated_meta_descriptions": [{"meta_description": desc, "count": count} for desc, count in meta_desc.items() if count > 1],
    }


def _competitor_gap(pages: List[CrawledPage], competitors: List[Dict], authority: Dict) -> Dict:
    own_terms = Counter()
    own_entities = Counter()
    own_questions = Counter()
    own_schema = Counter()
    for page in pages:
        for item in (page.semantic_analysis or {}).get("top_terms", []):
            own_terms[item.get("term", "")] += int(item.get("count", 0))
        for entity in (page.entity_analysis or {}).get("named_entities", []):
            own_entities[entity] += 1
        for schema_type in (page.schema_analysis or {}).get("types", []):
            own_schema[schema_type] += 1
        for heading in page.h2_tags or []:
            if "?" in heading:
                own_questions[heading] += 1

    competitor_terms = Counter()
    competitor_schema = Counter()
    competitor_entities = Counter()
    competitor_questions = Counter()
    for competitor in competitors:
        for item in competitor.get("top_terms", []) or []:
            competitor_terms[item.get("term", "")] += int(item.get("count", 0))
        for item in competitor.get("schema_types", []) or []:
            competitor_schema[item.get("type", "")] += int(item.get("count", 0))
        for item in competitor.get("entities", []) or []:
            competitor_entities[item.get("entity", "")] += int(item.get("count", 0))
        for item in competitor.get("questions", []) or []:
            competitor_questions[item.get("question", "")] += int(item.get("count", 0))

    missing_topics = [term for term, _count in competitor_terms.most_common(30) if term and term not in own_terms][:15]
    missing_schema = [schema for schema, _count in competitor_schema.most_common(20) if schema and schema not in own_schema][:10]
    missing_entities = [entity for entity, _count in competitor_entities.most_common(30) if entity and entity not in own_entities][:15]
    missing_questions = [question for question, _count in competitor_questions.most_common(20) if question and question not in own_questions][:10]
    weak_hubs = [
        segment for segment, data in authority.get("segments", {}).items()
        if data.get("pages", 0) >= 2 and data.get("avg_authority", 0) < 1
    ]
    return {
        "missing_topics": missing_topics,
        "missing_entities": missing_entities,
        "missing_questions": missing_questions or ([] if own_questions else ["Add explicit question-led headings for competitor-covered topics"]),
        "missing_schema_types": missing_schema,
        "missing_internal_link_hubs": weak_hubs,
    }


def _summarize_pages_for_competitor(domain: str, pages: List[PageData], stats: Dict) -> Dict:
    top_terms = Counter()
    schema_types = Counter()
    entities = Counter()
    questions = Counter()
    for page in pages:
        for item in page.semantic_analysis.get("top_terms", [])[:8]:
            top_terms[item.get("term", "")] += int(item.get("count", 0))
        for schema_type in page.schema_analysis.get("types", []):
            schema_types[schema_type] += 1
        for entity in page.entity_analysis.get("named_entities", []):
            entities[entity] += 1
        for heading in page.h2_tags:
            if "?" in heading:
                questions[heading] += 1

    return {
        "domain": domain,
        "stats": stats,
        "top_terms": [{"term": term, "count": count} for term, count in top_terms.most_common(10)],
        "schema_types": [{"type": schema_type, "count": count} for schema_type, count in schema_types.most_common(10)],
        "entities": [{"entity": entity, "count": count} for entity, count in entities.most_common(20)],
        "questions": [{"question": question, "count": count} for question, count in questions.most_common(20)],
    }


async def _crawl_competitors(domains: List[str], config: CrawlConfig) -> List[Dict]:
    results = []
    for raw_domain in domains[:5]:
        domain = _normalize_domain(raw_domain)
        if not domain:
            continue
        crawler = OrbWeaverCrawler(
            max_pages=min(config.max_pages, 50),
            delay=config.delay,
            max_depth=min(config.max_depth, 3),
        )
        start_url = f"https://{domain}" if not domain.startswith("http") else domain
        try:
            pages = await crawler.crawl(start_url)
            results.append(_summarize_pages_for_competitor(domain, pages, crawler.get_crawl_stats()))
        except Exception as exc:
            results.append({"domain": domain, "error": str(exc)})
    return results


def _serialize_crawl_job(crawl_job: CrawlJob, db: Session, include_pages: bool = False) -> Dict:
    pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job.id).all()
    config = crawl_job.config or {}
    stats = {**_compute_stats(pages), **(config.get("stats") or {})}

    payload = {
        "id": str(crawl_job.id),
        "project_id": str(crawl_job.project_id),
        "status": crawl_job.status,
        "config": config,
        "created_at": crawl_job.start_time.isoformat() if crawl_job.start_time else None,
        "start_time": crawl_job.start_time.isoformat() if crawl_job.start_time else None,
        "end_time": crawl_job.end_time.isoformat() if crawl_job.end_time else None,
        "pages_crawled": crawl_job.pages_crawled,
        "pages_found": crawl_job.pages_found,
        "errors_count": crawl_job.errors_count,
        "stats": stats,
        "historical": config.get("historical"),
        "trend_model": config.get("trend_model"),
        "internal_link_graph": config.get("internal_link_graph"),
        "authority_flow": config.get("authority_flow"),
        "knowledge_graph": config.get("knowledge_graph"),
        "competitors": config.get("competitors", []),
        "competitor_gap": config.get("competitor_gap"),
        "template_detection": config.get("template_detection"),
        "error": config.get("error"),
    }
    if include_pages:
        payload["pages"] = [_page_to_dict(p) for p in pages]
    return payload


def _serialize_audit_report(report: AuditReport) -> Dict:
    return {
        "id": str(report.id),
        "crawl_job_id": str(report.crawl_job_id) if report.crawl_job_id else None,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "report": report.report_data,
    }


async def run_crawl_job(crawl_job_id: int, config_data: Dict):
    db = SessionLocal()
    try:
        crawl_job = db.query(CrawlJob).filter(CrawlJob.id == crawl_job_id).first()
        if not crawl_job:
            return

        project = db.query(Project).filter(Project.id == crawl_job.project_id).first()
        if not project:
            return

        previous_crawl = (
            db.query(CrawlJob)
            .filter(
                CrawlJob.project_id == project.id,
                CrawlJob.status == "completed",
                CrawlJob.id != crawl_job.id,
            )
            .order_by(CrawlJob.id.desc())
            .first()
        )
        previous_stats = None
        if previous_crawl:
            previous_pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == previous_crawl.id).all()
            previous_stats = _compute_stats(previous_pages)
        previous_jobs = (
            db.query(CrawlJob)
            .filter(
                CrawlJob.project_id == project.id,
                CrawlJob.status == "completed",
                CrawlJob.id != crawl_job.id,
            )
            .order_by(CrawlJob.id.asc())
            .all()
        )

        config = CrawlConfig(**config_data)
        crawl_job.status = "running"
        crawl_job.start_time = datetime.utcnow()
        db.commit()

        crawler = OrbWeaverCrawler(
            max_pages=config.max_pages,
            delay=config.delay,
            max_depth=config.max_depth,
        )

        start_url = f"https://{project.domain}" if not project.domain.startswith("http") else project.domain
        pages = await crawler.crawl(start_url)
        crawl_stats = crawler.get_crawl_stats()

        db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job.id).delete()

        for page in pages:
            db.add(
                CrawledPage(
                    crawl_job_id=crawl_job.id,
                    url=page.url,
                    title=page.title,
                    meta_description=page.meta_description,
                    h1=page.h1,
                    h2_tags=page.h2_tags,
                    word_count=page.word_count,
                    status_code=page.status_code,
                    load_time_ms=page.load_time_ms,
                    canonical_url=page.canonical_url,
                    robots_meta=page.robots_meta,
                    schema_markup=page.schema_markup,
                    internal_links=page.internal_links,
                    external_links=page.external_links,
                    images_count=page.images_count,
                    images_without_alt=page.images_without_alt,
                    has_sitemap=page.has_sitemap,
                    has_robots_txt=page.has_robots_txt,
                    mobile_friendly=page.mobile_viewport,
                    ssl_enabled=page.ssl_enabled,
                    content_hash=page.content_hash,
                    semantic_analysis=page.semantic_analysis,
                    schema_analysis=page.schema_analysis,
                    internal_link_targets=page.internal_link_targets,
                    entity_analysis=page.entity_analysis,
                    mobile_ux_analysis=page.mobile_ux_analysis,
                    template_signature=page.template_signature,
                    crawl_depth=page.crawl_depth,
                )
            )

        db.flush()
        stored_pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job.id).all()
        stats = {**_compute_stats(stored_pages), **crawl_stats}
        link_graph = _build_internal_link_graph(stored_pages)
        authority_flow = _authority_flow(stored_pages, link_graph)
        knowledge_graph = _knowledge_graph(stored_pages)
        historical = _historical_delta(stats, previous_stats)
        trend_model = _trend_model(stats, previous_jobs, db)
        competitor_results = await _crawl_competitors(config.competitor_domains, config) if config.competitor_domains else []
        competitor_gap = _competitor_gap(stored_pages, competitor_results, authority_flow)
        template_detection = _template_detection(stored_pages)

        crawl_job.status = "completed"
        crawl_job.end_time = datetime.utcnow()
        crawl_job.pages_crawled = len(pages)
        crawl_job.pages_found = len(pages)
        crawl_job.errors_count = 0
        crawl_job.config = {
            **(crawl_job.config or {}),
            "stats": stats,
            "historical": historical,
            "trend_model": trend_model,
            "internal_link_graph": link_graph,
            "authority_flow": authority_flow,
            "knowledge_graph": knowledge_graph,
            "competitors": competitor_results,
            "competitor_gap": competitor_gap,
            "template_detection": template_detection,
        }
        db.commit()

        report_dir = _project_report_dir(project)
        snapshot = {
            "project": _serialize_project(project, db),
            "crawl": _serialize_crawl_job(crawl_job, db, include_pages=False),
            "saved_at": datetime.utcnow().isoformat(),
        }
        (report_dir / f"crawl_{crawl_job.id}.json").write_text(str(snapshot), encoding="utf-8")
        preserve_client_crawl_intelligence(project, crawl_job, stored_pages, db)
        db.commit()
    except Exception as exc:
        crawl_job = db.query(CrawlJob).filter(CrawlJob.id == crawl_job_id).first()
        if crawl_job:
            crawl_job.status = "failed"
            crawl_job.end_time = datetime.utcnow()
            config = crawl_job.config or {}
            config["error"] = str(exc)
            crawl_job.config = config
            db.commit()
    finally:
        db.close()


async def run_audit_job(audit_id: int, crawl_job_id: int):
    db = SessionLocal()
    try:
        crawl_job = db.query(CrawlJob).filter(CrawlJob.id == crawl_job_id).first()
        audit = db.query(AuditReport).filter(AuditReport.id == audit_id).first()
        if not crawl_job or not audit or crawl_job.status != "completed":
            return

        pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job_id).all()
        page_data = [PageData(**_page_to_dict(page)) for page in pages]
        stats = _compute_stats(pages)

        auditor = SEOAuditor()
        report_payload = auditor.audit(page_data, stats)

        audit.report_data = report_payload
        audit.overall_score = report_payload["scores"].get("overall")
        audit.seo_score = report_payload["scores"].get("seo")
        audit.performance_score = report_payload["scores"].get("performance")
        audit.accessibility_score = report_payload["scores"].get("accessibility")
        audit.content_score = report_payload["scores"].get("content")
        audit.technical_score = report_payload["scores"].get("technical")
        audit.issues_found = report_payload["summary"].get("critical_count", 0)
        audit.warnings_found = report_payload["summary"].get("warning_count", 0)
        audit.opportunities_found = report_payload["summary"].get("opportunity_count", 0)
        db.commit()

        project = db.query(Project).filter(Project.id == crawl_job.project_id).first()
        if project:
            report_dir = _project_report_dir(project)
            compiler = {
                "project": _serialize_project(project, db),
                "crawl": _serialize_crawl_job(crawl_job, db, include_pages=False),
                "audit": _serialize_audit_report(audit),
                "saved_at": datetime.utcnow().isoformat(),
            }
            (report_dir / f"audit_{audit.id}.json").write_text(str(compiler), encoding="utf-8")
            (report_dir / "latest_report.json").write_text(str(compiler), encoding="utf-8")
            preserve_client_audit_intelligence(project, crawl_job, audit, db)
            db.commit()
    finally:
        db.close()


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "operational",
    }


@app.post("/api/auth/signup")
async def signup_customer(payload: CustomerSignup, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    if not payload.business_name.strip():
        raise HTTPException(status_code=400, detail="Business name is required")
    existing = db.query(Customer).filter(Customer.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Customer email already exists")

    customer = Customer(
        email=email,
        password_hash=_hash_password(payload.password),
        business_name=payload.business_name.strip(),
        contact_name=(payload.contact_name or "").strip() or None,
        phone=(payload.phone or "").strip() or None,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return _issue_customer_session(customer, db)


@app.post("/api/auth/login")
async def login_customer(payload: CustomerLogin, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.email == _normalize_email(payload.email)).first()
    if not customer or not _verify_password(payload.password, customer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if customer.status != "active":
        raise HTTPException(status_code=403, detail="Customer account unavailable")
    return _issue_customer_session(customer, db)


@app.get("/api/auth/me")
async def get_customer_me(customer: Customer = Depends(get_current_customer)):
    return _serialize_customer(customer)


@app.post("/api/auth/logout")
async def logout_customer(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    token_hash = _hash_token(authorization.split(" ", 1)[1].strip()) if authorization else ""
    session = db.query(CustomerSession).filter(
        CustomerSession.customer_id == customer.id,
        CustomerSession.token_hash == token_hash,
    ).first()
    if session:
        session.revoked_at = datetime.utcnow()
        db.commit()
    return {"status": "logged_out"}


@app.post("/api/projects")
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    domain = _normalize_domain(project.domain)
    if not domain:
        raise HTTPException(status_code=400, detail="Domain is required")

    existing = db.query(Project).filter(Project.domain == domain, Project.customer_id == customer.id).first()
    if existing:
        if project.ga4_property_id:
            existing.ga4_property_id = project.ga4_property_id
            db.commit()
            db.refresh(existing)
        return _serialize_project(existing, db)

    existing_domain = db.query(Project).filter(Project.domain == domain).first()
    if existing_domain:
        if existing_domain.customer_id is None:
            existing_domain.customer_id = customer.id
            if project.name:
                existing_domain.name = project.name.strip()
            if project.ga4_property_id:
                existing_domain.ga4_property_id = project.ga4_property_id
            db.commit()
            db.refresh(existing_domain)
            return _serialize_project(existing_domain, db)
        raise HTTPException(status_code=409, detail="Domain is already registered to another customer")

    name = (project.name or "").strip() or _default_project_name(domain)
    created = Project(name=name, domain=domain, ga4_property_id=project.ga4_property_id, customer_id=customer.id)
    db.add(created)
    db.commit()
    db.refresh(created)
    _project_report_dir(created)
    return _serialize_project(created, db)


@app.get("/api/projects")
async def list_projects(db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    projects = db.query(Project).filter(Project.customer_id == customer.id).order_by(Project.id.asc()).all()
    return [_serialize_project(project, db) for project in projects]


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    project = _owned_project(project_id, customer, db)
    return _serialize_project(project, db)


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    project = _owned_project(project_id, customer, db)

    crawl_jobs = db.query(CrawlJob).filter(CrawlJob.project_id == project.id).all()
    crawl_ids = [job.id for job in crawl_jobs]

    if crawl_ids:
        db.query(CrawledPage).filter(CrawledPage.crawl_job_id.in_(crawl_ids)).delete(synchronize_session=False)
    db.query(AuditReport).filter(AuditReport.project_id == project.id).delete(synchronize_session=False)
    db.query(CrawlJob).filter(CrawlJob.project_id == project.id).delete(synchronize_session=False)
    db.delete(project)
    db.commit()

    return {"status": "deleted", "project_id": project_id}


@app.post("/api/projects/{project_id}/crawl")
async def start_crawl(
    project_id: str,
    config: CrawlConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    project = _owned_project(project_id, customer, db)

    crawl = CrawlJob(project_id=project.id, status="pending", config=config.model_dump(), start_time=datetime.utcnow())
    db.add(crawl)
    db.commit()
    db.refresh(crawl)

    background_tasks.add_task(run_crawl_job, crawl.id, config.model_dump())
    return _serialize_crawl_job(crawl, db)


@app.get("/api/crawl-jobs/{job_id}")
async def get_crawl_job(job_id: str, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    crawl_job = _owned_crawl_job(job_id, customer, db)
    return _serialize_crawl_job(crawl_job, db)


@app.get("/api/crawl-jobs/{job_id}/pages")
async def get_crawl_pages(
    job_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    crawl_job = _owned_crawl_job(job_id, customer, db)

    query = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job.id)
    total = query.count()
    pages = query.offset(skip).limit(limit).all()
    return {"total": total, "pages": [_page_to_dict(page) for page in pages]}


@app.get("/api/crawl-jobs/{job_id}/export/csv")
async def export_crawl_csv(job_id: str, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    crawl_job = _owned_crawl_job(job_id, customer, db)

    pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job.id).all()
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "url",
        "title",
        "status_code",
        "load_time_ms",
        "word_count",
        "internal_links",
        "external_links",
        "images_count",
        "images_without_alt",
        "ssl_enabled",
        "schema_count",
        "schema_errors",
        "semantic_depth",
        "internal_link_edges",
        "orb_semantic_score",
        "entity_count",
        "mobile_ux_score",
        "template_signature",
        "crawl_depth",
    ])
    for page in pages:
        writer.writerow([
            page.url,
            page.title or "",
            page.status_code or "",
            page.load_time_ms or "",
            page.word_count,
            page.internal_links,
            page.external_links,
            page.images_count,
            page.images_without_alt,
            page.ssl_enabled,
            len(page.schema_markup or []),
            (page.schema_analysis or {}).get("invalid_count", 0),
            (page.semantic_analysis or {}).get("semantic_depth", ""),
            len(page.internal_link_targets or []),
            (page.semantic_analysis or {}).get("orb_semantic_score", {}).get("overall", ""),
            len((page.entity_analysis or {}).get("named_entities", [])),
            (page.mobile_ux_analysis or {}).get("score", ""),
            page.template_signature or "",
            page.crawl_depth or 0,
        ])

    stream = BytesIO(buffer.getvalue().encode("utf-8"))
    headers = {"Content-Disposition": f"attachment; filename=crawl_{job_id}.csv"}
    return StreamingResponse(stream, media_type="text/csv", headers=headers)


@app.post("/api/crawl-jobs/{job_id}/audit")
async def run_audit(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    crawl_job = _owned_crawl_job(job_id, customer, db)

    audit = AuditReport(project_id=crawl_job.project_id, crawl_job_id=crawl_job.id, report_data={})
    db.add(audit)
    db.commit()
    db.refresh(audit)

    background_tasks.add_task(run_audit_job, audit.id, crawl_job.id)
    return {"audit_id": str(audit.id), "status": "started", "message": "Audit is running in background"}


@app.get("/api/audit-reports/{audit_id}")
async def get_audit_report(audit_id: str, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    report = _owned_audit_report(audit_id, customer, db)
    if not report.report_data:
        raise HTTPException(status_code=404, detail="Audit report not ready")
    return _serialize_audit_report(report)


@app.get("/api/audit-reports/{audit_id}/export/csv")
async def export_audit_csv(audit_id: str, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    report = _owned_audit_report(audit_id, customer, db)
    if not report.report_data:
        raise HTTPException(status_code=404, detail="Audit report not found")

    report_data = report.report_data
    rows = []
    for bucket in ["critical", "warnings", "opportunities"]:
        for issue in report_data.get("issues", {}).get(bucket, []):
            rows.append([
                bucket,
                issue.get("category", ""),
                issue.get("title", ""),
                issue.get("impact_score", ""),
                issue.get("description", ""),
                issue.get("recommendation", ""),
            ])

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["severity", "category", "title", "impact_score", "description", "recommendation"])
    writer.writerows(rows)

    stream = BytesIO(buffer.getvalue().encode("utf-8"))
    headers = {"Content-Disposition": f"attachment; filename=audit_{audit_id}.csv"}
    return StreamingResponse(stream, media_type="text/csv", headers=headers)


@app.get("/api/audit-reports/{audit_id}/export/pdf")
async def export_audit_pdf(audit_id: str, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    report = _owned_audit_report(audit_id, customer, db)
    if not report.report_data:
        raise HTTPException(status_code=404, detail="Audit report not found")

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF export dependency missing: {exc}")

    data = report.report_data
    buf = BytesIO()
    pdf = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    y = height - 50
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, f"SEO Audit Report #{audit_id}")
    y -= 30

    pdf.setFont("Helvetica", 11)
    scores = data.get("scores", {})
    pdf.drawString(40, y, f"Overall Score: {scores.get('overall', '-')}")
    y -= 20
    summary = data.get("summary", {})
    pdf.drawString(40, y, f"Critical: {summary.get('critical_count', 0)}  Warnings: {summary.get('warning_count', 0)}  Opportunities: {summary.get('opportunity_count', 0)}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, "Top Issues")
    y -= 20
    pdf.setFont("Helvetica", 10)

    for issue in data.get("top_issues", [])[:12]:
        text = f"- {issue.get('title', '')} (Impact {issue.get('impact_score', '-')})"
        pdf.drawString(40, y, text[:110])
        y -= 16
        if y < 50:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 10)

    pdf.save()
    buf.seek(0)
    headers = {"Content-Disposition": f"attachment; filename=audit_{audit_id}.pdf"}
    return StreamingResponse(buf, media_type="application/pdf", headers=headers)


@app.get("/api/projects/{project_id}/report-compiler")
async def report_compiler(project_id: str, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    project = _owned_project(project_id, customer, db)

    latest_crawl = (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project.id, CrawlJob.status == "completed")
        .order_by(CrawlJob.id.desc())
        .first()
    )
    latest_audit = (
        db.query(AuditReport)
        .filter(AuditReport.project_id == project.id)
        .order_by(AuditReport.id.desc())
        .first()
    )

    report_dir = _project_report_dir(project)
    files = sorted([p.name for p in report_dir.glob("*.json")])

    return {
        "project": _serialize_project(project, db),
        "latest_crawl": _serialize_crawl_job(latest_crawl, db) if latest_crawl else None,
        "latest_audit": _serialize_audit_report(latest_audit) if latest_audit and latest_audit.report_data else None,
        "files": files,
    }


@app.post("/api/projects/{project_id}/recrawl")
async def recrawl_project(
    project_id: str,
    config: CrawlConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    return await start_crawl(project_id, config, background_tasks, db, customer)


@app.post("/api/projects/{project_id}/reaudit")
async def reaudit_project(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    project = _owned_project(project_id, customer, db)
    crawl = (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project.id, CrawlJob.status == "completed")
        .order_by(CrawlJob.id.desc())
        .first()
    )
    if not crawl:
        raise HTTPException(status_code=400, detail="No completed crawl found for this project")
    return await run_audit(str(crawl.id), background_tasks, db, customer)


@app.post("/api/ga4/connect")
async def connect_ga4(config: GA4Config):
    try:
        connector = GA4Connector(property_id=config.property_id, credentials_path=config.credentials_path)
        overview = connector.get_traffic_overview(daysAgo="7daysAgo", end_date="today")
        return {
            "status": "connected",
            "property_id": config.property_id,
            "test_data": overview["totals"],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"GA4 connection failed: {exc}")


@app.get("/api/ga4/{property_id}/overview")
async def get_ga4_overview(property_id: str, days: int = Query(30, ge=1, le=365)):
    try:
        connector = GA4Connector(property_id=property_id)
        return connector.get_full_report(days=days)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/ga4/{property_id}/top-pages")
async def get_ga4_top_pages(property_id: str, days: int = Query(30, ge=1, le=365), limit: int = Query(50, ge=1, le=100)):
    try:
        connector = GA4Connector(property_id=property_id)
        start_date = (datetime.now() - __import__("datetime").timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        pages = connector.get_top_pages(start_date, end_date, limit)
        return {"pages": pages}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/ga4/{property_id}/search-queries")
async def get_ga4_search_queries(property_id: str, days: int = Query(30, ge=1, le=365), limit: int = Query(100, ge=1, le=500)):
    try:
        connector = GA4Connector(property_id=property_id)
        start_date = (datetime.now() - __import__("datetime").timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        queries = connector.get_search_queries(start_date, end_date, limit)
        return {"queries": queries}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/ga4/{property_id}/devices")
async def get_ga4_devices(property_id: str, days: int = Query(30, ge=1, le=365)):
    try:
        connector = GA4Connector(property_id=property_id)
        start_date = (datetime.now() - __import__("datetime").timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        devices = connector.get_device_breakdown(start_date, end_date)
        return {"devices": devices}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/combined/{project_id}/dashboard")
async def get_combined_dashboard(project_id: str, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    project = _owned_project(project_id, customer, db)

    latest_crawl = (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project.id, CrawlJob.status == "completed")
        .order_by(CrawlJob.id.desc())
        .first()
    )
    latest_audit = (
        db.query(AuditReport)
        .filter(AuditReport.project_id == project.id)
        .order_by(AuditReport.id.desc())
        .first()
    )

    ga4_data = None
    if project.ga4_property_id:
        try:
            connector = GA4Connector(property_id=project.ga4_property_id)
            ga4_data = connector.get_full_report(days=30)
        except Exception:
            ga4_data = None

    crawl_summary = _serialize_crawl_job(latest_crawl, db).get("stats") if latest_crawl else None
    audit_payload = latest_audit.report_data if latest_audit and latest_audit.report_data else None

    return {
        "project": _serialize_project(project, db),
        "crawl_summary": crawl_summary,
        "audit_scores": audit_payload.get("scores") if audit_payload else None,
        "audit_issues": audit_payload.get("summary") if audit_payload else None,
        "ga4_data": ga4_data,
        "top_issues": audit_payload.get("top_issues") if audit_payload else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=16500)
