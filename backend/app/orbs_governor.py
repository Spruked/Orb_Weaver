"""Authoritative ORBS customer-journey stage governor.

All state is derived from or persisted in Orb Weaver's canonical database/Vault.
No language model or Orb Assistant output participates in transition decisions.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Iterable, Mapping, Optional

from sqlalchemy.orm import Session

from app.core.storage import client_root
from app.models.database import (
    AuditReport,
    CheckoutOrder,
    CrawlJob,
    Customer,
    LifecycleJob,
    MarketplaceProduct,
    OrbsBuildOrder,
    OrbsEntitlement,
    OrbsIdempotencyRecord,
    OrbsOnboardingRecord,
    OrbsStageEvent,
    Project,
    ReviewItem,
)


SNAPSHOT_SCHEMA = "orb_weaver.orbs_stage_snapshot.v1"
JOURNEY = (
    "preflight",
    "crawl",
    "final_audit",
    "orbs",
    "package_presentation_and_recommendation",
    "final_closer_questionnaire",
    "package_selection_commitment",
    "build_configuration",
    "final_order_review",
    "signature",
    "checkout",
    "verified_payment",
    "fulfillment",
    "review_required",
    "package_generation",
    "installation",
    "launch_verification",
    "live",
)


class GovernorRejection(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 409):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def canonical_request_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def idempotency_record(db: Session, customer_id: int, key: str) -> Optional[OrbsIdempotencyRecord]:
    return db.query(OrbsIdempotencyRecord).filter(
        OrbsIdempotencyRecord.customer_id == customer_id,
        OrbsIdempotencyRecord.idempotency_key == key,
    ).first()


def persist_idempotency(
    db: Session,
    customer: Customer,
    project: Project,
    key: str,
    request_hash: str,
    status_code: int,
    response_payload: Mapping[str, Any],
) -> OrbsIdempotencyRecord:
    record = OrbsIdempotencyRecord(
        customer_id=customer.id,
        project_id=project.id,
        idempotency_key=key,
        request_hash=request_hash,
        response_status=status_code,
        response_payload=dict(response_payload),
    )
    db.add(record)
    db.flush()
    return record


def technical_evidence(db: Session, project: Project) -> Dict[str, Any]:
    preflight_path = client_root(project.domain) / "website_orb_context" / "site_preflight_report.json"
    preflight: Dict[str, Any] = {}
    if preflight_path.is_file():
        try:
            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            preflight = {}
    latest_crawl = db.query(CrawlJob).filter(CrawlJob.project_id == project.id).order_by(CrawlJob.id.desc()).first()
    completed_crawl = db.query(CrawlJob).filter(
        CrawlJob.project_id == project.id,
        CrawlJob.status == "completed",
    ).order_by(CrawlJob.id.desc()).first()
    latest_audit = db.query(AuditReport).filter(AuditReport.project_id == project.id).order_by(AuditReport.id.desc()).first()
    active_full_audit = db.query(LifecycleJob).filter(
        LifecycleJob.project_id == project.id,
        LifecycleJob.job_type == "FULL_AUDIT",
        LifecycleJob.status.in_({"PENDING", "RUNNING"}),
    ).order_by(LifecycleJob.id.desc()).first()
    completed_full_audit = db.query(LifecycleJob).filter(
        LifecycleJob.project_id == project.id,
        LifecycleJob.job_type == "FULL_AUDIT",
        LifecycleJob.status.in_({"COMPLETED", "APPROVED"}),
    ).order_by(LifecycleJob.id.desc()).first()
    preflight_complete = bool(preflight and int(preflight.get("pages_scanned") or 0) > 0)
    crawl_complete = bool(completed_crawl)
    audit_complete = bool(
        completed_full_audit
        or (latest_audit and latest_audit.report_data and latest_audit.overall_score is not None)
    )
    return {
        "preflight_complete": preflight_complete,
        "crawl_complete": crawl_complete,
        "audit_complete": audit_complete,
        "preflight": preflight,
        "latest_crawl": latest_crawl,
        "completed_crawl": completed_crawl,
        "latest_audit": latest_audit,
        "active_full_audit": active_full_audit,
        "completed_full_audit": completed_full_audit,
    }


def _technical_snapshot_version(evidence: Mapping[str, Any]) -> str:
    preflight = evidence.get("preflight") or {}
    crawl = evidence.get("latest_crawl")
    audit = evidence.get("latest_audit")
    material = {
        "preflight": preflight.get("scan_timestamp") or preflight.get("generated_at") or bool(preflight),
        "crawl_id": getattr(crawl, "id", None),
        "crawl_status": getattr(crawl, "status", None),
        "audit_id": getattr(audit, "id", None),
        "audit_ready": bool(getattr(audit, "report_data", None)),
    }
    digest = canonical_request_hash(material)[:16]
    return f"technical-{digest}"


def _ensure_build_order(db: Session, project: Project, customer: Customer) -> OrbsBuildOrder:
    order = db.query(OrbsBuildOrder).filter(OrbsBuildOrder.project_id == project.id).first()
    if order:
        if order.customer_id != customer.id:
            raise GovernorRejection("unauthorized_project", "Build order customer binding does not match", 403)
        return order
    order = OrbsBuildOrder(
        project_id=project.id,
        customer_id=customer.id,
        current_stage="orbs",
        stage_status="ready",
        version=1,
        customer_action_required="Review the site-specific ORBS integration evidence.",
    )
    db.add(order)
    db.flush()
    _event(db, order, customer, "stage_initialized", None, None, "orbs", str(order.version), {})
    db.commit()
    db.refresh(order)
    return order


def _action(
    name: str,
    display_label: str,
    *,
    confirmation_required: bool = False,
    allowed_input_fields: Iterable[str] = (),
    destination_route: Optional[str] = None,
    reason_available: str,
) -> Dict[str, Any]:
    return {
        "name": name,
        "display_label": display_label,
        "confirmation_required": confirmation_required,
        "allowed_input_fields": list(allowed_input_fields),
        "permitted_input_fields": list(allowed_input_fields),
        "destination_route": destination_route,
        "destination_verified": bool(destination_route),
        "reason_available": reason_available,
        "idempotency_required": True,
    }


def _approved_products(db: Session) -> list[MarketplaceProduct]:
    return db.query(MarketplaceProduct).filter(
        MarketplaceProduct.status == "active",
        MarketplaceProduct.visibility == "public",
        MarketplaceProduct.approval_status == "approved",
        MarketplaceProduct.category.in_({"orbs", "website-orbs"}),
    ).order_by(MarketplaceProduct.sort_order.asc(), MarketplaceProduct.id.asc()).all()


def _package_recommendation(
    products: list[MarketplaceProduct],
    evidence: Mapping[str, Any],
    order: Optional[OrbsBuildOrder],
) -> Optional[Dict[str, Any]]:
    if not products:
        return None
    crawl = evidence.get("completed_crawl") or evidence.get("latest_crawl")
    audit = evidence.get("latest_audit")
    page_count = int(getattr(crawl, "pages_crawled", 0) or 0)
    audit_data = getattr(audit, "report_data", None) or {}
    critical_count = int((audit_data.get("summary") or {}).get("critical_count") or 0)
    desired = "basic"
    reasons = [f"{page_count} completed crawl pages", f"{critical_count} critical final-audit findings"]
    if page_count > 500 or critical_count > 3:
        desired = "enterprise"
    elif page_count > 150 or critical_count > 1:
        desired = "premium"
    elif page_count > 40:
        desired = "enhanced"

    questionnaire = order.questionnaire if order else {}
    answer_text = " ".join(str(value).lower() for value in (questionnaire or {}).values())
    ranks = {"basic": 0, "enhanced": 1, "premium": 2, "enterprise": 3}
    if any(term in answer_text for term in ("managed", "governance", "multi-department", "multiple department")):
        desired = max((desired, "premium"), key=lambda value: ranks[value])
        reasons.append("Final Closer answers request managed, governance, or multi-department support")

    ranked = sorted(
        products,
        key=lambda product: (ranks.get(str(product.tier or "").lower(), 99), product.sort_order, product.id),
    )
    selected = next((item for item in ranked if str(item.tier or "").lower() == desired), None)
    if not selected:
        selected = next((item for item in ranked if ranks.get(str(item.tier or "").lower(), 99) >= ranks[desired]), ranked[-1])
    return {
        "marketplace_product_id": str(selected.id),
        "sku": selected.system_number,
        "name": selected.title,
        "tier": selected.tier,
        "price_cents": selected.price_cents,
        "currency": selected.currency,
        "recommendation_basis": reasons,
        "final_closer_answers_applied": bool(questionnaire),
    }


def _open_reviews(db: Session, project_id: int) -> list[ReviewItem]:
    return db.query(ReviewItem).join(LifecycleJob).filter(
        LifecycleJob.project_id == project_id,
        ReviewItem.status == "open",
    ).all()


def _allowed_actions(db: Session, project: Project, stage: str, evidence: Mapping[str, Any], order: Optional[OrbsBuildOrder]) -> list[Dict[str, Any]]:
    project_route = f"/projects?project={project.id}"
    if stage == "preflight":
        return [
            _action("run_preflight", "Run My Free Preflight", destination_route=project_route, reason_available="Preflight evidence is incomplete."),
            _action("explore_orbs_packages", "Explore ORBS Packages", destination_route="/marketplace", reason_available="Package information may be explored before technical eligibility is determined."),
            _action("open_dashboard", "Open My Dashboard", destination_route=f"/dashboard?project={project.id}", reason_available="The customer workspace is available."),
            _action("visit_orb_marketplace", "Visit the ORB Marketplace", destination_route="/marketplace", reason_available="The public ORB Marketplace is available."),
        ]
    if stage == "crawl":
        if evidence.get("latest_crawl") and evidence["latest_crawl"].status in {"pending", "running"}:
            return []
        return [_action("run_crawl", "Run Crawl", destination_route=project_route, reason_available="Preflight is complete and crawl evidence is required.")]
    if stage == "final_audit":
        if evidence.get("active_full_audit") or (evidence.get("latest_audit") and not evidence["latest_audit"].report_data):
            return []
        return [_action("run_final_audit", "Run Final Audit", destination_route=project_route, reason_available="A completed crawl is ready for final audit.")]
    if stage == "orbs":
        return [_action("review_orbs_integration", "Review ORBS Integration", destination_route=f"/orbs/{project.id}", reason_available="Preflight, Crawl, and Final Audit are complete.")]
    if stage == "package_presentation_and_recommendation":
        if not _approved_products(db):
            return []
        return [_action("start_final_closer_questionnaire", "Start Final Closer Questionnaire", destination_route=f"/orbs/{project.id}", reason_available="The evidence-supported recommendation is ready.")]
    if stage == "final_closer_questionnaire":
        return [_action(
            "submit_final_closer_questionnaire",
            "Submit Final Closer Questionnaire",
            allowed_input_fields=("business_outcome", "remaining_concern", "timing", "support_expectation", "readiness"),
            destination_route=f"/orbs/{project.id}",
            reason_available="The recommendation needs the customer's final decision-support answers.",
        )]
    if stage == "package_selection_commitment":
        if not _approved_products(db):
            return []
        return [_action(
            "package_commitment",
            "Commit to Package",
            confirmation_required=True,
            allowed_input_fields=("marketplace_product_id",),
            destination_route=f"/orbs/{project.id}",
            reason_available="Approved Website ORBS packages are available for selection.",
        )]
    if stage == "build_configuration":
        return [_action(
            "submit_build_configuration",
            "Submit Build Configuration",
            allowed_input_fields=("priority_routes", "installation_method", "support_level", "launch_timing", "technical_choices"),
            destination_route=f"/orbs/{project.id}",
            reason_available="A package has been committed for this project.",
        )]
    if stage == "final_order_review":
        return [
            _action("approve_final_order", "Approve Final Order", confirmation_required=True, destination_route=f"/orbs/{project.id}", reason_available="The itemized package and build configuration are ready for approval."),
            _action("view_final_order", "View Final Order", destination_route=f"/orbs/{project.id}", reason_available="The itemized package and build configuration can be reviewed without changing workflow state."),
        ]
    if stage == "signature":
        return [_action(
            "submit_signature",
            "Submit Signature",
            confirmation_required=True,
            allowed_input_fields=("signer_name", "accepted_terms", "signature_hash"),
            destination_route=f"/orbs/{project.id}",
            reason_available="The final order was approved and requires signature.",
        )]
    if stage == "checkout":
        return [_action(
            "open_checkout",
            "Open Checkout",
            confirmation_required=True,
            allowed_input_fields=("provider",),
            destination_route="/cart",
            reason_available="The signed project-bound order is ready for payment.",
        )]
    if stage == "verified_payment":
        return [_action("start_fulfillment", "Start Fulfillment", destination_route=f"/orbs/{project.id}", reason_available="Payment was verified and entitlement was granted.")]
    if stage == "fulfillment":
        return [_action("prepare_package_generation", "Prepare Package Generation", destination_route=f"/orbs/{project.id}", reason_available="Fulfillment prerequisites can now be checked.")]
    if stage == "review_required":
        return [_action("view_required_reviews", "View Required Reviews", destination_route=project_route, reason_available="Open review items must be resolved before package generation.")]
    if stage == "package_generation":
        return [_action("generate_entitled_orbpack", "Generate Entitled ORB Pack", confirmation_required=True, destination_route=f"/orbs/{project.id}", reason_available="Payment, entitlement, and review gates are satisfied.")]
    if stage == "installation":
        return [_action(
            "submit_installation_evidence",
            "Submit Installation Evidence",
            confirmation_required=True,
            allowed_input_fields=("method", "evidence", "installed_at"),
            destination_route=f"/orbs/{project.id}",
            reason_available="The entitled package was generated and is ready for installation.",
        )]
    if stage == "launch_verification":
        return [_action(
            "mark_website_orbs_live",
            "Verify Launch and Mark Live",
            confirmation_required=True,
            allowed_input_fields=("verification_evidence", "verified_url", "verified_at"),
            destination_route=f"/orbs/{project.id}",
            reason_available="Installation evidence exists and launch verification is required.",
        )]
    return []


def _stage_evidence(db: Session, project: Project, stage: str, evidence: Mapping[str, Any], order: Optional[OrbsBuildOrder]) -> Dict[str, Any]:
    preflight = evidence.get("preflight") or {}
    crawl = evidence.get("completed_crawl") or evidence.get("latest_crawl")
    audit = evidence.get("latest_audit")
    onboarding = db.query(OrbsOnboardingRecord).filter(
        OrbsOnboardingRecord.project_id == project.id
    ).first()
    onboarding_evidence = None
    if onboarding:
        onboarding_evidence = {
            "landing_intent": onboarding.landing_intent,
            "selected_tier_interest": onboarding.selected_tier_interest,
            "original_cta_destination": onboarding.original_cta_destination,
            "current_onboarding_step": onboarding.current_onboarding_step,
            "completed_onboarding_steps": list(onboarding.completed_onboarding_steps or []),
        }
    if stage == "preflight":
        return {
            "status": "complete" if evidence["preflight_complete"] else "incomplete",
            "pages_scanned": int(preflight.get("pages_scanned") or 0),
            "onboarding": onboarding_evidence,
        }
    if stage == "crawl":
        return {"status": getattr(crawl, "status", "not_started"), "pages_crawled": int(getattr(crawl, "pages_crawled", 0) or 0)}
    if stage == "final_audit":
        return {"status": "complete" if evidence["audit_complete"] else "incomplete", "overall_score": getattr(audit, "overall_score", None)}
    base = {
        "technical_gates": {key: bool(evidence[key]) for key in ("preflight_complete", "crawl_complete", "audit_complete")},
        "preflight": {"pages_scanned": int(preflight.get("pages_scanned") or 0), "warnings": len(preflight.get("warnings") or [])},
        "crawl": {"pages_crawled": int(getattr(crawl, "pages_crawled", 0) or 0)},
        "final_audit": {
            "overall_score": getattr(audit, "overall_score", None),
            "summary": ((getattr(audit, "report_data", None) or {}).get("summary") or {}),
            "pointer_summary": ((getattr(audit, "report_data", None) or {}).get("pointer_summary") or {}),
        },
    }
    base["onboarding"] = onboarding_evidence
    if stage in {"package_presentation_and_recommendation", "final_closer_questionnaire", "package_selection_commitment"}:
        products = _approved_products(db)
        base["approved_packages"] = [
            {"marketplace_product_id": str(item.id), "sku": item.system_number, "name": item.title, "tier": item.tier, "price_cents": item.price_cents, "currency": item.currency}
            for item in products
        ]
        base["package_recommendation"] = _package_recommendation(products, evidence, order)
    if order:
        base["build_order"] = {
            "package_sku": order.package_sku,
            "package_tier": order.package_tier,
            "payment_status": order.payment_status,
            "fulfillment_status": order.fulfillment_status,
            "has_package_artifact": bool(order.package_artifact),
            "installation_status": (order.installation or {}).get("status"),
            "launch_verification_status": (order.launch_verification or {}).get("status"),
        }
    return base


def compile_snapshot(db: Session, project: Project, customer: Customer) -> Dict[str, Any]:
    if project.customer_id != customer.id:
        raise GovernorRejection("unauthorized_project", "Project is not available", 404)
    evidence = technical_evidence(db, project)
    order: Optional[OrbsBuildOrder] = None
    if not evidence["preflight_complete"]:
        stage, status, blocking = "preflight", "action_required", "Preflight is incomplete."
    elif not evidence["crawl_complete"]:
        running = evidence.get("latest_crawl") and evidence["latest_crawl"].status in {"pending", "running"}
        stage, status, blocking = "crawl", "in_progress" if running else "action_required", None if running else "Crawl is incomplete."
    elif not evidence["audit_complete"]:
        running = bool(evidence.get("active_full_audit") or (evidence.get("latest_audit") and not evidence["latest_audit"].report_data))
        stage, status, blocking = "final_audit", "in_progress" if running else "action_required", None if running else "Final Audit is incomplete."
    else:
        order = _ensure_build_order(db, project, customer)
        stage, status, blocking = order.current_stage, order.stage_status, order.blocking_reason
        if stage == "fulfillment" and _open_reviews(db, project.id):
            stage, status, blocking = "review_required", "blocked", "Required review items remain open."
        elif stage in {"package_presentation_and_recommendation", "package_selection_commitment"} and not _approved_products(db):
            status, blocking = "blocked", "No approved public Website ORBS package is available in the authoritative marketplace catalog."
    actions = _allowed_actions(db, project, stage, evidence, order)
    completed = list(JOURNEY[:JOURNEY.index(stage)])
    if stage != "review_required":
        completed = [item for item in completed if item != "review_required"]
    version = str(order.version) if order else _technical_snapshot_version(evidence)
    next_action = actions[0]["name"] if actions else None
    customer_action = order.customer_action_required if order else None
    if not customer_action:
        customer_action = actions[0]["display_label"] if actions else ("Wait for the current operation to complete." if status == "in_progress" else None)
    approved_route = actions[0].get("destination_route") if len(actions) == 1 else None
    return {
        "schema": SNAPSHOT_SCHEMA,
        "snapshot_version": version,
        "customer_id": str(customer.id),
        "project_id": str(project.id),
        "project_display_name": project.name,
        "build_order_id": str(order.id) if order else None,
        "current_stage": stage,
        "stage_status": status,
        "completed_stages": completed,
        "blocking_reason": blocking,
        "customer_action_required": customer_action,
        "next_recommended_action": next_action,
        "approved_stage_evidence": _stage_evidence(db, project, stage, evidence, order),
        "approved_destination_route": approved_route,
        "approved_destination_verified": bool(approved_route),
        "updated_at": (order.updated_at if order else datetime.utcnow()).isoformat(),
        "allowed_actions": actions,
    }


def validate_submission(
    snapshot: Mapping[str, Any],
    payload: Mapping[str, Any],
    confirmation_evidence: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    if str(payload.get("project_id")) != str(snapshot["project_id"]):
        raise GovernorRejection("unauthorized_project", "Project binding does not match", 403)
    if str(payload.get("snapshot_version")) != str(snapshot["snapshot_version"]):
        raise GovernorRejection("stale_snapshot", "Snapshot version is stale")
    if payload.get("expected_stage") != snapshot["current_stage"]:
        raise GovernorRejection("stage_mismatch", "Expected stage does not match the authoritative stage")
    if snapshot.get("build_order_id") and str(payload.get("build_order_id")) != str(snapshot["build_order_id"]):
        raise GovernorRejection("precondition_failed", "Build order binding does not match")
    action = next((item for item in snapshot["allowed_actions"] if item["name"] == payload.get("action")), None)
    if not action:
        raise GovernorRejection("action_not_allowed", "Action is not allowed in the current stage")
    inputs = payload.get("inputs") or {}
    if not isinstance(inputs, Mapping):
        raise GovernorRejection("invalid_action_input", "Action inputs must be an object", 400)
    unexpected = set(inputs) - set(action.get("allowed_input_fields") or [])
    if unexpected:
        raise GovernorRejection("invalid_action_input", f"Unsupported action input fields: {sorted(unexpected)}", 400)
    if action.get("confirmation_required"):
        if not confirmation_evidence:
            raise GovernorRejection("confirmation_required", "Explicit customer confirmation is required", 400)
        if (
            confirmation_evidence.get("confirmed") is not True
            or
            str(confirmation_evidence.get("project_id")) != str(snapshot["project_id"])
            or confirmation_evidence.get("action_name") != action["name"]
            or str(confirmation_evidence.get("snapshot_version")) != str(snapshot["snapshot_version"])
        ):
            raise GovernorRejection("confirmation_required", "Confirmation evidence does not match this action snapshot", 400)
    return action


TRANSITIONS = {
    ("orbs", "review_orbs_integration"): "package_presentation_and_recommendation",
    ("package_presentation_and_recommendation", "start_final_closer_questionnaire"): "final_closer_questionnaire",
    ("final_closer_questionnaire", "submit_final_closer_questionnaire"): "package_selection_commitment",
    ("package_selection_commitment", "package_commitment"): "build_configuration",
    ("build_configuration", "submit_build_configuration"): "final_order_review",
    ("final_order_review", "approve_final_order"): "signature",
    ("signature", "submit_signature"): "checkout",
    ("verified_payment", "start_fulfillment"): "fulfillment",
    ("fulfillment", "prepare_package_generation"): "package_generation",
    ("package_generation", "generate_entitled_orbpack"): "installation",
    ("installation", "submit_installation_evidence"): "launch_verification",
    ("launch_verification", "mark_website_orbs_live"): "live",
}


def apply_transition_action(
    db: Session,
    project: Project,
    customer: Customer,
    snapshot: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> OrbsBuildOrder:
    order = db.get(OrbsBuildOrder, int(snapshot["build_order_id"])) if snapshot.get("build_order_id") else None
    if not order:
        raise GovernorRejection("precondition_failed", "A build order is required")
    if order.project_id != project.id or order.customer_id != customer.id:
        raise GovernorRejection("unauthorized_project", "Build order is not available", 404)
    action = str(payload["action"])
    inputs = dict(payload.get("inputs") or {})
    if action == "submit_final_closer_questionnaire":
        required = {"business_outcome", "remaining_concern", "timing", "support_expectation", "readiness"}
        if any(not str(inputs.get(field) or "").strip() for field in required):
            raise GovernorRejection("invalid_action_input", "All Final Closer Questionnaire answers are required", 400)
        order.questionnaire = inputs
    elif action == "package_commitment":
        try:
            product_id = int(inputs.get("marketplace_product_id"))
        except (TypeError, ValueError) as exc:
            raise GovernorRejection("invalid_action_input", "marketplace_product_id is required", 400) from exc
        product = next((item for item in _approved_products(db) if item.id == product_id), None)
        if not product:
            raise GovernorRejection("precondition_failed", "Selected package is not an approved Website ORBS product")
        order.package_product_id = product.id
        order.package_sku = product.system_number
        order.package_tier = product.tier or "standard"
        order.final_order = {
            "marketplace_product_id": str(product.id),
            "sku": product.system_number,
            "name": product.title,
            "description": product.description,
            "tier": product.tier,
            "unit_amount_cents": product.price_cents,
            "currency": product.currency,
            "quantity": 1,
            "total_amount_cents": product.price_cents,
            "recommendation_at_commitment": _package_recommendation(
                _approved_products(db),
                technical_evidence(db, project),
                order,
            ),
            "final_closer_answers": dict(order.questionnaire or {}),
        }
    elif action == "submit_build_configuration":
        required = {"priority_routes", "installation_method", "support_level", "launch_timing"}
        if any(inputs.get(field) in (None, "", []) for field in required):
            raise GovernorRejection("invalid_action_input", "Priority routes, installation method, support level, and launch timing are required", 400)
        order.build_configuration = inputs
    elif action == "approve_final_order":
        if not order.final_order or not order.build_configuration:
            raise GovernorRejection("precondition_failed", "Itemized order and build configuration are required")
    elif action == "submit_signature":
        if inputs.get("accepted_terms") is not True or not str(inputs.get("signer_name") or "").strip():
            raise GovernorRejection("invalid_action_input", "Signer name and accepted terms are required", 400)
        order.signature = {**inputs, "signed_at": datetime.utcnow().isoformat(), "customer_id": str(customer.id)}
    elif action == "start_fulfillment":
        if order.payment_status != "verified":
            raise GovernorRejection("payment_not_verified", "Verified payment is required")
        if not active_entitlement(db, order):
            raise GovernorRejection("entitlement_required", "Active project entitlement is required")
        order.fulfillment_status = "running"
    elif action == "prepare_package_generation":
        if _open_reviews(db, project.id):
            raise GovernorRejection("review_required", "Required reviews remain open")
        if not active_entitlement(db, order):
            raise GovernorRejection("entitlement_required", "Active project entitlement is required")
    elif action == "submit_installation_evidence":
        if not order.package_artifact:
            raise GovernorRejection("precondition_failed", "An entitled ORB pack must be generated first")
        if not inputs.get("method") or not inputs.get("evidence"):
            raise GovernorRejection("invalid_action_input", "Installation method and evidence are required", 400)
        order.installation = {**inputs, "status": "installed"}
    elif action == "mark_website_orbs_live":
        if (order.installation or {}).get("status") != "installed":
            raise GovernorRejection("precondition_failed", "Installation is not complete")
        if not inputs.get("verification_evidence") or not inputs.get("verified_url"):
            raise GovernorRejection("invalid_action_input", "Launch verification evidence and verified URL are required", 400)
        order.launch_verification = {**inputs, "status": "verified"}

    target = TRANSITIONS.get((order.current_stage, action))
    if not target:
        raise GovernorRejection("action_not_allowed", "No legal transition exists for this action")
    previous = order.current_stage
    order.current_stage = target
    order.stage_status = "complete" if target == "live" else "ready"
    order.blocking_reason = None
    order.customer_action_required = None
    order.version += 1
    order.updated_at = datetime.utcnow()
    _event(db, order, customer, "transition_accepted", action, previous, target, str(order.version), {"inputs": inputs})
    db.flush()
    return order


def active_entitlement(db: Session, order: OrbsBuildOrder) -> Optional[OrbsEntitlement]:
    return db.query(OrbsEntitlement).filter(
        OrbsEntitlement.build_order_id == order.id,
        OrbsEntitlement.project_id == order.project_id,
        OrbsEntitlement.customer_id == order.customer_id,
        OrbsEntitlement.package_sku == order.package_sku,
        OrbsEntitlement.status == "active",
    ).first()


def mark_payment_verified(db: Session, checkout_order: CheckoutOrder) -> OrbsBuildOrder:
    if not checkout_order.build_order_id or not checkout_order.project_id:
        raise GovernorRejection("precondition_failed", "Checkout order is not project-bound")
    order = db.get(OrbsBuildOrder, checkout_order.build_order_id)
    if not order or order.checkout_order_id != checkout_order.id or order.project_id != checkout_order.project_id:
        raise GovernorRejection("precondition_failed", "Checkout/build-order binding is invalid")
    if checkout_order.payment_verified_at and order.payment_status == "verified":
        return order
    if order.current_stage != "checkout":
        raise GovernorRejection("stage_mismatch", "Verified payment can advance only an order at Checkout")
    if not order.package_sku or not order.package_tier:
        raise GovernorRejection("precondition_failed", "A committed package is required before verified payment")
    if checkout_order.amount_cents != int((order.final_order or {}).get("total_amount_cents") or -1):
        raise GovernorRejection("precondition_failed", "Verified payment amount does not match the final order")
    checkout_order.status = "paid"
    checkout_order.payment_verified_at = datetime.utcnow()
    order.payment_status = "verified"
    order.current_stage = "verified_payment"
    order.stage_status = "ready"
    order.version += 1
    order.updated_at = datetime.utcnow()
    entitlement = active_entitlement(db, order)
    if not entitlement:
        entitlement = OrbsEntitlement(
            build_order_id=order.id,
            project_id=order.project_id,
            customer_id=order.customer_id,
            checkout_order_id=checkout_order.id,
            package_sku=str(order.package_sku),
            package_tier=str(order.package_tier),
            status="active",
        )
        db.add(entitlement)
    customer = db.get(Customer, order.customer_id)
    _event(db, order, customer, "payment_verified", "verified_webhook", "checkout", "verified_payment", str(order.version), {"checkout_order_id": str(checkout_order.id)})
    db.flush()
    return order


def record_package_artifact(db: Session, order: OrbsBuildOrder, customer: Customer, artifact: Mapping[str, Any]) -> None:
    if not active_entitlement(db, order):
        raise GovernorRejection("entitlement_required", "Matching active entitlement is required")
    order.package_artifact = dict(artifact)
    order.fulfillment_status = "package_generated"


def record_action_event(
    db: Session,
    project: Project,
    customer: Customer,
    event_type: str,
    action_name: str,
    snapshot_version: str,
    payload: Optional[Mapping[str, Any]] = None,
) -> None:
    order = db.query(OrbsBuildOrder).filter(OrbsBuildOrder.project_id == project.id).first()
    _event(
        db,
        order,
        customer,
        event_type,
        action_name,
        order.current_stage if order else None,
        order.current_stage if order else None,
        snapshot_version,
        {"project_id": str(project.id), **dict(payload or {})},
    )


def _event(
    db: Session,
    order: Optional[OrbsBuildOrder],
    customer: Customer,
    event_type: str,
    action_name: Optional[str],
    from_stage: Optional[str],
    to_stage: Optional[str],
    snapshot_version: str,
    payload: Mapping[str, Any],
    reason_code: Optional[str] = None,
) -> None:
    db.add(OrbsStageEvent(
        build_order_id=order.id if order else None,
        project_id=order.project_id if order else int(payload.get("project_id") or 0),
        customer_id=customer.id,
        event_type=event_type,
        action_name=action_name,
        from_stage=from_stage,
        to_stage=to_stage,
        snapshot_version=snapshot_version,
        reason_code=reason_code,
        payload=dict(payload),
    ))


def record_rejection(
    db: Session,
    project: Project,
    customer: Customer,
    payload: Mapping[str, Any],
    rejection: GovernorRejection,
) -> None:
    order = db.query(OrbsBuildOrder).filter(OrbsBuildOrder.project_id == project.id).first()
    _event(
        db,
        order,
        customer,
        "action_rejected",
        str(payload.get("action") or "") or None,
        order.current_stage if order else str(payload.get("expected_stage") or "") or None,
        None,
        str(order.version) if order else str(payload.get("snapshot_version") or "unknown"),
        {"project_id": str(project.id)},
        rejection.code,
    )
