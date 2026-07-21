from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, JSON, ForeignKey, BigInteger, UniqueConstraint, inspect, text
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
    ga4_measurement_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    crawls = relationship("CrawlJob", back_populates="project")
    audits = relationship("AuditReport", back_populates="project")
    lifecycle_jobs = relationship("LifecycleJob", back_populates="project")
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
    orb_memories = relationship("OrbUserMemory", back_populates="customer", cascade="all, delete-orphan")
    orb_recent_contexts = relationship("OrbRecentContext", back_populates="customer", cascade="all, delete-orphan")
    orb_tool_caches = relationship("OrbToolCache", back_populates="customer", cascade="all, delete-orphan")
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


class OrbUserMemory(Base):
    __tablename__ = "orb_user_memory"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    category = Column(String(80), nullable=False, index=True)
    key = Column(String(160), nullable=False, index=True)
    value = Column(Text, nullable=False)
    source = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    enabled = Column(Boolean, default=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="orb_memories")


class OrbRecentContext(Base):
    __tablename__ = "orb_recent_context"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    session_key = Column(String(120), nullable=False, index=True)
    summary = Column(Text, nullable=False, default="")
    turn_count = Column(Integer, default=0)
    last_source = Column(String(255), nullable=False, default="website_orb")
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="orb_recent_contexts")


class OrbToolCache(Base):
    __tablename__ = "orb_tool_cache"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    scope = Column(String(255), nullable=False, index=True)
    tool = Column(String(120), nullable=False, index=True)
    input_hash = Column(String(64), nullable=False, index=True)
    normalized_input = Column(JSON, default=dict)
    result_summary = Column(JSON, default=dict)
    provenance = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)

    customer = relationship("Customer", back_populates="orb_tool_caches")

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
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    build_order_id = Column(Integer, nullable=True, index=True)
    provider = Column(String(50), nullable=False)
    status = Column(String(50), default="created")
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(10), default="usd")
    provider_order_id = Column(String(255), nullable=True, index=True)
    checkout_url = Column(Text, nullable=True)
    line_items = Column(JSON, default=list)
    error = Column(Text, nullable=True)
    payment_verified_at = Column(DateTime, nullable=True)
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


class LifecycleJob(Base):
    __tablename__ = "lifecycle_jobs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    job_type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="PENDING", index=True)
    phase = Column(String(100), nullable=False, default="queued")
    progress_current = Column(Integer, default=0)
    progress_total = Column(Integer, default=0)
    config = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    evidence_root = Column(Text, nullable=True)
    manifest_hash = Column(String(64), nullable=True, index=True)
    previous_run_id = Column(Integer, nullable=True)
    previous_manifest_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="lifecycle_jobs")
    review_items = relationship("ReviewItem", back_populates="lifecycle_job", cascade="all, delete-orphan")


class ReviewItem(Base):
    __tablename__ = "review_items"

    id = Column(Integer, primary_key=True, index=True)
    lifecycle_job_id = Column(Integer, ForeignKey("lifecycle_jobs.id"), nullable=False, index=True)
    severity = Column(String(30), nullable=False, default="warning")
    category = Column(String(80), nullable=False)
    title = Column(String(255), nullable=False)
    details = Column(JSON, default=dict)
    status = Column(String(30), nullable=False, default="open", index=True)
    reviewer = Column(String(255), nullable=True)
    decision = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    signature_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)

    lifecycle_job = relationship("LifecycleJob", back_populates="review_items")


class OrbsGuestSession(Base):
    __tablename__ = "orbs_guest_sessions"

    id = Column(Integer, primary_key=True, index=True)
    guest_session_id = Column(String(128), nullable=False, unique=True, index=True)
    landing_intent = Column(String(255), nullable=False)
    selected_tier_interest = Column(String(80), nullable=True)
    website_url = Column(Text, nullable=True)
    original_cta_destination = Column(String(500), nullable=False)
    current_onboarding_step = Column(String(80), nullable=False, default="landing")
    completed_onboarding_steps = Column(JSON, default=list)
    non_sensitive_questionnaire_answers = Column(JSON, default=dict)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True, index=True)
    consumed_by_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    merged_project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    merge_idempotency_key = Column(String(255), nullable=True, index=True)
    merge_request_hash = Column(String(64), nullable=True)
    merge_result = Column(JSON, default=dict)


