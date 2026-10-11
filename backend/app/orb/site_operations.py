"""Bounded Website ORB product operations.

The initial product contract is intentionally small:

* MORBs inspect, research, diagnose, and report.  They never write.
* The primary ORB coordinates work and is the only component that may invoke
  a catalog adapter for a price change.
* The Governor authorizes the bounded write scope.
* Every attempted write receives durable evidence through the A.I.M.S. sink.

This module is adapter-driven so the same contracts can be used with a local
catalog, a commerce API, or a test fixture without giving cognition direct
database access.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence


SITE_OPERATIONS_SCHEMA = "orb_weaver.site_operations.v1"
MORB_REPORT_SCHEMA = "orb_weaver.morb_report.v1"
PRICE_JOB_SCHEMA = "orb_weaver.orb_price_job.v1"


MORB_CAPABILITIES = frozenset({
    "research_similar_products",
    "retrieve_catalog_prices",
    "diagnose_catalog_data",
    "assist_visitor",
})
MORB_FORBIDDEN_ACTIONS = frozenset({
    "modify_product_prices",
    "repair_website",
    "build_site_component",
    "modify_site_component",
})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _id(prefix: str, payload: Any) -> str:
    material = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}-{hashlib.sha256(material.encode()).hexdigest()[:24]}"


def _tokens(value: Any) -> set[str]:
    return {item for item in re.findall(r"[a-z0-9]{3,}", str(value or "").lower())}


class Mesh(Protocol):
    def publish(self, message: Mapping[str, Any]) -> None: ...


class EvidenceSink(Protocol):
    def record(self, evidence: Mapping[str, Any]) -> str: ...


class CatalogAdapter(Protocol):
    def read_price(self, entity_id: str) -> Mapping[str, Any]: ...
    def write_price(self, entity_id: str, amount: Decimal, currency: str) -> Mapping[str, Any]: ...


class Governor(Protocol):
    def authorize(self, action: str, scope: Sequence[str], *, actor: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class MorbAssignment:
    morb_id: str
    department: str
    capabilities: frozenset[str]
    task: str
    scope: Dict[str, Any]
    permissions: frozenset[str] = frozenset()
    assignment_id: str = ""

    def __post_init__(self) -> None:
        if not self.morb_id or not self.department or not self.task:
            raise ValueError("MORB assignment requires an id, department, and task")
        if self.permissions & MORB_FORBIDDEN_ACTIONS:
            raise ValueError("MORBs cannot receive execution permissions")
        if not self.capabilities <= MORB_CAPABILITIES:
            raise ValueError("MORB capability is outside the bounded information contract")
        if not self.assignment_id:
            object.__setattr__(self, "assignment_id", _id("MORB-JOB", {
                "morb_id": self.morb_id, "department": self.department,
                "task": self.task, "scope": self.scope,
            }))


@dataclass
class MorbReport:
    assignment_id: str
    morb_id: str
    status: str
    findings: List[Dict[str, Any]] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    reported_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {"schema": MORB_REPORT_SCHEMA, "assignment_id": self.assignment_id,
                "morb_id": self.morb_id, "status": self.status,
                "findings": self.findings, "evidence_ids": self.evidence_ids,
                "reported_at": self.reported_at}


class SiteMesh:
    """Small deterministic message transport used by the operation boundary."""

    def __init__(self) -> None:
        self.messages: List[Dict[str, Any]] = []

    def publish(self, message: Mapping[str, Any]) -> None:
        self.messages.append(dict(message))


class InMemoryEvidence:
    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    def record(self, evidence: Mapping[str, Any]) -> str:
        item = dict(evidence)
        evidence_id = str(item.get("evidence_id") or _id("AIMS", item))
        item["evidence_id"] = evidence_id
        item.setdefault("recorded_at", _now())
        self.records.append(item)
        return evidence_id


class AllowListGovernor:
    """Minimal policy adapter; production implementations can call site policy."""

    def __init__(self, allowed_actions: Iterable[str] = ()) -> None:
        self.allowed_actions = set(allowed_actions)

    def authorize(self, action: str, scope: Sequence[str], *, actor: str) -> Mapping[str, Any]:
        allowed = action in self.allowed_actions and actor == "primary_orb"
        return {"authorized": allowed, "action": action, "scope": list(scope),
                "actor": actor, "reason": "approved_scope" if allowed else "governor_denied"}


def assign_morb(*, morb_id: str, department: str, task: str, scope: Dict[str, Any],
               capabilities: Iterable[str]) -> MorbAssignment:
    """Create a read-only MORB assignment and reject execution authority."""
    if re.search(r"\b(update|modify|write|repair|build|change)\b", task.casefold()):
        raise ValueError("MORBs may investigate and report, but cannot be assigned execution work")
    return MorbAssignment(morb_id=morb_id, department=department, task=task,
                          scope=scope, capabilities=frozenset(capabilities))


def similar_products(records: Iterable[Mapping[str, Any]], source: Mapping[str, Any], *, limit: int = 4) -> List[Dict[str, Any]]:
    """Rank verified records deterministically for visitor comparison."""
    source_id = str(source.get("entity_id") or "")
    source_category = str(source.get("category") or "").casefold()
    source_terms = _tokens(" ".join(str(source.get(key) or "") for key in ("name", "description")))
    source_attrs = {str(k).casefold() + ":" + str(v).casefold() for k, v in (source.get("attributes") or {}).items()}
    ranked: List[tuple[float, Dict[str, Any]]] = []
    for raw in records:
        item = dict(raw)
        if str(item.get("entity_id") or "") == source_id or item.get("verified") is False:
            continue
        category = str(item.get("category") or "").casefold()
        terms = _tokens(" ".join(str(item.get(key) or "") for key in ("name", "description")))
        attrs = {str(k).casefold() + ":" + str(v).casefold() for k, v in (item.get("attributes") or {}).items()}
        category_score = 0.55 if source_category and category == source_category else 0.0
        term_score = 0.25 * len(source_terms & terms) / max(1, len(source_terms))
        attr_score = 0.20 * len(source_attrs & attrs) / max(1, len(source_attrs))
        score = round(category_score + term_score + attr_score, 4)
        if score > 0:
            item["similarity_score"] = score
            ranked.append((score, item))
    ranked.sort(key=lambda pair: (-pair[0], str(pair[1].get("entity_id") or "")))
    return [item for _, item in ranked[:max(0, limit)]]


def create_pointer_pings(products: Iterable[Mapping[str, Any]], *, authorized: bool = True) -> List[Dict[str, Any]]:
    """Create only route-backed, exact-one comparison targets."""
    if not authorized:
        return []
    pings = []
    for product in products:
        entity_id, route = str(product.get("entity_id") or ""), str(product.get("route") or "")
        if not entity_id or not route or not product.get("verified", True):
            continue
        pings.append({"target_id": entity_id, "route": route, "target_type": "price_card",
                      "meaning": f"Compare {product.get('name') or entity_id}",
                      "pointer_class": "live_guidance", "guidance_eligible": True,
                      "runtime_policy": {"may_point": True}})
    return pings


def inspect_similar_products(*, assignment: MorbAssignment, source: Mapping[str, Any],
                             records: Iterable[Mapping[str, Any]], mesh: Mesh) -> MorbReport:
    if "research_similar_products" not in assignment.capabilities:
        raise ValueError("assignment cannot research similar products")
    matches = similar_products(records, source)
    report = MorbReport(assignment.assignment_id, assignment.morb_id, "completed", matches)
    mesh.publish({"type": "morb_report", "destination": "primary_orb", "report": report.to_dict()})
    return report


def _parse_price(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("price must be a finite non-negative number") from exc
    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
        raise ValueError("price must be a finite non-negative amount with at most two decimals")
    return amount.quantize(Decimal("0.01"))


class PriceUpdateService:
    """Primary-ORB price workflow with dry-run, authorization, and verification."""

    def __init__(self, *, adapter: CatalogAdapter, governor: Governor, evidence: EvidenceSink,
                 mesh: Optional[Mesh] = None) -> None:
        self.adapter, self.governor, self.evidence = adapter, governor, evidence
        self.mesh = mesh or SiteMesh()

    def dry_run(self, updates: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        seen: set[str] = set()
        valid, errors = [], []
        for index, update in enumerate(updates):
            entity_id = str(update.get("entity_id") or update.get("sku") or "").strip()
            currency = str(update.get("currency") or "USD").upper()
            if not entity_id:
                errors.append({"index": index, "reason": "missing_entity_id"})
                continue
            if entity_id in seen:
                errors.append({"index": index, "entity_id": entity_id, "reason": "duplicate_entity_id"})
                continue
            seen.add(entity_id)
            try:
                amount = _parse_price(update.get("amount"))
            except ValueError as exc:
                errors.append({"index": index, "entity_id": entity_id, "reason": str(exc)})
                continue
            try:
                current = dict(self.adapter.read_price(entity_id))
            except Exception as exc:  # adapter boundary: report, never partially write
                errors.append({"index": index, "entity_id": entity_id, "reason": f"lookup_failed:{exc}"})
                continue
            if not current.get("found", True):
                errors.append({"index": index, "entity_id": entity_id, "reason": "catalog_record_not_found"})
                continue
            valid.append({"entity_id": entity_id, "requested_amount": str(amount),
                          "currency": currency, "original": current})
        return {"valid": not errors and bool(valid), "eligible": valid, "errors": errors,
                "counts": {"requested": len(updates), "eligible": len(valid), "errors": len(errors)}}

    def execute(self, updates: Sequence[Mapping[str, Any]], *, actor: str = "primary_orb") -> Dict[str, Any]:
        validation = self.dry_run(updates)
        job_id = _id("PRICE", validation)
        scope = [item["entity_id"] for item in validation["eligible"]]
        approval = self.governor.authorize("modify_product_prices", scope, actor=actor)
        if not validation["valid"] or not approval.get("authorized"):
            status = "validation_failed" if not validation["valid"] else "governor_denied"
            record = {"schema": PRICE_JOB_SCHEMA, "job_id": job_id, "status": status,
                      "validation": validation, "authorization": dict(approval), "actor": actor}
            evidence_id = self.evidence.record(record)
            record["evidence_id"] = evidence_id
            self.mesh.publish({"type": "price_job_report", "destination": "owner", "report": record})
            return record

        results, succeeded = [], 0
        for item in validation["eligible"]:
            entity_id, requested = item["entity_id"], Decimal(item["requested_amount"])
            try:
                write_result = dict(self.adapter.write_price(entity_id, requested, item["currency"]))
                observed = dict(self.adapter.read_price(entity_id))
                verified = (str(observed.get("amount")) == str(requested)
                            and str(observed.get("currency", item["currency"])).upper() == item["currency"])
                if verified:
                    succeeded += 1
                results.append({"entity_id": entity_id, "original": item["original"],
                                "requested": {"amount": str(requested), "currency": item["currency"]},
                                "write": write_result, "observed": observed,
                                "status": "verified" if verified else "verification_failed"})
            except Exception as exc:
                results.append({"entity_id": entity_id, "original": item["original"],
                                "requested": {"amount": str(requested), "currency": item["currency"]},
                                "status": "failed", "error": str(exc)})
        record = {"schema": PRICE_JOB_SCHEMA, "job_id": job_id,
                  "status": "completed" if succeeded == len(scope) else "completed_with_errors",
                  "authorization": dict(approval), "actor": actor, "results": results,
                  "counts": {"requested": len(updates), "eligible": len(scope), "succeeded": succeeded,
                             "failed": len(scope) - succeeded}}
        evidence_id = self.evidence.record(record)
        record["evidence_id"] = evidence_id
        self.mesh.publish({"type": "price_job_report", "destination": "owner", "report": record})
        return record

