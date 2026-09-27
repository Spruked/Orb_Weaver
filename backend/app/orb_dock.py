"""Versioned Website ORB Dock Station contracts and policy compiler."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


DOCK_CONFIGURATION_SCHEMA = "orb_weaver.orb_dock_configuration.v1"
COMPILED_POLICY_SCHEMA = "orb_weaver.website_orb_operating_policy.v1"

LOCKED_ORB_DOCTRINE: List[Dict[str, str]] = [
    {"id": "permission_boundaries", "label": "Permission boundaries", "rule": "Use only explicitly permitted routes, tools, and actions."},
    {"id": "privacy_behavior", "label": "Privacy behavior", "rule": "Minimize data and keep owner, private, and visitor scopes separated."},
    {"id": "verified_actions", "label": "Verified-action requirements", "rule": "Never report an action as completed without verified outcome evidence."},
    {"id": "site_world_evidence", "label": "Site World evidence rules", "rule": "Website claims and destinations must be supported by compiled Site World evidence."},
    {"id": "stage_governor", "label": "Stage Governor enforcement", "rule": "Project workflow transitions remain governed by authoritative snapshots."},
    {"id": "prohibited_exposure", "label": "Prohibited data exposure", "rule": "Never expose credentials, admin data, private records, or unrelated customer data."},
    {"id": "consent", "label": "Consent requirements", "rule": "Obtain required consent before collection, recording, transfer, or consequential action."},
    {"id": "owner_authentication", "label": "Owner authentication rules", "rule": "Owner controls and policy publication require an authenticated project owner."},
]

STANDARD_WEBSITE_ORB_BEHAVIOR: Dict[str, Any] = {
    "purpose": "Serve visitors through verified Website ORB capabilities and approved site paths.",
    "conversation": [
        "Use concise, natural language and ask one clarifying question when intent is unclear.",
        "Preserve visitor progress and offer a concrete next step when a workflow is available.",
        "Use the selected tone and response style without making the ORB sound scripted or hostile.",
    ],
    "grounding": [
        "Ground website claims, destinations, and availability in compiled Site World evidence.",
        "Never invent prices, policies, routes, tools, availability, or outcomes.",
    ],
    "verification": [
        "Never claim an action completed without verified outcome evidence.",
        "Require live exact-one target validation before pointer movement or Ping.",
    ],
    "privacy_and_authority": [
        "Keep owner, private, and visitor scopes separated.",
        "Require authorization for owner controls and consequential actions.",
        "Never expose credentials, private records, or unrelated customer data.",
    ],
}

_STANDARD_OWNER_RULES = {
    "use one short spoken response unless the visitor asks for detail.",
    "ask one helpful clarifying question when the visitor intent is unclear.",
    "use only verified routes, tools, and owner-approved actions.",
    "say when something needs owner or staff follow-up.",
    "do not sound angry, annoyed, sarcastic, rushed, or scripted.",
    "do not claim an action was completed without verified evidence.",
    "do not expose credentials, private owner data, or unrelated customer data.",
    "do not invent prices, policies, routes, tools, or availability.",
}


def classify_owner_preferences(configuration: "DockConfiguration") -> List[Dict[str, Any]]:
    """Classify owner additions without allowing them to weaken runtime authority."""
    reviews: List[Dict[str, Any]] = []
    conflict_patterns = (
        (re.compile(r"\b(skip|bypass|ignore|without)\b.{0,40}\b(payment|verification|consent|auth|authorization|approval|evidence)\b", re.I), "Conflicts with verification, consent, or authorization requirements."),
        (re.compile(r"\b(guarantee|guaranteed|promise|claim)\b.{0,80}\b(completed|approved|secure|available|paid|certified|certificate|outcome|results?|payment|service)\b", re.I), "Conflicts with evidence-grounded claims and verified outcomes."),
        (re.compile(r"\b(reveal|show|share|send|expose).{0,40}\b(password|credential|token|private|admin|secret|customer record)\b", re.I), "Conflicts with privacy and prohibited-data-exposure doctrine."),
        (re.compile(r"\b(always|never)\b.{0,60}\b(point|ping|click|navigate|open)\b", re.I), "Cannot override live exact-one pointer and navigation validation."),
    )
    unsupported_patterns = (
        (re.compile(r"\b(change|edit|delete|modify|write)\b.{0,50}\b(database|account|order|payment|record)\b", re.I), "Requests an unapproved side effect outside the Website ORB action contract."),
        (re.compile(r"\b(send|text|email|call|refund|charge|purchase)\b", re.I), "Requests a capability that must be provided by an explicitly approved tool."),
        (re.compile(r"\b(remember forever|read minds|know everything|guarantee results)\b", re.I), "Requests a capability the Website ORB cannot verify or provide."),
    )
    review_patterns = (
        (re.compile(r"\b(legal|medical|financial|pricing|price|discount|guarantee|contract|complaint)\b", re.I), "Potentially consequential preference requires owner review."),
        (re.compile(r"\b(always|never|must)\b", re.I), "Absolute instruction may be ambiguous or conflict with live context."),
    )
    fields = (
        ("additional_preferences", "must_follow_rules", configuration.behavior.must_follow_rules),
        ("avoid_preferences", "must_not_rules", configuration.behavior.must_not_rules),
        ("avoid_tone_preferences", "prohibited_tone", configuration.behavior.prohibited_tone),
    )
    for category, field, values in fields:
        for index, raw_value in enumerate(values):
            text = " ".join(str(raw_value).split())
            normalized = text.casefold()
            item = {"category": category, "field": field, "index": index, "text": text}
            if normalized in _STANDARD_OWNER_RULES or (
                field == "prohibited_tone" and normalized in {"angry", "annoyed", "sarcastic", "rushed", "scripted"}
            ):
                reviews.append({**item, "status": "redundant", "reason": "Already provided by the standard Website ORB behavior pack."})
                continue
            matched = next(((pattern, reason) for pattern, reason in conflict_patterns if pattern.search(text)), None)
            if matched:
                reviews.append({**item, "status": "conflict", "reason": matched[1]})
                continue
            matched = next(((pattern, reason) for pattern, reason in unsupported_patterns if pattern.search(text)), None)
            if matched:
                reviews.append({**item, "status": "unsupported", "reason": matched[1]})
                continue
            matched = next(((pattern, reason) for pattern, reason in review_patterns if pattern.search(text)), None)
            if matched:
                reviews.append({**item, "status": "needs_review", "reason": matched[1]})
                continue
            reviews.append({**item, "status": "compatible", "reason": "Supplemental owner preference; higher-authority rules remain in force."})
    text_fields = (
        ("job_description", configuration.behavior.job_description),
        ("persona_notes", configuration.behavior.persona_notes),
    )
    for field, raw_value in text_fields:
        text = " ".join(str(raw_value).split())
        item = {"category": "owner_context", "field": field, "index": 0, "text": text}
        if (
            field == "job_description"
            and text.startswith("Serve as the visitor-facing Website ORB.")
        ) or (
            field == "persona_notes"
            and text == "Sound warm, patient, curious, and never irritated. Avoid scripted or scolding language."
        ):
            reviews.append({**item, "status": "redundant", "reason": "Already provided by the standard Website ORB behavior pack."})
            continue
        matched = next(((pattern, reason) for pattern, reason in conflict_patterns if pattern.search(text)), None)
        if matched:
            reviews.append({**item, "status": "conflict", "reason": matched[1]})
            continue
        matched = next(((pattern, reason) for pattern, reason in unsupported_patterns if pattern.search(text)), None)
        if matched:
            reviews.append({**item, "status": "unsupported", "reason": matched[1]})
            continue
        matched = next(((pattern, reason) for pattern, reason in review_patterns if pattern.search(text)), None)
        if matched:
            reviews.append({**item, "status": "needs_review", "reason": matched[1]})
            continue
        reviews.append({**item, "status": "compatible", "reason": "Supplemental owner context; higher-authority rules remain in force."})
    return reviews

SKINS: List[Dict[str, Any]] = [
    {"skin_id": "orb_factory_default_v1", "display_name": "Work ORB", "asset_path": "/orb-skins/WORKORB21600.png", "factory_default": True},
    {"skin_id": "blue_sample", "display_name": "Blue Sample ORB", "asset_path": "/orb-skins/blueorbsampl1024.png"},
    {"skin_id": "blue_plastic", "display_name": "Blue Plastic ORB", "asset_path": "/orb-skins/blueplasticorb1600.png"},
    {"skin_id": "dark_green_earth", "display_name": "Dark Green Earth ORB", "asset_path": "/orb-skins/darkgreenearthyrobotorb1600.png"},
    {"skin_id": "digital_age_blue", "display_name": "Digital Age Blue ORB", "asset_path": "/orb-skins/digitalageblueorb1600.png"},
    {"skin_id": "electric_blue", "display_name": "Electric Blue ORB", "asset_path": "/orb-skins/electricbluerobotorb1600.png"},
    {"skin_id": "green_robot", "display_name": "Green Robot ORB", "asset_path": "/orb-skins/greenorbrobot.png"},
    {"skin_id": "nature", "display_name": "Nature ORB", "asset_path": "/orb-skins/natureorb1.png"},
    {"skin_id": "orb_example_2", "display_name": "Classic ORB", "asset_path": "/orb-skins/orbexample2.png"},
    {"skin_id": "pink_diamond", "display_name": "Pink Diamond ORB", "asset_path": "/orb-skins/pinkdiamondrobotorb.png"},
    {"skin_id": "purple_crystal", "display_name": "Purple Crystal ORB", "asset_path": "/orb-skins/purplecrystalorb1600.png"},
    {"skin_id": "purple_glass", "display_name": "Purple Glass ORB", "asset_path": "/orb-skins/purpleglassrobotorb1600.png"},
    {"skin_id": "purple_robot", "display_name": "Purple Robot ORB", "asset_path": "/orb-skins/purplerobotorb1600.png"},
    {"skin_id": "red_robot", "display_name": "Red Robot ORB", "asset_path": "/orb-skins/redrobotorb1600.png"},
]

SKIN_BY_ID = {item["skin_id"]: item for item in SKINS}


class LockedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppearanceConfiguration(LockedModel):
    skin_id: str = "orb_factory_default_v1"
    custom_skin_id: Optional[str] = Field(default=None, max_length=80, pattern=r"^custom_orb_[a-f0-9]{24}$")
    custom_skin_display_name: Optional[str] = Field(default=None, max_length=120)
    custom_skin_asset_path: Optional[str] = Field(default=None, max_length=300)
    custom_skin_sha256: Optional[str] = Field(default=None, max_length=64, pattern=r"^[a-f0-9]{64}$")
    custom_skin_width: Optional[int] = Field(default=None, ge=1, le=4096)
    custom_skin_height: Optional[int] = Field(default=None, ge=1, le=4096)
    custom_skin_file_size: Optional[int] = Field(default=None, ge=1, le=20_000_000)


class LlmConfiguration(LockedModel):
    provider: Literal["runtime_default", "ollama_local", "openai_api", "anthropic_api", "google_api", "openai_compatible"] = "runtime_default"
    model: Optional[str] = Field(default=None, max_length=160)
    base_url: Optional[str] = Field(default=None, max_length=500)
    api_key_env: Optional[str] = Field(default=None, max_length=80)
    temperature: float = Field(default=0.35, ge=0, le=1.5)
    max_output_tokens: int = Field(default=160, ge=16, le=1200)

    @field_validator("model", "base_url", "api_key_env")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        normalized = (value or "").strip()
        return normalized or None

    @field_validator("api_key_env")
    @classmethod
    def validate_api_key_env(cls, value: Optional[str]) -> Optional[str]:
        if value and not re.fullmatch(r"[A-Z][A-Z0-9_]{2,79}", value):
            raise ValueError("Use an uppercase environment variable name such as OPENAI_API_KEY")
        return value


class BehaviorConfiguration(LockedModel):
    tone: Literal["warm", "calm", "professional", "playful", "direct"] = "warm"
    response_style: Literal["concise", "guided", "diagnostic", "sales_assistant"] = "concise"
    greeting_enabled: bool = True
    startup_listening_enabled: bool = True
    voice_only: bool = True
    mute_by_default: bool = False
    sleep_by_default: bool = False
    greeting_script: str = Field(
        default="Hi, I am Weaver. I am here, listening when you are ready.",
        max_length=500,
    )
    job_description: str = Field(
        default=(
            "Serve as the visitor-facing Website ORB. Listen first, answer clearly, guide visitors only through verified site paths, "
            "and help them complete approved owner objectives without pretending that unverified actions happened."
        ),
        max_length=2000,
    )
    persona_notes: str = Field(
        default="Sound warm, patient, curious, and never irritated. Avoid scripted or scolding language.",
        max_length=1500,
    )
    must_follow_rules: List[str] = Field(
        default_factory=lambda: [
            "Use one short spoken response unless the visitor asks for detail.",
            "Ask one helpful clarifying question when the visitor intent is unclear.",
            "Use only verified routes, tools, and owner-approved actions.",
            "Say when something needs owner or staff follow-up.",
        ],
        max_length=30,
    )
    must_not_rules: List[str] = Field(
        default_factory=lambda: [
            "Do not sound angry, annoyed, sarcastic, rushed, or scripted.",
            "Do not claim an action was completed without verified evidence.",
            "Do not expose credentials, private owner data, or unrelated customer data.",
            "Do not invent prices, policies, routes, tools, or availability.",
        ],
        max_length=30,
    )
    prohibited_tone: List[str] = Field(
        default_factory=lambda: ["angry", "annoyed", "sarcastic", "rushed"],
        max_length=20,
    )

    @field_validator("greeting_script", "job_description", "persona_notes")
    @classmethod
    def normalize_behavior_text(cls, value: str) -> str:
        return (value or "").strip()


class BusinessObjective(LockedModel):
    objective_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=160)
    enabled: bool = True
    completion_evidence: List[str] = Field(default_factory=list, max_length=20)
    required_fields: List[str] = Field(default_factory=list, max_length=30)
    permitted_routes: List[str] = Field(default_factory=list, max_length=40)
    permitted_tools: List[str] = Field(default_factory=list, max_length=40)
    escalation_route: str = Field(default="", max_length=300)
    success_condition: str = Field(default="", max_length=1000)
    failure_condition: str = Field(default="", max_length=1000)


class AdditionalGuideRail(LockedModel):
    guide_rail_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=160)
    enabled: bool = True
    applies_when: str = Field(min_length=1, max_length=1500)
    orb_should: str = Field(min_length=1, max_length=2000)
    orb_must_not: str = Field(min_length=1, max_length=2000)
    permitted_actions: List[str] = Field(default_factory=list, max_length=40)
    required_evidence: List[str] = Field(default_factory=list, max_length=40)
    escalate_when: str = Field(default="", max_length=1500)
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    effective_from: Optional[date] = None
    effective_until: Optional[date] = None
    owner_note: str = Field(default="", max_length=2000)


class SituationConditions(LockedModel):
    current_pages: List[str] = Field(default_factory=list, max_length=40)
    visitor_types: List[str] = Field(default_factory=list, max_length=30)
    workflow_stages: List[str] = Field(default_factory=list, max_length=30)
    product_categories: List[str] = Field(default_factory=list, max_length=30)
    business_hours: List[str] = Field(default_factory=list, max_length=20)
    geographic_eligibility: List[str] = Field(default_factory=list, max_length=30)
    minimum_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    authentication_states: List[Literal["anonymous", "authenticated"]] = Field(default_factory=list)
    active_promotions: List[str] = Field(default_factory=list, max_length=30)
    prior_history_terms: List[str] = Field(default_factory=list, max_length=30)


class SituationalGuideRail(LockedModel):
    guide_rail_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=160)
    enabled: bool = True
    conditions: SituationConditions = Field(default_factory=SituationConditions)
    orb_should: str = Field(min_length=1, max_length=2000)
    orb_must_not: str = Field(min_length=1, max_length=2000)
    permitted_actions: List[str] = Field(default_factory=list, max_length=40)
    required_evidence: List[str] = Field(default_factory=list, max_length=40)
    escalate_when: str = Field(default="", max_length=1500)
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    owner_note: str = Field(default="", max_length=2000)


class DockConfiguration(LockedModel):
    schema: Literal[DOCK_CONFIGURATION_SCHEMA] = DOCK_CONFIGURATION_SCHEMA
    orb_name: str = Field(default="Website ORB", min_length=1, max_length=80)
    appearance: AppearanceConfiguration = Field(default_factory=AppearanceConfiguration)
    llm: LlmConfiguration = Field(default_factory=LlmConfiguration)
    behavior: BehaviorConfiguration = Field(default_factory=BehaviorConfiguration)
    business_objectives: List[BusinessObjective] = Field(default_factory=list, max_length=40)
    additional_guide_rails: List[AdditionalGuideRail] = Field(default_factory=list, max_length=80)
    situational_guide_rails: List[SituationalGuideRail] = Field(default_factory=list, max_length=80)

    @field_validator("orb_name")
    @classmethod
    def normalize_orb_name(cls, value: str) -> str:
        normalized = " ".join((value or "").split())
        if not normalized:
            raise ValueError("Name the ORB before publishing")
        return normalized


def default_configuration() -> Dict[str, Any]:
    return DockConfiguration().model_dump(mode="json")


def doctrine_hash() -> str:
    canonical = json.dumps(LOCKED_ORB_DOCTRINE, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_route(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://dock.local{raw if raw.startswith('/') else '/' + raw}")
    route = (parsed.path or "/").rstrip("/") or "/"
    return route if route.startswith("/") else f"/{route}"


def _string_list(values: List[str]) -> List[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def _known_site_evidence(website_context: Optional[Dict[str, Any]]) -> Tuple[Set[str], Set[str]]:
    routes: Set[str] = set()
    tools: Set[str] = set()
    context = website_context or {}
    for route in (context.get("route_hints") or {}).values():
        normalized = normalize_route(str(route))
        if normalized:
            routes.add(normalized)
    for page in (context.get("authority_flow") or {}).get("pages") or []:
        normalized = normalize_route(str(page.get("url") or ""))
        if normalized:
            routes.add(normalized)
    for tool in context.get("visitor_tools") or []:
        tool_id = str(tool.get("id") or "").strip()
        if tool_id:
            tools.add(tool_id)
    return routes, tools


def compile_configuration(
    configuration: DockConfiguration,
    website_context: Optional[Dict[str, Any]],
    *,
    project_id: str,
    domain: str,
    next_version: int,
) -> Dict[str, Any]:
    blockers: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    known_routes, known_tools = _known_site_evidence(website_context)
    preference_reviews = classify_owner_preferences(configuration)
    compatible_preferences = [item["text"] for item in preference_reviews if item["status"] == "compatible"]
    compatible_by_field = {
        field: [
            item["text"] for item in preference_reviews
            if item["field"] == field and item["status"] == "compatible"
        ]
        for field in ("must_follow_rules", "must_not_rules", "prohibited_tone")
    }
    compatible_text_by_field = {
        item["field"]: item["text"]
        for item in preference_reviews
        if item["field"] in {"job_description", "persona_notes"} and item["status"] == "compatible"
    }
    preference_statuses = {"conflict", "unsupported", "needs_review"}
    for item in preference_reviews:
        path = f"behavior.{item['field']}.{item['index']}"
        if item["status"] in preference_statuses:
            blockers.append({
                "path": path,
                "code": f"owner_preference_{item['status']}",
                "message": f"{item['status'].replace('_', ' ').title()}: {item['reason']}",
            })
        elif item["status"] == "redundant":
            warnings.append({
                "path": path,
                "code": "owner_preference_redundant",
                "message": item["reason"],
            })
    legacy_factory_alias = configuration.appearance.skin_id == "work_orb"
    skin = SKIN_BY_ID.get("orb_factory_default_v1" if legacy_factory_alias else configuration.appearance.skin_id)
    if legacy_factory_alias:
        skin = {**skin, "skin_id": "orb_factory_default_v1"}
    if not skin and configuration.appearance.custom_skin_id == configuration.appearance.skin_id:
        custom_asset_path = configuration.appearance.custom_skin_asset_path or ""
        if custom_asset_path.startswith("/api/orb/custom-skins/"):
            skin = {
                "skin_id": configuration.appearance.skin_id,
                "display_name": configuration.appearance.custom_skin_display_name or "Custom ORB Skin",
                "asset_path": custom_asset_path,
                "factory_default": False,
                "custom": True,
            }
    if not skin:
        blockers.append({"path": "appearance.skin_id", "code": "unknown_skin", "message": "Select a registered ORB skin."})
        skin = SKIN_BY_ID["orb_factory_default_v1"]
    if configuration.llm.provider == "ollama_local" and not configuration.llm.model:
        blockers.append({"path": "llm.model", "code": "model_required", "message": "Select or download an Ollama model before publication."})
    if configuration.llm.provider in {"openai_api", "anthropic_api", "google_api"}:
        if not configuration.llm.model:
            blockers.append({"path": "llm.model", "code": "model_required", "message": "Select the API model before publication."})
        if not configuration.llm.api_key_env:
            blockers.append({"path": "llm.api_key_env", "code": "api_key_env_required", "message": "Name the server environment variable that holds this provider API key."})
    if configuration.llm.provider == "openai_compatible":
        if not configuration.llm.base_url:
            blockers.append({"path": "llm.base_url", "code": "base_url_required", "message": "Enter the OpenAI-compatible API base URL."})
        if not configuration.llm.model:
            blockers.append({"path": "llm.model", "code": "model_required", "message": "Select the OpenAI-compatible model before publication."})
        if not configuration.llm.api_key_env:
            warnings.append({"path": "llm.api_key_env", "code": "api_key_env_missing", "message": "No API key env var is set; this only works for unauthenticated local-compatible endpoints."})
    if configuration.behavior.greeting_enabled and not configuration.behavior.greeting_script:
        blockers.append({"path": "behavior.greeting_script", "code": "greeting_required", "message": "A spoken greeting is required when startup greeting is enabled."})

    objective_ids: Set[str] = set()
    rail_ids: Set[str] = set()
    allowed_routes: Set[str] = set()
    allowed_tools: Set[str] = set()
    compiled_objectives: List[Dict[str, Any]] = []
    compiled_additional: List[Dict[str, Any]] = []
    compiled_situational: List[Dict[str, Any]] = []

    for index, objective in enumerate(configuration.business_objectives):
        path = f"business_objectives.{index}"
        if objective.objective_id in objective_ids:
            blockers.append({"path": f"{path}.objective_id", "code": "duplicate_id", "message": "Objective IDs must be unique."})
        objective_ids.add(objective.objective_id)
        routes = _string_list([normalize_route(value) for value in objective.permitted_routes])
        tools = _string_list(objective.permitted_tools)
        for route in routes:
            if route not in known_routes:
                blockers.append({"path": f"{path}.permitted_routes", "code": "route_not_in_site_world", "message": f"{route} is not verified by the current Site World."})
            else:
                allowed_routes.add(route)
        for tool in tools:
            if tool not in known_tools:
                blockers.append({"path": f"{path}.permitted_tools", "code": "tool_not_in_site_world", "message": f"{tool} is not an approved Website ORB tool."})
            else:
                allowed_tools.add(tool)
        if objective.enabled:
            for field, value in (
                ("completion_evidence", objective.completion_evidence),
                ("success_condition", objective.success_condition),
                ("failure_condition", objective.failure_condition),
                ("escalation_route", objective.escalation_route),
            ):
                if not value:
                    blockers.append({"path": f"{path}.{field}", "code": "required_for_enabled_objective", "message": f"{field.replace('_', ' ').title()} is required."})
        compiled_objectives.append({
            **objective.model_dump(mode="json"),
            "completion_evidence": _string_list(objective.completion_evidence),
            "required_fields": _string_list(objective.required_fields),
            "permitted_routes": routes,
            "permitted_tools": tools,
        })

    def compile_rail(rail: Any, path: str, *, situational: bool) -> Dict[str, Any]:
        if rail.guide_rail_id in rail_ids:
            blockers.append({"path": f"{path}.guide_rail_id", "code": "duplicate_id", "message": "Guide Rail IDs must be unique."})
        rail_ids.add(rail.guide_rail_id)
        effective_from = getattr(rail, "effective_from", None)
        effective_until = getattr(rail, "effective_until", None)
        if effective_from and effective_until and effective_until < effective_from:
            blockers.append({"path": f"{path}.effective_until", "code": "invalid_date_range", "message": "The end date cannot be earlier than the start date."})
        if rail.enabled and not rail.required_evidence:
            blockers.append({"path": f"{path}.required_evidence", "code": "evidence_required", "message": "Enabled Guide Rails must name their required evidence."})
        compiled = rail.model_dump(mode="json")
        compiled.pop("owner_note", None)
        compiled["permitted_actions"] = _string_list(rail.permitted_actions)
        compiled["required_evidence"] = _string_list(rail.required_evidence)
        if situational:
            conditions = compiled.get("conditions") or {}
            conditions["current_pages"] = _string_list([normalize_route(value) for value in conditions.get("current_pages") or []])
            for route in conditions["current_pages"]:
                if route not in known_routes:
                    blockers.append({"path": f"{path}.conditions.current_pages", "code": "route_not_in_site_world", "message": f"{route} is not verified by the current Site World."})
            if not any(value not in (None, [], "") for value in conditions.values()):
                blockers.append({"path": f"{path}.conditions", "code": "condition_required", "message": "A situational Guide Rail needs at least one activation condition."})
            compiled["conditions"] = conditions
        return compiled

    for index, rail in enumerate(configuration.additional_guide_rails):
        compiled_additional.append(compile_rail(rail, f"additional_guide_rails.{index}", situational=False))
    for index, rail in enumerate(configuration.situational_guide_rails):
        compiled_situational.append(compile_rail(rail, f"situational_guide_rails.{index}", situational=True))

    if not website_context:
        warnings.append({"path": "site_world", "code": "site_world_unavailable", "message": "Run the project scan before publishing route- or tool-bound policy."})

    compiled_at = datetime.utcnow().isoformat()
    compiled = {
        "schema": COMPILED_POLICY_SCHEMA,
        "project_id": project_id,
        "domain": domain,
        "orb_name": configuration.orb_name,
        "version": next_version,
        "compiled_at": compiled_at,
        "locked_doctrine": {"hash": doctrine_hash(), "rules": LOCKED_ORB_DOCTRINE},
        "appearance": {**skin, "customization_state": "FACTORY_DEFAULT" if skin.get("factory_default") else "CUSTOM"},
        "llm": configuration.llm.model_dump(mode="json"),
        "behavior": {
            **configuration.behavior.model_dump(mode="json"),
            "job_description": compatible_text_by_field.get("job_description", "Serve as the visitor-facing Website ORB and guide visitors only through verified site paths."),
            "persona_notes": compatible_text_by_field.get("persona_notes", "Sound warm, patient, curious, and never irritated or scripted."),
            "must_follow_rules": compatible_by_field["must_follow_rules"],
            "must_not_rules": compatible_by_field["must_not_rules"],
            "prohibited_tone": compatible_by_field["prohibited_tone"],
            "standard_behavior": STANDARD_WEBSITE_ORB_BEHAVIOR,
            "owner_preferences": compatible_preferences,
        },
        "preference_review": preference_reviews,
        "business_objectives": compiled_objectives,
        "additional_guide_rails": compiled_additional,
        "situational_guide_rails": compiled_situational,
        "enforcement": {
            "allowed_routes": sorted(allowed_routes),
            "allowed_tools": sorted(allowed_tools),
            "route_default": "deny_unverified",
            "tool_default": "deny_unverified",
            "verified_outcome_required": True,
            "stage_governor_required": True,
        },
        "source_evidence": {
            "site_world_available": bool(website_context),
            "verified_routes": sorted(known_routes),
            "approved_tools": sorted(known_tools),
        },
    }
    canonical = json.dumps(compiled, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {
        "compiled_policy": compiled,
        "compiled_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "blockers": blockers,
        "warnings": warnings,
        "publishable": not blockers,
    }


def public_runtime_policy(compiled_policy: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not compiled_policy:
        return None
    return {
        key: compiled_policy.get(key)
        for key in (
            "schema",
            "project_id",
            "domain",
            "version",
            "compiled_at",
            "locked_doctrine",
            "appearance",
            "llm",
            "behavior",
            "business_objectives",
            "additional_guide_rails",
            "situational_guide_rails",
            "preference_review",
            "enforcement",
            "source_evidence",
        )
    }


def active_policy_directives(
    compiled_policy: Optional[Dict[str, Any]],
    *,
    route: str,
    authenticated: bool,
    confidence: Optional[float] = None,
) -> Dict[str, Any]:
    if not compiled_policy:
        return {"matched_guide_rails": [], "allowed_routes": [], "allowed_tools": []}
    today = date.today().isoformat()
    numeric_confidence = float(confidence) if isinstance(confidence, (int, float)) else None
    matched: List[Dict[str, Any]] = []
    for rail in compiled_policy.get("additional_guide_rails") or []:
        if not rail.get("enabled", True):
            continue
        if rail.get("effective_from") and rail["effective_from"] > today:
            continue
        if rail.get("effective_until") and rail["effective_until"] < today:
            continue
        matched.append(rail)
    for rail in compiled_policy.get("situational_guide_rails") or []:
        if not rail.get("enabled", True):
            continue
        conditions = rail.get("conditions") or {}
        pages = conditions.get("current_pages") or []
        states = conditions.get("authentication_states") or []
        minimum = conditions.get("minimum_confidence")
        if pages and normalize_route(route) not in pages:
            continue
        if states and ("authenticated" if authenticated else "anonymous") not in states:
            continue
        if minimum is not None and (numeric_confidence is None or numeric_confidence < float(minimum)):
            continue
        matched.append(rail)
    priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    matched.sort(key=lambda item: priority.get(str(item.get("priority")), 9))
    enforcement = compiled_policy.get("enforcement") or {}
    return {
        "matched_guide_rails": matched,
        "allowed_routes": enforcement.get("allowed_routes") or [],
        "allowed_tools": enforcement.get("allowed_tools") or [],
    }


def safe_model_name(value: str) -> str:
    model = (value or "").strip()
    if not model or len(model) > 160 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", model):
        raise ValueError("Model name contains unsupported characters")
    return model
