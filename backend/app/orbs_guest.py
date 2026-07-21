"""Vault-backed guest onboarding and deterministic authenticated merge."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any, Mapping, Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.database import (
    Customer,
    OrbsGuestSession,
    OrbsOnboardingRecord,
    Project,
)
from app.orbs_contracts import (
    GUEST_SESSION_SCHEMA,
    OrbsGuestMergeResultContract,
    OrbsGuestSessionContract,
)
from app.orbs_governor import GovernorRejection, canonical_request_hash, compile_snapshot


GUEST_SESSION_TTL = timedelta(days=7)
SENSITIVE_KEY_FRAGMENTS = {
    "address",
    "card",
    "email",
    "password",
    "payment",
    "phone",
    "secret",
    "ssn",
    "tax",
    "token",
}


def _validated_destination(value: str) -> str:
    destination = (value or "").strip()
    if not destination.startswith("/") or destination.startswith("//"):
        raise GovernorRejection(
            "invalid_guest_session",
            "The original CTA destination must be a verified local route",
            400,
        )
    return destination


def _validated_website(value: Optional[str], *, required: bool = False) -> Optional[str]:
    website = (value or "").strip()
    if not website:
        if required:
            raise GovernorRejection(
                "website_required", "A website URL is required before merge", 400
            )
        return None
    parsed = urlparse(website if "://" in website else f"https://{website}")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise GovernorRejection("invalid_website", "Website URL is invalid", 400)
    return f"{parsed.scheme}://{parsed.hostname}{parsed.path.rstrip('/')}"


def _domain(website_url: str) -> str:
    return str(urlparse(website_url).hostname or "").lower()


def _approved_answers(value: Mapping[str, Any]) -> dict[str, Any]:
    approved = {}
    for key, answer in value.items():
        normalized = str(key).strip().lower()
        if not normalized or any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS):
            raise GovernorRejection(
                "sensitive_guest_data_rejected",
                f"Guest questionnaire field is not permitted: {key}",
                400,
            )
        if not isinstance(answer, (str, int, float, bool, list, type(None))):
            raise GovernorRejection(
                "invalid_guest_session",
                f"Guest questionnaire field must be non-sensitive JSON data: {key}",
                400,
            )
        approved[str(key)] = answer
    return approved


def serialize_guest_session(session: OrbsGuestSession) -> dict[str, Any]:
    return OrbsGuestSessionContract(
        schema=GUEST_SESSION_SCHEMA,
        guest_session_id=session.guest_session_id,
        landing_intent=session.landing_intent,
        selected_tier_interest=session.selected_tier_interest,
        website_url=session.website_url,
        original_cta_destination=session.original_cta_destination,
        current_onboarding_step=session.current_onboarding_step,
        completed_onboarding_steps=list(session.completed_onboarding_steps or []),
        non_sensitive_questionnaire_answers=dict(
            session.non_sensitive_questionnaire_answers or {}
        ),
        created_at=session.created_at,
        expires_at=session.expires_at,
        version=session.version,
    ).model_dump(mode="json")


def create_guest_session(db: Session, payload: Mapping[str, Any]) -> dict[str, Any]:
    now = datetime.utcnow()
    session = OrbsGuestSession(
        guest_session_id=secrets.token_urlsafe(32),
        landing_intent=str(payload.get("landing_intent") or "").strip(),
        selected_tier_interest=(
            str(payload.get("selected_tier_interest") or "").strip() or None
        ),
        website_url=_validated_website(payload.get("website_url")),
        original_cta_destination=_validated_destination(
            str(payload.get("original_cta_destination") or "")
        ),
        current_onboarding_step=str(
            payload.get("current_onboarding_step") or "landing"
        ).strip(),
        completed_onboarding_steps=list(
            payload.get("completed_onboarding_steps") or []
        ),
        non_sensitive_questionnaire_answers=_approved_answers(
            payload.get("non_sensitive_questionnaire_answers") or {}
        ),
        created_at=now,
        expires_at=now + GUEST_SESSION_TTL,
        version=1,
    )
    if not session.landing_intent:
        raise GovernorRejection(
            "invalid_guest_session", "Landing intent is required", 400
        )
    db.add(session)
    db.commit()
    db.refresh(session)
    return serialize_guest_session(session)


def merge_guest_session(
    db: Session,
    customer: Customer,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    guest_id = str(payload.get("guest_session_id") or "").strip()
    key = str(payload.get("idempotency_key") or "").strip()
    request_hash = canonical_request_hash(payload)
    session = (
        db.query(OrbsGuestSession)
        .filter(OrbsGuestSession.guest_session_id == guest_id)
        .with_for_update()
        .first()
    )
    if not session:
        raise GovernorRejection("guest_session_not_found", "Guest session is unavailable", 404)
    if session.consumed_at:
        if session.consumed_by_customer_id != customer.id:
            raise GovernorRejection(
                "guest_session_consumed",
                "Guest session was consumed by another customer",
                403,
            )
        if session.merge_idempotency_key == key and session.merge_request_hash == request_hash:
            return dict(session.merge_result or {})
        raise GovernorRejection(
            "guest_session_consumed", "Guest session has already been consumed", 409
        )
    if session.expires_at <= datetime.utcnow():
        raise GovernorRejection("guest_session_expired", "Guest session has expired", 410)

    website_url = _validated_website(session.website_url, required=True)
    domain = _domain(website_url)
    attach_project_id = payload.get("attach_project_id")
    project = None
    if attach_project_id:
        project = db.get(Project, int(attach_project_id))
        if not project or project.customer_id != customer.id:
            raise GovernorRejection(
                "unauthorized_project", "Project is not available", 404
            )
    if project is None:
        project = (
            db.query(Project)
            .filter(Project.customer_id == customer.id, Project.domain == domain)
            .first()
        )
    if project is None:
        project = Project(
            customer_id=customer.id,
            name=(
                str(payload.get("project_display_name") or "").strip()
                or domain.split(".")[0].replace("-", " ").title()
                or domain
            ),
            domain=domain,
            is_active=True,
        )
        db.add(project)
        db.flush()

    onboarding = OrbsOnboardingRecord(
        guest_session_id=session.guest_session_id,
        customer_id=customer.id,
        project_id=project.id,
        original_cta_destination=session.original_cta_destination,
        landing_intent=session.landing_intent,
        selected_tier_interest=session.selected_tier_interest,
        current_onboarding_step=session.current_onboarding_step,
        completed_onboarding_steps=list(session.completed_onboarding_steps or []),
        transferred_progress={
            "website_url": website_url,
            "non_sensitive_questionnaire_answers": dict(
                session.non_sensitive_questionnaire_answers or {}
            ),
        },
        version=1,
    )
    db.add(onboarding)
    db.flush()

    consumed_at = datetime.utcnow()
    session.consumed_at = consumed_at
    session.consumed_by_customer_id = customer.id
    session.merged_project_id = project.id
    session.merge_idempotency_key = key
    session.merge_request_hash = request_hash
    fresh_snapshot = compile_snapshot(db, project, customer)
    result = OrbsGuestMergeResultContract(
        merge_status="merged",
        guest_session_id=session.guest_session_id,
        customer_id=str(customer.id),
        project_id=str(project.id),
        onboarding_record_id=str(onboarding.id),
        original_cta_destination=session.original_cta_destination,
        transferred_fields=[
            "landing_intent",
            "selected_tier_interest",
            "website_url",
            "current_onboarding_step",
            "completed_onboarding_steps",
            "non_sensitive_questionnaire_answers",
            "original_cta_destination",
        ],
        consumed_at=consumed_at,
        fresh_snapshot=fresh_snapshot,
    ).model_dump(mode="json")
    session.merge_result = result
    db.commit()
    return result

