from datetime import datetime, timedelta
from io import BytesIO, StringIO
import asyncio
import base64
import csv
import hashlib
import importlib.util
import json
import os
import re
import secrets
import shutil
import sqlite3
import sys
import tempfile
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import Counter
from urllib.parse import urlparse

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.analytics.ga4 import GA4Connector
from app.audit.engine import SEOAuditor
from app.core.config import settings
from app.crawler.engine import OrbWeaverCrawler, PageData
from app.orb import scan_semantic_topology
from app.orb.pointer_plot import pointer_plot_map_from_pages
from app.pack_generator import generate_pack_file
from app.services.chrome_devtools import ChromeDevToolsReviewRunner
from app.services.orb_desktop_mcp import DEFAULT_ORB_MCP_TOOLS, ORBDesktopMCPClient
from app.models.database import (
    AuditReport,
    CartItem,
    CheckoutOrder,
    CrawlJob,
    CrawledPage,
    Customer,
    CustomerSession,
    GA4Data,
    MarketplaceAdSlot,
    MarketplaceNumberSequence,
    MarketplaceProduct,
    MarketplaceProductImage,
    MarketplaceThemeSetting,
    OrbRecentContext,
    OrbToolCache,
    OrbUserMemory,
    Project,
    get_engine,
    get_session_maker,
    init_db,
)

DEFAULT_TESSDATA_PATH = Path("/usr/share/tesseract-ocr/5/tessdata")
if not os.environ.get("TESSDATA_PREFIX") and (DEFAULT_TESSDATA_PATH / "eng.traineddata").exists():
    os.environ["TESSDATA_PREFIX"] = str(DEFAULT_TESSDATA_PATH)


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
ORB_TTS_CACHE_ROOT = Path(settings.ORB_TTS_CACHE_DIR)
ORB_TTS_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
ORB_TTS_INFLIGHT_LOCK = asyncio.Lock()
ORB_TTS_INFLIGHT: Dict[str, asyncio.Task] = {}
ORB_TTS_PROVIDER_LOCKS: Dict[str, asyncio.Lock] = {}
logger = logging.getLogger("orb_weaver")
LLM_WARM_STATUS: Dict[str, Any] = {
    "configured": bool(settings.LOCAL_LLM_URL and settings.LOCAL_LLM_MODEL),
    "ready": False,
    "model": settings.LOCAL_LLM_MODEL,
    "checked_at": None,
    "error": None,
}


async def _warm_local_llm() -> None:
    """Load the configured Ollama model and retain it without delaying app startup."""
    if not settings.LOCAL_LLM_URL or not settings.LOCAL_LLM_MODEL:
        return
    try:
        async with httpx.AsyncClient(timeout=min(120.0, max(15.0, settings.LOCAL_LLM_TIMEOUT_SECONDS))) as client:
            response = await client.post(
                settings.LOCAL_LLM_URL,
                json={
                    "model": settings.LOCAL_LLM_MODEL,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": settings.LOCAL_LLM_KEEP_ALIVE,
                    "options": {"num_predict": 1},
                },
            )
            response.raise_for_status()
        LLM_WARM_STATUS.update({
            "ready": True,
            "checked_at": datetime.utcnow().isoformat(),
            "error": None,
        })
    except Exception as exc:
        LLM_WARM_STATUS.update({
            "ready": False,
            "checked_at": datetime.utcnow().isoformat(),
            "error": str(exc)[:240],
        })
        logger.warning("Local LLM warmup failed: %s", exc)


@app.on_event("startup")
async def warm_local_llm_on_startup() -> None:
    asyncio.create_task(_warm_local_llm())

SUBSTRATE_ROOT = Path(settings.ORB_WEAVER_SUBSTRATE_ROOT)
PREFLIGHT_SCANNER_ROOT = Path(__file__).resolve().parent.parent / "Preflight Scanner"
PREFLIGHT_SCANNER_MODULE = PREFLIGHT_SCANNER_ROOT / "preflight_site_scan.py"
ORB_CONTROLLER = None
ORB_DESKTOP_MCP_CLIENT: Optional[ORBDesktopMCPClient] = None


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
    ga4_measurement_id: Optional[str] = None


class ProjectGA4Config(BaseModel):
    ga4_property_id: Optional[str] = None
    ga4_measurement_id: Optional[str] = None
    days: int = Field(default=30, ge=1, le=365)


class CrawlConfig(BaseModel):
    max_pages: int = Field(default=100, ge=1, le=5000)
    delay: float = Field(default=1.0, ge=0.1, le=10.0)
    max_depth: int = Field(default=5, ge=1, le=10)
    tier: str = Field(default="authenticated", pattern="^(free|authenticated)$")
    competitor_domains: List[str] = Field(default_factory=list)
    seed_urls: List[str] = Field(default_factory=list)


class GA4Config(BaseModel):
    property_id: str
    credentials_path: Optional[str] = None
    days: int = Field(default=30, ge=1, le=365)


class CustomerSignup(BaseModel):
    email: str
    password: str = Field(min_length=8)
    full_name: str
    business_name: Optional[str] = None
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    business_phone: Optional[str] = None
    business_address_line1: Optional[str] = None
    business_address_line2: Optional[str] = None
    business_city: Optional[str] = None
    business_state: Optional[str] = None
    business_postal_code: Optional[str] = None
    business_country: Optional[str] = None
    tax_id: Optional[str] = None


class CustomerLogin(BaseModel):
    email: str
    password: str


class WebsiteOrbVoiceResponse(BaseModel):
    transcript: str
    spoken_output: str
    cognitive_pulse: Optional[Dict[str, Any]] = None
    llm_source: str = "local-fallback"
    memory_context: Optional[Dict[str, Any]] = None
    tts_audio_url: Optional[str] = None
    tts_provider: Optional[str] = None
    tts_error: Optional[str] = None


class WebsiteOrbTextRequest(BaseModel):
    transcript: str = Field(..., min_length=1, max_length=1000)
    synthesize_tts: bool = True
    project_id: Optional[str] = None
    target_url: Optional[str] = Field(default=None, max_length=500)


class WebsiteOrbTtsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1200)


class WebsiteOrbTtsResponse(BaseModel):
    text: str
    tts_audio_url: Optional[str] = None
    tts_provider: Optional[str] = None
    tts_error: Optional[str] = None


class WebsiteOrbPointerMapResponse(BaseModel):
    schema: str
    generated_at: Optional[str] = None
    record_count: int = 0
    records: List[Dict[str, Any]] = Field(default_factory=list)
    by_page: Dict[str, List[str]] = Field(default_factory=dict)


class WebsiteOrbPageCapsuleResponse(BaseModel):
    schema: str
    site_name: Optional[str] = None
    domain: Optional[str] = None
    current_url: str
    route: str
    page_purpose: str
    page_summary: Optional[str] = None
    likely_visitor_tasks: List[str] = Field(default_factory=list)
    top_pointer_targets: List[Dict[str, Any]] = Field(default_factory=list)
    secondary_pointer_targets: List[Dict[str, Any]] = Field(default_factory=list)
    relevant_navigation: Dict[str, str] = Field(default_factory=dict)
    relevant_guiderails: List[str] = Field(default_factory=list)


class OrbMemoryUpsert(BaseModel):
    category: str = Field(..., min_length=2, max_length=80)
    key: str = Field(..., min_length=1, max_length=160)
    value: str = Field(..., min_length=1, max_length=2000)
    source: str = Field(default="explicit_user_preference", min_length=2, max_length=255)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CartItemUpsert(BaseModel):
    sku: str
    quantity: int = Field(default=1, ge=1, le=99)


class CheckoutCreate(BaseModel):
    provider: str = Field(pattern="^(stripe|paypal)$")


class PreflightRunConfig(BaseModel):
    output_dir: Optional[str] = None


class PublicPreflightRequest(BaseModel):
    website_url: str = Field(..., min_length=3, max_length=255)


class BrowserReviewRequest(BaseModel):
    website_url: str = Field(..., min_length=3, max_length=255)


class BrowserLabToolRequest(BaseModel):
    tool: str = Field(..., min_length=2, max_length=80)
    params: Dict[str, Any] = Field(default_factory=dict)


class OrbToolRunRequest(BaseModel):
    tool: str = Field(..., min_length=2, max_length=120)
    project_id: Optional[str] = None
    target_url: Optional[str] = Field(default=None, max_length=500)
    transcript: Optional[str] = Field(default=None, max_length=1000)
    mcp_tool: Optional[str] = Field(default=None, max_length=120)
    params: Dict[str, Any] = Field(default_factory=dict)


class TPCPackRequest(BaseModel):
    tier: str = Field(default="basic", pattern="^(basic|enhanced|premium)$")


class MarketplaceProductCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    price_cents: int = Field(default=0, ge=0)
    currency: str = Field(default="usd", min_length=3, max_length=10)
    category: str = Field(default="uncategorized", min_length=1, max_length=100)
    tier: Optional[str] = Field(default=None, max_length=50)
    status: str = Field(default="draft", max_length=50)
    visibility: str = Field(default="private", max_length=50)
    approval_status: str = Field(default="pending_review", max_length=50)
    inventory_type: str = Field(default="unlimited", max_length=50)
    quantity: Optional[int] = Field(default=None, ge=0)
    is_digital: bool = True
    is_featured: bool = False
    sort_order: int = 0
    source_type: Optional[str] = Field(default=None, max_length=50)
    submit_for_approval: bool = False


class MarketplaceProductUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    price_cents: Optional[int] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=10)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    tier: Optional[str] = Field(default=None, max_length=50)
    status: Optional[str] = Field(default=None, max_length=50)
    visibility: Optional[str] = Field(default=None, max_length=50)
    approval_status: Optional[str] = Field(default=None, max_length=50)
    inventory_type: Optional[str] = Field(default=None, max_length=50)
    quantity: Optional[int] = Field(default=None, ge=0)
    is_digital: Optional[bool] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None
    submit_for_approval: bool = False


class MarketplaceProductImageCreate(BaseModel):
    file_path: Optional[str] = None
    file_url: str = Field(min_length=1)
    alt_text: Optional[str] = Field(default=None, max_length=255)
    sort_order: int = 0
    is_primary: bool = False
    width: Optional[int] = Field(default=None, ge=1)
    height: Optional[int] = Field(default=None, ge=1)
    mime_type: Optional[str] = Field(default=None, max_length=120)


class MarketplaceAdSlotUpsert(BaseModel):
    slot_key: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=255)
    placement: str = Field(min_length=1, max_length=120)
    title: Optional[str] = Field(default=None, max_length=255)
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    html_content: Optional[str] = None
    active: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    sort_order: int = 0


class MarketplaceThemeUpsert(BaseModel):
    theme_name: str = Field(min_length=1, max_length=120)
    primary_color: Optional[str] = Field(default=None, max_length=30)
    accent_color: Optional[str] = Field(default=None, max_length=30)
    background_style: Optional[str] = None
    card_style: Optional[str] = None
    font_family: Optional[str] = Field(default=None, max_length=255)
    hero_image_url: Optional[str] = None
    logo_url: Optional[str] = None
    custom_css: Optional[str] = None
    active: bool = True


class MarketplaceProductStatusPatch(BaseModel):
    status: Optional[str] = Field(default=None, max_length=50)
    visibility: Optional[str] = Field(default=None, max_length=50)
    approval_status: Optional[str] = Field(default=None, max_length=50)
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None


MARKETPLACE_ALLOWED_STATUS = {
    "draft",
    "pending_review",
    "approved",
    "active",
    "hidden",
    "rejected",
    "archived",
}

MARKETPLACE_ALLOWED_VISIBILITY = {"private", "public"}
MARKETPLACE_ALLOWED_APPROVAL = {"pending_review", "approved", "rejected"}


def _slugify(value: str) -> str:
    candidate = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return candidate or "marketplace-item"


def _build_unique_marketplace_slug(db: Session, title: str, exclude_id: Optional[int] = None) -> str:
    base = _slugify(title)
    candidate = base
    suffix = 2
    while True:
        query = db.query(MarketplaceProduct).filter(MarketplaceProduct.slug == candidate)
        if exclude_id is not None:
            query = query.filter(MarketplaceProduct.id != exclude_id)
        if query.first() is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


def _next_marketplace_system_number(db: Session, prefix: str = "OW-MKT") -> str:
    sequence = db.query(MarketplaceNumberSequence).filter(MarketplaceNumberSequence.prefix == prefix).first()
    now = datetime.utcnow()
    if not sequence:
        sequence = MarketplaceNumberSequence(prefix=prefix, last_number=0, created_at=now, updated_at=now)
        db.add(sequence)
        db.flush()
    sequence.last_number += 1
    sequence.updated_at = now
    return f"{prefix}-{sequence.last_number:06d}"


def _serialize_marketplace_image(image: MarketplaceProductImage) -> Dict[str, Any]:
    return {
        "id": str(image.id),
        "product_id": str(image.product_id),
        "uploaded_by_user_id": str(image.uploaded_by_user_id) if image.uploaded_by_user_id else None,
        "file_path": image.file_path,
        "file_url": image.file_url,
        "alt_text": image.alt_text,
        "sort_order": image.sort_order,
        "is_primary": bool(image.is_primary),
        "width": image.width,
        "height": image.height,
        "mime_type": image.mime_type,
        "created_at": image.created_at.isoformat() if image.created_at else None,
    }


def _serialize_marketplace_product(product: MarketplaceProduct, include_images: bool = True) -> Dict[str, Any]:
    image_payload = []
    if include_images:
        ordered_images = sorted(product.images or [], key=lambda img: (img.sort_order, img.id))
        image_payload = [_serialize_marketplace_image(image) for image in ordered_images]

    return {
        "id": str(product.id),
        "system_number": product.system_number,
        "seller_user_id": str(product.seller_user_id) if product.seller_user_id else None,
        "created_by_admin_id": str(product.created_by_admin_id) if product.created_by_admin_id else None,
        "source_type": product.source_type,
        "title": product.title,
        "slug": product.slug,
        "description": product.description,
        "price_cents": product.price_cents,
        "currency": product.currency,
        "category": product.category,
        "tier": product.tier,
        "status": product.status,
        "visibility": product.visibility,
        "approval_status": product.approval_status,
        "inventory_type": product.inventory_type,
        "quantity": product.quantity,
        "is_digital": bool(product.is_digital),
        "is_featured": bool(product.is_featured),
        "sort_order": product.sort_order,
        "primary_image_id": str(product.primary_image_id) if product.primary_image_id else None,
        "primary_image_url": product.primary_image.file_url if product.primary_image else None,
        "images": image_payload,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
        "published_at": product.published_at.isoformat() if product.published_at else None,
    }


def _serialize_marketplace_ad_slot(slot: MarketplaceAdSlot) -> Dict[str, Any]:
    return {
        "id": str(slot.id),
        "slot_key": slot.slot_key,
        "name": slot.name,
        "placement": slot.placement,
        "title": slot.title,
        "image_url": slot.image_url,
        "link_url": slot.link_url,
        "html_content": slot.html_content,
        "active": bool(slot.active),
        "starts_at": slot.starts_at.isoformat() if slot.starts_at else None,
        "ends_at": slot.ends_at.isoformat() if slot.ends_at else None,
        "sort_order": slot.sort_order,
        "created_at": slot.created_at.isoformat() if slot.created_at else None,
        "updated_at": slot.updated_at.isoformat() if slot.updated_at else None,
    }


def _serialize_marketplace_theme(theme: MarketplaceThemeSetting) -> Dict[str, Any]:
    return {
        "id": str(theme.id),
        "theme_name": theme.theme_name,
        "primary_color": theme.primary_color,
        "accent_color": theme.accent_color,
        "background_style": theme.background_style,
        "card_style": theme.card_style,
        "font_family": theme.font_family,
        "hero_image_url": theme.hero_image_url,
        "logo_url": theme.logo_url,
        "custom_css": theme.custom_css,
        "active": bool(theme.active),
        "created_at": theme.created_at.isoformat() if theme.created_at else None,
        "updated_at": theme.updated_at.isoformat() if theme.updated_at else None,
    }


def _is_public_marketplace_product(product: MarketplaceProduct) -> bool:
    return bool(
        product.system_number
        and product.status == "active"
        and product.visibility == "public"
        and product.approval_status == "approved"
    )


def _get_marketplace_product_or_404(product_id: int, db: Session) -> MarketplaceProduct:
    product = db.get(MarketplaceProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Marketplace product not found")
    return product


def _get_owned_seller_product_or_404(product_id: int, customer: Customer, db: Session) -> MarketplaceProduct:
    product = db.get(MarketplaceProduct, product_id)
    if not product or product.seller_user_id != customer.id:
        raise HTTPException(status_code=404, detail="Marketplace product not found")
    return product


def _set_primary_product_image(product: MarketplaceProduct, image: MarketplaceProductImage, db: Session):
    images = db.query(MarketplaceProductImage).filter(MarketplaceProductImage.product_id == product.id).all()
    for entry in images:
        entry.is_primary = entry.id == image.id
    product.primary_image_id = image.id


def _validate_marketplace_status_fields(
    status: Optional[str],
    visibility: Optional[str],
    approval_status: Optional[str],
) -> None:
    if status and status not in MARKETPLACE_ALLOWED_STATUS:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if visibility and visibility not in MARKETPLACE_ALLOWED_VISIBILITY:
        raise HTTPException(status_code=400, detail=f"Invalid visibility: {visibility}")
    if approval_status and approval_status not in MARKETPLACE_ALLOWED_APPROVAL:
        raise HTTPException(status_code=400, detail=f"Invalid approval_status: {approval_status}")


SERVICE_CATALOG = {
    "orb-weaver-starter-audit": {
        "sku": "orb-weaver-starter-audit",
        "name": "Starter Website Audit",
        "description": "One website crawl with technical SEO and ORB-readable report output.",
        "unit_amount_cents": 9900,
        "currency": "usd",
    },
    "orb-weaver-growth-audit": {
        "sku": "orb-weaver-growth-audit",
        "name": "Growth Website Audit",
        "description": "Deeper crawl, report compiler output, and prioritized recommendations.",
        "unit_amount_cents": 24900,
        "currency": "usd",
    },
    "orb-weaver-premium-pack": {
        "sku": "orb-weaver-premium-pack",
        "name": "Premium Intelligence Pack",
        "description": "Client pack setup, crawl history, audit exports, and website ORB context.",
        "unit_amount_cents": 49900,
        "currency": "usd",
    },
}


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
        "full_name": customer.full_name,
        "business_name": customer.business_name,
        "company_name": customer.company_name,
        "contact_name": customer.contact_name,
        "phone": customer.phone,
        "address_line1": customer.address_line1,
        "address_line2": customer.address_line2,
        "city": customer.city,
        "state": customer.state,
        "postal_code": customer.postal_code,
        "country": customer.country,
        "business_phone": customer.business_phone,
        "business_address_line1": customer.business_address_line1,
        "business_address_line2": customer.business_address_line2,
        "business_city": customer.business_city,
        "business_state": customer.business_state,
        "business_postal_code": customer.business_postal_code,
        "business_country": customer.business_country,
        "tax_id": customer.tax_id,
        "is_admin": bool(customer.is_admin),
        "status": customer.status,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
        "last_login_at": customer.last_login_at.isoformat() if customer.last_login_at else None,
    }


