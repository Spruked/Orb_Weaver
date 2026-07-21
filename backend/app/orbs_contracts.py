"""Locked wire contracts for the authoritative ORBS Stage Governor."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


STAGE_SNAPSHOT_SCHEMA = "orb_weaver.orbs_stage_snapshot.v1"
STAGE_ACTION_REQUEST_SCHEMA = "orb_weaver.orbs_stage_action_request.v1"
STAGE_ACTION_RESULT_SCHEMA = "orb_weaver.orbs_stage_action_result.v1"
GUEST_SESSION_SCHEMA = "orb_weaver.orbs_guest_session.v1"
GUEST_MERGE_REQUEST_SCHEMA = "orb_weaver.orbs_guest_merge_request.v1"
GUEST_MERGE_RESULT_SCHEMA = "orb_weaver.orbs_guest_merge_result.v1"


class LockedContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AllowedStageAction(LockedContract):
    name: str = Field(min_length=1, max_length=120)
    display_label: str = Field(min_length=1, max_length=255)
    confirmation_required: bool
    permitted_input_fields: List[str] = Field(default_factory=list)
    allowed_input_fields: List[str] = Field(default_factory=list)
    destination_route: Optional[str] = None
    destination_verified: bool
    idempotency_required: bool
    reason_available: Optional[str] = None


class OrbsStageSnapshotContract(LockedContract):
    schema: Literal[STAGE_SNAPSHOT_SCHEMA] = STAGE_SNAPSHOT_SCHEMA
    customer_id: str
    project_id: str
    project_display_name: str
    build_order_id: Optional[str] = None
    current_stage: str
    stage_status: str
    snapshot_version: str
    completed_stages: List[str]
    blocking_reason: Optional[str] = None
    customer_action_required: Optional[str] = None
    approved_stage_evidence: Dict[str, Any]
    allowed_actions: List[AllowedStageAction]
    next_recommended_action: Optional[str] = None
    approved_destination_route: Optional[str] = None
    approved_destination_verified: bool = False
    updated_at: datetime


class OrbsStageActionRequestContract(LockedContract):
    schema: Literal[STAGE_ACTION_REQUEST_SCHEMA] = STAGE_ACTION_REQUEST_SCHEMA
    customer_id: str
    project_id: str
    build_order_id: Optional[str] = None
    action: str = Field(min_length=1, max_length=120)
    expected_stage: str
    snapshot_version: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    confirmation_evidence: Optional[Dict[str, Any]] = None
    idempotency_key: str = Field(min_length=8, max_length=255)


class OrbsStageActionResultContract(LockedContract):
    schema: Literal[STAGE_ACTION_RESULT_SCHEMA] = STAGE_ACTION_RESULT_SCHEMA
    accepted: bool
    action: str
    idempotency_key: str
    transition_applied: bool
    rejection_code: Optional[str] = None
    fresh_snapshot: OrbsStageSnapshotContract
    recorded_at: datetime


class OrbsGuestSessionContract(LockedContract):
    schema: Literal[GUEST_SESSION_SCHEMA] = GUEST_SESSION_SCHEMA
    guest_session_id: str
    landing_intent: str
    selected_tier_interest: Optional[str] = None
    website_url: Optional[str] = None
    original_cta_destination: str
    current_onboarding_step: str
    completed_onboarding_steps: List[str] = Field(default_factory=list)
    non_sensitive_questionnaire_answers: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    expires_at: datetime
    version: int = Field(ge=1)


class OrbsGuestMergeRequestContract(LockedContract):
    schema: Literal[GUEST_MERGE_REQUEST_SCHEMA] = GUEST_MERGE_REQUEST_SCHEMA
    guest_session_id: str
    idempotency_key: str = Field(min_length=8, max_length=255)
    attach_project_id: Optional[str] = None
    project_display_name: Optional[str] = Field(default=None, max_length=255)


class OrbsGuestMergeResultContract(LockedContract):
    schema: Literal[GUEST_MERGE_RESULT_SCHEMA] = GUEST_MERGE_RESULT_SCHEMA
    merge_status: Literal["merged", "idempotent_replay"]
    guest_session_id: str
    customer_id: str
    project_id: str
    onboarding_record_id: str
    original_cta_destination: str
    transferred_fields: List[str]
    consumed_at: datetime
    fresh_snapshot: OrbsStageSnapshotContract
