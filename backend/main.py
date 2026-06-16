from datetime import datetime, timedelta
from io import BytesIO, StringIO
import base64
import csv
import hashlib
import importlib.util
import json
import re
import secrets
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import Counter

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.analytics.ga4 import GA4Connector
from app.audit.engine import SEOAuditor
from app.core.config import settings
from app.crawler.engine import OrbWeaverCrawler, PageData
from app.models.database import (
    AuditReport,
    CartItem,
    CheckoutOrder,
    CrawlJob,
    CrawledPage,
    Customer,
    CustomerSession,
    MarketplaceAdSlot,
    MarketplaceNumberSequence,
    MarketplaceProduct,
    MarketplaceProductImage,
    MarketplaceThemeSetting,
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
PREFLIGHT_SCANNER_ROOT = Path(__file__).resolve().parent.parent / "Preflight Scanner"
PREFLIGHT_SCANNER_MODULE = PREFLIGHT_SCANNER_ROOT / "preflight_site_scan.py"


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


class CartItemUpsert(BaseModel):
    sku: str
    quantity: int = Field(default=1, ge=1, le=99)


class CheckoutCreate(BaseModel):
    provider: str = Field(pattern="^(stripe|paypal)$")


class PreflightRunConfig(BaseModel):
    output_dir: Optional[str] = None


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


def _content_disposition(filename: str, disposition: str = "attachment") -> Dict[str, str]:
    safe_disposition = "inline" if disposition == "inline" else "attachment"
    safe_filename = filename.replace("\\", "_").replace("/", "_").replace('"', "")
    return {"Content-Disposition": f'{safe_disposition}; filename="{safe_filename}"'}


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
