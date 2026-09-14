import type { TourJourneyStage, WebsiteJourneyStateV2 } from '../state/tourControllerStore';
import type { DiscoveryAcquisitionContext } from '../tour/governor';

export type PermissionTier = 'OBSERVE' | 'NAVIGATE' | 'PREPARE' | 'COMMIT';
export type CognitiveAction = 'DISCOVER' | 'REFINE' | 'CLARIFY' | 'COMPARE' | 'NARROW' | 'EXPLAIN' | 'SUMMARIZE' | 'DEMONSTRATE' | 'TRANSITION' | 'CONVERGE';
export type Choreography = 'POINT_AT' | 'PING' | 'HIGHLIGHT' | 'GUIDE_TO' | 'SCROLL_TO' | 'FOLLOW_SEQUENCE' | 'EXPLAIN_IN_PLACE' | 'DEMONSTRATE_FLOW' | 'NAVIGATE_TO';
export type SiteAction = 'SEARCH' | 'FILTER' | 'SELECT' | 'CONFIGURE' | 'OPEN' | 'START_FORM' | 'PREPARE_ACTION' | 'START_CHECKOUT' | 'HANDOFF' | 'DOWNLOAD';
export type AgencyInvalidation = 'position' | 'route' | 'dom' | 'target' | 'permissions' | 'visitor' | 'evidence' | 'execution';

export interface AgencyBudget {
  /** Kmax bounds candidate count before the cognition request is assembled. */
  maxCandidates: number;
  /** Serialized ceiling for B; B also limits which working-state fields are active. */
  maxPayloadBytes: number;
  maxEvidenceItems: number;
  maxEvidenceBytes: number;
}

export interface CandidateMove {
  candidate_id: string;
  bounded_set_revision: string;
  purpose: string;
  cognitive_action: CognitiveAction;
  pattern_id?: string;
  decision_dimension?: string;
  proposed_stage?: TourJourneyStage;
  semantic_destination?: string;
  semantic_target?: string;
  choreography?: Choreography;
  site_action?: SiteAction;
  /** Consequence tier is independent of cognitive_action, choreography, and site_action. */
  permission_tier: PermissionTier;
  requires_confirmation: boolean;
  evidence_basis: string[];
  preconditions: string[];
  invalidation_events: AgencyInvalidation[];
}

/** These coherent bindings are assembled by the environment, never by the LLM. */
export interface AgencyBinding extends Omit<CandidateMove, 'candidate_id' | 'bounded_set_revision' | 'invalidation_events'> {
  binding_id: string;
}

export interface AgencyEnvironment {
  journey: WebsiteJourneyStateV2;
  route: string;
  /** Incremented by existing state/event sources, including movement away and back. */
  positionRevision: number;
  domRevision: number;
  visitorRevision: number;
  evidenceRevision: number;
  permissionRevision: number;
  universalCapabilities: string[];
  scannedAffordances: string[];
  liveAffordances: string[];
  governedCapabilities: string[];
  policyCapabilities: string[];
  permissionTiers: PermissionTier[];
  /** Exact binding identities for which the visitor has confirmed the consequence. */
  confirmations: string[];
  validEvidenceIds: string[];
  satisfiedPreconditions: string[];
  legalStageTransitions: TourJourneyStage[];
  destinations: Record<string, { route: string; evidenceId: string; targetAlias: string }>;
  spatialTargets: Record<string, { targetId: string; evidenceId: string }>;
  bindings: AgencyBinding[];
  acquisition: DiscoveryAcquisitionContext;
  budget?: AgencyBudget;
}

export interface AgencyEnvelope {
  bounded_set_revision: string;
  position: { stage: TourJourneyStage; chapter: string | null; stop: string | null; route: string; governed_position: number };
  vectors: {
    LEGAL_PATTERNS: string[];
    LEGAL_DIMENSIONS: string[];
    LEGAL_STAGE_TRANSITIONS: TourJourneyStage[];
    LEGAL_SEMANTIC_DESTINATIONS: string[];
    LEGAL_SPATIAL_TARGETS: string[];
    LEGAL_ACTIONS: string[];
  };
  candidates: CandidateMove[];
}

export interface CandidateSelection {
  selected_candidate_id: string;
  confidence?: number;
  rationale?: string;
}

export interface AgencyAuthorization {
  nonce: string;
  candidate_id: string;
  bounded_set_revision: string;
  stage: TourJourneyStage;
  chapter: string | null;
  stop: string | null;
  governed_position: number;
  authorized_action: string;
  semantic_answer?: string;
}
