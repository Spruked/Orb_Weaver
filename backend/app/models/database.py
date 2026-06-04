from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, JSON, ForeignKey, BigInteger, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=False)
    ga4_property_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    crawls = relationship("CrawlJob", back_populates="project")
    audits = relationship("AuditReport", back_populates="project")
    customer = relationship("Customer", back_populates="projects")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    business_name = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    projects = relationship("Project", back_populates="customer")
    sessions = relationship("CustomerSession", back_populates="customer")

class CustomerSession(Base):
    __tablename__ = "customer_sessions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="sessions")

class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    pages_crawled = Column(Integer, default=0)
    pages_found = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    config = Column(JSON, default=dict)

    project = relationship("Project", back_populates="crawls")
    pages = relationship("CrawledPage", back_populates="crawl_job")

class CrawledPage(Base):
    __tablename__ = "crawled_pages"

    id = Column(Integer, primary_key=True, index=True)
    crawl_job_id = Column(Integer, ForeignKey("crawl_jobs.id"))
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    meta_description = Column(Text, nullable=True)
    h1 = Column(Text, nullable=True)
    h2_tags = Column(JSON, default=list)
    word_count = Column(Integer, default=0)
    status_code = Column(Integer, nullable=True)
    load_time_ms = Column(Float, nullable=True)
    canonical_url = Column(Text, nullable=True)
    robots_meta = Column(String(50), nullable=True)
    schema_markup = Column(JSON, default=list)
    internal_links = Column(Integer, default=0)
    external_links = Column(Integer, default=0)
    images_count = Column(Integer, default=0)
    images_without_alt = Column(Integer, default=0)
    has_sitemap = Column(Boolean, default=False)
    has_robots_txt = Column(Boolean, default=False)
    mobile_friendly = Column(Boolean, nullable=True)
    ssl_enabled = Column(Boolean, default=False)
    content_hash = Column(String(64), nullable=True)
    semantic_analysis = Column(JSON, default=dict)
    schema_analysis = Column(JSON, default=dict)
    internal_link_targets = Column(JSON, default=list)
    entity_analysis = Column(JSON, default=dict)
    mobile_ux_analysis = Column(JSON, default=dict)
    template_signature = Column(String(64), nullable=True)
    crawl_depth = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    crawl_job = relationship("CrawlJob", back_populates="pages")

class AuditReport(Base):
    __tablename__ = "audit_reports"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    crawl_job_id = Column(Integer, ForeignKey("crawl_jobs.id"), nullable=True)
    overall_score = Column(Float, nullable=True)
    seo_score = Column(Float, nullable=True)
    performance_score = Column(Float, nullable=True)
    accessibility_score = Column(Float, nullable=True)
    content_score = Column(Float, nullable=True)
    technical_score = Column(Float, nullable=True)
    issues_found = Column(Integer, default=0)
    warnings_found = Column(Integer, default=0)
    opportunities_found = Column(Integer, default=0)
    report_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="audits")

class GA4Data(Base):
    __tablename__ = "ga4_data"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    page_path = Column(Text, nullable=False)
    sessions = Column(BigInteger, default=0)
    users = Column(BigInteger, default=0)
    pageviews = Column(BigInteger, default=0)
    bounce_rate = Column(Float, nullable=True)
    avg_session_duration = Column(Float, nullable=True)
    date_range_start = Column(DateTime, nullable=False)
    date_range_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class KeywordRanking(Base):
    __tablename__ = "keyword_rankings"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    keyword = Column(String(500), nullable=False)
    position = Column(Integer, nullable=True)
    search_volume = Column(Integer, nullable=True)
    difficulty = Column(Integer, nullable=True)
    cpc = Column(Float, nullable=True)
    url = Column(Text, nullable=True)
    date_checked = Column(DateTime, default=datetime.utcnow)

# Database setup
def get_engine(database_url: str, **kwargs):
    return create_engine(database_url, **kwargs)

def get_session_maker(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(engine):
    Base.metadata.create_all(bind=engine)
    _ensure_json_columns(engine)
    _ensure_project_customer_column(engine)


def _ensure_json_columns(engine):
    inspector = inspect(engine)
    if "crawled_pages" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("crawled_pages")}
    missing = [
        name
        for name in (
            "semantic_analysis",
            "schema_analysis",
            "internal_link_targets",
            "entity_analysis",
            "mobile_ux_analysis",
            "template_signature",
            "crawl_depth",
        )
        if name not in existing
    ]
    if not missing:
        return

    type_name = "JSON" if engine.dialect.name != "sqlite" else "TEXT"
    with engine.begin() as connection:
        for name in missing:
            if name == "crawl_depth":
                connection.execute(text(f"ALTER TABLE crawled_pages ADD COLUMN {name} INTEGER DEFAULT 0"))
            elif name == "template_signature":
                connection.execute(text(f"ALTER TABLE crawled_pages ADD COLUMN {name} VARCHAR(64)"))
            else:
                connection.execute(text(f"ALTER TABLE crawled_pages ADD COLUMN {name} {type_name}"))


def _ensure_project_customer_column(engine):
    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("projects")}
    if "customer_id" in existing:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE projects ADD COLUMN customer_id INTEGER"))
