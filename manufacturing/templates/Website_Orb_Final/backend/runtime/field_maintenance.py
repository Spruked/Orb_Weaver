"""Governed field maintenance for a manufactured Website ORB.

Orb Weaver creates the initial Site World.  This module gives an installed
clone a bounded, explicit maintenance loop for known commercial surfaces:

    observe -> compare -> update -> reverify affected targets -> publish

It deliberately does not crawl a site, mutate products, or choose arbitrary
targets.  A Dock/browser adapter supplies observations and live-verification
evidence.  Until the affected evidence is accepted, changed facts remain
pending and cannot replace the authoritative Site World answer path.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA = "orb_weaver.field_site_world_maintenance.v1"
STATE_FILENAME = "state.json"
COMMERCIAL_FIELDS = (
    "title",
    "sku",
    "price",
    "sale_price",
    "availability",
    "inventory_status",
    "variants",
    "sizes",
    "colors",
    "options",
    "specifications",
    "images",
    "product_url",
    "shipping_state",
    "primary_cta",
)
STRUCTURAL_FIELDS = {"page_structure_hash", "navigation_hash", "template_hash", "primary_cta", "target_identity"}
FIELD_DEPENDENCIES = {
    "price": {"price", "sale_price"},
    "sale_price": {"price", "sale_price"},
    "variants": {"variant", "variants", "option", "options", "size", "color", "cart", "cta"},
    "sizes": {"variant", "variants", "option", "options", "size", "cart"},
    "colors": {"variant", "variants", "option", "options", "color", "cart"},
    "options": {"variant", "variants", "option", "options", "cart"},
    "availability": {"availability", "inventory", "cart", "cta"},
    "inventory_status": {"availability", "inventory", "cart", "cta"},
    "primary_cta": {"cta", "cart", "purchase"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _slug_tokens(value: Any) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", str(value or "").lower()) if len(token) > 2}


def _safe_copy(value: Any, *, limit: int = 200) -> Any:
    """Keep adapter-provided evidence bounded before it enters the Vault."""
    if isinstance(value, str):
        return value[:limit]
    if isinstance(value, list):
        return [_safe_copy(item, limit=limit) for item in value[:32]]
    if isinstance(value, dict):
        return {str(key)[:80]: _safe_copy(child, limit=limit) for key, child in list(value.items())[:64]}
    return value


def _product_id(observation: Dict[str, Any]) -> str:
    for key in ("product_id", "entity_id", "id", "sku", "product_url", "url"):
        value = str(observation.get(key) or "").strip()
        if value:
            return value[:240]
    raise ValueError("Each product observation requires product_id, entity_id, id, sku, or product_url")


def _target_id(target: Dict[str, Any]) -> str:
    value = str(target.get("target_id") or target.get("id") or "").strip()
    if not value:
        raise ValueError("Each target observation requires target_id")
    return value[:240]


def _target_identity_hash(target: Dict[str, Any]) -> str:
    explicit = str(target.get("identity_hash") or "").strip()
    if explicit:
        return explicit[:128]
    identity = {
        "target_id": _target_id(target),
        "target_type": target.get("target_type") or target.get("kind"),
        "selector": target.get("selector") or target.get("semantic_locator") or target.get("locator"),
        "dom_signature": target.get("dom_signature") or target.get("structure_hash"),
    }
    return _hash(identity)


def _target_verified(target: Dict[str, Any]) -> bool:
    if target.get("verified") is True:
        return True
    return bool(
        target.get("exists") is True
        and target.get("unique_match") is True
        and target.get("visible", True) is not False
        and (target.get("evidence") or target.get("verification_evidence"))
    )


def normalize_target(target: Dict[str, Any]) -> Dict[str, Any]:
    target_id = _target_id(target)
    verified = _target_verified(target)
    return {
        "target_id": target_id,
        "target_type": str(target.get("target_type") or target.get("kind") or "commercial").lower()[:80],
        "meaning": str(target.get("meaning") or target.get("label") or target_id)[:300],
        "identity_hash": _target_identity_hash(target),
        "depends_on": [str(item)[:80].lower() for item in (target.get("depends_on") or [])[:16]],
        "verified": verified,
        "status": "verified" if verified else "unverified",
        "observed_at": str(target.get("observed_at") or utc_now())[:64],
        "evidence": _safe_copy(target.get("evidence") or target.get("verification_evidence") or []),
        "geometry": _safe_copy(target.get("geometry") or {}),
        "locator": _safe_copy(target.get("locator") or target.get("selector") or target.get("semantic_locator") or ""),
    }


def normalize_product(observation: Dict[str, Any]) -> Dict[str, Any]:
    product_id = _product_id(observation)
    targets = [normalize_target(item) for item in (observation.get("targets") or []) if isinstance(item, dict)]
    values = {
        field: _safe_copy(observation.get(field))
        for field in COMMERCIAL_FIELDS
        if field in observation
    }
    for field in ("page_structure_hash", "navigation_hash", "template_hash"):
        if field in observation:
            values[field] = str(observation.get(field) or "")[:160]
    return {
        "product_id": product_id,
        "product_url": str(observation.get("product_url") or observation.get("url") or values.get("product_url") or "")[:1000],
        "values": values,
        "fingerprint": _hash(values),
        "targets": targets,
        "observed_at": str(observation.get("observed_at") or utc_now())[:64],
        "source": str(observation.get("source") or "dock_product_state_observation")[:160],
        "observation_verified": observation.get("verified") is True,
    }


def _changed_fields(previous: Dict[str, Any], current: Dict[str, Any]) -> List[str]:
    before = previous.get("values") or (previous.get("observed") or {}).get("values") or {}
    after = current.get("values") or {}
    return sorted({field for field in set(before) | set(after) if before.get(field) != after.get(field)})


def _target_identity_map(product: Dict[str, Any]) -> Dict[str, str]:
    observed = product.get("observed") or product
    return {
        str(target.get("target_id")): str(target.get("identity_hash"))
        for target in (observed.get("targets") or [])
        if isinstance(target, dict) and target.get("target_id")
    }


def _affected_target_kinds(changed_fields: Iterable[str]) -> set[str]:
    changed = set(changed_fields)
    if changed & {"page_structure_hash", "navigation_hash", "template_hash"}:
        return {"*"}
    kinds: set[str] = set()
    for field in changed:
        kinds.update(FIELD_DEPENDENCIES.get(field, {field}))
    return kinds


def _default_state() -> Dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": 1,
        "config": {
            "enabled": True,
            "auto_run": False,
            "auto_publish": False,
            "execution_mode": "observe_only",
            "mutation_authorized": False,
        },
        "products": {},
        "targets": {},
        "last_scan": None,
        "last_reverification": None,
        "last_published": None,
        "deep_rescan_required": False,
        "events": [],
    }


class FieldMaintenanceStore:
    """Atomic state store under the manufactured canonical Vault."""

    def __init__(self, root: Path):
        self.root = root
        self.path = root / STATE_FILENAME
        self.root.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not self.path.is_file():
            return _default_state()
        with self.path.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
        if not isinstance(state, dict) or state.get("schema") != SCHEMA:
            raise RuntimeError("Field maintenance state has an invalid schema")
        return state

    def save(self, state: Dict[str, Any]) -> None:
        temp = self.path.with_name(f".{self.path.name}.tmp")
        temp.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(self.path)

    def event(self, state: Dict[str, Any], event_type: str, payload: Dict[str, Any]) -> None:
        state.setdefault("events", []).append({
            "event": event_type,
            "recorded_at": utc_now(),
            **_safe_copy(payload),
        })
        state["events"] = state["events"][-100:]


class FieldMaintenanceEngine:
    def __init__(self, store: FieldMaintenanceStore, known_products: Optional[Iterable[Dict[str, Any]]] = None):
        self.store = store
        self.known_products = {
            str(item.get("entity_id") or item.get("product_id") or item.get("id") or item.get("sku")): item
            for item in (known_products or [])
            if isinstance(item, dict) and (item.get("entity_id") or item.get("product_id") or item.get("id") or item.get("sku"))
        }

    def status(self) -> Dict[str, Any]:
        state = self.store.load()
        products = state.get("products") or {}
        targets = state.get("targets") or {}
        return {
            "schema": SCHEMA,
            "capability": "field_site_world_maintenance",
            "operations": ["product_delta_scan", "affected_target_reverification", "maintenance_cycle"],
            "config": state.get("config") or {},
            "dormant": not bool((state.get("config") or {}).get("auto_run")),
            "execution_mode": (state.get("config") or {}).get("execution_mode", "observe_only"),
            "mutation_authorized": bool((state.get("config") or {}).get("mutation_authorized")),
            "products_tracked": len(products),
            "authoritative_products": sum(1 for item in products.values() if item.get("authoritative")),
            "targets_tracked": sum(len(item) for item in targets.values() if isinstance(item, dict)),
            "deep_rescan_required": bool(state.get("deep_rescan_required")),
            "last_scan": state.get("last_scan"),
            "last_reverification": state.get("last_reverification"),
            "last_published": state.get("last_published"),
        }

    def product_delta_scan(self, observations: List[Dict[str, Any]], *, dry_run: bool = False) -> Dict[str, Any]:
        if not isinstance(observations, list) or not observations:
            raise ValueError("Product Delta Scan requires at least one product observation")
        state = self.store.load()
        config = state.get("config") or {}
        if not config.get("enabled", True):
            raise PermissionError("Field Site World Maintenance is disabled by owner policy")
        previous_products = state.get("products") or {}
        results: List[Dict[str, Any]] = []
        proposed_products: Dict[str, Any] = deepcopy(previous_products)
        proposed_targets: Dict[str, Any] = deepcopy(state.get("targets") or {})
        deep_rescan = bool(state.get("deep_rescan_required"))

        for raw in observations:
            if not isinstance(raw, dict):
                raise ValueError("Product observations must be objects")
            current = normalize_product(raw)
            product_id = current["product_id"]
            previous = previous_products.get(product_id)
            known = not self.known_products or product_id in self.known_products
            changed = _changed_fields(previous, current) if previous else list(current["values"])
            if previous and _target_identity_map(previous) != _target_identity_map(current):
                changed = sorted(set(changed) | {"target_identity"})
            structural = bool(set(changed) & STRUCTURAL_FIELDS)
            unknown_product = not known
            if unknown_product:
                deep_rescan = True

            if previous and not changed:
                if current["targets"]:
                    proposed_targets[product_id] = {
                        target["target_id"]: target
                        for target in current["targets"]
                    }
                record = {
                    **previous,
                    "observed": current,
                    "last_observed": current["observed_at"],
                    "freshness": "fresh",
                    "delta_status": "unchanged",
                }
                proposed_products[product_id] = record
                results.append({
                    "product_id": product_id,
                    "status": "unchanged",
                    "changed_fields": [],
                    "authoritative": bool(previous.get("authoritative")),
                    "target_reverification_required": [],
                })
                continue

            affected_kinds = _affected_target_kinds(changed)
            previous_targets = (state.get("targets") or {}).get(product_id) or {}
            current_targets = {target["target_id"]: target for target in current["targets"]}
            # A first observation is never authoritative by itself.  The
            # affected target pass is the publish gate, including for a new
            # product, so the ordinary cycle remains observe -> reverify ->
            # publish rather than allowing a scalar observation to bypass DOM
            # evidence.
            can_publish_baseline = False
            preserved_targets = []
            if previous:
                for target_id, old_target in previous_targets.items():
                    new_target = current_targets.get(target_id)
                    if new_target and new_target["identity_hash"] == old_target.get("identity_hash") and new_target["verified"]:
                        preserved_targets.append(target_id)
            record = {
                "product_id": product_id,
                "observed": current,
                "published": current if can_publish_baseline else previous.get("published") if previous else None,
                "authoritative": can_publish_baseline or (bool(previous) and not changed),
                "freshness": "fresh" if can_publish_baseline else "pending_target_reverification",
                "delta_status": "baseline" if not previous else "changed",
                "changed_fields": changed,
                "structural_drift": structural,
                "unknown_product": unknown_product,
                "last_observed": current["observed_at"],
                "last_verified": previous.get("last_verified") if previous else current["observed_at"] if can_publish_baseline else None,
                "preserved_target_ids": preserved_targets,
            }
            proposed_products[product_id] = record
            if not previous and current["targets"]:
                proposed_targets[product_id] = {
                    target["target_id"]: target
                    for target in current["targets"]
                }
            if structural or unknown_product:
                deep_rescan = True
            results.append({
                "product_id": product_id,
                "status": record["delta_status"],
                "changed_fields": changed,
                "structural_drift": structural,
                "unknown_product": unknown_product,
                "authoritative": record["authoritative"],
                "target_reverification_required": sorted(affected_kinds),
                "preserved_target_ids": preserved_targets,
            })

        response = {
            "schema": SCHEMA,
            "operation": "product_delta_scan",
            "mode": "dry_run" if dry_run else "published_observation",
            "observed_at": utc_now(),
            "results": results,
            "deep_rescan_required": deep_rescan,
            "governance": {
                "authority": "installed_orb_field_maintenance",
                "source": "dock_product_state_observation",
                "mutation_authorized": False,
                "auto_run": bool(config.get("auto_run")),
                "auto_publish": bool(config.get("auto_publish")),
                "unresolved_changes_remain_non_authoritative": True,
            },
        }
        if dry_run:
            return response
        state["products"] = proposed_products
        state["targets"] = proposed_targets
        state["deep_rescan_required"] = deep_rescan
        state["last_scan"] = response["observed_at"]
        self.store.event(state, "product_delta_scan", {
            "products": [item["product_id"] for item in results],
            "changed": [item["product_id"] for item in results if item["changed_fields"]],
            "deep_rescan_required": deep_rescan,
        })
        self.store.save(state)
        return response

    def reverify_targets(self, product_id: str, targets: List[Dict[str, Any]]) -> Dict[str, Any]:
        product_id = str(product_id or "").strip()
        if not product_id:
            raise ValueError("Affected Target Reverification requires product_id")
        state = self.store.load()
        config = state.get("config") or {}
        if not config.get("enabled", True):
            raise PermissionError("Field Site World Maintenance is disabled by owner policy")
        product = (state.get("products") or {}).get(product_id)
        if not product:
            raise KeyError(f"No observed product state exists for {product_id}")
        observed_targets = {target["target_id"]: target for target in (normalize_target(item) for item in targets)}
        old_targets = ((state.get("targets") or {}).get(product_id) or {})
        changes = product.get("changed_fields") or []
        affected_kinds = _affected_target_kinds(changes)
        next_targets: Dict[str, Any] = {}
        promoted: List[str] = []
        quarantined: List[str] = []
        pending: List[str] = []

        for target_id, old_target in old_targets.items():
            candidate = observed_targets.get(target_id)
            if candidate is None:
                next_targets[target_id] = {**old_target, "status": "quarantined", "verified": False, "quarantine_reason": "target_missing"}
                quarantined.append(target_id)
                continue
            identity_same = candidate["identity_hash"] == old_target.get("identity_hash")
            dependency_match = not affected_kinds or "*" in affected_kinds or not candidate["depends_on"] or bool(set(candidate["depends_on"]) & affected_kinds)
            if candidate["verified"] and identity_same and dependency_match:
                next_targets[target_id] = {**candidate, "status": "verified", "verified": True, "last_verified": utc_now()}
                promoted.append(target_id)
            elif candidate["verified"] and not identity_same:
                next_targets[target_id] = {**old_target, "status": "quarantined", "verified": False, "quarantine_reason": "target_identity_changed"}
                quarantined.append(target_id)
            else:
                next_targets[target_id] = {**candidate, "status": "pending", "verified": False}
                pending.append(target_id)

        for target_id, candidate in observed_targets.items():
            if target_id in next_targets:
                continue
            if candidate["verified"]:
                next_targets[target_id] = {**candidate, "status": "verified", "verified": True, "last_verified": utc_now(), "promotion": "new_candidate"}
                promoted.append(target_id)
            else:
                next_targets[target_id] = {**candidate, "status": "pending", "verified": False}
                pending.append(target_id)

        replacement_promoted = [target_id for target_id in promoted if target_id not in old_targets]
        observation_verified = bool((product.get("observed") or {}).get("observation_verified"))
        all_affected_verified = (
            observation_verified
            and not product.get("unknown_product")
            and bool(promoted)
            and not pending
            and (not quarantined or bool(replacement_promoted))
        )
        if not old_targets and observed_targets:
            all_affected_verified = (
                observation_verified
                and not product.get("unknown_product")
                and all(item["verified"] for item in observed_targets.values())
            )
        if not old_targets and not observed_targets:
            all_affected_verified = False

        if all_affected_verified:
            product["published"] = product.get("observed")
            product["authoritative"] = True
            product["freshness"] = "verified"
            product["last_verified"] = utc_now()
            product["delta_status"] = "published"
            state["last_published"] = product["last_verified"]
        else:
            product["authoritative"] = False
            product["freshness"] = "pending_target_reverification"
        product["target_reverification"] = {
            "affected_kinds": sorted(affected_kinds),
            "promoted": promoted,
            "quarantined": quarantined,
            "pending": pending,
            "verified_at": utc_now(),
        }
        state.setdefault("targets", {})[product_id] = next_targets
        state.setdefault("products", {})[product_id] = product
        state["last_reverification"] = utc_now()
        self.store.event(state, "affected_target_reverification", {
            "product_id": product_id,
            "promoted": promoted,
            "quarantined": quarantined,
            "pending": pending,
            "published": all_affected_verified,
        })
        self.store.save(state)
        return {
            "schema": SCHEMA,
            "operation": "affected_target_reverification",
            "product_id": product_id,
            "promoted": promoted,
            "quarantined": quarantined,
            "pending": pending,
            "published": all_affected_verified,
            "authoritative": bool(product.get("authoritative")),
            "freshness": product.get("freshness"),
            "governance": {
                "mutation_authorized": False,
                "target_identity_required": True,
                "new_targets_require_live_verification": True,
                "old_targets_quarantined_before_replacement": True,
            },
        }

    def run_cycle(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        scan = self.product_delta_scan(observations)
        reverification: List[Dict[str, Any]] = []
        for raw, result in zip(observations, scan["results"]):
            if not result.get("target_reverification_required"):
                continue
            targets = raw.get("targets") if isinstance(raw, dict) else None
            if targets is not None:
                reverification.append(self.reverify_targets(result["product_id"], targets))
        return {
            "schema": SCHEMA,
            "operation": "maintenance_cycle",
            "scan": scan,
            "reverification": reverification,
            "status": self.status(),
        }

    def answer(self, message: str) -> Optional[Dict[str, Any]]:
        """Answer only from a product state that passed the publish gate."""
        state = self.store.load()
        query_tokens = _slug_tokens(message)
        for product in (state.get("products") or {}).values():
            published = product.get("published") or {}
            if not published:
                continue
            values = published.get("values") or {}
            searchable = " ".join(str(values.get(key) or "") for key in ("title", "sku", "product_url"))
            if not query_tokens or not (query_tokens & _slug_tokens(searchable)):
                continue
            display_name = str(values.get("title") or product.get("product_id"))
            lower = message.lower()
            if any(term in lower for term in ("price", "cost", "sale")):
                price = values.get("sale_price") or values.get("price")
                answer = f"{display_name} is currently listed at {price}." if price is not None else None
            elif any(term in lower for term in ("stock", "inventory", "available")):
                availability = values.get("availability") or values.get("inventory_status")
                answer = f"{display_name} is currently {availability}." if availability is not None else None
            else:
                answer = None
            if answer:
                return {
                    "answer": answer,
                    "intent": "field_product_state",
                    "source": "field_site_world_maintenance",
                    "confidence": 1.0,
                    "routing_confidence": 1.0,
                    "resolution_path": ["field_maintenance", "published_state"],
                    "entity_id": product.get("product_id"),
                    "data": {
                        "observed_at": published.get("observed_at"),
                        "last_verified": product.get("last_verified"),
                        "freshness": "verified" if product.get("authoritative") else "stale_pending_verification",
                        "evidence": published.get("targets") or [],
                    },
                }
        return None


def load_known_products(payload_catalog_path: Path) -> List[Dict[str, Any]]:
    if not payload_catalog_path.is_file():
        return []
    with payload_catalog_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    entries = data.get("entries") if isinstance(data, dict) else data
    return [item for item in (entries or []) if isinstance(item, dict)]
