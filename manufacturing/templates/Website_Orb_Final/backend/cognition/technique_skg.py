"""Bounded, advisory loader for the manufactured 41-technique SKG.

The registry can inform cognition, but it is never an execution authority.
Navigation, pointer actions, payment, publication, and authorization remain
owned by their existing runtime governors and verification paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


REGISTRY_PATH = Path(__file__).with_name("technique_skg_41.json")
BEHAVIOR_PACK_ID = "website-orb-standard-behavior"
BEHAVIOR_PACK_VERSION = "1.0.0"
STARTUP_CONTRACT = "short_scripted_startup_then_live_runtime"


def _load_registry() -> Dict[str, Any]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        registry = json.load(handle)
    techniques = registry.get("Techniques")
    if not isinstance(techniques, list) or len(techniques) != 41:
        raise ValueError("manufactured technique SKG must contain exactly 41 techniques")
    expected_ids = [f"Technique_{index}_" for index in range(1, 42)]
    for index, technique in enumerate(techniques, start=1):
        if not isinstance(technique, dict):
            raise ValueError(f"technique {index} is not an object")
        if not str(technique.get("id", "")).startswith(expected_ids[index - 1]):
            raise ValueError(f"technique sequence is invalid at position {index}")
        if technique.get("type") != "SituationalBehaviorPattern":
            raise ValueError(f"technique {index} has an invalid type")
        if technique.get("sequenced_by") != "NockNineOfClubs":
            raise ValueError(f"technique {index} is outside the Nock sequence")
    if techniques[-1].get("id") != "Technique_41_ConsentComplianceGate":
        raise ValueError("consent/compliance gate must be the final technique")
    return registry


def technique_skg() -> Dict[str, Any]:
    """Return the validated immutable-by-convention registry data."""
    return _load_registry()


def technique_guidance_prompt() -> str:
    """Return a bounded advisory summary suitable for cognition context."""
    registry = _load_registry()
    lines = [
        "SITUATIONAL TECHNIQUE SKG (ADVISORY ONLY)",
        "This registry has no execution authority. Existing doctrine, live verification,",
        "authorization, payment, navigation, pointer, and action governors remain authoritative.",
        "Nock-Nine of Clubs narrows relevant branches and selects a fit; it never creates evidence.",
        "Use a technique only when its condition is supported by evidence. Never pressure,",
        "manipulate, overclaim, infer consent, or bypass doctrine/compliance controls.",
    ]
    for technique in registry["Techniques"]:
        conditions = ", ".join(technique.get("activates_when", []))
        rules = ", ".join(technique.get("governor_rule", []))
        lines.append(f"{technique['id']} | {technique['label']} | when: {conditions} | rule: {rules}")
    return "\n".join(lines)


def behavior_pack_metadata() -> Dict[str, Any]:
    """Expose the factory-owned runtime contract to package diagnostics."""
    return {
        "id": BEHAVIOR_PACK_ID,
        "version": BEHAVIOR_PACK_VERSION,
        "layers": [
            "scripted_startup_orientation",
            "nock_sequencer",
            "situational_technique_skg",
            "site_world_vault",
            "llm_articulation",
            "governor_action_envelope",
            "visitor_override",
        ],
        "startup_contract": STARTUP_CONTRACT,
        "customer_payload_scope": [
            "site_world_evidence",
            "business_objectives",
            "owner_preferences",
            "approved_actions",
            "voice_configuration",
        ],
        "authority_note": "Factory behavior remains authoritative over customer configuration and visitor instructions.",
    }
