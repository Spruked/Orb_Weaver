"""Pydantic v2 implementation of the canonical Web-TAMP wire contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


CONTRACT_VERSION = "web-tamp/v1"
JsonObject = Dict[str, Any]
Domain = str


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class CoverageTarget(ContractModel):
    target_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required: bool
    achieved: Optional[bool] = None
    measured_value: Optional[float] = None
    target_value: Optional[float] = None
    unit: Optional[str] = None


class SuccessCriterion(ContractModel):
    criterion_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required: bool
    satisfied: Optional[bool] = None
    evidence_ids: List[str] = Field(default_factory=list)


class Task(ContractModel):
    schema: Literal["web_tamp.task.v1"] = "web_tamp.task.v1"
    task_id: str = Field(min_length=1)
    domain: Domain = Field(min_length=1)
    objective: str = Field(min_length=1)
    parent_task_id: Optional[str] = None
    child_task_ids: List[str] = Field(default_factory=list)
    dependency_task_ids: List[str] = Field(default_factory=list)
    priority: int = Field(ge=0, le=100)
    constraints: JsonObject = Field(default_factory=dict)
    coverage_targets: List[CoverageTarget] = Field(default_factory=list)
    success_criteria: List[SuccessCriterion] = Field(default_factory=list)
    lifecycle_state: Literal["proposed", "ready", "blocked", "running", "succeeded", "failed", "cancelled", "superseded"]
    created_at: datetime
    updated_at: datetime
    metadata: JsonObject = Field(default_factory=dict)


class ContractDescriptor(ContractModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    json_schema: JsonObject


class HarvestMotionPrimitive(ContractModel):
    schema: Literal["web_tamp.harvest_motion_primitive.v1"] = "web_tamp.harvest_motion_primitive.v1"
    primitive_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: Literal["harvest", "motion"]
    supported_domains: List[Domain] = Field(min_length=1)
    input_contract: ContractDescriptor
    output_contract: ContractDescriptor
    preconditions: List[str] = Field(default_factory=list)
    execution_requirements: List[str] = Field(default_factory=list)
    mutates_world_model: bool
    authorization_scopes: List[str] = Field(default_factory=list)
    registered_by: str = Field(min_length=1)
    version: str = Field(min_length=1)
    metadata: JsonObject = Field(default_factory=dict)


class Provenance(ContractModel):
    source_type: str = Field(min_length=1)
    source_uri: Optional[str] = None
    source_id: Optional[str] = None
    collector: str = Field(min_length=1)
    collection_method: str = Field(min_length=1)
    source_hash: Optional[str] = None


class Observation(ContractModel):
    schema: Literal["web_tamp.observation.v1"] = "web_tamp.observation.v1"
    observation_id: str = Field(min_length=1)
    domain: Domain = Field(min_length=1)
    source: str = Field(min_length=1)
    provenance: Provenance
    observed_at: datetime
    confidence: float = Field(ge=0, le=1)
    verification_status: Literal["unverified", "observed", "verified", "rejected"]
    payload: JsonObject = Field(default_factory=dict)
    environmental_changes: JsonObject = Field(default_factory=dict)
    world_model_version: Optional[str] = None
    metadata: JsonObject = Field(default_factory=dict)


WorldLayer = Literal["structural", "semantic", "visual_spatial", "temporal", "operational_approval"]


class WorldNode(ContractModel):
    node_id: str = Field(min_length=1)
    node_type: str = Field(min_length=1)
    layers: List[WorldLayer] = Field(min_length=1)
    properties: JsonObject = Field(default_factory=dict)
    observation_ids: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class WorldEdge(ContractModel):
    edge_id: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    from_node_id: str = Field(min_length=1)
    to_node_id: str = Field(min_length=1)
    layers: List[WorldLayer] = Field(min_length=1)
    properties: JsonObject = Field(default_factory=dict)
    observation_ids: List[str] = Field(default_factory=list)


class WorldModel(ContractModel):
    schema: Literal["web_tamp.world_model.v1"] = "web_tamp.world_model.v1"
    world_model_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    domain: Domain = Field(min_length=1)
    nodes: List[WorldNode] = Field(default_factory=list)
    edges: List[WorldEdge] = Field(default_factory=list)
    projections: JsonObject = Field(default_factory=dict)
    updated_at: datetime

    @model_validator(mode="after")
    def validate_edges_reference_known_nodes(self) -> "WorldModel":
        node_ids = {node.node_id for node in self.nodes}
        if any(edge.from_node_id not in node_ids or edge.to_node_id not in node_ids for edge in self.edges):
            raise ValueError("World Model edges must reference nodes in the same version")
        return self


class Approval(ContractModel):
    schema: Literal["web_tamp.approval.v1"] = "web_tamp.approval.v1"
    approval_id: str = Field(min_length=1)
    authority_subject_id: str = Field(min_length=1)
    authority_kind: Literal["owner", "user", "operator", "system"]
    scopes: List[str] = Field(default_factory=list)
    consent: bool
    policy_decision: Literal["pending", "allowed", "denied", "expired", "revoked"]
    issued_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    reason: Optional[str] = None
    metadata: JsonObject = Field(default_factory=dict)


class Proposal(ContractModel):
    schema: Literal["web_tamp.proposal.v1"] = "web_tamp.proposal.v1"
    proposal_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    primitive_id: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    inputs: JsonObject = Field(default_factory=dict)
    rationale: str = Field(min_length=1)
    planner_version: str = Field(min_length=1)
    world_model_version: str = Field(min_length=1)
    proposed_at: datetime
    status: Literal["proposed", "superseded", "withdrawn"] = "proposed"


class Authorization(ContractModel):
    schema: Literal["web_tamp.authorization.v1"] = "web_tamp.authorization.v1"
    authorization_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    approval_id: str = Field(min_length=1)
    scopes: List[str] = Field(default_factory=list)
    issued_by: str = Field(min_length=1)
    issued_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    policy_decision: Literal["allowed", "revoked", "expired"]


class ExecutionReceipt(ContractModel):
    schema: Literal["web_tamp.execution_receipt.v1"] = "web_tamp.execution_receipt.v1"
    receipt_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    primitive_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    authorization_id: Optional[str] = None
    started_at: datetime
    completed_at: datetime
    outcome: Literal["succeeded", "failed", "blocked", "cancelled", "skipped"]
    observation_ids: List[str] = Field(default_factory=list)
    state_changes: JsonObject = Field(default_factory=dict)
    evidence: JsonObject = Field(default_factory=dict)
    failure: Optional[Dict[str, Any]] = None
    trace_id: str = Field(min_length=1)
