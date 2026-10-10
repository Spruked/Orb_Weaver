/** Canonical Web-TAMP wire contracts. Keep field names aligned with Python. */

export const WEB_TAMP_CONTRACT_VERSION = "web-tamp/v1" as const;

export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export type Domain = "website" | "desktop" | "physical" | "hybrid" | "app" | (string & {});
export type LifecycleState = "proposed" | "ready" | "blocked" | "running" | "succeeded" | "failed" | "cancelled" | "superseded";
export type PrimitiveKind = "harvest" | "motion";
export type VerificationStatus = "unverified" | "observed" | "verified" | "rejected";
export type PolicyDecision = "pending" | "allowed" | "denied" | "expired" | "revoked";
export type ExecutionOutcome = "succeeded" | "failed" | "blocked" | "cancelled" | "skipped";

export interface CoverageTarget {
  target_id: string;
  description: string;
  required: boolean;
  achieved?: boolean;
  measured_value?: number;
  target_value?: number;
  unit?: string;
}

export interface SuccessCriterion {
  criterion_id: string;
  description: string;
  required: boolean;
  satisfied?: boolean;
  evidence_ids?: string[];
}

export interface Task {
  schema: "web_tamp.task.v1";
  task_id: string;
  domain: Domain;
  objective: string;
  parent_task_id?: string;
  child_task_ids: string[];
  dependency_task_ids: string[];
  priority: number;
  constraints: Record<string, JsonValue>;
  coverage_targets: CoverageTarget[];
  success_criteria: SuccessCriterion[];
  lifecycle_state: LifecycleState;
  created_at: string;
  updated_at: string;
  metadata: Record<string, JsonValue>;
}

export interface ContractDescriptor {
  name: string;
  version: string;
  json_schema: Record<string, JsonValue>;
}

export interface HarvestMotionPrimitive {
  schema: "web_tamp.harvest_motion_primitive.v1";
  primitive_id: string;
  name: string;
  kind: PrimitiveKind;
  supported_domains: Domain[];
  input_contract: ContractDescriptor;
  output_contract: ContractDescriptor;
  preconditions: string[];
  execution_requirements: string[];
  mutates_world_model: boolean;
  authorization_scopes: string[];
  registered_by: string;
  version: string;
  metadata: Record<string, JsonValue>;
}

export interface Provenance {
  source_type: string;
  source_uri?: string;
  source_id?: string;
  collector: string;
  collection_method: string;
  source_hash?: string;
}

export interface Observation {
  schema: "web_tamp.observation.v1";
  observation_id: string;
  domain: Domain;
  source: string;
  provenance: Provenance;
  observed_at: string;
  confidence: number;
  verification_status: VerificationStatus;
  payload: Record<string, JsonValue>;
  environmental_changes: Record<string, JsonValue>;
  world_model_version?: string;
  metadata: Record<string, JsonValue>;
}

export type WorldLayer = "structural" | "semantic" | "visual_spatial" | "temporal" | "operational_approval";

export interface WorldNode {
  node_id: string;
  node_type: string;
  layers: WorldLayer[];
  properties: Record<string, JsonValue>;
  observation_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface WorldEdge {
  edge_id: string;
  relation: string;
  from_node_id: string;
  to_node_id: string;
  layers: WorldLayer[];
  properties: Record<string, JsonValue>;
  observation_ids: string[];
}

export interface WorldModel {
  schema: "web_tamp.world_model.v1";
  world_model_id: string;
  version: string;
  domain: Domain;
  nodes: WorldNode[];
  edges: WorldEdge[];
  projections: Record<string, JsonValue>;
  updated_at: string;
}

export interface Approval {
  schema: "web_tamp.approval.v1";
  approval_id: string;
  authority_subject_id: string;
  authority_kind: "owner" | "user" | "operator" | "system";
  scopes: string[];
  consent: boolean;
  policy_decision: PolicyDecision;
  issued_at: string;
  expires_at?: string;
  revoked_at?: string;
  reason?: string;
  metadata: Record<string, JsonValue>;
}

/** Planner output only. It is not execution authority. */
export interface Proposal {
  schema: "web_tamp.proposal.v1";
  proposal_id: string;
  task_id: string;
  primitive_id: string;
  sequence: number;
  inputs: Record<string, JsonValue>;
  rationale: string;
  planner_version: string;
  world_model_version: string;
  proposed_at: string;
  status: "proposed" | "superseded" | "withdrawn";
}

/** Governor-issued authority derived from a Proposal and Approval. */
export interface Authorization {
  schema: "web_tamp.authorization.v1";
  authorization_id: string;
  proposal_id: string;
  approval_id: string;
  scopes: string[];
  issued_by: string;
  issued_at: string;
  expires_at: string;
  revoked_at?: string;
  policy_decision: "allowed" | "revoked" | "expired";
}

export interface ExecutionReceipt {
  schema: "web_tamp.execution_receipt.v1";
  receipt_id: string;
  task_id: string;
  primitive_id: string;
  proposal_id: string;
  authorization_id?: string;
  started_at: string;
  completed_at: string;
  outcome: ExecutionOutcome;
  observation_ids: string[];
  state_changes: Record<string, JsonValue>;
  evidence: Record<string, JsonValue>;
  failure?: { code: string; message: string; retryable: boolean };
  trace_id: string;
}

export type WebTampContract = Task | HarvestMotionPrimitive | Observation | WorldModel | Approval | Proposal | Authorization | ExecutionReceipt;

export { parseAuthorization, parseTask } from "./validation";

