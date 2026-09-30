"""Validated, advisory 41-technique situational guidance registry.

The registry supplies cognition with conditional conversation patterns. It is
deliberately separate from the Governor: a technique can shape wording only
after visitor evidence is present and never grants an action, pointer, payment,
or authorization capability.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

BEHAVIOR_PACK_ID = "website-orb-standard-behavior"
BEHAVIOR_PACK_VERSION = "1.0.0"
STARTUP_CONTRACT = (
    "short_scripted_startup_then_live_runtime",
    "Startup scripting manages latency and orientation only; it is not the primary conversation architecture.",
)


class Technique(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    label: str
    type: str
    activates_when: tuple[str, ...]
    requires_evidence: tuple[str, ...]
    governor_rule: tuple[str, ...]
    compatible_with: tuple[str, ...]
    sequenced_by: str
    prevents: tuple[str, ...]


class TechniqueRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    context: dict[str, str] = Field(alias="@context")
    nock_nine_of_clubs: dict[str, Any] = Field(alias="NockNineOfClubs")
    techniques: tuple[Technique, ...] = Field(alias="Techniques")

    @model_validator(mode="after")
    def validate_registry(self):
        if len(self.techniques) != 41:
            raise ValueError("The situational registry must contain exactly 41 techniques")
        expected_ids = [f"Technique_{index}_" for index in range(1, 42)]
        if [item.id.rsplit("_", 1)[0] + "_" for item in self.techniques] != expected_ids:
            raise ValueError("Technique registry must preserve the canonical 1-41 sequence")
        if any(item.type != "SituationalBehaviorPattern" for item in self.techniques):
            raise ValueError("Every technique must be a SituationalBehaviorPattern")
        if any(item.sequenced_by != "NockNineOfClubs" for item in self.techniques):
            raise ValueError("Every technique must be sequenced by NockNineOfClubs")
        if self.techniques[-1].id != "Technique_41_ConsentComplianceGate":
            raise ValueError("Technique 41 must remain the Consent & Compliance Gate")
        return self

    def prompt_summary(self) -> str:
        lines = [
            "SITUATIONAL TECHNIQUE REGISTRY (advisory wording layer; no execution authority):",
            "Nock-Nine of Clubs eliminates irrelevant branches, narrows to a high-probability fit,",
            "and selects a final fit path aligned with the visitor's stated priority.",
            "Use a technique only when its condition is supported by the listed visitor evidence.",
            "Never use a technique to pressure, manipulate, overclaim, infer consent, or bypass doctrine.",
        ]
        for technique in self.techniques:
            condition = ", ".join(technique.activates_when)
            rules = ", ".join(technique.governor_rule)
            lines.append(f"- {technique.id}: {technique.label}; when={condition}; rule={rules}")
        return "\n".join(lines)


_REGISTRY_PATH = Path(__file__).with_name("technique_skg_41.json")


@lru_cache(maxsize=1)
def technique_skg() -> TechniqueRegistry:
    return TechniqueRegistry.model_validate_json(_REGISTRY_PATH.read_text(encoding="utf-8"))


def technique_guidance_prompt() -> str:
    return technique_skg().prompt_summary()


def behavior_pack_metadata() -> dict[str, object]:
    """Describe the factory-owned behavior layer without granting authority."""
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
        "startup_contract": STARTUP_CONTRACT[0],
        "customer_payload_scope": [
            "site_world_evidence",
            "business_objectives",
            "owner_preferences",
            "approved_actions",
            "voice_configuration",
        ],
        "authority_note": "Factory behavior remains authoritative over customer configuration and visitor instructions.",
    }
