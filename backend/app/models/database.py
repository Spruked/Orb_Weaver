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
    full_name = Column(String(255), nullable=True)
    business_name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(120), nullable=True)
    state = Column(String(120), nullable=True)
    postal_code = Column(String(50), nullable=True)
    country = Column(String(120), nullable=True)
    business_phone = Column(String(50), nullable=True)
    business_address_line1 = Column(String(255), nullable=True)
    business_address_line2 = Column(String(255), nullable=True)
    business_city = Column(String(120), nullable=True)
    business_state = Column(String(120), nullable=True)
    business_postal_code = Column(String(50), nullable=True)
    business_country = Column(String(120), nullable=True)
    tax_id = Column(String(120), nullable=True)
    is_admin = Column(Boolean, default=False)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    projects = relationship("Project", back_populates="customer")
    sessions = relationship("CustomerSession", back_populates="customer")
    cart_items = relationship("CartItem", back_populates="customer")
    checkout_orders = relationship("CheckoutOrder", back_populates="customer")
    marketplace_products = relationship(
        "MarketplaceProduct",
        foreign_keys="MarketplaceProduct.seller_user_id",
        back_populates="seller",
    )
    marketplace_uploaded_images = relationship(
        "MarketplaceProductImage",
        foreign_keys="MarketplaceProductImage.uploaded_by_user_id",
        back_populates="uploader",
    )

class CustomerSession(Base):
    __tablename__ = "customer_sessions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="sessions")

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    sku = Column(String(120), nullable=False)
    name = Column(String(255), nullable=False)
    unit_amount_cents = Column(Integer, nullable=False)
    currency = Column(String(10), default="usd")
    quantity = Column(Integer, default=1)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="cart_items")

class CheckoutOrder(Base):
    __tablename__ = "checkout_orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    status = Column(String(50), default="created")
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(10), default="usd")
    provider_order_id = Column(String(255), nullable=True, index=True)
    checkout_url = Column(Text, nullable=True)
    line_items = Column(JSON, default=list)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="checkout_orders")

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