class OrbsOnboardingRecord(Base):
    __tablename__ = "orbs_onboarding_records"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_orbs_onboarding_project"),
        UniqueConstraint("guest_session_id", name="uq_orbs_onboarding_guest_session"),
    )

    id = Column(Integer, primary_key=True, index=True)
    guest_session_id = Column(String(128), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    original_cta_destination = Column(String(500), nullable=False)
    landing_intent = Column(String(255), nullable=False)
    selected_tier_interest = Column(String(80), nullable=True)
    current_onboarding_step = Column(String(80), nullable=False)
    completed_onboarding_steps = Column(JSON, default=list)
    transferred_progress = Column(JSON, default=dict)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrbsBuildOrder(Base):
    __tablename__ = "orbs_build_orders"
    __table_args__ = (UniqueConstraint("project_id", name="uq_orbs_build_order_project"),)

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    current_stage = Column(String(80), nullable=False, default="orbs", index=True)
    stage_status = Column(String(50), nullable=False, default="ready")
    version = Column(Integer, nullable=False, default=1)
    blocking_reason = Column(Text, nullable=True)
    customer_action_required = Column(Text, nullable=True)
    package_product_id = Column(Integer, ForeignKey("marketplace_products.id"), nullable=True, index=True)
    package_sku = Column(String(120), nullable=True, index=True)
    package_tier = Column(String(50), nullable=True)
    questionnaire = Column(JSON, default=dict)
    build_configuration = Column(JSON, default=dict)
    final_order = Column(JSON, default=dict)
    signature = Column(JSON, default=dict)
    checkout_order_id = Column(Integer, ForeignKey("checkout_orders.id"), nullable=True, index=True)
    payment_status = Column(String(50), nullable=False, default="not_started", index=True)
    fulfillment_status = Column(String(50), nullable=False, default="not_started", index=True)
    package_artifact = Column(JSON, default=dict)
    installation = Column(JSON, default=dict)
    launch_verification = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrbsStageEvent(Base):
    __tablename__ = "orbs_stage_events"

    id = Column(Integer, primary_key=True, index=True)
    build_order_id = Column(Integer, ForeignKey("orbs_build_orders.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    action_name = Column(String(120), nullable=True, index=True)
    from_stage = Column(String(80), nullable=True)
    to_stage = Column(String(80), nullable=True)
    snapshot_version = Column(String(120), nullable=False)
    reason_code = Column(String(80), nullable=True, index=True)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class OrbsIdempotencyRecord(Base):
    __tablename__ = "orbs_idempotency_records"
    __table_args__ = (UniqueConstraint("customer_id", "idempotency_key", name="uq_orbs_idempotency_customer_key"),)

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), nullable=False, index=True)
    request_hash = Column(String(64), nullable=False)
    response_status = Column(Integer, nullable=False)
    response_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class OrbsEntitlement(Base):
    __tablename__ = "orbs_entitlements"
    __table_args__ = (UniqueConstraint("build_order_id", name="uq_orbs_entitlement_build_order"),)

    id = Column(Integer, primary_key=True, index=True)
    build_order_id = Column(Integer, ForeignKey("orbs_build_orders.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    checkout_order_id = Column(Integer, ForeignKey("checkout_orders.id"), nullable=False, index=True)
    package_sku = Column(String(120), nullable=False, index=True)
    package_tier = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="active", index=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

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
    _ensure_project_ga4_measurement_column(engine)
    _ensure_customer_profile_columns(engine)
    _ensure_checkout_governor_columns(engine)
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


def _ensure_project_ga4_measurement_column(engine):
    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("projects")}
    if "ga4_measurement_id" in existing:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE projects ADD COLUMN ga4_measurement_id VARCHAR(100)"))


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


def _ensure_checkout_governor_columns(engine):
    inspector = inspect(engine)
    if "checkout_orders" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("checkout_orders")}
    columns = {
        "project_id": "INTEGER",
        "build_order_id": "INTEGER",
        "payment_verified_at": "DATETIME",
    }
    missing = [(name, type_name) for name, type_name in columns.items() if name not in existing]
    if not missing:
        return
    with engine.begin() as connection:
        for name, type_name in missing:
            connection.execute(text(f"ALTER TABLE checkout_orders ADD COLUMN {name} {type_name}"))


def _ensure_default_admin_customer(engine):
    inspector = inspect(engine)
    if "customers" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("customers")}
    if "is_admin" not in existing:
        return

    with engine.begin() as connection:
        admin_filter = "is_admin IS TRUE" if engine.dialect.name == "postgresql" else "is_admin = 1"
        admin_count = connection.execute(text(f"SELECT COUNT(*) FROM customers WHERE {admin_filter}")).scalar() or 0
        if admin_count:
            return
        first_id = connection.execute(text("SELECT id FROM customers ORDER BY id ASC LIMIT 1")).scalar()
        if first_id:
            admin_value = True if engine.dialect.name == "postgresql" else 1
            connection.execute(text("UPDATE customers SET is_admin = :is_admin WHERE id = :id"), {"id": first_id, "is_admin": admin_value})


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
