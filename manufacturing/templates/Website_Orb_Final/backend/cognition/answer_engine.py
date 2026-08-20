from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .doctrine_gate import apply_doctrine_gate
from .tpc_pipeline import run_tpc
from ..runtime.intent_router import classify_intent


# ---------------------------------------------------------------------------
# ORB VAULT
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
ORB_VAULT_ROOT = REPO_ROOT / "Orb_Vault_System" / "orb_vault_skg"

if str(ORB_VAULT_ROOT) not in sys.path:
    sys.path.insert(0, str(ORB_VAULT_ROOT))

from vault.orb_assistant import QueryRouter, VaultCoordinator


_vault_coordinator: Optional[VaultCoordinator] = None


def _get_vault_coordinator() -> VaultCoordinator:
    global _vault_coordinator

    if _vault_coordinator is None:
        _vault_coordinator = VaultCoordinator()

    return _vault_coordinator


def _try_vault(message: str) -> Optional[Dict[str, Any]]:
    """
    Fast deterministic answer path.

    A Priori:
        catalog -> ontology/SKG -> QA

    A Posteriori:
        verified learned experience

    Returns None on a vault miss so the existing TPC path remains intact.
    """
    try:
        coordinator = _get_vault_coordinator()

        catalog_names = [
            entry.name
            for entry in coordinator.priori.catalog_state.entries.values()
            if getattr(entry, "name", None)
        ]

        vault_intent, entities, routing_confidence = QueryRouter.route(
            message,
            catalog_names=catalog_names,
        )

        result = coordinator.resolve(
            message,
            intent=vault_intent,
            entities=entities,
        )

        if not result.success:
            return None

        return {
            "answer": result.answer,
            "intent": vault_intent.name,
            "source": result.source or "orb_vault",
            "confidence": result.confidence,
            "routing_confidence": routing_confidence,
            "resolution_path": list(coordinator.last_resolution_path),
            "entity_id": getattr(result, "entity_id", None),
            "data": getattr(result, "data", None),
        }

    except Exception:
        # Vault failure must never take the Website ORB offline.
        # Existing TPC/runtime path remains the deterministic fallback.
        return None


# ---------------------------------------------------------------------------
# WEBSITE ORB ANSWER ENGINE
# ---------------------------------------------------------------------------

def answer_from_world(
    message: str,
    route: str,
    route_record: Dict[str, Any],
    runtime_language: Dict[str, Any],
    pointer_targets: List[Dict[str, Any]],
) -> Dict[str, Any]:

    # FAST PATH:
    # A Priori -> A Posteriori
    vault_result = _try_vault(message)

    if vault_result is not None:
        return {
            "answer": vault_result["answer"],
            "route": route,
            "intent": vault_result["intent"],
            "action_class": "informational",
            "pointer_targets": pointer_targets,
            "requires_confirmation": False,
            "source": vault_result["source"],
            "vault_trace": {
                "confidence": vault_result["confidence"],
                "routing_confidence": vault_result["routing_confidence"],
                "resolution_path": vault_result["resolution_path"],
                "entity_id": vault_result["entity_id"],
                "data": vault_result["data"],
            },
        }

    # EXISTING PATH:
    # Website intent -> TPC -> doctrine gate -> existing composition
    intent, _score = classify_intent(message, route_record)

    tpc = run_tpc(
        message,
        intent,
        route_record,
        runtime_language,
        pointer_targets,
    )

    gate = apply_doctrine_gate(tpc, route_record)

    answer = _compose_answer(
        intent,
        route_record,
        runtime_language,
        pointer_targets,
    )

    if not gate["allowed"]:
        answer = (
            "I can explain that, but this Website ORB cannot perform "
            "that action from the site."
        )

    return {
        "answer": answer,
        "route": route,
        "intent": intent,
        "action_class": gate["action_class"],
        "pointer_targets": pointer_targets,
        "requires_confirmation": gate["requires_confirmation"],
        "source": tpc.get("source", "tpc_website_runtime"),
        "tpc_trace": {
            "hlsf": tpc.get("hlsf"),
            "egf": tpc.get("egf"),
            "gate": gate,
        },
    }


def _compose_answer(
    intent: str,
    route_record: Dict[str, Any],
    runtime_language: Dict[str, Any],
    pointer_targets: List[Dict[str, Any]],
) -> str:

    tools = runtime_language.get("visitor_tools") or []

    for tool in tools:
        if tool.get("id") == intent or intent in str(tool.get("id", "")):
            return str(tool.get("spoken_output"))

    if intent == "desktop_boundary":
        return (
            "Website ORBs help visitors inside the site. "
            "DockStation and Desktop ORB tools are separate "
            "and must be configured explicitly."
        )

    if intent == "current_route":
        return str(
            route_record.get("summary")
            or route_record.get("page_purpose")
            or runtime_language.get("site_summary")
        )

    if pointer_targets:
        label = (
            pointer_targets[0].get("meaning")
            or pointer_targets[0].get("target_id")
        )

        return (
            f"I can help with that here. "
            f"The best visible target appears to be {label}."
        )

    identity = runtime_language.get("first_person_identity") or {}

    return str(
        identity.get("job")
        or runtime_language.get("site_summary")
        or "I help visitors understand this site."
    )