class MarketplaceProduct(Base):
    __tablename__ = "marketplace_products"

    id = Column(Integer, primary_key=True, index=True)
    system_number = Column(String(32), nullable=False, unique=True, index=True)
    seller_user_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    created_by_admin_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    source_type = Column(String(50), nullable=False, default="user_upload")
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    price_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="usd")
    category = Column(String(100), nullable=False, default="uncategorized")
    tier = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="draft")
    visibility = Column(String(50), nullable=False, default="private")
    approval_status = Column(String(50), nullable=False, default="pending_review")
    inventory_type = Column(String(50), nullable=False, default="unlimited")
    quantity = Column(Integer, nullable=True)
    is_digital = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    primary_image_id = Column(Integer, ForeignKey("marketplace_product_images.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

    seller = relationship("Customer", foreign_keys=[seller_user_id], back_populates="marketplace_products")
    images = relationship(
        "MarketplaceProductImage",
        foreign_keys="MarketplaceProductImage.product_id",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    primary_image = relationship("MarketplaceProductImage", foreign_keys=[primary_image_id], post_update=True)


class MarketplaceProductImage(Base):
    __tablename__ = "marketplace_product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("marketplace_products.id"), nullable=False, index=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    file_path = Column(Text, nullable=True)
    file_url = Column(Text, nullable=False)
    alt_text = Column(String(255), nullable=True)
    sort_order = Column(Integer, default=0)
    is_primary = Column(Boolean, default=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    mime_type = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("MarketplaceProduct", foreign_keys=[product_id], back_populates="images")
    uploader = relationship("Customer", foreign_keys=[uploaded_by_user_id], back_populates="marketplace_uploaded_images")


class MarketplaceAdSlot(Base):
    __tablename__ = "marketplace_ad_slots"

    id = Column(Integer, primary_key=True, index=True)
    slot_key = Column(String(120), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    placement = Column(String(120), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    image_url = Column(Text, nullable=True)
    link_url = Column(Text, nullable=True)
    html_content = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketplaceThemeSetting(Base):
    __tablename__ = "marketplace_theme_settings"

    id = Column(Integer, primary_key=True, index=True)
    theme_name = Column(String(120), nullable=False)
    primary_color = Column(String(30), nullable=True)
    accent_color = Column(String(30), nullable=True)
    background_style = Column(Text, nullable=True)
    card_style = Column(Text, nullable=True)
    font_family = Column(String(255), nullable=True)
    hero_image_url = Column(Text, nullable=True)
    logo_url = Column(Text, nullable=True)
    custom_css = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketplaceNumberSequence(Base):
    __tablename__ = "marketplace_number_sequence"

    id = Column(Integer, primary_key=True, index=True)
    prefix = Column(String(40), nullable=False, unique=True, index=True)
    last_number = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database setup
def get_engine(database_url: str, **kwargs):
    return create_engine(database_url, **kwargs)

def get_session_maker(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(engine):
    Base.metadata.create_all(bind=engine)
    _ensure_json_columns(engine)
    _ensure_project_customer_column(engine)
    _ensure_customer_profile_columns(engine)
    _ensure_default_admin_customer(engine)
    _ensure_marketplace_number_sequence(engine)


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


def _ensure_customer_profile_columns(engine):
    inspector = inspect(engine)
    if "customers" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("customers")}
    columns = {
        "full_name": "VARCHAR(255)",
        "company_name": "VARCHAR(255)",
        "address_line1": "VARCHAR(255)",
        "address_line2": "VARCHAR(255)",
        "city": "VARCHAR(120)",
        "state": "VARCHAR(120)",
        "postal_code": "VARCHAR(50)",
        "country": "VARCHAR(120)",
        "business_phone": "VARCHAR(50)",
        "business_address_line1": "VARCHAR(255)",
        "business_address_line2": "VARCHAR(255)",
        "business_city": "VARCHAR(120)",
        "business_state": "VARCHAR(120)",
        "business_postal_code": "VARCHAR(50)",
        "business_country": "VARCHAR(120)",
        "tax_id": "VARCHAR(120)",
        "is_admin": "BOOLEAN DEFAULT 0",
    }
    missing = [(name, type_name) for name, type_name in columns.items() if name not in existing]
    if not missing:
        return

    with engine.begin() as connection:
        for name, type_name in missing:
            connection.execute(text(f"ALTER TABLE customers ADD COLUMN {name} {type_name}"))


def _ensure_default_admin_customer(engine):
    inspector = inspect(engine)
    if "customers" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("customers")}
    if "is_admin" not in existing:
        return

    with engine.begin() as connection:
        admin_count = connection.execute(text("SELECT COUNT(*) FROM customers WHERE is_admin = 1")).scalar() or 0
        if admin_count:
            return
        first_id = connection.execute(text("SELECT id FROM customers ORDER BY id ASC LIMIT 1")).scalar()
        if first_id:
            connection.execute(text("UPDATE customers SET is_admin = 1 WHERE id = :id"), {"id": first_id})


def _ensure_marketplace_number_sequence(engine):
    inspector = inspect(engine)
    if "marketplace_number_sequence" not in inspector.get_table_names():
        return

    with engine.begin() as connection:
        existing = connection.execute(
            text("SELECT id FROM marketplace_number_sequence WHERE prefix = :prefix LIMIT 1"),
            {"prefix": "OW-MKT"},
        ).scalar()
        if existing:
            return
        connection.execute(
            text(
                """
                INSERT INTO marketplace_number_sequence (prefix, last_number, created_at, updated_at)
                VALUES (:prefix, :last_number, :created_at, :updated_at)
                """
            ),
            {
                "prefix": "OW-MKT",
                "last_number": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        )