def _serialize_admin_customer(customer: Customer, db: Session) -> Dict:
    payload = _serialize_customer(customer)
    payload.update(
        {
            "project_count": db.query(Project).filter(Project.customer_id == customer.id).count(),
            "cart_item_count": db.query(CartItem).filter(CartItem.customer_id == customer.id).count(),
            "checkout_order_count": db.query(CheckoutOrder).filter(CheckoutOrder.customer_id == customer.id).count(),
            "last_checkout_status": (
                db.query(CheckoutOrder)
                .filter(CheckoutOrder.customer_id == customer.id)
                .order_by(CheckoutOrder.id.desc())
                .first()
            ).status
            if db.query(CheckoutOrder).filter(CheckoutOrder.customer_id == customer.id).count()
            else None,
        }
    )
    return payload


def require_admin(
    x_admin_token: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[Customer]:
    if settings.ADMIN_TOKEN and x_admin_token and secrets.compare_digest(x_admin_token, settings.ADMIN_TOKEN):
        return db.query(Customer).filter(Customer.is_admin == True).first()  # noqa: E712

    customer = get_current_customer(authorization=authorization, db=db)
    if not customer.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return customer


def _serialize_cart_item(item: CartItem) -> Dict:
    return {
        "id": str(item.id),
        "sku": item.sku,
        "name": item.name,
        "unit_amount_cents": item.unit_amount_cents,
        "currency": item.currency,
        "quantity": item.quantity,
        "line_total_cents": item.unit_amount_cents * item.quantity,
        "metadata": item.metadata_json or {},
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def _cart_payload(customer: Customer, db: Session) -> Dict:
    items = db.query(CartItem).filter(CartItem.customer_id == customer.id).order_by(CartItem.id.asc()).all()
    total = sum(item.unit_amount_cents * item.quantity for item in items)
    return {
        "items": [_serialize_cart_item(item) for item in items],
        "total_amount_cents": total,
        "currency": "usd",
    }


def _serialize_checkout_order(order: CheckoutOrder) -> Dict:
    return {
        "id": str(order.id),
        "provider": order.provider,
        "status": order.status,
        "amount_cents": order.amount_cents,
        "currency": order.currency,
        "provider_order_id": order.provider_order_id,
        "checkout_url": order.checkout_url,
        "line_items": order.line_items or [],
        "error": order.error,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }


async def _create_stripe_checkout(order: CheckoutOrder, customer: Customer) -> Dict:
    if not settings.STRIPE_SECRET_KEY:
        return {"status": "provider_not_configured", "error": "STRIPE_SECRET_KEY is not configured"}

    data = {
        "mode": "payment",
        "success_url": f"{settings.PUBLIC_BASE_URL}/checkout/success?order_id={order.id}",
        "cancel_url": f"{settings.PUBLIC_BASE_URL}/cart?order_id={order.id}",
        "customer_email": customer.email,
        "metadata[orb_weaver_order_id]": str(order.id),
    }
    for index, item in enumerate(order.line_items or []):
        data[f"line_items[{index}][price_data][currency]"] = order.currency
        data[f"line_items[{index}][price_data][product_data][name]"] = item["name"]
        data[f"line_items[{index}][price_data][unit_amount]"] = str(item["unit_amount_cents"])
        data[f"line_items[{index}][quantity]"] = str(item["quantity"])

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://api.stripe.com/v1/checkout/sessions",
            data=data,
            headers={
                "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
                "Stripe-Version": settings.STRIPE_API_VERSION,
            },
        )
    if response.status_code >= 400:
        return {"status": "provider_error", "error": response.text}
    payload = response.json()
    return {"status": "checkout_created", "provider_order_id": payload.get("id"), "checkout_url": payload.get("url")}


async def _create_paypal_checkout(order: CheckoutOrder) -> Dict:
    if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
        return {"status": "provider_not_configured", "error": "PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET are not configured"}

    token = base64.b64encode(f"{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}".encode("utf-8")).decode("ascii")
    async with httpx.AsyncClient(timeout=20) as client:
        token_response = await client.post(
            f"{settings.PAYPAL_API_BASE}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {token}"},
        )
        if token_response.status_code >= 400:
            return {"status": "provider_error", "error": token_response.text}
        access_token = token_response.json().get("access_token")
        order_response = await client.post(
            f"{settings.PAYPAL_API_BASE}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": str(order.id),
                        "amount": {
                            "currency_code": order.currency.upper(),
                            "value": f"{order.amount_cents / 100:.2f}",
                        },
                    }
                ],
                "application_context": {
                    "return_url": f"{settings.PUBLIC_BASE_URL}/checkout/success?order_id={order.id}",
                    "cancel_url": f"{settings.PUBLIC_BASE_URL}/cart?order_id={order.id}",
                },
            },
        )
    if order_response.status_code >= 400:
        return {"status": "provider_error", "error": order_response.text}
    payload = order_response.json()
    approve_url = next((link.get("href") for link in payload.get("links", []) if link.get("rel") == "approve"), None)
    return {"status": "checkout_created", "provider_order_id": payload.get("id"), "checkout_url": approve_url}


