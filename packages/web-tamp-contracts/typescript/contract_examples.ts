import type { Authorization, HarvestMotionPrimitive, Observation, Proposal, Task, WorldModel } from "./index";
import { parseTask } from "./validation";

export const websiteTaskExample: Task = parseTask({
  schema: "web_tamp.task.v1",
  task_id: "task:website:public-crawl:001",
  domain: "website",
  objective: "Map public website structure and verified visitor guidance targets.",
  child_task_ids: [],
  dependency_task_ids: [],
  priority: 80,
  constraints: { public_only: true },
  coverage_targets: [],
  success_criteria: [],
  lifecycle_state: "ready",
  created_at: "2026-10-10T12:00:00Z",
  updated_at: "2026-10-10T12:00:00Z",
  metadata: {},
});

export const websitePrimitiveExample: HarvestMotionPrimitive = {
  schema: "web_tamp.harvest_motion_primitive.v1",
  primitive_id: "primitive:website:render-public-route",
  name: "Render public route",
  kind: "harvest",
  supported_domains: ["website"],
  input_contract: { name: "render-input", version: "v1", json_schema: {} },
  output_contract: { name: "observation", version: "v1", json_schema: {} },
  preconditions: ["route_is_public"],
  execution_requirements: ["browser"],
  mutates_world_model: true,
  authorization_scopes: ["website.read_public"],
  registered_by: "orb-weaver-factory",
  version: "1.0.0",
  metadata: {},
};

export const websiteObservationExample: Observation = {
  schema: "web_tamp.observation.v1",
  observation_id: "observation:website:route:/",
  domain: "website",
  source: "render-public-route",
  provenance: { source_type: "web", source_uri: "https://example.test/", collector: "browser", collection_method: "render", source_hash: "sha256:example" },
  observed_at: "2026-10-10T12:01:00Z",
  confidence: 0.98,
  verification_status: "verified",
  payload: { route: "/", title: "Example" },
  environmental_changes: {},
  metadata: {},
};

export const websiteWorldModelExample: WorldModel = {
  schema: "web_tamp.world_model.v1",
  world_model_id: "world:website:example.test",
  version: "world-v1",
  domain: "website",
  nodes: [],
  edges: [],
  projections: {},
  updated_at: "2026-10-10T12:01:00Z",
};

export const websiteProposalExample: Proposal = {
  schema: "web_tamp.proposal.v1",
  proposal_id: "proposal:website:render:/",
  task_id: websiteTaskExample.task_id,
  primitive_id: websitePrimitiveExample.primitive_id,
  sequence: 0,
  inputs: { route: "/" },
  rationale: "The public route is required to satisfy route coverage.",
  planner_version: "planner-contract-only",
  world_model_version: "world-v1",
  proposed_at: "2026-10-10T12:01:00Z",
  status: "proposed",
};
