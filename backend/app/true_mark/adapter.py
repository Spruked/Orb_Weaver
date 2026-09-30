"""ORB certification contract for the independent True Mark company.

This module records an auditable request and refuses to guess an external API.
True Mark remains the certification/minting authority.
"""

from __future__ import annotations

import json
import hashlib
import hmac
from pathlib import Path
from typing import Any

import httpx

from app.core import storage
from app.core.storage import require_vault_path
from app.core.config import settings
from app.core.timekeeping import stamp_record


TRUEMARK_CERTIFICATION_FEE_USD = 12.88
def _requests_root() -> Path:
    return storage.VAULT_ROOT / "integrations" / "true_mark" / "orb_certification_requests"


def build_certification_request(
    *,
    orb_identity: dict[str, Any],
    order_reference: str | None = None,
    licensee_reference: str | None = None,
) -> dict[str, Any]:
    serial = str(orb_identity.get("serial_number") or "")
    if not serial.startswith("ORB-SN-"):
        raise ValueError("True Mark certification requires a permanent ORB serial")
    return stamp_record({
        "schema": "orb_weaver.true_mark.orb_certification_request.v1",
        "request_id": f"TM-ORB-REQ-{hashlib.sha256(serial.encode('utf-8')).hexdigest()[:24]}",
        "status": "PENDING_EXTERNAL_ISSUANCE",
        "issuer_company": "True Mark",
        "customer_company": "ORB Weaver",
        "orb_serial_number": serial,
        "site_id": orb_identity.get("site_id"),
        "domain": orb_identity.get("domain"),
        "orb_product_edition": orb_identity.get("product_edition"),
        "order_reference": order_reference,
        "licensee_reference": licensee_reference,
        "issuance_fee_usd": TRUEMARK_CERTIFICATION_FEE_USD,
        "requested_artifacts": [
            "certificate_of_authenticity",
            "polygon_kl_nft",
            "embedded_orb_license",
            "true_mark_provenance_record",
        ],
        "external_authority": "True Mark must validate and issue; no simulated identifiers are accepted.",
        "orb_runtime_dependency": False,
    }, source="orb_weaver.true_mark_boundary")


def record_pending_certification_request(request: dict[str, Any]) -> Path:
    """Persist a pending request; never claims that True Mark issued it."""
    target_root = require_vault_path(_requests_root(), "True Mark certification request")
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / f"{request['request_id']}.json"
    target.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")
    return target


def _request_path(request_id: str) -> Path:
    return require_vault_path(_requests_root(), "True Mark certification request") / f"{request_id}.json"


def _update_request(request_id: str, **changes: Any) -> dict[str, Any]:
    path = _request_path(request_id)
    current = json.loads(path.read_text(encoding="utf-8"))
    current.update(changes)
    updated = stamp_record(current, source="orb_weaver.true_mark_submission")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(updated, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
    return updated


def submit_certification_request(request: dict[str, Any]) -> dict[str, Any]:
    """Submit once to True Mark when configured; never fabricate issuance."""
    base_url = (settings.TRUEMARK_BASE_URL or "").rstrip("/")
    secret = (settings.TRUEMARK_ORB_SHARED_SECRET or "").strip()
    if not base_url or not secret:
        return {"status": "NOT_CONFIGURED", "request_id": request["request_id"]}

    body = json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    url = f"{base_url}{settings.TRUEMARK_ORB_CERTIFICATION_PATH}"
    try:
        response = httpx.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-ORB-Weaver-Signature": signature,
                "X-ORB-Weaver-Request-Id": request["request_id"],
            },
            timeout=settings.TRUEMARK_TIMEOUT_SECONDS,
        )
        response_payload = response.json()
        if 200 <= response.status_code < 300:
            updated = _update_request(
                request["request_id"],
                status="ACCEPTED_PENDING_ISSUANCE",
                external_response=response_payload,
            )
            return {"status": updated["status"], "request_id": request["request_id"], "response": response_payload}
        updated = _update_request(
            request["request_id"],
            status="EXTERNAL_REJECTED",
            external_error={"status_code": response.status_code, "response": response_payload},
        )
        return {"status": updated["status"], "request_id": request["request_id"], "response": response_payload}
    except (httpx.HTTPError, ValueError) as exc:
        updated = _update_request(
            request["request_id"],
            status="EXTERNAL_UNAVAILABLE",
            external_error={"error": str(exc)},
        )
        return {"status": updated["status"], "request_id": request["request_id"], "error": str(exc)}