def _issue_customer_session(customer: Customer, db: Session) -> Dict:
    token = secrets.token_urlsafe(32)
    session_days = max(1, settings.CUSTOMER_SESSION_EXPIRE_DAYS)
    db.add(
        CustomerSession(
            customer_id=customer.id,
            token_hash=_hash_token(token),
            expires_at=datetime.utcnow() + timedelta(days=session_days),
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


def get_optional_customer(
    authorization: Optional[str],
    db: Session,
) -> Optional[Customer]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return get_current_customer(authorization=authorization, db=db)
    except HTTPException:
        return None


ORB_MEMORY_CATEGORIES = {
    "preferred_name",
    "communication_preference",
    "project_context",
    "scan_context",
    "orb_entitlement",
    "explicit_preference",
    "conversation_summary",
}
ORB_MEMORY_MAX_ITEMS_PER_USER = 80
ORB_MEMORY_SUMMARY_LIMIT = 12
ORB_RECENT_CONTEXT_TTL_DAYS = 14
ORB_RECENT_CONTEXT_MAX_CHARS = 1200
ORB_RECENT_CONTEXT_MAX_LINES = 8
ORB_TOOL_CACHE_DEFAULT_TTL_SECONDS = 900
ORB_PREFLIGHT_TOOL_CACHE_TTL_DAYS = 14
ORB_TOOL_CACHE_SCOPE_PREFIX = "project:"
ORB_SENSITIVE_MEMORY_TERMS = {
    "password",
    "token",
    "secret",
    "payment",
    "card",
    "credit_card",
    "ssn",
    "tax_id",
    "recording",
    "microphone",
    "raw_document",
    "browser_history",
}
ORB_PUBLIC_IDENTITY_ANSWER = (
    "I'm Weaver, the Orb Weaver website guide. I help visitors understand scans, Website ORBs, pointer maps, marketplace options, and deployment readiness."
)


def _normalize_memory_key(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9_.:-]+", "_", value.strip().lower())
    return normalized.strip("_")[:160]


def _is_orb_identity_question(transcript: str) -> bool:
    normalized = re.sub(r"[^a-z0-9' ]+", " ", transcript.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return False
    identity_phrases = {
        "who are you",
        "what are you",
        "what is your purpose",
        "what's your purpose",
        "what do you do",
        "what can you do",
        "tell me about yourself",
        "introduce yourself",
    }
    return any(phrase in normalized for phrase in identity_phrases)


def _neutral_recent_context_line(transcript: str) -> str:
    clean = re.sub(r"\s+", " ", transcript.strip())[:220]
    if not clean:
        return "Visitor intent: Asked the ORB for help."
    return f"Visitor intent: {clean}"


def _validate_memory_payload(payload: OrbMemoryUpsert) -> tuple[str, str]:
    category = payload.category.strip().lower()
    key = _normalize_memory_key(payload.key)
    if category not in ORB_MEMORY_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Unsupported memory category: {payload.category}")
    if not key:
        raise HTTPException(status_code=400, detail="Memory key is required")
    risk_text = f"{category} {key} {payload.source}".lower()
    if any(term in risk_text for term in ORB_SENSITIVE_MEMORY_TERMS):
        raise HTTPException(status_code=400, detail="That memory type is not allowed")
    return category, key


def _serialize_orb_memory(item: OrbUserMemory) -> Dict[str, Any]:
    return {
        "id": str(item.id),
        "category": item.category,
        "key": item.key,
        "value": item.value,
        "source": item.source,
        "confidence": item.confidence,
        "enabled": bool(item.enabled),
        "metadata": item.metadata_json or {},
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "expires_at": item.expires_at.isoformat() if item.expires_at else None,
    }


def _orb_memory_summary(customer: Optional[Customer], db: Session) -> Dict[str, Any]:
    if not customer:
        return {
            "scope": "anonymous_session",
            "durable": False,
            "items": [],
            "recent_context": None,
            "policy": "Anonymous visitors receive only request/session context, not durable account memory.",
        }

    now = datetime.utcnow()
    memories = (
        db.query(OrbUserMemory)
        .filter(
            OrbUserMemory.customer_id == customer.id,
            OrbUserMemory.enabled == True,  # noqa: E712
        )
        .filter(or_(OrbUserMemory.expires_at == None, OrbUserMemory.expires_at > now))  # noqa: E711
        .order_by(OrbUserMemory.updated_at.desc(), OrbUserMemory.id.desc())
        .limit(ORB_MEMORY_SUMMARY_LIMIT)
        .all()
    )
    recent = (
        db.query(OrbRecentContext)
        .filter(
            OrbRecentContext.customer_id == customer.id,
            OrbRecentContext.expires_at > now,
        )
        .order_by(OrbRecentContext.updated_at.desc(), OrbRecentContext.id.desc())
        .first()
    )
    return {
        "scope": "authenticated_user",
        "durable": True,
        "user_id": str(customer.id),
        "items": [_serialize_orb_memory(item) for item in memories],
        "recent_context": {
            "summary": recent.summary,
            "turn_count": recent.turn_count,
            "source": recent.last_source,
            "updated_at": recent.updated_at.isoformat() if recent.updated_at else None,
        }
        if recent
        else None,
        "retention": {
            "profile_memory_max_items": ORB_MEMORY_MAX_ITEMS_PER_USER,
            "memory_summary_limit": ORB_MEMORY_SUMMARY_LIMIT,
            "recent_context_ttl_days": ORB_RECENT_CONTEXT_TTL_DAYS,
            "recent_context_max_chars": ORB_RECENT_CONTEXT_MAX_CHARS,
            "tool_cache_default_ttl_seconds": ORB_TOOL_CACHE_DEFAULT_TTL_SECONDS,
        },
    }


def _upsert_orb_memory(customer: Customer, payload: OrbMemoryUpsert, db: Session) -> OrbUserMemory:
    category, key = _validate_memory_payload(payload)
    item = (
        db.query(OrbUserMemory)
        .filter(
            OrbUserMemory.customer_id == customer.id,
            OrbUserMemory.category == category,
            OrbUserMemory.key == key,
        )
        .first()
    )
    if not item:
        count = db.query(OrbUserMemory).filter(OrbUserMemory.customer_id == customer.id).count()
        if count >= ORB_MEMORY_MAX_ITEMS_PER_USER:
            oldest = (
                db.query(OrbUserMemory)
                .filter(OrbUserMemory.customer_id == customer.id)
                .order_by(OrbUserMemory.updated_at.asc(), OrbUserMemory.id.asc())
                .first()
            )
            if oldest:
                db.delete(oldest)
                db.flush()
        item = OrbUserMemory(customer_id=customer.id, category=category, key=key)
        db.add(item)
    item.value = payload.value.strip()[:2000]
    item.source = payload.source.strip()[:255]
    item.confidence = float(payload.confidence)
    item.enabled = bool(payload.enabled)
    item.metadata_json = dict(payload.metadata or {})
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


def _update_orb_recent_context(customer: Optional[Customer], transcript: str, spoken_output: str, db: Session) -> None:
    if not customer:
        return
    now = datetime.utcnow()
    session_key = "website_orb"
    context = (
        db.query(OrbRecentContext)
        .filter(
            OrbRecentContext.customer_id == customer.id,
            OrbRecentContext.session_key == session_key,
        )
        .first()
    )
    if not context:
        context = OrbRecentContext(customer_id=customer.id, session_key=session_key)
        db.add(context)

    existing_lines = [
        line.strip()
        for line in (context.summary or "").splitlines()
        if line.strip().startswith("Visitor intent:")
    ]
    existing_lines.append(_neutral_recent_context_line(transcript))
    summary = "\n".join(existing_lines[-ORB_RECENT_CONTEXT_MAX_LINES:])
    context.summary = summary[-ORB_RECENT_CONTEXT_MAX_CHARS:]
    context.turn_count = int(context.turn_count or 0) + 1
    context.last_source = "website_orb"
    context.metadata_json = {
        "source": "orb_conversation_summary",
        "bounded": True,
        "format": "neutral_visitor_intent",
        "stores_generated_answers": False,
    }
    context.updated_at = now
    context.expires_at = now + timedelta(days=ORB_RECENT_CONTEXT_TTL_DAYS)
    db.commit()


def _cache_key_for_tool(scope: str, tool: str, normalized_input: Dict[str, Any]) -> str:
    payload = json.dumps({"scope": scope, "tool": tool, "input": normalized_input}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_intent_text(value: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (value or "").lower()).strip()


def _tokenize_intent(value: str) -> Set[str]:
    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "can",
        "do",
        "for",
        "how",
        "i",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "or",
        "the",
        "to",
        "what",
        "you",
    }
    return {word for word in _normalize_intent_text(value).split() if len(word) > 2 and word not in stop_words}


def _project_tool_cache_scope(project_id: str) -> str:
    return f"{ORB_TOOL_CACHE_SCOPE_PREFIX}{project_id}:website_orb_voice"


def _preflight_cache_entries(project: Project, report: Dict[str, Any]) -> List[Dict[str, Any]]:
    pages_scanned = int(report.get("pages_scanned") or 0)
    confidence = float(report.get("confidence") or 0)
    detected = report.get("detected") or {}
    warnings = report.get("warnings") or []
    site_url = report.get("site_url") or _project_target_url(project)
    confidence_percent = max(0, min(100, round(confidence * 100)))
    has_checkout = bool(detected.get("has_checkout") or detected.get("has_products"))
    has_contact = bool(detected.get("has_contact_form") or detected.get("has_booking"))

    return [
        {
            "id": "preflight_status",
            "intents": [
                "what did the scan find",
                "is this site ready",
                "preflight status",
                "scan result",
            ],
            "spoken_output": (
                f"I scanned {pages_scanned} public pages for {project.name or project.domain} "
                f"and found about {confidence_percent}% basic ORB readiness."
            ),
            "facts": {"pages_scanned": pages_scanned, "confidence": confidence, "site_url": site_url},
        },
        {
            "id": "site_boundaries",
            "intents": [
                "did you find checkout",
                "did you find forms",
                "what boundaries did you find",
                "login checkout contact",
            ],
            "spoken_output": (
                "I found checkout or product signals, so premium browser verification is recommended."
                if has_checkout
                else "I did not find checkout as a public blocker in the preflight sample."
            ),
            "facts": {"has_checkout": has_checkout, "has_contact_or_booking": has_contact},
        },
        {
            "id": "recommended_next_step",
            "intents": [
                "what should i do next",
                "next step",
                "recommendation",
                "which orb should i use",
            ],
            "spoken_output": (
                "Start with a Basic Website ORB, then add premium browser verification before deeper tool actions."
                if pages_scanned > 0
                else "Fix public site readability first, then rerun the preflight scan."
            ),
            "facts": {"pages_scanned": pages_scanned, "warnings": warnings[:6]},
        },
        {
            "id": "capability_summary",
            "intents": [
                "what tools can you use",
                "mcp tesseract tools",
                "can you read the page",
                "can you call tools",
            ],
            "spoken_output": "I can use cached preflight answers instantly, and I can fall back to MCP and Tesseract checks when owner tools are enabled.",
            "facts": {"source": "preflight_tool_cache"},
        },
    ]


async def _build_project_tool_cache(
    project: Project,
    report: Dict[str, Any],
    db: Session,
    synthesize_tts: bool = False,
) -> Dict[str, Any]:
    scope = _project_tool_cache_scope(str(project.id))
    expires_at = datetime.utcnow() + timedelta(days=ORB_PREFLIGHT_TOOL_CACHE_TTL_DAYS)
    generated_at = datetime.utcnow().isoformat()
    entries = _preflight_cache_entries(project, report)
    entry_audio: Dict[str, Dict[str, Optional[str]]] = {}

    if synthesize_tts:
        for entry in entries:
            entry_audio[entry["id"]] = await _synthesize_orb_tts(entry["spoken_output"])

    artifact = {
        "schema": "orb_weaver.preflight_tool_cache.v1",
        "project_id": str(project.id),
        "domain": project.domain,
        "generated_at": generated_at,
        "expires_at": expires_at.isoformat(),
        "latency_target_ms": 150,
        "fallback_strategy": "Say a filler line, then call MCP asynchronously for cache misses.",
        "entries": [
            {
                "id": entry["id"],
                "intents": entry["intents"],
                "spoken_output": entry["spoken_output"],
                "facts": entry.get("facts") or {},
                "tts_audio_url": entry_audio.get(entry["id"], {}).get("tts_audio_url"),
                "tts_provider": entry_audio.get(entry["id"], {}).get("tts_provider"),
            }
            for entry in entries
        ],
    }
    root = _ensure_client_pack(project)
    cache_path = root / "website_orb_context" / "tool_cache.json"
    _write_json(cache_path, artifact)
    _init_client_index(_client_index_path(project))
    with sqlite3.connect(_client_index_path(project)) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO context_documents(key, kind, json_path, updated_at) VALUES (?, ?, ?, ?)",
            ("tool_cache", "website_orb_preflight_tool_cache", str(cache_path), generated_at),
        )
    if project.customer_id:
        db.query(OrbToolCache).filter(
            OrbToolCache.scope == scope,
            OrbToolCache.tool == "website_voice_answer",
        ).delete()

        for entry in entries:
            tts_result = entry_audio.get(entry["id"]) or {"tts_audio_url": None, "tts_provider": None, "tts_error": None}
            normalized_input = {
                "entry_id": entry["id"],
                "intents": entry["intents"],
                "intent_tokens": sorted(set().union(*[_tokenize_intent(intent) for intent in entry["intents"]])),
                "project_id": str(project.id),
                "site_url": report.get("site_url") or _project_target_url(project),
            }
            db.add(
                OrbToolCache(
                    customer_id=project.customer_id,
                    scope=scope,
                    tool="website_voice_answer",
                    input_hash=_cache_key_for_tool(scope, "website_voice_answer", normalized_input),
                    normalized_input=normalized_input,
                    result_summary={
                        "entry_id": entry["id"],
                        "spoken_output": entry["spoken_output"],
                        "facts": entry.get("facts") or {},
                        **tts_result,
                    },
                    provenance={
                        "source": "preflight_tool_cache",
                        "schema": "orb_weaver.preflight_tool_cache_entry.v1",
                        "generated_at": generated_at,
                    },
                    expires_at=expires_at,
                )
            )
        db.commit()
    return {"entries": len(entries), "path": str(cache_path), "scope": scope, "expires_at": expires_at.isoformat()}


def _lookup_project_tool_cache(project: Project, transcript: str, db: Session) -> Optional[Dict[str, Any]]:
    query_tokens = _tokenize_intent(transcript)
    if not query_tokens:
        return None
    now = datetime.utcnow()
    rows = (
        db.query(OrbToolCache)
        .filter(
            OrbToolCache.scope == _project_tool_cache_scope(str(project.id)),
            OrbToolCache.tool == "website_voice_answer",
            OrbToolCache.expires_at > now,
        )
        .all()
    )
    best: Optional[Tuple[float, OrbToolCache]] = None
    for row in rows:
        intent_tokens = set((row.normalized_input or {}).get("intent_tokens") or [])
        if not intent_tokens:
            continue
        overlap = query_tokens & intent_tokens
        score = len(overlap) / max(1, min(len(query_tokens), len(intent_tokens)))
        if score >= 0.34 and (best is None or score > best[0]):
            best = (score, row)
    if not best:
        return None
    summary = best[1].result_summary or {}
    return {
        "spoken_output": summary.get("spoken_output") or summary.get("summary"),
        "llm_source": "preflight-tool-cache",
        "cache_entry_id": summary.get("entry_id"),
        "cache_score": round(best[0], 3),
        "tts_audio_url": summary.get("tts_audio_url"),
        "tts_provider": summary.get("tts_provider"),
        "tts_error": summary.get("tts_error"),
    }


def _owned_project(project_id: str, customer: Customer, db: Session) -> Project:
    try:
        project_pk = int(project_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Project not found")

    project = db.get(Project, project_pk)
    if not project or project.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _owned_crawl_job(job_id: str, customer: Customer, db: Session) -> CrawlJob:
    try:
        job_pk = int(job_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Crawl job not found")

    crawl_job = (
        db.query(CrawlJob)
        .join(Project, CrawlJob.project_id == Project.id)
        .filter(CrawlJob.id == job_pk, Project.customer_id == customer.id)
        .first()
    )
    if not crawl_job:
        raise HTTPException(status_code=404, detail="Crawl job not found")
    return crawl_job


def _owned_audit_report(audit_id: str, customer: Customer, db: Session) -> AuditReport:
    try:
        audit_pk = int(audit_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Audit report not found")

    report = (
        db.query(AuditReport)
        .join(Project, AuditReport.project_id == Project.id)
        .filter(AuditReport.id == audit_pk, Project.customer_id == customer.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Audit report not found")
    return report


def _normalize_domain(raw_domain: str) -> str:
    return raw_domain.strip().replace("http://", "").replace("https://", "").rstrip("/")


def _default_project_name(domain: str) -> str:
    parts = [p for p in domain.split(".") if p and p not in {"www", "com", "net", "org", "io", "co"}]
    if not parts:
        return domain
    return " ".join([p.replace("-", " ").capitalize() for p in parts[:2]])


def _serialize_project(project: Project, db: Session) -> Dict:
    report_folder = _project_report_dir(project)
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
        "folder_title": report_folder.name,
        "ga4_property_id": project.ga4_property_id,
        "ga4_measurement_id": project.ga4_measurement_id,
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


def _project_preflight_dir(project: Project) -> Path:
    folder = _project_report_dir(project) / "preflight"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _load_preflight_scanner():
    if not PREFLIGHT_SCANNER_MODULE.is_file():
        raise RuntimeError(f"Preflight scanner not found: {PREFLIGHT_SCANNER_MODULE}")

    module_name = "orb_weaver_preflight_site_scan"
    if module_name in sys.modules:
        module = sys.modules[module_name]
    else:
        sys.path.insert(0, str(PREFLIGHT_SCANNER_ROOT))
        spec = importlib.util.spec_from_file_location(module_name, PREFLIGHT_SCANNER_MODULE)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load preflight scanner module")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

    scanner_cls = getattr(module, "PreflightScanner", None)
    if scanner_cls is None:
        raise RuntimeError("PreflightScanner class not found in preflight scanner module")
    return scanner_cls


async def _run_project_preflight(project: Project, output_dir: Optional[str] = None) -> Dict:
    scanner_cls = _load_preflight_scanner()
    target_output = Path(output_dir).resolve() if output_dir else _project_preflight_dir(project).resolve()
    root_url = project.domain if project.domain.startswith(("http://", "https://")) else f"https://{project.domain}"
    scanner = scanner_cls(root_url=root_url, output_dir=str(target_output))
    report = await scanner.scan()
    report["orb_weaver_project"] = {
        "project_id": str(project.id),
        "domain": project.domain,
        "name": project.name,
        "output_dir": str(target_output),
    }
    _write_json(target_output / "site_preflight_report.json", report)
    return report


async def _run_preflight_url(site_url: str, output_dir: str) -> Dict:
    scanner_cls = _load_preflight_scanner()
    scanner = scanner_cls(root_url=site_url, output_dir=output_dir)
    return await scanner.scan()


def _normalize_public_site_url(raw_url: str) -> str:
    candidate = raw_url.strip()
    if not candidate:
        raise ValueError("Website URL is required")
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if not parsed.netloc or "." not in parsed.netloc:
        raise ValueError("Enter a valid website domain or URL")
    return candidate.rstrip("/")


def _public_preflight_report(scan: Dict) -> Dict:
    detected = scan.get("detected") or {}
    warnings = scan.get("warnings") or []
    pages_scanned = int(scan.get("pages_scanned") or 0)
    confidence = float(scan.get("confidence") or 0)
    fit_score = max(0, min(100, round(confidence * 100)))
    has_auth = bool(detected.get("has_auth_pages"))
    has_checkout = bool(detected.get("has_checkout") or detected.get("has_products"))

    if pages_scanned == 0:
        outcome = "not_ready_any_orb"
        title = "Not Ready for Any ORB"
        summary = "The free preflight could not read enough public site structure to recommend an ORB."
    elif confidence < 0.45 or has_auth or has_checkout:
        outcome = "needs_browser_verification"
        title = "Basic ORB Recommended - Premium Review Required"
        summary = "The site appears ready for a Basic Visitor ORB, but Premium readiness needs browser verification."
    else:
        outcome = "basic_orb_recommended"
        title = "Basic ORB Recommended - Premium Review Required"
        summary = "The free scan found enough public structure to recommend starting with a Basic Visitor ORB."

    return {
        "schema": "orb_weaver.public_preflight.v1",
        "generated_at": datetime.utcnow().isoformat(),
        "site_url": scan.get("site_url"),
        "notice": "The free Preflight Scan is not a full audit. It is a basic readiness check.",
        "outcome": outcome,
        "outcome_title": title,
        "summary": summary,
        "premium_status": "Needs Browser Verification" if outcome == "needs_browser_verification" else title,
        "recommended_next_step": "Start with Basic ORB" if outcome != "not_ready_any_orb" else "Fix site readiness first",
        "primary_cta": "Start with Basic ORB" if outcome != "not_ready_any_orb" else "Request Manual Review",
        "secondary_ctas": ["Request Premium Review", "Create Account to Save Report", "Download Basic Report"],
        "fit_score": fit_score,
        "complexity": scan.get("complexity") or "medium",
        "install_path": "basic_orb_with_browser_verification" if outcome == "needs_browser_verification" else outcome,
        "reasons": warnings[:6] or ["The free scan completed without a major blocker."],
        "likely_orb_benefits": [
            "Guide visitors toward important pages and next actions.",
            "Answer basic questions from readable public content.",
            "Create a cleaner path for support, booking, sales, or service questions.",
        ],
        "basic_checks": {
            "site_loaded": pages_scanned > 0,
            "https_checked": str(scan.get("site_url") or "").startswith("https://"),
            "sample_pages_read": pages_scanned,
            "sitemap_detected": bool(detected.get("sitemap_xml")),
            "robots_detected": bool(detected.get("robots_txt")),
            "contact_or_conversion_signals": bool(detected.get("has_contact_form") or detected.get("has_booking") or detected.get("has_products")),
            "login_or_checkout_detected": bool(has_auth or has_checkout),
            "sample_broken_link_count": len(scan.get("broken_links") or []),
        },
        "limited_findings": {
            "cms_or_framework": detected.get("cms_framework") or "unknown",
            "existing_chat_widget": bool(detected.get("existing_chat_widget")),
            "forms_detected": bool(detected.get("has_contact_form")),
            "products_detected": bool(detected.get("has_products")),
            "booking_detected": bool(detected.get("has_booking")),
            "blog_detected": bool(detected.get("has_blog")),
            "sitemap_url_count": int(scan.get("sitemap_url_count") or 0),
            "warnings": warnings[:4],
        },
        "next_steps": [
            "Start with the Basic Visitor ORB.",
            "Request Premium Review to verify browser-rendered content, protected routes, checkout, login, and install safety.",
            "Create a free Orb Weaver account to save the report.",
        ],
    }


async def _transcribe_with_faster_whisper(audio: UploadFile) -> str:
    content = await audio.read()
    if not content:
        raise HTTPException(status_code=400, detail="No audio was received")

    filename = audio.filename or "website-orb.webm"
    content_type = audio.content_type or "application/octet-stream"
    stt_urls = [settings.FASTER_WHISPER_STT_URL]
    if settings.FASTER_WHISPER_STT_URL == "http://127.0.0.1:9000/stt":
        stt_urls.append("http://127.0.0.1:9880/stt")

    last_error = None
    payload: Dict[str, Any] = {}
    for stt_url in stt_urls:
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    stt_url,
                    files={"file": (filename, content, content_type)},
                )
                response.raise_for_status()
                payload = response.json()
                break
        except httpx.HTTPError as exc:
            last_error = exc
    else:
        raise HTTPException(status_code=502, detail=f"Faster-whisper STT failed: {last_error}")

    transcript = str(payload.get("text") or "").strip()
    if not transcript:
        raise HTTPException(status_code=422, detail="Faster-whisper did not return a transcript")
    return transcript

def _load_orb_controller():
    global ORB_CONTROLLER
    if ORB_CONTROLLER is not None:
        return ORB_CONTROLLER

    root = Path(settings.ORB_ASSISTANT_ROOT).expanduser()
    if not root.is_absolute():
        root = (Path(__file__).resolve().parent / root).resolve()
    src = root / "src"
    if not src.exists():
        raise RuntimeError(f"ORB cognition path not found: {src}")

    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    if str(root.parent) not in sys.path:
        sys.path.insert(0, str(root.parent))

    previous_cwd = Path.cwd()
    try:
        os.chdir(src)
        from Orb_Assistant.src.orb_controller import SF_ORB_Controller

        ORB_CONTROLLER = SF_ORB_Controller()
    finally:
        os.chdir(previous_cwd)
    return ORB_CONTROLLER


def _orb_capabilities() -> Dict[str, Any]:
    root = Path(settings.ORB_ASSISTANT_ROOT).expanduser()
    if not root.is_absolute():
        root = (Path(__file__).resolve().parent / root).resolve()
    current_src = root / "src"
    legacy_electron_src = root / "electron" / "src"
    chrome_tool = shutil.which(settings.CHROME_DEVTOOLS_CLI) or shutil.which("npx")
    tesseract_bin = shutil.which("tesseract")
    tessdata_path = Path(os.environ.get("TESSDATA_PREFIX") or "")
    website_tesseract_ready = bool(tesseract_bin and (tessdata_path / "eng.traineddata").exists())
    windows_tesseract_path = Path("/mnt/c/Program Files/Tesseract-OCR/tesseract.exe")
    windows_tesseract_available = windows_tesseract_path.exists()
    desktop_mcp_root = Path(settings.ORB_DESKTOP_MCP_ROOT).expanduser()
    desktop_mcp_server = desktop_mcp_root / "orb_mcp_server.py"
    desktop_mcp_available = bool(settings.ORB_DESKTOP_MCP_ENABLED and desktop_mcp_server.exists())

    return {
        "schema": "orb_weaver.website_orb_capabilities.v1",
        "orb_id": "ORB_WEAVER_SHOWCASE_ORB_V1",
        "role": "website_orb_showcase",
        "product_boundary": {
            "demo_orb_mcp_access": True,
            "default_customer_website_orb_mcp_access": False,
            "advanced_customer_adapters_require_explicit_configuration": True,
            "desktop_orb_primary_mcp_home": True,
            "statement": (
                "Orb Weaver's demo ORB may use Desktop/MCP tools to showcase the ecosystem. "
                "Installed customer Website ORBs run from their site package, target map, "
                "compiled intent cache, voice assets, and approved website context unless "
                "an advanced adapter is deliberately configured."
            ),
        },
        "cognition_source": str(current_src if current_src.exists() else legacy_electron_src),
        "current_orb_source_available": current_src.exists(),
        "legacy_electron_source_available": legacy_electron_src.exists(),
        "tesseract": {
            "available": website_tesseract_ready,
            "binary": tesseract_bin,
            "tessdata_prefix": str(tessdata_path) if website_tesseract_ready else None,
            "website_runtime": {
                "available": website_tesseract_ready,
                "binary": tesseract_bin,
                "tessdata_prefix": str(tessdata_path) if website_tesseract_ready else None,
                "purpose": "WSL/Linux website scanning and localized pointer verification",
            },
            "windows_app_runtime": {
                "available": windows_tesseract_available,
                "binary": str(windows_tesseract_path) if windows_tesseract_available else None,
                "purpose": "Direct Windows and Tauri application OCR",
            },
        },
        "local_llm": dict(LLM_WARM_STATUS),
        "chrome_devtools_mcp": {
            "enabled": settings.CHROME_DEVTOOLS_ENABLED,
            "public_enabled": settings.CHROME_DEVTOOLS_PUBLIC_ENABLED,
            "available": bool(chrome_tool),
            "runner": settings.CHROME_DEVTOOLS_CLI,
        },
        "orb_desktop_mcp": {
            "enabled": settings.ORB_DESKTOP_MCP_ENABLED,
            "available": desktop_mcp_available,
            "root": str(desktop_mcp_root),
            "server": str(desktop_mcp_server),
            "runner": settings.ORB_DESKTOP_MCP_PYTHON,
            "relay_url": settings.ORB_DESKTOP_MCP_URL,
            "transport": "http_relay" if settings.ORB_DESKTOP_MCP_URL else "direct_stdio",
        },
        "voice": {
            "browser_speech_recognition": "client_detected",
            "browser_speech_synthesis": False,
            "recorded_audio_stt_url": settings.FASTER_WHISPER_STT_URL,
            "text_query_low_latency": True,
            "tts_primary": "kokoro",
            "tts_primary_configured": bool(settings.ORB_TTS_KOKORO_URL),
            "tts_primary_url": settings.ORB_TTS_KOKORO_URL,
            "tts_fallback": "qwen" if settings.ORB_TTS_QWEN_URL else None,
            "tts_fallback_url": settings.ORB_TTS_QWEN_URL,
        },
        "tools": [
            "public_preflight",
            "website_voice",
            "website_text",
            "dockstation_websocket_handoff",
            "chrome_devtools_mcp_optional",
            "rdrive_orb_desktop_mcp" if desktop_mcp_available else "rdrive_orb_desktop_mcp_missing",
            "tesseract_ocr_available" if tesseract_bin else "tesseract_ocr_missing_python_binding",
        ],
    }


def _orb_tool_catalog(customer: Customer) -> Dict[str, Any]:
    capabilities = _orb_capabilities()
    chrome_enabled = bool(settings.CHROME_DEVTOOLS_ENABLED and capabilities["chrome_devtools_mcp"]["available"])
    desktop_mcp_enabled = bool(capabilities.get("orb_desktop_mcp", {}).get("available"))
    desktop_mcp_tools = DEFAULT_ORB_MCP_TOOLS
    if desktop_mcp_enabled:
        try:
            listed = _orb_desktop_mcp_client().list_tools().get("tools") or []
            names = [tool.get("name") for tool in listed if isinstance(tool, dict) and tool.get("name")]
            if names:
                desktop_mcp_tools = names
        except Exception:
            desktop_mcp_enabled = False
    return {
        "schema": "orb_weaver.orb_tool_catalog.v1",
        "orb_id": capabilities["orb_id"],
        "scope": "orb_weaver_showcase_authenticated_owner",
        "product_boundary": capabilities.get("product_boundary"),
        "customer_id": str(customer.id),
        "tools": [
            {
                "id": "capabilities",
                "label": "ORB Capability Probe",
                "description": "Inspect current ORB source, voice, OCR, and MCP availability.",
                "requires_project": False,
                "available": True,
            },
            {
                "id": "project_preflight",
                "label": "Project Preflight",
                "description": "Run the deterministic site readiness scanner and refresh the fast ORB voice cache.",
                "requires_project": True,
                "available": True,
            },
            {
                "id": "project_tool_cache",
                "label": "Pre-Flight Tool Cache",
                "description": "Build page-specific cached voice answers from the latest project preflight report.",
                "requires_project": True,
                "available": True,
            },
            {
                "id": "project_browser_review",
                "label": "Project Browser Review",
                "description": "Run the configured Chrome DevTools MCP browser review for an owned project.",
                "requires_project": True,
                "available": chrome_enabled,
            },
            {
                "id": "semantic_topology",
                "label": "Semantic Topology Scan",
                "description": "Map links, forms, and data-orb targets from a target URL.",
                "requires_project": False,
                "available": True,
            },
            {
                "id": "website_text",
                "label": "ORB Text Cognition",
                "description": "Ask the real ORB cognition wrapper to answer a text task.",
                "requires_project": False,
                "available": True,
            },
            {
                "id": "chrome_devtools_mcp",
                "label": "Showcase Chrome DevTools MCP Tool",
                "description": "Run an allow-listed Chrome DevTools MCP command for the Orb Weaver demo/development ORB.",
                "requires_project": False,
                "available": chrome_enabled,
                "mcp_tools": [
                    "new_page",
                    "take_snapshot",
                    "list_console_messages",
                    "list_network_requests",
                    "take_screenshot",
                    "lighthouse_audit",
                ],
            },
            {
                "id": "rdrive_orb_mcp",
                "label": "Showcase Desktop ORB MCP Tool",
                "description": "Run the real Desktop ORB MCP server for Orb Weaver showcase/development use.",
                "requires_project": False,
                "available": desktop_mcp_enabled,
                "mcp_tools": desktop_mcp_tools,
            },
            {
                "id": "visual_audit",
                "label": "Showcase Visual OCR Audit",
                "description": "Capture visible browser state through Desktop MCP/OCR for the Orb Weaver demo ORB or explicitly configured advanced adapters.",
                "requires_project": False,
                "available": desktop_mcp_enabled,
                "mcp_tools": ["orb_browser_screenshot", "orb_ocr_screen"],
            },
        ],
        "capabilities": capabilities,
    }


ORB_ADMIN_ONLY_TOOLS = frozenset({
    "chrome_devtools_mcp",
    "rdrive_orb_mcp",
    "visual_audit",
})


def _require_orb_tool_permission(customer: Customer, tool: str) -> None:
    if tool in ORB_ADMIN_ONLY_TOOLS and not bool(customer.is_admin):
        raise HTTPException(
            status_code=403,
            detail="This ORB tool is restricted to Orb Weaver administrators",
        )


def _cache_orb_tool_result(
    db: Session,
    customer: Customer,
    scope: str,
    tool: str,
    normalized_input: Dict[str, Any],
    result: Dict[str, Any],
) -> None:
    try:
        cache_item = OrbToolCache(
            customer_id=customer.id,
            scope=scope,
            tool=tool,
            input_hash=_cache_key_for_tool(scope, tool, normalized_input),
            normalized_input=normalized_input,
            result_summary={
                "status": result.get("status"),
                "summary": result.get("summary") or result.get("spoken_output") or result.get("reason"),
            },
            provenance={
                "source": "orb_tool_dispatcher",
                "schema": result.get("schema"),
                "generated_at": result.get("generated_at") or datetime.utcnow().isoformat(),
            },
            expires_at=datetime.utcnow() + timedelta(seconds=ORB_TOOL_CACHE_DEFAULT_TTL_SECONDS),
        )
        db.add(cache_item)
        db.commit()
    except Exception:
        db.rollback()


def _project_target_url(project: Project) -> str:
    domain = (project.domain or "").strip()
    if domain.startswith(("http://", "https://")):
        return domain
    return f"https://{domain}"


async def _run_orb_tool(payload: OrbToolRunRequest, customer: Customer, db: Session) -> Dict[str, Any]:
    tool = payload.tool.strip()
    _require_orb_tool_permission(customer, tool)
    generated_at = datetime.utcnow().isoformat()
    pulse = _orb_cognitive_pulse(f"Run ORB tool: {tool}")
    normalized_input = payload.model_dump()
    project: Optional[Project] = None
    if payload.project_id:
        project = _owned_project(payload.project_id, customer, db)

    result: Dict[str, Any]
    if tool == "capabilities":
        result = {
            "schema": "orb_weaver.orb_tool_result.v1",
            "status": "completed",
            "tool": tool,
            "generated_at": generated_at,
            "result": _orb_capabilities(),
        }
    elif tool == "project_preflight":
        if not project:
            raise HTTPException(status_code=400, detail="project_id is required for project_preflight")
        report = await _run_project_preflight(project)
        preserve_client_preflight_intelligence(project, report)
        cache_summary = await _build_project_tool_cache(
            project,
            report,
            db,
            synthesize_tts=bool(payload.params.get("synthesize_tts")),
        )
        result = {
            "schema": "orb_weaver.orb_tool_result.v1",
            "status": "completed",
            "tool": tool,
            "generated_at": generated_at,
            "project_id": str(project.id),
            "summary": {
                "pages_scanned": report.get("pages_scanned"),
                "confidence": report.get("confidence"),
                "warnings": len(report.get("warnings") or []),
                "tool_cache": cache_summary,
            },
            "result": report,
        }
    elif tool == "project_tool_cache":
        if not project:
            raise HTTPException(status_code=400, detail="project_id is required for project_tool_cache")
        preflight_path = _client_intelligence_root(project) / "website_orb_context" / "site_preflight_report.json"
        if preflight_path.exists():
            report = json.loads(preflight_path.read_text(encoding="utf-8"))
        else:
            report = await _run_project_preflight(project)
            preserve_client_preflight_intelligence(project, report)
        cache_summary = await _build_project_tool_cache(
            project,
            report,
            db,
            synthesize_tts=bool(payload.params.get("synthesize_tts")),
        )
        result = {
            "schema": "orb_weaver.orb_tool_result.v1",
            "status": "completed",
            "tool": tool,
            "generated_at": generated_at,
            "project_id": str(project.id),
            "summary": cache_summary,
            "result": cache_summary,
        }
    elif tool == "project_browser_review":
        if not project:
            raise HTTPException(status_code=400, detail="project_id is required for project_browser_review")
        if not settings.CHROME_DEVTOOLS_ENABLED:
            raise HTTPException(status_code=403, detail="Chrome DevTools browser verification is not enabled")
        review = _chrome_devtools_runner().review(_project_target_url(project), label=f"orb_tool_project_{project.id}")
        result = {
            "schema": "orb_weaver.orb_tool_result.v1",
            "status": review.get("status", "completed"),
            "tool": tool,
            "generated_at": generated_at,
            "project_id": str(project.id),
            "summary": review.get("summary"),
            "result": review,
        }
    elif tool == "semantic_topology":
        target_url = payload.target_url or (_project_target_url(project) if project else None)
        if not target_url:
            raise HTTPException(status_code=400, detail="target_url or project_id is required for semantic_topology")
        topology = scan_semantic_topology(target_url)
        result = {
            "schema": "orb_weaver.orb_tool_result.v1",
            "status": "completed" if topology.get("valid") else "failed",
            "tool": tool,
            "generated_at": generated_at,
            "summary": topology.get("counts"),
            "result": topology,
        }
    elif tool == "website_text":
        transcript = (payload.transcript or "").strip()
        if not transcript:
            raise HTTPException(status_code=400, detail="transcript is required for website_text")
        memory_context = _orb_memory_summary(customer, db)
        response = await _llm_orb_spoken_output(transcript, pulse, memory_context)
        result = {
            "schema": "orb_weaver.orb_tool_result.v1",
            "status": "completed",
            "tool": tool,
            "generated_at": generated_at,
            "transcript": transcript,
            "spoken_output": response["spoken_output"],
            "llm_source": response["llm_source"],
        }
    elif tool == "chrome_devtools_mcp":
        if not settings.CHROME_DEVTOOLS_ENABLED:
            raise HTTPException(status_code=403, detail="Chrome DevTools MCP is not enabled")
        allowed = {
            "new_page",
            "take_snapshot",
            "list_console_messages",
            "list_network_requests",
            "take_screenshot",
            "lighthouse_audit",
        }
        mcp_tool = (payload.mcp_tool or "").strip()
        if mcp_tool not in allowed:
            raise HTTPException(status_code=400, detail=f"Unsupported MCP tool: {mcp_tool}")
        mcp_result = _chrome_devtools_runner().run_tool(mcp_tool, dict(payload.params), label=f"orb_tool_{mcp_tool}")
        result = {
            "schema": "orb_weaver.orb_tool_result.v1",
            "status": mcp_result.get("status", "completed"),
            "tool": tool,
            "mcp_tool": mcp_tool,
            "generated_at": generated_at,
            "result": mcp_result,
        }
    elif tool == "rdrive_orb_mcp":
        if not settings.ORB_DESKTOP_MCP_ENABLED:
            raise HTTPException(status_code=403, detail="R-drive ORB MCP is not enabled")
        mcp_tool = (payload.mcp_tool or "").strip()
        if mcp_tool not in set(DEFAULT_ORB_MCP_TOOLS):
            raise HTTPException(status_code=400, detail=f"Unsupported R-drive ORB MCP tool: {mcp_tool}")
        mcp_result = _orb_desktop_mcp_client().call_tool(mcp_tool, dict(payload.params))
        result = {
            "schema": "orb_weaver.orb_tool_result.v1",
            "status": "failed" if mcp_result.get("isError") else "completed",
            "tool": tool,
            "mcp_tool": mcp_tool,
            "generated_at": generated_at,
            "result": mcp_result,
        }
    elif tool == "visual_audit":
        if not settings.ORB_DESKTOP_MCP_ENABLED:
            raise HTTPException(status_code=403, detail="R-drive ORB MCP is not enabled")
        client = _orb_desktop_mcp_client()
        if payload.target_url:
            client.call_tool("orb_browser_navigate", {"url": payload.target_url})
        screenshot = client.call_tool("orb_browser_screenshot", dict(payload.params.get("screenshot_args") or {}))
        ocr = client.call_tool("orb_ocr_screen", dict(payload.params.get("ocr_args") or {}))
        ocr_text = json.dumps(ocr, default=str)
        expected_text = str(payload.params.get("expected_text") or "").strip()
        api_value = str(payload.params.get("api_value") or "").strip()
        checks = {
            "expected_text_visible": bool(expected_text and expected_text.lower() in ocr_text.lower()) if expected_text else None,
            "api_value_visible": bool(api_value and api_value.lower() in ocr_text.lower()) if api_value else None,
        }
        mismatch = any(value is False for value in checks.values())
        result = {
            "schema": "orb_weaver.orb_tool_result.v1",
            "status": "warning" if mismatch else "completed",
            "tool": tool,
            "generated_at": generated_at,
            "summary": {
                "visual_consistency": "mismatch" if mismatch else "not_enough_expected_data" if not expected_text and not api_value else "matched",
                "checks": checks,
            },
            "result": {
                "target_url": payload.target_url,
                "screenshot": screenshot,
                "ocr": ocr,
                "checks": checks,
            },
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown ORB tool: {tool}")

    result["cognitive_pulse"] = pulse
    _cache_orb_tool_result(db, customer, "authenticated_owner", tool, normalized_input, result)
    return result


def _orb_cognitive_pulse(transcript: str) -> Optional[Dict[str, Any]]:
    try:
        controller = _load_orb_controller()
        thought = controller.cognitively_emerge({
            "type": "website_voice_query",
            "content": transcript,
            "coordinates": [0, 0],
            "velocity": 0.0,
            "intent": "visitor_voice_assistance",
        })
        if hasattr(thought, "pulse"):
            pulse = thought.pulse()
        else:
            pulse = thought
        return pulse if isinstance(pulse, dict) else {"result": str(pulse)}
    except Exception as exc:
        return {"cognitive_mode": "FALLBACK", "error": str(exc), "glow_intensity": 0.62}


def _fallback_orb_spoken_output(
    transcript: str,
    pulse: Optional[Dict[str, Any]],
    memory_context: Optional[Dict[str, Any]] = None,
    website_context: Optional[Dict[str, Any]] = None,
) -> str:
    normalized = transcript.lower()
    mode = (pulse or {}).get("cognitive_mode") or "READY"
    memory_items = (memory_context or {}).get("items") or []
    site_name = (website_context or {}).get("site_name") or (website_context or {}).get("brand")
    site_role = (website_context or {}).get("orb_role")
    preferred_name = next(
        (
            item.get("value")
            for item in memory_items
            if item.get("category") == "preferred_name" and item.get("value")
        ),
        None,
    )
    if preferred_name and any(term in normalized for term in ("remember", "know me", "who am i", "my name")):
        return f"I remember that you prefer to be addressed as {preferred_name}."
    if site_name and any(term in normalized for term in ("where am i", "what site", "what website", "where are you")):
        return f"You are on {site_name}, and I am here to help visitors understand and use this site."
    if site_role and any(term in normalized for term in ("your job", "what do you do", "help me", "what are you for")):
        return str(site_role).strip()[:240]
    if "preflight" in normalized or "scan" in normalized:
        return "I can run a public Preflight scan now. It checks basic Website ORB readiness without requiring an account."
    if "tool" in normalized or "mcp" in normalized or "tesseract" in normalized:
        return "My showcase tools are Preflight, voice cognition, optional Chrome DevTools MCP review, and local Tesseract OCR readiness."
    if "basic" in normalized or "premium" in normalized:
        return "Basic ORBs handle public visitor guidance. Premium adds deeper browser verification, install review, and richer owner controls."
    if "market" in normalized or "product" in normalized:
        return "Orb Weaver Marketplace sells compatible ORB skins, upgrades, diagnostics, scan bundles, and future approved behavior packs."
    return "I am online and ready. I can demonstrate public Preflight, ORB cognition, voice, and deployment readiness."


def _website_weaver_capabilities(website_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Public-only capability registry supplied to the Website Weaver runtime."""
    has_pointer_map = bool(
        website_context
        and website_context.get("domain")
        and _load_pointer_records_for_domain(str(website_context["domain"]))
    )
    return [
        {
            "id": "website_text_answer",
            "display_name": "Website answer",
            "description": "Answer from approved website context and the current route record.",
            "allowed_audience": "public",
            "required_fields": ["transcript", "target_url"],
            "safe_to_run_without_confirmation": True,
            "requires_confirmation": False,
            "route_or_endpoint": "/api/orb/website-text",
            "available_now": True,
            "affects_state": False,
            "failure_message": "I cannot answer that reliably from the available website context.",
        },
        {
            "id": "website_voice_answer",
            "display_name": "Website voice answer",
            "description": "Transcribe a visitor question and return an approved spoken answer.",
            "allowed_audience": "public",
            "required_fields": ["audio", "target_url"],
            "safe_to_run_without_confirmation": True,
            "requires_confirmation": False,
            "route_or_endpoint": "/api/orb/website-voice",
            "available_now": True,
            "affects_state": False,
            "failure_message": "Voice is unavailable right now, but the site can still provide visual guidance.",
        },
        {
            "id": "public_preflight_scan",
            "display_name": "Public Preflight",
            "description": "Run the public Website ORB readiness scan for a visitor-supplied URL.",
            "allowed_audience": "public",
            "required_fields": ["url"],
            "safe_to_run_without_confirmation": False,
            "requires_confirmation": True,
            "route_or_endpoint": "/api/public/preflight",
            "available_now": True,
            "affects_state": True,
            "failure_message": "I could not run Preflight; the visitor can open the Preflight page and try again.",
        },
        {
            "id": "marketplace_guidance",
            "display_name": "Marketplace guidance",
            "description": "Explain verified public marketplace products and direct the visitor to the marketplace.",
            "allowed_audience": "public",
            "required_fields": [],
            "safe_to_run_without_confirmation": True,
            "requires_confirmation": True,
            "route_or_endpoint": "/marketplace",
            "available_now": True,
            "affects_state": False,
            "failure_message": "I can explain the marketplace, but I cannot complete a purchase for the visitor.",
        },
        {
            "id": "pointer_guidance_if_target_verified",
            "display_name": "Verified pointer guidance",
            "description": "Select a known page target; the pointer runtime must verify it before movement.",
            "allowed_audience": "public",
            "required_fields": ["target_id", "current_url"],
            "safe_to_run_without_confirmation": True,
            "requires_confirmation": True,
            "route_or_endpoint": "/api/orb/pointer-map",
            "available_now": has_pointer_map,
            "affects_state": False,
            "failure_message": "I can explain where to go, but I cannot verify a safe pointer target on this page.",
        },
        {
            "id": "human_escalation_if_requested",
            "display_name": "Human escalation",
            "description": "Offer a governed handoff when the visitor explicitly asks for a person.",
            "allowed_audience": "public",
            "required_fields": ["visitor_consent"],
            "safe_to_run_without_confirmation": False,
            "requires_confirmation": True,
            "route_or_endpoint": None,
            "available_now": False,
            "affects_state": True,
            "failure_message": "Human handoff is not connected yet; I can explain the available contact path.",
        },
    ]


def _build_website_weaver_envelope(
    website_context: Optional[Dict[str, Any]],
    page_capsule: Optional[Dict[str, Any]],
    transcript: str,
) -> Dict[str, Any]:
    """Assemble the single source of operational guiderails for public Website Weaver."""
    context = website_context or {}
    capsule = page_capsule or {}
    current_page = {
        "current_url": capsule.get("current_url") or context.get("current_url"),
        "route": capsule.get("route") or _route_from_url(context.get("current_url")),
        "page_purpose": capsule.get("page_purpose"),
        "page_summary": capsule.get("page_summary"),
        "likely_visitor_tasks": (capsule.get("likely_visitor_tasks") or [])[:5],
        "top_pointer_targets": (capsule.get("top_pointer_targets") or [])[:3],
    }
    return {
        "identity": {
            "name": "Weaver",
            "role": "Public Website ORB for Orb Weaver; website consultant, guide, and explainer.",
            "not_roles": ["generic chatbot", "Desktop CALI", "navigation authority"],
        },
        "job": context.get("orb_role") or "Help visitors understand and safely use this website.",
        "current_page": current_page,
        "site_intelligence": {
            "site_name": context.get("site_name") or context.get("brand"),
            "domain": context.get("domain"),
            "site_summary": context.get("site_summary"),
            "primary_user_tasks": (context.get("primary_user_tasks") or [])[:8],
            "key_facts": (context.get("key_facts") or [])[:8],
            "route_hints": context.get("route_hints") or {},
            "pointer_matches": _lookup_pointer_context(context, transcript),
        },
        "memory_architecture": {
            "site_world_skg": {
                "role": "Durable compiled knowledge of the website, routes, facts, targets, permissions, and relationships.",
                "source": context.get("source") or "compiled_site_world",
                "lookup_policy": "Load the current route record; do not rebuild the site-world during a visitor turn.",
            },
            "user_memory": {
                "role": "Explicit preferences and bounded recent context for an authenticated account only.",
                "public_visitor_policy": "Anonymous visitors receive no durable personal memory.",
                "sensitive_data_policy": "Never store credentials, payment data, raw recordings, or private browsing history.",
            },
            "cognitive_vaults": {
                "apriori": "Protected doctrine and invariant operating laws.",
                "posteriori": "Reusable resolved cognitive patterns for faster future reasoning.",
                "authority": "Advisory cognition only; tool permissions and live target verification remain authoritative.",
            },
            "improvement_loop": [
                "Use new approved scans and rescans to refresh the site-world/SKG.",
                "Use explicit authenticated preferences to improve relevant answers.",
                "Use bounded interaction summaries and posteriori resolutions to reduce repeated reasoning cost.",
                "Never promote guessed facts or runtime pointer corrections into authoritative memory automatically.",
            ],
        },
        "capabilities": _website_weaver_capabilities(context),
        "policy": {
            "answer_directly_when": "Known context answers the question and no tool or state change is needed.",
            "use_tools_when": "A matching available public capability is needed and its confirmation rule is satisfied.",
            "pointer_rule": "Choose only a known target; pointer runtime must verify it. If unverified, answer voice-only.",
            "navigation_rule": "Require confirmation before cross-page navigation and never click for the visitor.",
            "escalation_rule": "Escalate only on explicit request; frustration alone triggers an offer.",
            "prohibitions": [
                "Never invent tools, routes, prices, targets, reports, scan results, or completed actions.",
                "Never claim a tool ran unless the runtime returned a successful result.",
                "Never expose owner or admin data to public visitors.",
            ],
            "site_boundaries": context.get("answer_boundaries") or [],
        },
    }


async def _llm_orb_spoken_output(
    transcript: str,
    pulse: Optional[Dict[str, Any]],
    memory_context: Optional[Dict[str, Any]] = None,
    website_context: Optional[Dict[str, Any]] = None,
    page_capsule: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    if _is_orb_identity_question(transcript):
        return {"spoken_output": ORB_PUBLIC_IDENTITY_ANSWER, "llm_source": "deterministic-identity"}

    fallback = _fallback_orb_spoken_output(transcript, pulse, memory_context, website_context)
    if not settings.LOCAL_LLM_URL or not settings.LOCAL_LLM_MODEL:
        return {"spoken_output": fallback, "llm_source": "local-fallback"}

    pulse_brief = {
        "cognitive_mode": (pulse or {}).get("cognitive_mode"),
        "final_verdict": (pulse or {}).get("final_verdict"),
        "epistemic_alignment": (pulse or {}).get("epistemic_alignment"),
        "glow_intensity": (pulse or {}).get("glow_intensity"),
    }
    memory_brief = {
        "scope": (memory_context or {}).get("scope"),
        "durable": (memory_context or {}).get("durable"),
        "items": ((memory_context or {}).get("items") or [])[:6],
        "recent_context": (memory_context or {}).get("recent_context") if (memory_context or {}).get("durable") else None,
    }
    weaver_envelope = _build_website_weaver_envelope(website_context, page_capsule, transcript)
    prompt = (
        "You are Weaver. Obey the Website Weaver envelope as the authoritative operating contract.\n"
        f"Website Weaver envelope: {json.dumps(weaver_envelope, ensure_ascii=False)}\n"
        f"Safe account memory, only if relevant: {json.dumps(memory_brief, ensure_ascii=False)}\n"
        f"Advisory cognitive pulse: {json.dumps(pulse_brief, ensure_ascii=False)}\n"
        f"Visitor question: {transcript}\n"
        "Answer the visitor as Weaver in exactly one short spoken sentence. "
        "Follow tool availability and confirmation rules, never claim an action ran, and use no markdown or chat-UI language."
    )
    try:
        timeout_seconds = min(120.0, max(5.0, float(settings.LOCAL_LLM_TIMEOUT_SECONDS or 60.0)))
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                settings.LOCAL_LLM_URL,
                json={
                    "model": settings.LOCAL_LLM_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": settings.LOCAL_LLM_KEEP_ALIVE,
                    "options": {
                        "num_ctx": min(4096, max(512, int(settings.LOCAL_LLM_NUM_CTX or 1024))),
                        "num_predict": min(160, max(16, int(settings.LOCAL_LLM_NUM_PREDICT or 64))),
                        "temperature": min(1.0, max(0.0, float(settings.LOCAL_LLM_TEMPERATURE or 0.35))),
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
        spoken = str(payload.get("response") or payload.get("text") or "").strip()
        return {"spoken_output": spoken or fallback, "llm_source": "local-llm"}
    except Exception:
        return {"spoken_output": fallback, "llm_source": "local-fallback"}


def _content_type_for_audio_format(audio_format: str) -> str:
    normalized = (audio_format or "wav").lower().strip(".")
    if normalized == "mp3":
        return "audio/mpeg"
    if normalized == "ogg":
        return "audio/ogg"
    if normalized == "webm":
        return "audio/webm"
    if normalized == "flac":
        return "audio/flac"
    return "audio/wav"


def _audio_extension_for_content(content_type: str, audio_format: str) -> str:
    normalized_type = (content_type or "").lower()
    if "mpeg" in normalized_type or "mp3" in normalized_type:
        return "mp3"
    if "ogg" in normalized_type:
        return "ogg"
    if "webm" in normalized_type:
        return "webm"
    if "flac" in normalized_type:
        return "flac"
    return (audio_format or "wav").lower().strip(".") or "wav"


def _tts_payload(mode: str, text: str, model: str, voice: str, audio_format: str) -> Dict[str, Any]:
    normalized_mode = (mode or "openai").lower()
    if normalized_mode in {"kokoro-direct", "kokoro_direct", "kokoro"}:
        return {
            "text": text,
            "voice": voice,
            "format": audio_format,
            "speed": 1.05,
        }
    if normalized_mode in {"qwen-custom", "qwen_custom", "custom"}:
        return {
            "text": text,
            "mode": "custom",
            "speaker": voice,
            "language": settings.ORB_TTS_QWEN_LANGUAGE,
            "instruct": settings.ORB_TTS_QWEN_INSTRUCT,
            "format": audio_format,
        }
    if normalized_mode == "generic":
        return {
            "text": text,
            "model": model,
            "voice": voice,
            "format": audio_format,
        }
    return {
        "model": model,
        "input": text,
        "voice": voice,
        "response_format": audio_format,
    }


def _visitor_safe_tts_unavailable() -> Dict[str, Optional[str]]:
    return {
        "tts_audio_url": None,
        "tts_provider": None,
        "tts_error": "Voice is temporarily unavailable, but I can still help here in text.",
    }


def _extract_base64_audio(payload: Dict[str, Any]) -> Optional[str]:
    candidates = [
        payload.get("audio"),
        payload.get("audio_base64"),
        payload.get("audioContent"),
        (payload.get("data") or {}).get("audio") if isinstance(payload.get("data"), dict) else None,
        (payload.get("output") or {}).get("audio") if isinstance(payload.get("output"), dict) else None,
    ]
    for value in candidates:
        if not isinstance(value, str) or not value.strip():
            continue
        if value.startswith("data:"):
            return value.split(",", 1)[-1]
        return value
    return None


def _extract_audio_url(payload: Dict[str, Any]) -> Optional[str]:
    candidates = [
        payload.get("audio_url"),
        payload.get("url"),
        (payload.get("data") or {}).get("url") if isinstance(payload.get("data"), dict) else None,
        (payload.get("output") or {}).get("url") if isinstance(payload.get("output"), dict) else None,
    ]
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value
    return None


async def _call_tts_provider(
    provider: str,
    url: Optional[str],
    api_key: Optional[str],
    payload_mode: str,
    text: str,
    model: str,
    voice: str,
    audio_format: str,
) -> Dict[str, Any]:
    if not url:
        raise RuntimeError(f"{provider} TTS URL is not configured")

    headers: Dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = _tts_payload(payload_mode, text, model, voice, audio_format)
    provider_lock = ORB_TTS_PROVIDER_LOCKS.setdefault(provider, asyncio.Lock())
    async with httpx.AsyncClient(timeout=settings.ORB_TTS_TIMEOUT_SECONDS) as client:
        async with provider_lock:
            response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        content_type = response.headers.get("content-type") or _content_type_for_audio_format(audio_format)

        if content_type.startswith("audio/") or content_type in {"application/octet-stream"}:
            return {
                "provider": provider,
                "audio": response.content,
                "content_type": content_type,
                "extension": _audio_extension_for_content(content_type, audio_format),
            }

        result = response.json()
        encoded_audio = _extract_base64_audio(result)
        if encoded_audio:
            return {
                "provider": provider,
                "audio": base64.b64decode(encoded_audio),
                "content_type": _content_type_for_audio_format(audio_format),
                "extension": audio_format.lower().strip(".") or "wav",
            }

        audio_url = _extract_audio_url(result)
        if audio_url:
            audio_response = await client.get(audio_url, headers=headers)
            audio_response.raise_for_status()
            fetched_type = audio_response.headers.get("content-type") or _content_type_for_audio_format(audio_format)
            return {
                "provider": provider,
                "audio": audio_response.content,
                "content_type": fetched_type,
                "extension": _audio_extension_for_content(fetched_type, audio_format),
            }

    raise RuntimeError(f"{provider} TTS response did not include audio")


def _cached_tts_result(digest: str, provider: str) -> Optional[Dict[str, Optional[str]]]:
    cached_matches = sorted(ORB_TTS_CACHE_ROOT.glob(f"{digest}.*"))
    if not cached_matches:
        return None
    return {
        "tts_audio_url": f"/api/orb/tts/{cached_matches[0].name}",
        "tts_provider": provider,
        "tts_error": None,
    }


def _tts_cache_probe(text: str) -> Dict[str, Any]:
    clean_text = text.strip()
    probes = []
    for provider, url, _api_key, _payload_mode, model, voice, _audio_format in [
        (
            "kokoro",
            settings.ORB_TTS_KOKORO_URL,
            settings.ORB_TTS_KOKORO_API_KEY,
            settings.ORB_TTS_KOKORO_PAYLOAD_MODE,
            settings.ORB_TTS_KOKORO_MODEL,
            settings.ORB_TTS_KOKORO_VOICE,
            settings.ORB_TTS_KOKORO_FORMAT,
        ),
    ]:
        if not url or not clean_text:
            continue
        digest = hashlib.sha256(f"{provider}:{model}:{voice}:{clean_text}".encode("utf-8")).hexdigest()[:24]
        probes.append({
            "provider": provider,
            "digest": digest,
            "hit": bool(_cached_tts_result(digest, provider)),
        })
    return {"hit": any(probe["hit"] for probe in probes), "probes": probes}


async def _synthesize_orb_tts_uncached(
    clean_text: str,
    digest: str,
    provider: str,
    url: Optional[str],
    api_key: Optional[str],
    payload_mode: str,
    model: str,
    voice: str,
    audio_format: str,
) -> Dict[str, Optional[str]]:
    cached = _cached_tts_result(digest, provider)
    if cached:
        return cached

    result = await _call_tts_provider(
        provider=provider,
        url=url,
        api_key=api_key,
        payload_mode=payload_mode,
        text=clean_text,
        model=model,
        voice=voice,
        audio_format=audio_format,
    )
    extension = result["extension"] or "wav"
    audio_id = f"{digest}.{extension}"
    audio_path = ORB_TTS_CACHE_ROOT / audio_id
    audio_path.write_bytes(result["audio"])
    return {
        "tts_audio_url": f"/api/orb/tts/{audio_id}",
        "tts_provider": provider,
        "tts_error": None,
    }


async def _run_tts_singleflight(key: str, factory) -> Dict[str, Optional[str]]:
    async with ORB_TTS_INFLIGHT_LOCK:
        task = ORB_TTS_INFLIGHT.get(key)
        if task is None:
            task = asyncio.create_task(factory())
            ORB_TTS_INFLIGHT[key] = task

    try:
        return await task
    finally:
        async with ORB_TTS_INFLIGHT_LOCK:
            if ORB_TTS_INFLIGHT.get(key) is task:
                ORB_TTS_INFLIGHT.pop(key, None)


async def _synthesize_orb_tts(text: str) -> Dict[str, Optional[str]]:
    clean_text = text.strip()
    if not clean_text:
        return _visitor_safe_tts_unavailable()

    providers = [
        (
            "kokoro",
            settings.ORB_TTS_KOKORO_URL,
            settings.ORB_TTS_KOKORO_API_KEY,
            settings.ORB_TTS_KOKORO_PAYLOAD_MODE,
            settings.ORB_TTS_KOKORO_MODEL,
            settings.ORB_TTS_KOKORO_VOICE,
            settings.ORB_TTS_KOKORO_FORMAT,
        ),
    ]

    errors: List[str] = []
    for provider, url, api_key, payload_mode, model, voice, audio_format in providers:
        if not url:
            continue
        digest = hashlib.sha256(
            f"{provider}:{model}:{voice}:{clean_text}".encode("utf-8")
        ).hexdigest()[:24]
        cached = _cached_tts_result(digest, provider)
        if cached:
            return cached

        try:
            return await _run_tts_singleflight(
                f"{provider}:{digest}",
                lambda provider=provider,
                url=url,
                api_key=api_key,
                payload_mode=payload_mode,
                model=model,
                voice=voice,
                audio_format=audio_format,
                digest=digest: _synthesize_orb_tts_uncached(
                    clean_text=clean_text,
                    digest=digest,
                    provider=provider,
                    url=url,
                    api_key=api_key,
                    payload_mode=payload_mode,
                    model=model,
                    voice=voice,
                    audio_format=audio_format,
                ),
            )
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            logger.warning("ORB TTS provider failed", extra={"provider": provider, "error": message})
            errors.append(f"{provider}: {message}")

    return _visitor_safe_tts_unavailable()


def _chrome_devtools_runner() -> ChromeDevToolsReviewRunner:
    return ChromeDevToolsReviewRunner(
        cli=settings.CHROME_DEVTOOLS_CLI,
        output_root=settings.CHROME_DEVTOOLS_OUTPUT_ROOT,
        timeout_seconds=settings.CHROME_DEVTOOLS_TIMEOUT_SECONDS,
        start_args=settings.CHROME_DEVTOOLS_START_ARGS,
        browser_start_cmd=settings.CHROME_DEVTOOLS_BROWSER_START_CMD,
    )


def _orb_desktop_mcp_client() -> ORBDesktopMCPClient:
    global ORB_DESKTOP_MCP_CLIENT
    if ORB_DESKTOP_MCP_CLIENT is None:
        ORB_DESKTOP_MCP_CLIENT = ORBDesktopMCPClient(
            root=settings.ORB_DESKTOP_MCP_ROOT,
            python_bin=settings.ORB_DESKTOP_MCP_PYTHON,
            timeout_seconds=settings.ORB_DESKTOP_MCP_TIMEOUT_SECONDS,
            remote_url=settings.ORB_DESKTOP_MCP_URL,
            remote_token=settings.ORB_DESKTOP_MCP_TOKEN,
        )
    return ORB_DESKTOP_MCP_CLIENT


def _cali_crm_import_dir() -> Path:
    return Path(settings.CALI_CRM_SUBSTRATE_ROOT) / "imports" / "pending"


def _customer_crm_import_record(customer: Customer, db: Session) -> Dict:
    projects = db.query(Project).filter(Project.customer_id == customer.id).all()
    return {
        "schema": "orb_weaver.crm_contact_import.v1",
        "source": "orb_weaver",
        "source_record_id": str(customer.id),
        "name": customer.full_name or customer.contact_name or customer.business_name,
        "type": "orb_weaver_customer",
        "phone": customer.phone or customer.business_phone,
        "email": customer.email,
        "lead_source": "orb_weaver",
        "tags": ["orb_weaver", "website_orb", "customer_base"],
        "metadata_payload": {
            "business_name": customer.business_name,
            "company_name": customer.company_name,
            "status": customer.status,
            "project_count": len(projects),
            "projects": [_serialize_project(project, db) for project in projects],
        },
    }


def _tpc_pack_output_dir(project: Project) -> Path:
    folder = _project_report_dir(project) / "tpc_packs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _build_tpc_pack_scan_data(project: Project, db: Session) -> Dict:
    latest_crawl = db.query(CrawlJob).filter(CrawlJob.project_id == project.id).order_by(CrawlJob.id.desc()).first()
    pages = []
    if latest_crawl:
        pages = [
            {
                "url": page.url,
                "title": page.title,
                "meta_description": page.meta_description,
                "h1": page.h1,
                "word_count": page.word_count,
                "status_code": page.status_code,
                "semantic_analysis": page.semantic_analysis or {},
            }
            for page in db.query(CrawledPage).filter(CrawledPage.crawl_job_id == latest_crawl.id).limit(250).all()
        ]
    return {
        "project": _serialize_project(project, db),
        "latest_crawl": _serialize_crawl_job(latest_crawl, db, include_pages=False) if latest_crawl else None,
        "pages": pages,
        "generated_at": datetime.utcnow().isoformat(),
    }


def _content_disposition(filename: str, disposition: str = "attachment") -> Dict[str, str]:
    safe_disposition = "inline" if disposition == "inline" else "attachment"
    safe_filename = filename.replace("\\", "_").replace("/", "_").replace('"', "")
    return {"Content-Disposition": f'{safe_disposition}; filename="{safe_filename}"'}


def _safe_pack_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip().lower())
    return cleaned.strip("._-") or "unknown_site"


def _domain_from_url(value: Optional[str]) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    candidate = raw if "://" in raw else f"https://{raw}"
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").strip().lower()
    return host[4:] if host.startswith("www.") else host


def _route_from_url(value: Optional[str]) -> str:
    raw = (value or "").strip()
    if not raw:
        return "/"
    candidate = raw if "://" in raw else f"https://{raw}"
    parsed = urlparse(candidate)
    return (parsed.path or "/").rstrip("/") or "/"


def _load_json_if_present(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else None
    except Exception:
        return None
    return None


def _website_context_root(domain: str) -> Optional[Path]:
    repo_root = Path(__file__).resolve().parent.parent
    roots = [
        SUBSTRATE_ROOT,
        repo_root / "substrate",
        Path.cwd().parent / "substrate",
    ]
    seen: Set[str] = set()
    for substrate_root in roots:
        root_key = str(substrate_root.resolve() if substrate_root.exists() else substrate_root)
        if root_key in seen:
            continue
        seen.add(root_key)
        root = substrate_root / "clients" / _safe_pack_name(domain) / "website_orb_context"
        if root.exists():
            return root
    return None


def _load_domain_website_context(target_url: Optional[str]) -> Optional[Dict[str, Any]]:
    domain = _domain_from_url(target_url)
    if not domain:
        return None

    root = _website_context_root(domain)
    if root:
        for filename in ("orb_runtime_context.json", "latest_context.json"):
            payload = _load_json_if_present(root / filename)
            if payload:
                payload.setdefault("domain", domain)
                return payload
    return None


def _score_keyword_match(transcript: str, keywords: List[str]) -> float:
    query_tokens = _tokenize_intent(transcript)
    if not query_tokens:
        return 0.0
    best = 0.0
    for keyword in keywords:
        keyword_tokens = _tokenize_intent(str(keyword))
        if not keyword_tokens:
            continue
        overlap = query_tokens & keyword_tokens
        score = len(overlap) / max(1, min(len(query_tokens), len(keyword_tokens)))
        if score > best:
            best = score
    return best


def _lookup_domain_runtime_tool(
    website_context: Optional[Dict[str, Any]],
    transcript: str,
) -> Optional[Dict[str, Any]]:
    if not website_context:
        return None

    candidates: List[Tuple[float, Dict[str, Any], str]] = []
    for entry in website_context.get("visitor_tools") or []:
        score = _score_keyword_match(transcript, entry.get("keywords") or [])
        if score >= 0.34 and entry.get("spoken_output"):
            candidates.append((score, entry, "orb-runtime-context"))

    domain = website_context.get("domain")
    if domain:
        cache_path = SUBSTRATE_ROOT / "clients" / _safe_pack_name(str(domain)) / "website_orb_context" / "tool_cache.json"
        tool_cache = _load_json_if_present(cache_path) or {}
        for entry in tool_cache.get("entries") or []:
            score = _score_keyword_match(transcript, entry.get("keywords") or entry.get("intents") or [])
            if score >= 0.42 and entry.get("spoken_output"):
                candidates.append((score, entry, "website-tool-cache"))

    if not candidates:
        return None

    score, entry, source = sorted(candidates, key=lambda item: item[0], reverse=True)[0]
    return {
        "spoken_output": str(entry.get("spoken_output") or "").strip(),
        "llm_source": source,
        "cache_entry_id": entry.get("id"),
        "cache_score": round(score, 3),
        "suggested_route": entry.get("suggested_route"),
        "tts_audio_url": entry.get("tts_audio_url"),
        "tts_provider": entry.get("tts_provider"),
        "tts_error": entry.get("tts_error"),
    }


def _pointer_record_text(record: Dict[str, Any]) -> str:
    parts: List[str] = [
        str(record.get("meaning") or ""),
        str(record.get("target_type") or ""),
        str(record.get("page_route") or ""),
    ]
    for key in ("intent_aliases", "direct_aliases", "topic_aliases"):
        parts.extend(str(item) for item in (record.get(key) or []))
    structural = record.get("structural_context") or {}
    parts.extend(
        str(structural.get(key) or "")
        for key in ("landmark", "parent_heading", "tag")
    )
    return " ".join(part for part in parts if part)


def _pointer_summary(record: Dict[str, Any], score: float = 0.0) -> Dict[str, Any]:
    return {
        "target_id": record.get("target_id"),
        "page_route": record.get("page_route"),
        "target_type": record.get("target_type"),
        "meaning": record.get("meaning"),
        "semantic_locator": record.get("semantic_locator"),
        "structural_context": record.get("structural_context") or {},
        "allowed_actions": record.get("allowed_actions") or [],
        "confidence": record.get("confidence"),
        "match_score": round(score, 3),
    }


def _load_pointer_records_for_domain(domain: str) -> List[Dict[str, Any]]:
    root = _website_context_root(domain)
    if not root:
        return []
    pointer_map = _load_json_if_present(root / "pointer_plot_map.json") or {}
    return [record for record in (pointer_map.get("records") or []) if isinstance(record, dict)]


def _lookup_pointer_context(
    website_context: Optional[Dict[str, Any]],
    transcript: str,
    max_records: int = 6,
) -> List[Dict[str, Any]]:
    if not website_context:
        return []
    domain = website_context.get("domain")
    if not domain:
        return []
    records = _load_pointer_records_for_domain(str(domain))
    query_tokens = _tokenize_intent(transcript)
    if not query_tokens:
        return []

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for record in records:
        if not isinstance(record, dict) or record.get("status") not in (None, "active"):
            continue
        record_tokens = _tokenize_intent(_pointer_record_text(record))
        if not record_tokens:
            continue
        overlap = query_tokens & record_tokens
        if not overlap:
            continue
        score = len(overlap) / max(1, min(len(query_tokens), len(record_tokens)))
        if record.get("target_type") in {"nav", "button", "link", "product"}:
            score += 0.08
        if score >= 0.2:
            scored.append((score, record))

    matches = sorted(scored, key=lambda item: item[0], reverse=True)[:max_records]
    return [_pointer_summary(record, score) for score, record in matches]


def _build_page_capsule(target_url: str) -> Dict[str, Any]:
    website_context = _load_domain_website_context(target_url) or {}
    domain = website_context.get("domain") or _domain_from_url(target_url)
    route = _route_from_url(target_url)
    records = _load_pointer_records_for_domain(str(domain))

    def record_route(record: Dict[str, Any]) -> str:
        return _route_from_url(record.get("page_route"))

    route_records = [
        record for record in records
        if record.get("status") in (None, "active") and record_route(record) == route
    ]

    def value_score(record: Dict[str, Any]) -> float:
        target_type = str(record.get("target_type") or "")
        meaning = str(record.get("meaning") or "").lower()
        score = float(record.get("confidence") or 0.5)
        if target_type in {"nav", "button", "form", "product", "link"}:
            score += 0.22
        if any(term in meaning for term in ("preflight", "marketplace", "scan", "pricing", "login", "website orb", "premium", "basic", "diagnostic")):
            score += 0.28
        return score

    ranked = sorted(route_records, key=value_score, reverse=True)
    route_hints = website_context.get("route_hints") or {}
    visitor_tools = website_context.get("visitor_tools") or []
    route_text = " ".join([route, *[str(item.get("id") or "") for item in visitor_tools]])
    likely_tools = [
        item for item in visitor_tools
        if _score_keyword_match(route_text, item.get("keywords") or [item.get("id") or ""]) >= 0.2
    ][:5]
    return {
        "schema": "orb_weaver.current_page_capsule.v1",
        "site_name": website_context.get("site_name"),
        "domain": domain,
        "current_url": target_url,
        "route": route,
        "page_purpose": "Help visitors understand and use this Orb Weaver page.",
        "page_summary": website_context.get("site_summary"),
        "likely_visitor_tasks": [
            item.get("id", "").replace("_", " ")
            for item in likely_tools
            if item.get("id")
        ] or (website_context.get("primary_user_tasks") or [])[:5],
        "top_pointer_targets": [_pointer_summary(record, value_score(record)) for record in ranked[:5]],
        "secondary_pointer_targets": [_pointer_summary(record, value_score(record)) for record in ranked[5:15]],
        "relevant_navigation": route_hints,
        "relevant_guiderails": (website_context.get("answer_boundaries") or [])[:8],
    }


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
        connection.execute(
            "INSERT OR REPLACE INTO context_documents(key, kind, json_path, updated_at) VALUES (?, ?, ?, ?)",
            ("pointer_plot_map", "website_orb_pointer_plot_map", str(_client_intelligence_root(project) / "website_orb_context" / "pointer_plot_map.json"), payload.get("saved_at")),
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
    pointer_plot_map = pointer_plot_map_from_pages(pages)
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
        "pointer_plot_map": pointer_plot_map,
        "website_orb_context": {
            "orb_ready_score": crawl_payload.get("stats", {}).get("avg_orb_semantic_score", 0),
            "authority_flow": crawl_payload.get("authority_flow"),
            "knowledge_graph": crawl_payload.get("knowledge_graph"),
            "competitor_gap": crawl_payload.get("competitor_gap"),
            "template_detection": crawl_payload.get("template_detection"),
            "pointer_plot_map": pointer_plot_map,
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
        pointer_path = root / "website_orb_context" / "pointer_plot_map.json"
        existing_pointer_map = _load_json_if_present(pointer_path) or {}
        new_pointer_map = payload["pointer_plot_map"]
        if int(new_pointer_map.get("record_count") or 0) > 0 or int(existing_pointer_map.get("record_count") or 0) == 0:
            _write_json(pointer_path, new_pointer_map)
        else:
            payload["website_orb_context"]["pointer_plot_map"] = existing_pointer_map
            payload["website_orb_context"]["pointer_map_preservation"] = {
                "status": "preserved_previous_verified_map",
                "rejected_crawl_id": str(crawl_job.id),
                "reason": "new_crawl_produced_zero_pointer_records",
            }
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


def preserve_client_preflight_intelligence(project: Project, report: Dict) -> None:
    root = _ensure_client_pack(project)
    _init_client_index(_client_index_path(project))
    _index_pack_meta(project, root)
    preflight_path = root / "website_orb_context" / "site_preflight_report.json"
    _write_json(preflight_path, report)
    _write_json(root / "current" / "latest_preflight.json", report)
    with sqlite3.connect(_client_index_path(project)) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO context_documents(key, kind, json_path, updated_at) VALUES (?, ?, ?, ?)",
            (
                "site_preflight_report",
                "website_orb_preflight",
                str(preflight_path),
                report.get("scan_timestamp") or datetime.utcnow().isoformat(),
            ),
        )


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
    pointer_summary = _pointer_summary_from_pages(pages)
    if not pages:
        planned_tool_calls = _planned_tool_calls(pointer_summary, pages=pages)
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
            "pointer_summary": pointer_summary,
            "planned_tool_calls": planned_tool_calls,
        }

    load_times = [p.load_time_ms for p in pages if p.load_time_ms is not None]
    content_hashes = [p.content_hash for p in pages if p.content_hash]
    duplicate_hashes = {h for h in content_hashes if content_hashes.count(h) > 1}
    stats = {
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
        "pointer_summary": pointer_summary,
    }
    stats["planned_tool_calls"] = _planned_tool_calls(pointer_summary, stats, pages)
    return stats


def _pointer_summary_from_pages(pages: List[CrawledPage]) -> Dict:
    records = []
    route_ids: Dict[str, List[str]] = {}
    type_counts: Dict[str, int] = {}
    for page in pages:
        page_records = (page.semantic_analysis or {}).get("pointer_plot_records") or []
        if not isinstance(page_records, list):
            continue
        for record in page_records:
            if not isinstance(record, dict) or not record.get("target_id"):
                continue
            target_id = str(record.get("target_id"))
            records.append(record)
            route_ids.setdefault(page.url, []).append(target_id)
            target_type = str(record.get("target_type") or "other")
            type_counts[target_type] = type_counts.get(target_type, 0) + 1

    duplicate_count = sum(1 for count in Counter(str(record.get("target_id")) for record in records).values() if count > 1)
    return {
        "schema": "orb_weaver.pointer_summary.v1",
        "record_count": len(records),
        "routes_with_pointers": len(route_ids),
        "duplicate_target_ids": duplicate_count,
        "target_type_counts": type_counts,
        "status": "passed" if records and duplicate_count == 0 else "needs_review",
    }


def _planned_tool_calls(pointer_summary: Dict, stats: Optional[Dict] = None, pages: Optional[List[CrawledPage]] = None) -> List[Dict[str, Any]]:
    stats = stats or {}
    record_count = int(pointer_summary.get("record_count") or 0)
    duplicate_count = int(pointer_summary.get("duplicate_target_ids") or 0)
    depth_limit_hit = bool(stats.get("depth_limit_hit"))
    max_page_limit_hit = bool(stats.get("max_page_limit_hit"))

    planned = [
        {
            "id": "load_pointer_plot_map",
            "tool": "pointer_plot_map",
            "scope": "basic_customer_orb",
            "trigger": "website_orb_boot",
            "purpose": "Load verified pointable targets for the current site package.",
            "status": "ready" if record_count > 0 and duplicate_count == 0 else "needs_review",
            "requires_mcp": False,
        },
        {
            "id": "resolve_pointer_target",
            "tool": "runtime_pointer_resolver",
            "scope": "basic_customer_orb",
            "trigger": "visitor_intent_match",
            "purpose": "Resolve a cached target record against the live DOM before moving or blooming.",
            "status": "ready" if record_count > 0 and duplicate_count == 0 else "blocked_until_pointer_map_passes",
            "requires_mcp": False,
        },
        {
            "id": "build_preflight_tool_cache",
            "tool": "build_preflight_tool_cache",
            "scope": "basic_customer_orb",
            "trigger": "post_scan_or_pack_build",
            "purpose": "Compile fast static voice answers and route hints without live tool dependencies.",
            "status": "ready",
            "requires_mcp": False,
        },
    ]

    if duplicate_count > 0 or record_count == 0:
        planned.append(
            {
                "id": "repair_pointer_map",
                "tool": "self_scan_or_pointer_extraction",
                "scope": "owner_build_pipeline",
                "trigger": "pointer_summary_needs_review",
                "purpose": "Rerun rendered extraction or repair duplicate/missing target identities before deployment.",
                "status": "recommended",
                "requires_mcp": False,
            }
        )

    if depth_limit_hit or max_page_limit_hit:
        planned.append(
            {
                "id": "expanded_route_scan",
                "tool": "authenticated_crawler",
                "scope": "owner_build_pipeline",
                "trigger": "crawl_limit_hit",
                "purpose": "Increase page/depth coverage for a denser pointer map on important routes.",
                "status": "recommended",
                "requires_mcp": False,
            }
        )

    planned.append(
        {
            "id": "visual_audit",
            "tool": "visual_audit",
            "scope": "orb_weaver_showcase_or_advanced_adapter",
            "trigger": "owner_enabled_visual_verification",
            "purpose": "Compare API/DOM expectations with rendered visual text for high-confidence diagnostics.",
            "status": "gated",
            "requires_mcp": True,
        }
    )
    return planned + _planned_pointer_tool_calls_from_pages(pages or [])


def _planned_pointer_tool_calls_from_pages(pages: List[CrawledPage], limit: int = 80) -> List[Dict[str, Any]]:
    planned: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str, str]] = set()

    for page in pages:
        page_records = (page.semantic_analysis or {}).get("pointer_plot_records") or []
        if not isinstance(page_records, list):
            continue
        for record in page_records:
            if len(planned) >= limit:
                return planned
            if not isinstance(record, dict) or not record.get("target_id"):
                continue

            target_type = str(record.get("target_type") or "other")
            meaning = str(record.get("meaning") or "")
            context = record.get("structural_context") if isinstance(record.get("structural_context"), dict) else {}
            section = str(context.get("parent_heading") or context.get("landmark") or "page")
            route = str(record.get("page_route") or page.url)
            plan = _planned_tool_for_pointer_target(target_type, meaning)
            key = (route, section, plan["tool"])
            if key in seen:
                continue
            seen.add(key)

            planned.append(
                {
                    "id": f"pointer_{hashlib.sha256('|'.join(key).encode('utf-8')).hexdigest()[:12]}",
                    "tool": plan["tool"],
                    "scope": plan["scope"],
                    "trigger": plan["trigger"],
                    "purpose": plan["purpose"],
                    "status": plan["status"],
                    "requires_mcp": plan["requires_mcp"],
                    "route": route,
                    "section": section[:120],
                    "target_type": target_type,
                    "target_id": str(record.get("target_id")),
                    "anchor_strategy": record.get("anchor_strategy"),
                }
            )
    return planned


def _planned_tool_for_pointer_target(target_type: str, meaning: str) -> Dict[str, Any]:
    text = f"{target_type} {meaning}".lower()
    if target_type == "form_field" or any(term in text for term in ("contact", "support", "email", "phone", "quote", "lead")):
        return {
            "tool": "contact_or_lead_context",
            "scope": "advanced_customer_adapter",
            "trigger": "visitor_intent_on_form_or_contact_section",
            "purpose": "Prepare a verified handoff/contact context for the visitor without submitting forms by default.",
            "status": "anticipated",
            "requires_mcp": False,
        }
    if any(term in text for term in ("price", "pricing", "cart", "checkout", "product", "marketplace")):
        return {
            "tool": "commerce_context_lookup",
            "scope": "advanced_customer_adapter",
            "trigger": "visitor_intent_on_pricing_product_or_checkout_section",
            "purpose": "Lookup approved pricing/cart/product context when the deployment has a commerce adapter.",
            "status": "gated",
            "requires_mcp": True,
        }
    if target_type in {"faq_answer", "policy_line"} or any(term in text for term in ("faq", "privacy", "terms", "policy")):
        return {
            "tool": "knowledge_base_answer",
            "scope": "basic_customer_orb",
            "trigger": "visitor_question_on_policy_or_faq_section",
            "purpose": "Answer from the installed website context and point to the verified section.",
            "status": "ready",
            "requires_mcp": False,
        }
    if target_type in {"button", "nav", "download"}:
        return {
            "tool": "pointer_guidance",
            "scope": "basic_customer_orb",
            "trigger": "visitor_intent_on_navigation_or_action_target",
            "purpose": "Move, point, and bloom at the verified target without clicking for the visitor by default.",
            "status": "ready",
            "requires_mcp": False,
        }
    return {
        "tool": "section_context_guidance",
        "scope": "basic_customer_orb",
        "trigger": "visitor_intent_on_verified_section",
        "purpose": "Guide the visitor to the verified section and answer from cached website context.",
        "status": "ready",
        "requires_mcp": False,
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
            tier="free",
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
    project = db.query(Project).filter(Project.id == crawl_job.project_id).first()
    config = crawl_job.config or {}
    stats = {**_compute_stats(pages), **(config.get("stats") or {})}

    payload = {
        "id": str(crawl_job.id),
        "project_id": str(crawl_job.project_id),
        "project_name": project.name if project else None,
        "project_domain": project.domain if project else None,
        "status": crawl_job.status,
        "config": config,
        "created_at": crawl_job.start_time.isoformat() if crawl_job.start_time else None,
        "start_time": crawl_job.start_time.isoformat() if crawl_job.start_time else None,
        "end_time": crawl_job.end_time.isoformat() if crawl_job.end_time else None,
        "pages_crawled": crawl_job.pages_crawled,
        "pages_found": crawl_job.pages_found,
        "errors_count": crawl_job.errors_count,
        "stats": stats,
        "pointer_summary": stats.get("pointer_summary") or _pointer_summary_from_pages(pages),
        "planned_tool_calls": stats.get("planned_tool_calls") or _planned_tool_calls(stats.get("pointer_summary") or {}, stats),
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
    project = getattr(report, "project", None)
    return {
        "id": str(report.id),
        "crawl_job_id": str(report.crawl_job_id) if report.crawl_job_id else None,
        "project": {
            "id": str(project.id),
            "name": project.name,
            "domain": project.domain,
            "ga4_property_id": project.ga4_property_id,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        } if project else None,
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

        def persist_crawl_progress(active_crawler: OrbWeaverCrawler) -> None:
            active_stats = active_crawler.get_crawl_stats()
            crawl_job.pages_crawled = len(active_crawler.crawled_data)
            crawl_job.pages_found = int(active_stats.get("discovered_urls") or active_stats.get("visited_urls") or 0)
            crawl_job.config = {
                **(crawl_job.config or {}),
                "stats": {
                    **((crawl_job.config or {}).get("stats") or {}),
                    **active_stats,
                },
            }
            db.commit()

        crawler = OrbWeaverCrawler(
            max_pages=config.max_pages,
            delay=config.delay,
            max_depth=config.max_depth,
            tier=config.tier,
            progress_callback=persist_crawl_progress,
        )

        start_url = f"https://{project.domain}" if not project.domain.startswith("http") else project.domain
        pages = await crawler.crawl(start_url, seed_urls=config.seed_urls)
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
        crawl_job.pages_found = int(stats.get("discovered_urls") or stats.get("visited_urls") or len(pages))
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
        report_payload["pointer_summary"] = stats.get("pointer_summary") or _pointer_summary_from_pages(pages)
        report_payload["planned_tool_calls"] = stats.get("planned_tool_calls") or _planned_tool_calls(report_payload["pointer_summary"], stats)

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


@app.post("/api/public/preflight")
async def public_preflight(payload: PublicPreflightRequest):
    try:
        site_url = _normalize_public_site_url(payload.website_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        with tempfile.TemporaryDirectory(prefix="orb_public_preflight_") as output_dir:
            scan = await _run_preflight_url(site_url, output_dir)
        report = _public_preflight_report(scan)
        if settings.CHROME_DEVTOOLS_ENABLED and settings.CHROME_DEVTOOLS_PUBLIC_ENABLED:
            report["browser_verification"] = _chrome_devtools_runner().review(site_url, label="public_preflight")
        else:
            report["browser_verification"] = {
                "status": "not_run",
                "reason": "Browser verification is reserved for deeper ORB reviews.",
            }
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Preflight scan failed: {exc}")


@app.post("/api/orb/website-voice", response_model=WebsiteOrbVoiceResponse)
async def website_orb_voice(
    audio: UploadFile = File(...),
    target_url: Optional[str] = Form(default=None),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    route_started = time.perf_counter()
    timings: Dict[str, float] = {}
    request_id = secrets.token_hex(4)

    def mark(label: str, started: float) -> None:
        timings[label] = round((time.perf_counter() - started) * 1000, 1)

    started = time.perf_counter()
    customer = get_optional_customer(authorization=authorization, db=db)
    mark("auth", started)

    started = time.perf_counter()
    transcript = await _transcribe_with_faster_whisper(audio)
    mark("transcription", started)

    started = time.perf_counter()
    memory_context = _orb_memory_summary(customer, db)
    website_context = _load_domain_website_context(target_url)
    if website_context is not None:
        website_context["current_url"] = target_url
    page_capsule = _build_page_capsule(target_url) if target_url else None
    mark("memory_summary", started)

    started = time.perf_counter()
    cognitive_pulse = _orb_cognitive_pulse(transcript)
    mark("cognitive_pulse", started)

    pointer_matches = _lookup_pointer_context(website_context, transcript)
    domain_cache_hit = _lookup_domain_runtime_tool(website_context, transcript)
    if domain_cache_hit and domain_cache_hit.get("spoken_output"):
        spoken_output = domain_cache_hit["spoken_output"]
        tts_cache_before = _tts_cache_probe(spoken_output)
        started = time.perf_counter()
        tts_result = await _synthesize_orb_tts(spoken_output)
        mark("tts", started)
        tts_cache_after = _tts_cache_probe(spoken_output)
        started = time.perf_counter()
        _update_orb_recent_context(customer, transcript, spoken_output, db)
        mark("context_update", started)
        timings["answer_selection"] = 0.0
        timings["total"] = round((time.perf_counter() - route_started) * 1000, 1)
        logger.warning(
            "ORB voice timing %s",
            json.dumps(
                {
                    "request_id": request_id,
                    "transcript": transcript,
                    "target_url": target_url,
                    "llm_source": domain_cache_hit["llm_source"],
                    "cache_entry_id": domain_cache_hit.get("cache_entry_id"),
                    "tts_cache_before": tts_cache_before,
                    "tts_cache_after": tts_cache_after,
                    "tts_provider": tts_result.get("tts_provider"),
                    "timings_ms": timings,
                },
                sort_keys=True,
            ),
        )
        return {
            "transcript": transcript,
            "spoken_output": spoken_output,
            "cognitive_pulse": {
                **(cognitive_pulse or {}),
                "cognitive_mode": "RUNTIME_TOOL_HIT",
                "cache_entry_id": domain_cache_hit.get("cache_entry_id"),
                "cache_score": domain_cache_hit.get("cache_score"),
                "suggested_route": domain_cache_hit.get("suggested_route"),
                "pointer_matches": pointer_matches,
                "glow_intensity": 0.78,
            },
            "llm_source": domain_cache_hit["llm_source"],
            "memory_context": memory_context,
            **tts_result,
        }

    started = time.perf_counter()
    llm_result = await _llm_orb_spoken_output(transcript, cognitive_pulse, memory_context, website_context, page_capsule)
    mark("answer_selection", started)

    tts_cache_before = _tts_cache_probe(llm_result["spoken_output"])
    started = time.perf_counter()
    tts_result = await _synthesize_orb_tts(llm_result["spoken_output"])
    mark("tts", started)
    tts_cache_after = _tts_cache_probe(llm_result["spoken_output"])

    started = time.perf_counter()
    _update_orb_recent_context(customer, transcript, llm_result["spoken_output"], db)
    mark("context_update", started)

    timings["total"] = round((time.perf_counter() - route_started) * 1000, 1)
    logger.warning(
        "ORB voice timing %s",
        json.dumps(
            {
            "request_id": request_id,
            "transcript": transcript,
            "target_url": target_url,
            "llm_source": llm_result["llm_source"],
            "tts_cache_before": tts_cache_before,
            "tts_cache_after": tts_cache_after,
            "tts_provider": tts_result.get("tts_provider"),
            "timings_ms": timings,
            },
            sort_keys=True,
        ),
    )
    return {
        "transcript": transcript,
        "spoken_output": llm_result["spoken_output"],
        "cognitive_pulse": {
            **(cognitive_pulse or {}),
            "pointer_matches": pointer_matches,
        },
        "llm_source": llm_result["llm_source"],
        "memory_context": memory_context,
        **tts_result,
    }


@app.post("/api/orb/website-text", response_model=WebsiteOrbVoiceResponse)
async def website_orb_text(
    payload: WebsiteOrbTextRequest,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    customer = get_optional_customer(authorization=authorization, db=db)
    transcript = payload.transcript.strip()
    memory_context = _orb_memory_summary(customer, db)
    project = _owned_project(payload.project_id, customer, db) if customer and payload.project_id else None
    website_context = _load_domain_website_context(payload.target_url or (_project_target_url(project) if project else None))
    page_capsule = _build_page_capsule(payload.target_url or (_project_target_url(project) if project else "")) if (payload.target_url or project) else None
    if website_context is not None:
        website_context["current_url"] = payload.target_url or (_project_target_url(project) if project else None)
    pointer_matches = _lookup_pointer_context(website_context, transcript)
    cache_hit = _lookup_project_tool_cache(project, transcript, db) if project else None
    if cache_hit and cache_hit.get("spoken_output"):
        tts_result = {
            "tts_audio_url": cache_hit.get("tts_audio_url"),
            "tts_provider": cache_hit.get("tts_provider"),
            "tts_error": cache_hit.get("tts_error"),
        }
        if payload.synthesize_tts and not tts_result["tts_audio_url"]:
            tts_result = await _synthesize_orb_tts(cache_hit["spoken_output"])
        _update_orb_recent_context(customer, transcript, cache_hit["spoken_output"], db)
        return {
            "transcript": transcript,
            "spoken_output": cache_hit["spoken_output"],
            "cognitive_pulse": {
                "cognitive_mode": "TOOL_CACHE_HIT",
                "cache_entry_id": cache_hit.get("cache_entry_id"),
                "cache_score": cache_hit.get("cache_score"),
                "glow_intensity": 0.72,
            },
            "llm_source": cache_hit["llm_source"],
            "memory_context": memory_context,
            **tts_result,
        }
    domain_cache_hit = _lookup_domain_runtime_tool(website_context, transcript)
    if domain_cache_hit and domain_cache_hit.get("spoken_output"):
        tts_result = {
            "tts_audio_url": domain_cache_hit.get("tts_audio_url"),
            "tts_provider": domain_cache_hit.get("tts_provider"),
            "tts_error": domain_cache_hit.get("tts_error"),
        }
        if payload.synthesize_tts and not tts_result["tts_audio_url"]:
            tts_result = await _synthesize_orb_tts(domain_cache_hit["spoken_output"])
        _update_orb_recent_context(customer, transcript, domain_cache_hit["spoken_output"], db)
        return {
            "transcript": transcript,
            "spoken_output": domain_cache_hit["spoken_output"],
            "cognitive_pulse": {
                "cognitive_mode": "RUNTIME_TOOL_HIT",
                "cache_entry_id": domain_cache_hit.get("cache_entry_id"),
                "cache_score": domain_cache_hit.get("cache_score"),
                "suggested_route": domain_cache_hit.get("suggested_route"),
                "pointer_matches": pointer_matches,
                "glow_intensity": 0.78,
            },
            "llm_source": domain_cache_hit["llm_source"],
            "memory_context": memory_context,
            **tts_result,
        }
    cognitive_pulse = _orb_cognitive_pulse(transcript)
    llm_result = await _llm_orb_spoken_output(transcript, cognitive_pulse, memory_context, website_context, page_capsule)
    tts_result = (
        await _synthesize_orb_tts(llm_result["spoken_output"])
        if payload.synthesize_tts
        else {"tts_audio_url": None, "tts_provider": None, "tts_error": None}
    )
    _update_orb_recent_context(customer, transcript, llm_result["spoken_output"], db)
    return {
        "transcript": transcript,
        "spoken_output": llm_result["spoken_output"],
        "cognitive_pulse": {
            **(cognitive_pulse or {}),
            "pointer_matches": pointer_matches,
        },
        "llm_source": llm_result["llm_source"],
        "memory_context": memory_context,
        **tts_result,
    }


@app.get("/api/orb/capabilities")
async def website_orb_capabilities():
    return _orb_capabilities()


@app.get("/api/orb/pointer-map", response_model=WebsiteOrbPointerMapResponse)
async def website_orb_pointer_map(
    domain: Optional[str] = Query(default=None, max_length=255),
    host: Optional[str] = Header(default=None),
    x_forwarded_host: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    raw_domain = domain or x_forwarded_host or host or ""
    raw_domain = raw_domain.split(",")[0].split(":")[0].strip()
    if not raw_domain:
        raise HTTPException(status_code=404, detail="Pointer map domain is unknown")

    context_root = _website_context_root(raw_domain)
    pointer_map: Dict[str, Any] = {}
    if context_root:
        pointer_path = context_root / "pointer_plot_map.json"
        if pointer_path.is_file():
            try:
                pointer_map = json.loads(pointer_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raise HTTPException(status_code=500, detail="Pointer map is unreadable")

    if int(pointer_map.get("record_count") or 0) == 0:
        project = db.query(Project).filter(Project.domain == raw_domain).first()
        if project:
            completed_crawls = (
                db.query(CrawlJob)
                .filter(CrawlJob.project_id == project.id, CrawlJob.status == "completed")
                .order_by(CrawlJob.id.desc())
                .limit(12)
                .all()
            )
            for crawl in completed_crawls:
                recovered = pointer_plot_map_from_pages(
                    db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl.id).all()
                )
                if int(recovered.get("record_count") or 0) == 0:
                    continue
                seen_ids: Set[str] = set()
                unique_records = []
                for record in recovered.get("records") or []:
                    target_id = str(record.get("target_id") or "")
                    if not target_id or target_id in seen_ids:
                        continue
                    seen_ids.add(target_id)
                    unique_records.append(record)
                recovered["records"] = unique_records
                recovered["record_count"] = len(unique_records)
                recovered["by_page"] = {}
                for record in unique_records:
                    recovered["by_page"].setdefault(str(record.get("page_route") or ""), []).append(record["target_id"])
                recovered["recovered_from_crawl_id"] = str(crawl.id)
                pointer_map = recovered
                break

    if int(pointer_map.get("record_count") or 0) == 0:
        raise HTTPException(status_code=404, detail="Pointer map not found")

    return {
        "schema": pointer_map.get("schema") or "orb_weaver.pointer_plot_map.v1",
        "generated_at": pointer_map.get("generated_at"),
        "record_count": int(pointer_map.get("record_count") or 0),
        "records": pointer_map.get("records") if isinstance(pointer_map.get("records"), list) else [],
        "by_page": pointer_map.get("by_page") if isinstance(pointer_map.get("by_page"), dict) else {},
    }


@app.get("/api/orb/page-capsule", response_model=WebsiteOrbPageCapsuleResponse)
async def website_orb_page_capsule(
    target_url: str = Query(..., min_length=1, max_length=500),
):
    return _build_page_capsule(target_url)


@app.get("/api/orb/tools/catalog")
async def orb_tool_catalog(customer: Customer = Depends(get_current_customer)):
    catalog = _orb_tool_catalog(customer)

    if bool(customer.is_admin):
        return catalog

    catalog["tools"] = [
        item
        for item in catalog.get("tools", [])
        if item.get("id") not in ORB_ADMIN_ONLY_TOOLS
    ]
    return catalog


@app.post("/api/orb/tools/run")
async def orb_tool_run(
    payload: OrbToolRunRequest,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    return await _run_orb_tool(payload, customer, db)


@app.post("/api/orb/tts", response_model=WebsiteOrbTtsResponse)
async def website_orb_tts(payload: WebsiteOrbTtsRequest):
    text = payload.text.strip()
    tts_result = await _synthesize_orb_tts(text)
    return {"text": text, **tts_result}


@app.get("/api/orb/tts/{audio_id}")
async def website_orb_tts_audio(audio_id: str):
    if not re.fullmatch(r"[a-f0-9]{24}\.(wav|mp3|ogg|webm|flac)", audio_id):
        raise HTTPException(status_code=404, detail="TTS audio not found")
    audio_path = ORB_TTS_CACHE_ROOT / audio_id
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="TTS audio not found")
    return FileResponse(
        audio_path,
        media_type=_content_type_for_audio_format(audio_path.suffix.lstrip(".")),
        filename=audio_id,
    )


@app.get("/api/orb/memory")
async def read_orb_memory(
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    return _orb_memory_summary(customer, db)


@app.post("/api/orb/memory")
async def upsert_orb_memory(
    payload: OrbMemoryUpsert,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    item = _upsert_orb_memory(customer, payload, db)
    return _serialize_orb_memory(item)


@app.delete("/api/orb/memory/{memory_id}")
async def clear_orb_memory_item(
    memory_id: int,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    item = (
        db.query(OrbUserMemory)
        .filter(
            OrbUserMemory.id == memory_id,
            OrbUserMemory.customer_id == customer.id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Memory item not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": str(memory_id)}


@app.delete("/api/orb/memory")
async def clear_all_orb_memory(
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    deleted = db.query(OrbUserMemory).filter(OrbUserMemory.customer_id == customer.id).delete()
    db.query(OrbRecentContext).filter(OrbRecentContext.customer_id == customer.id).delete()
    db.query(OrbToolCache).filter(OrbToolCache.customer_id == customer.id).delete()
    db.commit()
    return {"status": "deleted", "deleted_memory_items": int(deleted)}


@app.post("/api/public/browser-review")
async def public_browser_review(payload: BrowserReviewRequest):
    if not settings.CHROME_DEVTOOLS_ENABLED or not settings.CHROME_DEVTOOLS_PUBLIC_ENABLED:
        raise HTTPException(status_code=403, detail="Public browser verification is not enabled")
    try:
        site_url = _normalize_public_site_url(payload.website_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _chrome_devtools_runner().review(site_url, label="public")


@app.post("/api/auth/signup")
async def signup_customer(payload: CustomerSignup, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    for label, value in {
        "Full name": payload.full_name,
        "Address line 1": payload.address_line1,
        "City": payload.city,
        "State": payload.state,
        "Postal code": payload.postal_code,
        "Country": payload.country,
        "Phone": payload.phone,
    }.items():
        if not value or not value.strip():
            raise HTTPException(status_code=400, detail=f"{label} is required")
    existing = db.query(Customer).filter(Customer.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Customer email already exists")

    business_name = (payload.business_name or payload.company_name or payload.full_name).strip()
    is_first_customer = db.query(Customer).count() == 0
    customer = Customer(
        email=email,
        password_hash=_hash_password(payload.password),
        full_name=payload.full_name.strip(),
        business_name=business_name,
        company_name=(payload.company_name or "").strip() or None,
        contact_name=(payload.contact_name or "").strip() or None,
        phone=(payload.phone or "").strip() or None,
        address_line1=payload.address_line1.strip(),
        address_line2=(payload.address_line2 or "").strip() or None,
        city=payload.city.strip(),
        state=payload.state.strip(),
        postal_code=payload.postal_code.strip(),
        country=payload.country.strip(),
        business_phone=(payload.business_phone or "").strip() or None,
        business_address_line1=(payload.business_address_line1 or "").strip() or None,
        business_address_line2=(payload.business_address_line2 or "").strip() or None,
        business_city=(payload.business_city or "").strip() or None,
        business_state=(payload.business_state or "").strip() or None,
        business_postal_code=(payload.business_postal_code or "").strip() or None,
        business_country=(payload.business_country or "").strip() or None,
        tax_id=(payload.tax_id or "").strip() or None,
        is_admin=is_first_customer,
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


@app.get("/api/admin/customers")
async def admin_list_customers(
    db: Session = Depends(get_db),
    _admin: Customer = Depends(require_admin),
):
    customers = db.query(Customer).order_by(Customer.created_at.desc(), Customer.id.desc()).all()
    return [_serialize_admin_customer(customer, db) for customer in customers]


@app.get("/api/admin/customers/{customer_id}")
async def admin_get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    _admin: Customer = Depends(require_admin),
):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    payload = _serialize_admin_customer(customer, db)
    payload["projects"] = [_serialize_project(project, db) for project in db.query(Project).filter(Project.customer_id == customer.id).all()]
    payload["orders"] = [
        _serialize_checkout_order(order)
        for order in db.query(CheckoutOrder).filter(CheckoutOrder.customer_id == customer.id).order_by(CheckoutOrder.id.desc()).all()
    ]
    return payload


@app.post("/api/admin/cali-crm/export-customers")
async def admin_export_customers_to_cali_crm(
    db: Session = Depends(get_db),
    _admin: Customer = Depends(require_admin),
):
    import_dir = _cali_crm_import_dir()
    import_dir.mkdir(parents=True, exist_ok=True)
    customers = db.query(Customer).order_by(Customer.created_at.asc(), Customer.id.asc()).all()
    payload = {
        "schema": "orb_weaver.cali_crm_customer_export.v1",
        "generated_at": datetime.utcnow().isoformat(),
        "source": "orb_weaver",
        "target": "cali_crm",
        "record_count": len(customers),
        "records": [_customer_crm_import_record(customer, db) for customer in customers],
    }
    output_path = import_dir / f"orb_weaver_customers_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    _write_json(output_path, payload)
    return {"status": "exported", "record_count": len(customers), "path": str(output_path), "crm_url": settings.CALI_CRM_URL}


@app.get("/api/admin/browser-lab/tools")
async def admin_browser_lab_tools(_admin: Customer = Depends(require_admin)):
    return {
        "schema": "orb_weaver.chrome_devtools_browser_lab.v1",
        "enabled": bool(settings.CHROME_DEVTOOLS_ENABLED),
        "public_enabled": bool(settings.CHROME_DEVTOOLS_PUBLIC_ENABLED),
        "product_boundary": "Admin/custom ORB install use.",
        "groups": {"navigation": {"label": "Browser navigation", "tools": {"review": "Run browser review for a URL"}}},
    }


@app.post("/api/admin/browser-lab/run")
async def admin_browser_lab_run(
    payload: BrowserLabToolRequest,
    _admin: Customer = Depends(require_admin),
):
    if not settings.CHROME_DEVTOOLS_ENABLED:
        raise HTTPException(status_code=403, detail="Chrome DevTools browser verification is not enabled")
    return _chrome_devtools_runner().run_tool(payload.tool, dict(payload.params), label="admin_browser_lab")


@app.get("/api/marketplace/public/products")
async def marketplace_public_products(
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=60, ge=1, le=250),
    db: Session = Depends(get_db),
):
    query = (
        db.query(MarketplaceProduct)
        .filter(
            and_(
                MarketplaceProduct.system_number.isnot(None),
                MarketplaceProduct.status == "active",
                MarketplaceProduct.visibility == "public",
                MarketplaceProduct.approval_status == "approved",
            )
        )
        .order_by(MarketplaceProduct.sort_order.asc(), MarketplaceProduct.id.desc())
    )
    if category:
        query = query.filter(MarketplaceProduct.category == category)
    products = query.limit(limit).all()
    return [_serialize_marketplace_product(product, include_images=True) for product in products]


@app.get("/api/marketplace/public/products/{product_id}")
async def marketplace_public_product_detail(product_id: int, db: Session = Depends(get_db)):
    product = _get_marketplace_product_or_404(product_id, db)
    if not _is_public_marketplace_product(product):
        raise HTTPException(status_code=404, detail="Marketplace product not found")
    return _serialize_marketplace_product(product, include_images=True)


@app.get("/api/admin/marketplace/sequence")
async def admin_marketplace_sequence(
    db: Session = Depends(get_db),
    _admin: Customer = Depends(require_admin),
):
    sequence = db.query(MarketplaceNumberSequence).filter(MarketplaceNumberSequence.prefix == "OW-MKT").first()
    if not sequence:
        sequence = MarketplaceNumberSequence(prefix="OW-MKT", last_number=0)
        db.add(sequence)
        db.commit()
        db.refresh(sequence)
    return {
        "prefix": sequence.prefix,
        "last_number": sequence.last_number,
        "next_number": f"{sequence.prefix}-{int(sequence.last_number or 0) + 1:06d}",
    }


@app.get("/api/admin/marketplace/products")
async def admin_marketplace_products(
    status: Optional[str] = Query(default=None),
    visibility: Optional[str] = Query(default=None),
    approval_status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _admin: Customer = Depends(require_admin),
):
    query = db.query(MarketplaceProduct).order_by(MarketplaceProduct.id.desc())
    if status:
        query = query.filter(MarketplaceProduct.status == status)
    if visibility:
        query = query.filter(MarketplaceProduct.visibility == visibility)
    if approval_status:
        query = query.filter(MarketplaceProduct.approval_status == approval_status)
    return [_serialize_marketplace_product(product, include_images=True) for product in query.all()]


@app.post("/api/admin/marketplace/products")
async def admin_create_marketplace_product(
    payload: MarketplaceProductCreate,
    db: Session = Depends(get_db),
    admin: Customer = Depends(require_admin),
):
    _validate_marketplace_status_fields(payload.status, payload.visibility, payload.approval_status)
    created = MarketplaceProduct(
        system_number=_next_marketplace_system_number(db),
        seller_user_id=payload.source_type == "user_upload" and admin.id or None,
        created_by_admin_id=admin.id,
        source_type=(payload.source_type or "admin_manual"),
        title=payload.title.strip(),
        slug=_build_unique_marketplace_slug(db, payload.title),
        description=(payload.description or "").strip() or None,
        price_cents=payload.price_cents,
        currency=payload.currency.lower().strip(),
        category=payload.category.strip(),
        tier=(payload.tier or "").strip() or None,
        status=payload.status,
        visibility=payload.visibility,
        approval_status=payload.approval_status,
        inventory_type=payload.inventory_type,
        quantity=payload.quantity,
        is_digital=payload.is_digital,
        is_featured=payload.is_featured,
        sort_order=payload.sort_order,
        published_at=datetime.utcnow() if (payload.status == "active" and payload.visibility == "public" and payload.approval_status == "approved") else None,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return _serialize_marketplace_product(created, include_images=True)


@app.patch("/api/admin/marketplace/products/{product_id}")
async def admin_update_marketplace_product(
    product_id: int,
    payload: MarketplaceProductUpdate,
    db: Session = Depends(get_db),
    _admin: Customer = Depends(require_admin),
):
    product = _get_marketplace_product_or_404(product_id, db)
    _validate_marketplace_status_fields(payload.status, payload.visibility, payload.approval_status)

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates and updates["title"]:
        updates["title"] = updates["title"].strip()
        updates["slug"] = _build_unique_marketplace_slug(db, updates["title"], exclude_id=product.id)

    for field, value in updates.items():
        if field == "submit_for_approval":
            continue
        if field == "slug":
            setattr(product, "slug", value)
            continue
        setattr(product, field, value)

    if payload.submit_for_approval:
        product.status = "pending_review"
        product.approval_status = "pending_review"
        product.visibility = "private"

    if product.status == "active" and product.visibility == "public" and product.approval_status == "approved":
        product.published_at = product.published_at or datetime.utcnow()

    db.commit()
    db.refresh(product)
    return _serialize_marketplace_product(product, include_images=True)


@app.post("/api/admin/marketplace/products/{product_id}/images")
async def admin_add_marketplace_product_image(
    product_id: int,
    payload: MarketplaceProductImageCreate,
    db: Session = Depends(get_db),
    admin: Customer = Depends(require_admin),
):
    product = _get_marketplace_product_or_404(product_id, db)
    image = MarketplaceProductImage(
        product_id=product.id,
        uploaded_by_user_id=admin.id,
        file_path=payload.file_path,
        file_url=payload.file_url,
        alt_text=payload.alt_text,
        sort_order=payload.sort_order,
        is_primary=payload.is_primary,
        width=payload.width,
        height=payload.height,
        mime_type=payload.mime_type,
    )
    db.add(image)
    db.flush()
    if payload.is_primary or not product.primary_image_id:
        _set_primary_product_image(product, image, db)
    db.commit()
    db.refresh(image)
    return _serialize_marketplace_image(image)


@app.get("/api/admin/marketplace/ads")
async def admin_marketplace_ads(
    db: Session = Depends(get_db),
    _admin: Customer = Depends(require_admin),
):
    slots = db.query(MarketplaceAdSlot).order_by(MarketplaceAdSlot.placement.asc(), MarketplaceAdSlot.sort_order.asc(), MarketplaceAdSlot.id.asc()).all()
    return [_serialize_marketplace_ad_slot(slot) for slot in slots]


@app.post("/api/admin/marketplace/ads")
async def admin_upsert_marketplace_ad(
    payload: MarketplaceAdSlotUpsert,
    db: Session = Depends(get_db),
    _admin: Customer = Depends(require_admin),
):
    slot = db.query(MarketplaceAdSlot).filter(MarketplaceAdSlot.slot_key == payload.slot_key).first()
    if not slot:
        slot = MarketplaceAdSlot(slot_key=payload.slot_key)
        db.add(slot)
    slot.name = payload.name
    slot.placement = payload.placement
    slot.title = payload.title
    slot.image_url = payload.image_url
    slot.link_url = payload.link_url
    slot.html_content = payload.html_content
    slot.active = payload.active
    slot.starts_at = payload.starts_at
    slot.ends_at = payload.ends_at
    slot.sort_order = payload.sort_order
    db.commit()
    db.refresh(slot)
    return _serialize_marketplace_ad_slot(slot)


@app.get("/api/admin/marketplace/theme")
async def admin_marketplace_theme(
    db: Session = Depends(get_db),
    _admin: Customer = Depends(require_admin),
):
    active_theme = db.query(MarketplaceThemeSetting).order_by(MarketplaceThemeSetting.active.desc(), MarketplaceThemeSetting.updated_at.desc()).first()
    if not active_theme:
        return None
    return _serialize_marketplace_theme(active_theme)


@app.post("/api/admin/marketplace/theme")
async def admin_upsert_marketplace_theme(
    payload: MarketplaceThemeUpsert,
    db: Session = Depends(get_db),
    _admin: Customer = Depends(require_admin),
):
    if payload.active:
        db.query(MarketplaceThemeSetting).update({MarketplaceThemeSetting.active: False})

    theme = MarketplaceThemeSetting(
        theme_name=payload.theme_name,
        primary_color=payload.primary_color,
        accent_color=payload.accent_color,
        background_style=payload.background_style,
        card_style=payload.card_style,
        font_family=payload.font_family,
        hero_image_url=payload.hero_image_url,
        logo_url=payload.logo_url,
        custom_css=payload.custom_css,
        active=payload.active,
    )
    db.add(theme)
    db.commit()
    db.refresh(theme)
    return _serialize_marketplace_theme(theme)


@app.get("/api/account/seller/products")
async def seller_list_products(
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    products = (
        db.query(MarketplaceProduct)
        .filter(MarketplaceProduct.seller_user_id == customer.id)
        .order_by(MarketplaceProduct.id.desc())
        .all()
    )
    return [_serialize_marketplace_product(product, include_images=True) for product in products]


@app.post("/api/account/seller/products")
async def seller_create_product(
    payload: MarketplaceProductCreate,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    created = MarketplaceProduct(
        system_number=_next_marketplace_system_number(db),
        seller_user_id=customer.id,
        created_by_admin_id=None,
        source_type="user_upload",
        title=payload.title.strip(),
        slug=_build_unique_marketplace_slug(db, payload.title),
        description=(payload.description or "").strip() or None,
        price_cents=payload.price_cents,
        currency=payload.currency.lower().strip(),
        category=payload.category.strip(),
        tier=(payload.tier or "").strip() or None,
        status="draft",
        visibility="private",
        approval_status="pending_review",
        inventory_type=payload.inventory_type,
        quantity=payload.quantity,
        is_digital=payload.is_digital,
        is_featured=False,
        sort_order=payload.sort_order,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return _serialize_marketplace_product(created, include_images=True)


@app.patch("/api/account/seller/products/{product_id}")
async def seller_update_product(
    product_id: int,
    payload: MarketplaceProductUpdate,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    product = _get_owned_seller_product_or_404(product_id, customer, db)
    updates = payload.model_dump(exclude_unset=True)

    allowed_fields = {
        "title",
        "description",
        "price_cents",
        "currency",
        "category",
        "tier",
        "inventory_type",
        "quantity",
        "is_digital",
        "sort_order",
    }
    for field, value in updates.items():
        if field not in allowed_fields:
            continue
        if field == "title" and value:
            value = value.strip()
            product.slug = _build_unique_marketplace_slug(db, value, exclude_id=product.id)
        setattr(product, field, value)

    if payload.submit_for_approval:
        product.status = "pending_review"
        product.visibility = "private"
        product.approval_status = "pending_review"

    db.commit()
    db.refresh(product)
    return _serialize_marketplace_product(product, include_images=True)


@app.post("/api/account/seller/products/{product_id}/submit")
async def seller_submit_product_for_review(
    product_id: int,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    product = _get_owned_seller_product_or_404(product_id, customer, db)
    product.status = "pending_review"
    product.visibility = "private"
    product.approval_status = "pending_review"
    db.commit()
    db.refresh(product)
    return _serialize_marketplace_product(product, include_images=True)


@app.post("/api/account/seller/products/{product_id}/images")
async def seller_add_product_image(
    product_id: int,
    payload: MarketplaceProductImageCreate,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    product = _get_owned_seller_product_or_404(product_id, customer, db)
    image = MarketplaceProductImage(
        product_id=product.id,
        uploaded_by_user_id=customer.id,
        file_path=payload.file_path,
        file_url=payload.file_url,
        alt_text=payload.alt_text,
        sort_order=payload.sort_order,
        is_primary=payload.is_primary,
        width=payload.width,
        height=payload.height,
        mime_type=payload.mime_type,
    )
    db.add(image)
    db.flush()
    if payload.is_primary or not product.primary_image_id:
        _set_primary_product_image(product, image, db)
    db.commit()
    db.refresh(image)
    return _serialize_marketplace_image(image)


@app.patch("/api/admin/marketplace/products/{product_id}/status")
async def admin_patch_marketplace_status(
    product_id: int,
    payload: MarketplaceProductStatusPatch,
    db: Session = Depends(get_db),
    _admin: Customer = Depends(require_admin),
):
    product = _get_marketplace_product_or_404(product_id, db)
    _validate_marketplace_status_fields(payload.status, payload.visibility, payload.approval_status)

    if payload.status is not None:
        product.status = payload.status
    if payload.visibility is not None:
        product.visibility = payload.visibility
    if payload.approval_status is not None:
        product.approval_status = payload.approval_status
    if payload.is_featured is not None:
        product.is_featured = payload.is_featured
    if payload.sort_order is not None:
        product.sort_order = payload.sort_order

    if product.status == "active" and product.visibility == "public" and product.approval_status == "approved":
        product.published_at = product.published_at or datetime.utcnow()

    db.commit()
    db.refresh(product)
    return _serialize_marketplace_product(product, include_images=True)


@app.get("/api/products")
async def list_products():
    return list(SERVICE_CATALOG.values())


@app.get("/api/cart")
async def get_cart(db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    return _cart_payload(customer, db)


@app.post("/api/cart/items")
async def upsert_cart_item(
    payload: CartItemUpsert,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    product = SERVICE_CATALOG.get(payload.sku)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    item = db.query(CartItem).filter(CartItem.customer_id == customer.id, CartItem.sku == payload.sku).first()
    if item:
        item.quantity = payload.quantity
        item.updated_at = datetime.utcnow()
    else:
        item = CartItem(
            customer_id=customer.id,
            sku=product["sku"],
            name=product["name"],
            unit_amount_cents=product["unit_amount_cents"],
            currency=product["currency"],
            quantity=payload.quantity,
            metadata_json={"description": product["description"]},
        )
        db.add(item)
    db.commit()
    return _cart_payload(customer, db)


@app.delete("/api/cart/items/{sku}")
async def delete_cart_item(
    sku: str,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    db.query(CartItem).filter(CartItem.customer_id == customer.id, CartItem.sku == sku).delete()
    db.commit()
    return _cart_payload(customer, db)


@app.post("/api/cart/checkout")
async def create_checkout(
    payload: CheckoutCreate,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    cart = _cart_payload(customer, db)
    if not cart["items"]:
        raise HTTPException(status_code=400, detail="Cart is empty")

    order = CheckoutOrder(
        customer_id=customer.id,
        provider=payload.provider,
        status="created",
        amount_cents=cart["total_amount_cents"],
        currency=cart["currency"],
        line_items=cart["items"],
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    provider_result = (
        await _create_stripe_checkout(order, customer)
        if payload.provider == "stripe"
        else await _create_paypal_checkout(order)
    )
    order.status = provider_result.get("status", "provider_error")
    order.provider_order_id = provider_result.get("provider_order_id")
    order.checkout_url = provider_result.get("checkout_url")
    order.error = provider_result.get("error")
    db.commit()
    db.refresh(order)
    return _serialize_checkout_order(order)


@app.get("/api/checkout/orders")
async def list_checkout_orders(db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    orders = db.query(CheckoutOrder).filter(CheckoutOrder.customer_id == customer.id).order_by(CheckoutOrder.id.desc()).all()
    return [_serialize_checkout_order(order) for order in orders]


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
        if project.ga4_measurement_id:
            existing.ga4_measurement_id = project.ga4_measurement_id
        if project.ga4_property_id or project.ga4_measurement_id:
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
            if project.ga4_measurement_id:
                existing_domain.ga4_measurement_id = project.ga4_measurement_id
            db.commit()
            db.refresh(existing_domain)
            return _serialize_project(existing_domain, db)
        raise HTTPException(status_code=409, detail="Domain is already registered to another customer")

    name = (project.name or "").strip() or _default_project_name(domain)
    created = Project(
        name=name,
        domain=domain,
        ga4_property_id=project.ga4_property_id,
        ga4_measurement_id=project.ga4_measurement_id,
        customer_id=customer.id,
    )
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


@app.post("/api/projects/{project_id}/ga4/config")
async def update_project_ga4_config(
    project_id: str,
    config: ProjectGA4Config,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    project = _owned_project(project_id, customer, db)
    if config.ga4_property_id is not None:
        project.ga4_property_id = config.ga4_property_id.strip() or None
    if config.ga4_measurement_id is not None:
        project.ga4_measurement_id = config.ga4_measurement_id.strip().upper() or None
    db.commit()
    db.refresh(project)
    return _serialize_project(project, db)


@app.post("/api/projects/{project_id}/ga4/import")
async def import_project_ga4_data(
    project_id: str,
    config: ProjectGA4Config = ProjectGA4Config(),
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    project = _owned_project(project_id, customer, db)
    if config.ga4_property_id is not None:
        project.ga4_property_id = config.ga4_property_id.strip() or None
    if config.ga4_measurement_id is not None:
        project.ga4_measurement_id = config.ga4_measurement_id.strip().upper() or None
    if not project.ga4_property_id:
        raise HTTPException(status_code=400, detail="GA4 property ID is required before importing Google Analytics data")

    try:
        connector = GA4Connector(property_id=project.ga4_property_id)
        report = connector.get_full_report(days=config.days)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"GA4 import failed: {exc}")

    end_at = datetime.utcnow()
    start_at = end_at - timedelta(days=config.days)
    top_pages = report.get("top_pages") or []
    db.query(GA4Data).filter(GA4Data.project_id == project.id).delete(synchronize_session=False)
    for page in top_pages:
        db.add(
            GA4Data(
                project_id=project.id,
                page_path=page.get("path") or "/",
                sessions=int(page.get("sessions") or 0),
                users=int(page.get("users") or 0),
                pageviews=int(page.get("pageviews") or 0),
                bounce_rate=page.get("bounce_rate"),
                avg_session_duration=page.get("avg_session_duration"),
                date_range_start=start_at,
                date_range_end=end_at,
            )
        )
    db.commit()
    db.refresh(project)

    output_path = _project_report_dir(project) / "ga4" / "ga4_import_latest.json"
    _write_json(output_path, {"project": _serialize_project(project, db), "days": config.days, "report": report})
    return {
        "status": "imported",
        "project": _serialize_project(project, db),
        "imported_page_rows": len(top_pages),
        "artifact_path": str(output_path),
        "traffic_totals": (report.get("traffic_overview") or {}).get("totals", {}),
    }


@app.get("/api/projects/{project_id}/preflight")
async def get_project_preflight(project_id: str, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    project = _owned_project(project_id, customer, db)
    report_path = _project_preflight_dir(project) / "site_preflight_report.json"
    if not report_path.is_file():
        return {"status": "not_run", "project": _serialize_project(project, db)}
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read preflight report: {exc}")


@app.post("/api/projects/{project_id}/preflight")
async def run_project_preflight(
    project_id: str,
    config: Optional[PreflightRunConfig] = None,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    project = _owned_project(project_id, customer, db)
    try:
        report = await _run_project_preflight(project, output_dir=config.output_dir if config else None)
        preserve_client_preflight_intelligence(project, report)
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Preflight scan failed: {exc}")


@app.post("/api/projects/{project_id}/browser-review")
async def run_project_browser_review(
    project_id: str,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    if not settings.CHROME_DEVTOOLS_ENABLED:
        raise HTTPException(status_code=403, detail="Chrome DevTools browser verification is not enabled")
    project = _owned_project(project_id, customer, db)
    site_url = project.domain if project.domain.startswith(("http://", "https://")) else f"https://{project.domain}"
    return _chrome_devtools_runner().review(site_url, label=f"project_{project.id}")


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


@app.get("/api/crawl-jobs")
async def list_crawl_jobs(db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    jobs = (
        db.query(CrawlJob)
        .join(Project, CrawlJob.project_id == Project.id)
        .filter(Project.customer_id == customer.id)
        .order_by(CrawlJob.id.desc())
        .all()
    )
    return [_serialize_crawl_job(job, db) for job in jobs]


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


@app.get("/api/crawl-jobs/{job_id}/pointer-plot-map")
async def get_crawl_pointer_plot_map(
    job_id: str,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    crawl_job = _owned_crawl_job(job_id, customer, db)
    pages = db.query(CrawledPage).filter(CrawledPage.crawl_job_id == crawl_job.id).all()
    pointer_map = pointer_plot_map_from_pages(pages)
    return {
        "crawl_id": str(crawl_job.id),
        "project_id": str(crawl_job.project_id),
        **pointer_map,
    }


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

    pointer_summary = data.get("pointer_summary") or {}
    if pointer_summary:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, y, "ORB Pointer Guidance")
        y -= 18
        pdf.setFont("Helvetica", 10)
        pdf.drawString(
            40,
            y,
            (
                f"Targets: {pointer_summary.get('record_count', 0)}  "
                f"Routes: {pointer_summary.get('routes_with_pointers', 0)}  "
                f"Duplicate IDs: {pointer_summary.get('duplicate_target_ids', 0)}  "
                f"Status: {pointer_summary.get('status', 'needs_review')}"
            )[:110],
        )
        y -= 30

    planned_tool_calls = data.get("planned_tool_calls") or []
    if planned_tool_calls:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, y, "Planned ORB Tool Calls")
        y -= 18
        pdf.setFont("Helvetica", 9)
        for item in planned_tool_calls[:5]:
            line = (
                f"- {item.get('tool', '')}: {item.get('status', '')} "
                f"({item.get('scope', '')})"
            )
            pdf.drawString(40, y, line[:120])
            y -= 14
            if y < 50:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica", 9)
        y -= 16

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


@app.get("/api/projects/{project_id}/report-files/{filename}")
async def open_report_file(
    project_id: str,
    filename: str,
    disposition: str = Query("inline", pattern="^(inline|attachment)$"),
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    project = _owned_project(project_id, customer, db)
    report_dir = _project_report_dir(project).resolve()
    file_path = (report_dir / filename).resolve()

    if report_dir not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(
        file_path,
        media_type="application/json" if file_path.suffix.lower() == ".json" else "application/octet-stream",
        headers=_content_disposition(file_path.name, disposition),
    )


@app.post("/api/projects/{project_id}/tpc-pack")
async def create_tpc_pack(
    project_id: str,
    payload: TPCPackRequest,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    project = _owned_project(project_id, customer, db)
    report = generate_pack_file(
        scan_data=_build_tpc_pack_scan_data(project, db),
        site_id=str(project.id),
        domain=project.domain,
        tier=payload.tier,
        output_dir=_tpc_pack_output_dir(project),
    )
    return {
        "status": "created",
        "project": _serialize_project(project, db),
        "pack": report,
        "download_url": f"/api/projects/{project.id}/tpc-pack/download/{report['filename']}",
    }


@app.get("/api/projects/{project_id}/tpc-packs")
async def list_tpc_packs(
    project_id: str,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    project = _owned_project(project_id, customer, db)
    packs = []
    for pack_path in _tpc_pack_output_dir(project).glob("*.orbpack"):
        packs.append({
            "filename": pack_path.name,
            "size_kb": max(pack_path.stat().st_size // 1024, 1),
            "generated_at": datetime.fromtimestamp(pack_path.stat().st_mtime).isoformat(),
            "download_url": f"/api/projects/{project.id}/tpc-pack/download/{pack_path.name}",
        })
    return {"packs": sorted(packs, key=lambda item: item["generated_at"], reverse=True)}


@app.get("/api/projects/{project_id}/tpc-pack/download/{filename}")
async def download_tpc_pack(
    project_id: str,
    filename: str,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    project = _owned_project(project_id, customer, db)
    if "/" in filename or "\\" in filename or not filename.endswith(".orbpack"):
        raise HTTPException(status_code=400, detail="Invalid pack filename")
    pack_path = _tpc_pack_output_dir(project) / filename
    if not pack_path.is_file():
        raise HTTPException(status_code=404, detail="TPC pack not found")
    return FileResponse(pack_path, media_type="application/octet-stream", filename=filename)


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
