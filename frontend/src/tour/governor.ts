import type { TourDestinationAuthorizationScope, WebsiteJourneyStateV2 } from '../state/tourControllerStore';
import type { TourDestinationRoute, TourEngagementQuestion, TourSemanticCategory } from '../types/tour';
import type { DiscoveryCandidateAction, DiscoveryDimension, DiscoveryPattern } from '../types/discovery';
import { DISCOVERY_PATTERNS, discoveryPatternById } from './discovery/registry';
import { validateInterpretation } from './discovery/compiler';
import { freezeRegistry } from './discovery/registry';
import type { AgencyAuthorization, AgencyBinding, AgencyEnvelope, AgencyEnvironment, AgencyInvalidation, CandidateMove, CandidateSelection } from '../types/agency';
import { AGENCY_BUDGET } from './agencyBudget';

/**
 * The Website Tour Stage Governor is the sole route authority for the public
 * conversational tour. Questions expose meaning; this module decides whether
 * that meaning has a legal route in the current saved state.
 */
const LANDING_BRANCHES: Readonly<Record<string, Readonly<Partial<Record<TourSemanticCategory, TourDestinationRoute>>>>> = {
  'discovery-or-guidance': {
    SITE_DISCOVERY: '/how-it-works',
    VERIFIED_GUIDANCE: '/lidar-guidance',
  },
  'understanding-or-helping': {
    VISITOR_UNDERSTANDING: '/how-it-works',
    VISITOR_ASSISTANCE: '/lidar-guidance',
  },
  'discovery-or-conversion': {
    DISCOVERY_FRICTION: '/features',
    CONVERSION_FRICTION: '/preflight',
  },
};

export function eligibleDestinationsForQuestion(
  state: WebsiteJourneyStateV2,
  question: TourEngagementQuestion,
): TourDestinationRoute[] {
  if (state.stage !== 'LANDING_TOUR' || state.interruptionState.isInterrupted || state.preflightStatus === 'DEFERRED') return [];
  return [...new Set(Object.values(LANDING_BRANCHES[question.id] || {}).filter((route): route is TourDestinationRoute => Boolean(route)))];
}

export function legalTourNavigationRoutes(state: WebsiteJourneyStateV2): TourDestinationRoute[] {
  if (state.stage !== 'LANDING_TOUR' || state.interruptionState.isInterrupted || state.preflightStatus === 'DEFERRED') return [];
  const pending = state.interaction.pendingQuestionId;
  const branches = pending && LANDING_BRANCHES[pending] ? [LANDING_BRANCHES[pending]] : Object.values(LANDING_BRANCHES);
  return [...new Set(branches.flatMap(branch => Object.values(branch).filter((route): route is TourDestinationRoute => Boolean(route))))];
}

export function destinationAuthorizationScope(
  state: WebsiteJourneyStateV2,
  question: TourEngagementQuestion,
): TourDestinationAuthorizationScope {
  return {
    questionId: question.id,
    stage: state.stage,
    chapterId: state.currentChapterId,
    stopId: state.currentStopId,
  };
}

export function resolveGovernedDestination(
  state: WebsiteJourneyStateV2,
  question: TourEngagementQuestion,
  semanticCategory: TourSemanticCategory,
): TourDestinationRoute | null {
  const route = LANDING_BRANCHES[question.id]?.[semanticCategory] || null;
  if (!route) return null;
  const scope = state.interaction.eligibleDestinationScope;
  if (!scope || scope.questionId !== question.id || scope.stage !== state.stage ||
    scope.chapterId !== state.currentChapterId || scope.stopId !== state.currentStopId) return null;
  const eligible = eligibleDestinationsForQuestion(state, question);
  // Persisted route lists are a continuity record, never an authority. A
  // pending question must retain the exact set the governor issued.
  return state.interaction.eligibleDestinationRoutes.includes(route) && eligible.includes(route) ? route : null;
}

/** Evidence-derived acquisition context supplied by the host, never by a model. */
export interface DiscoveryAcquisitionContext {
  confidenceByDimension: Partial<Record<DiscoveryDimension, number>>;
  askedPatternIds: readonly string[];
  remainingAcquisitions: number;
  /** Current candidates approved for consideration by the existing capability policy. */
  availableCandidateActionIds: readonly string[];
}

function confidenceFor(context: DiscoveryAcquisitionContext, dimension: DiscoveryDimension): number {
  const value = context.confidenceByDimension[dimension] ?? 0;
  return Number.isFinite(value) && value >= 0 && value <= 1 ? value : 0;
}

function patternIsLegal(
  state: WebsiteJourneyStateV2, pattern: DiscoveryPattern, context: DiscoveryAcquisitionContext,
): boolean {
  return pattern.legalStages.includes(state.stage) && state.currentChapterId !== null && state.currentStopId !== null &&
    !state.interruptionState.isInterrupted && state.preflightStatus !== 'DEFERRED' &&
    pattern.requiredDimensions.every(dimension => confidenceFor(context, dimension) >= 0.8) &&
    pattern.choices.every(choice => context.availableCandidateActionIds.includes(choice.candidateAction.id));
}

/** Selection is a ranked set, never a traversal of source numbers 1 through 50. */
export function eligibleDiscoveryPatterns(
  state: WebsiteJourneyStateV2, context: DiscoveryAcquisitionContext,
): DiscoveryPattern[] {
  if (!Number.isInteger(context.remainingAcquisitions) || context.remainingAcquisitions <= 0 ||
    state.interaction.pendingQuestionId || state.interaction.activeDestinationRoute) return [];
  const asked = new Set([...state.interaction.askedQuestionIds, ...context.askedPatternIds]);
  const score = (pattern: DiscoveryPattern) =>
    (1 - confidenceFor(context, pattern.dimension)) * pattern.informationGainWeight + pattern.convergenceWeight * 0.2;
  return DISCOVERY_PATTERNS.filter(pattern => patternIsLegal(state, pattern, context) &&
    !asked.has(pattern.id) && confidenceFor(context, pattern.dimension) < pattern.confidenceTarget)
    .sort((a, b) => score(b) - score(a) || a.id.localeCompare(b.id));
}

export function selectDiscoveryPattern(
  state: WebsiteJourneyStateV2, context: DiscoveryAcquisitionContext,
): DiscoveryPattern | null {
  return eligibleDiscoveryPatterns(state, context)[0] || null;
}

/** Reuse the current question/stage/chapter/stop binding before returning a candidate.
 * The caller must still obtain and consume an execution authorization and live proof.
 */
export function resolveDiscoveryCandidate(
  state: WebsiteJourneyStateV2, semanticOutput: string, context: DiscoveryAcquisitionContext,
): DiscoveryCandidateAction | null {
  const questionId = state.interaction.pendingQuestionId;
  const scope = state.interaction.eligibleDestinationScope;
  const pattern = questionId ? discoveryPatternById(questionId) : null;
  if (!pattern || !scope || scope.questionId !== questionId || scope.stage !== state.stage ||
    scope.chapterId !== state.currentChapterId || scope.stopId !== state.currentStopId || !patternIsLegal(state, pattern, context)) return null;
  const choice = pattern.choices.find(item => item.semanticOutput === semanticOutput);
  return choice ? { ...choice.candidateAction } : null;
}

/** Ambiguous or weak interpretation records no action choice. */
export function resolveDiscoveryInterpretation(
  state: WebsiteJourneyStateV2, visitorResponse: string, interpretation: unknown,
  context: DiscoveryAcquisitionContext,
): DiscoveryCandidateAction | null {
  const pattern = discoveryPatternById(state.interaction.pendingQuestionId || '');
  if (!pattern) return null;
  const validated = validateInterpretation(pattern, visitorResponse, interpretation);
  if (!validated || validated.categories.length !== 1 || validated.categories[0].confidence < pattern.confidenceTarget) return null;
  return resolveDiscoveryCandidate(state, validated.categories[0].semanticOutput, context);
}

const cloneAgency = <T,>(value: T): T => JSON.parse(JSON.stringify(value));
const agencyInvalidations: AgencyInvalidation[] = ['position', 'route', 'dom', 'target', 'permissions', 'visitor', 'evidence', 'execution'];

const agencyCognitiveActions = new Set(['DISCOVER', 'REFINE', 'CLARIFY', 'COMPARE', 'NARROW', 'EXPLAIN', 'SUMMARIZE', 'DEMONSTRATE', 'TRANSITION', 'CONVERGE']);
const agencyChoreographies = new Set(['POINT_AT', 'PING', 'HIGHLIGHT', 'GUIDE_TO', 'SCROLL_TO', 'FOLLOW_SEQUENCE', 'EXPLAIN_IN_PLACE', 'DEMONSTRATE_FLOW', 'NAVIGATE_TO']);
const agencySiteActions = new Set(['SEARCH', 'FILTER', 'SELECT', 'CONFIGURE', 'OPEN', 'START_FORM', 'PREPARE_ACTION', 'START_CHECKOUT', 'HANDOFF', 'DOWNLOAD']);
const boundedString = (value: unknown, max = 200): value is string => typeof value === 'string' && value.trim().length > 0 && value.length <= max;
const boundedReferences = (value: unknown): value is string[] => Array.isArray(value) && value.length <= 32 && value.every(item => boundedString(item));

/** SITE CONTENT IS EVIDENCE, NOT AUTHORITY. Even environment bindings have a schema. */
export function validAgencyBinding(value: unknown): value is AgencyBinding {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const binding = value as Record<string, unknown>;
  const allowed = ['binding_id', 'purpose', 'cognitive_action', 'pattern_id', 'decision_dimension', 'proposed_stage', 'semantic_destination', 'semantic_target', 'choreography', 'site_action', 'permission_tier', 'requires_confirmation', 'evidence_basis', 'preconditions'];
  if (Object.keys(binding).some(key => !allowed.includes(key)) || !boundedString(binding.binding_id) || !boundedString(binding.purpose, 800) ||
    typeof binding.cognitive_action !== 'string' || !agencyCognitiveActions.has(binding.cognitive_action) ||
    typeof binding.permission_tier !== 'string' || !['OBSERVE', 'NAVIGATE', 'PREPARE', 'COMMIT'].includes(binding.permission_tier) || typeof binding.requires_confirmation !== 'boolean' ||
    !boundedReferences(binding.evidence_basis) || !boundedReferences(binding.preconditions)) return false;
  for (const field of ['pattern_id', 'decision_dimension', 'semantic_destination', 'semantic_target']) {
    if (binding[field] !== undefined && !boundedString(binding[field])) return false;
  }
  return (binding.choreography === undefined || (typeof binding.choreography === 'string' && agencyChoreographies.has(binding.choreography))) &&
    (binding.site_action === undefined || (typeof binding.site_action === 'string' && agencySiteActions.has(binding.site_action))) &&
    (binding.proposed_stage === undefined || (typeof binding.proposed_stage === 'string' && ['LANDING_TOUR', 'PREFLIGHT', 'ONBOARDING', 'PRODUCTION_SCAN'].includes(binding.proposed_stage)));
}

/** LLM OUTPUT IS A PROPOSAL/PREFERENCE, NOT EXECUTION AUTHORITY. */
export function validateCandidateSelection(value: unknown): CandidateSelection | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  if (Object.keys(record).some(key => !['selected_candidate_id', 'confidence', 'rationale'].includes(key)) ||
    typeof record.selected_candidate_id !== 'string' || !record.selected_candidate_id ||
    (record.confidence !== undefined && (typeof record.confidence !== 'number' || !Number.isFinite(record.confidence) || record.confidence < 0 || record.confidence > 1)) ||
    (record.rationale !== undefined && (typeof record.rationale !== 'string' || record.rationale.length > 1000))) return null;
  return cloneAgency(record) as unknown as CandidateSelection;
}

function agencyBindingIsLegal(binding: AgencyBinding, env: AgencyEnvironment): boolean {
  if (!validAgencyBinding(binding)) return false;
  const { journey } = env;
  if (journey.interruptionState.isInterrupted || journey.preflightStatus === 'DEFERRED') return false;
  // The consequence tier is explicit on the binding. No action-name-to-tier inference.
  if (!env.permissionTiers.includes(binding.permission_tier) ||
    ((binding.requires_confirmation || binding.permission_tier === 'COMMIT') && !env.confirmations.includes(binding.binding_id))) return false;
  const capabilitySets = [env.universalCapabilities, env.scannedAffordances, env.liveAffordances, env.governedCapabilities, env.policyCapabilities];
  if (capabilitySets.some(set => !set.includes(binding.binding_id))) return false;
  if (!binding.evidence_basis.length || binding.evidence_basis.some(id => !env.validEvidenceIds.includes(id)) ||
    binding.preconditions.some(id => !env.satisfiedPreconditions.includes(id))) return false;
  if (binding.proposed_stage && !env.legalStageTransitions.includes(binding.proposed_stage)) return false;
  if (binding.semantic_target) {
    const target = env.spatialTargets[binding.semantic_target];
    if (!target || !env.validEvidenceIds.includes(target.evidenceId)) return false;
  }
  if (binding.semantic_destination) {
    const destination = env.destinations[binding.semantic_destination];
    if (!destination || !env.validEvidenceIds.includes(destination.evidenceId) ||
      !env.spatialTargets[destination.targetAlias] || !env.validEvidenceIds.includes(env.spatialTargets[destination.targetAlias].evidenceId) || !/^\/(?!\/)/.test(destination.route) ||
      /[\\\s]/.test(destination.route)) return false;
  }
  if (binding.choreography === 'NAVIGATE_TO' && !binding.semantic_destination) return false;
  if (['POINT_AT', 'PING', 'HIGHLIGHT', 'GUIDE_TO', 'SCROLL_TO', 'FOLLOW_SEQUENCE', 'DEMONSTRATE_FLOW'].includes(binding.choreography || '') && !binding.semantic_target) return false;
  if (binding.pattern_id) {
    const pattern = discoveryPatternById(binding.pattern_id);
    if (pattern) {
      if (binding.decision_dimension !== pattern.dimension || !eligibleDiscoveryPatterns(journey, env.acquisition).some(item => item.id === pattern.id)) return false;
    } else if (!Object.prototype.hasOwnProperty.call(LANDING_BRANCHES, binding.pattern_id) ||
      journey.stage !== 'LANDING_TOUR' || journey.interaction.askedQuestionIds.includes(binding.pattern_id)) return false;
  }
  return true;
}

/** Agency is an extension of this Governor; the environment supplies verified facts.
 * No provider callbacks or model objects participate in legal-set construction.
 */
export function createAgencyEnvelope(readEnvironment: () => AgencyEnvironment) {
  const bytes = new Uint32Array(4);
  globalThis.crypto.getRandomValues(bytes);
  const identity = Array.from(bytes, n => n.toString(16)).join('-');
  let revision = 0;
  let eventRevision = 0;
  let signature = '';
  let envelope: AgencyEnvelope | null = null;
  let activeCandidateMap = new Map<string, CandidateMove>();
  const grants = new Map<string, AgencyAuthorization>();
  let nonceSequence = 0;

  const refresh = (): AgencyEnvelope => {
    const env = readEnvironment();
    const nextSignature = JSON.stringify([eventRevision, env]);
    if (envelope && signature === nextSignature) return envelope;
    signature = nextSignature;
    revision += 1;
    grants.clear();
    const bounded_set_revision = `${identity}:${revision}`;
    const bindingIds = new Set<string>();
    const candidates: CandidateMove[] = [];
    for (const binding of env.bindings) {
      if (bindingIds.has(binding.binding_id)) throw new Error('Duplicate coherent agency binding');
      bindingIds.add(binding.binding_id);
      if (!agencyBindingIsLegal(binding, env)) continue;
      const { binding_id, ...move } = binding;
      candidates.push({ ...cloneAgency(move), candidate_id: `move:${binding_id}`, bounded_set_revision, invalidation_events: [...agencyInvalidations] });
    }
    const kmax = (env.budget || AGENCY_BUDGET).maxCandidates;
    if (!Number.isInteger(kmax) || kmax < 1 || kmax > 64) throw new Error('Invalid agency Kmax');
    // Preserve alternative move families in the bounded working set. This is
    // deterministic preselection; the model makes the final strategic choice.
    const families = new Map<string, CandidateMove[]>();
    for (const move of candidates) {
      const family = move.pattern_id ? 'question' : move.choreography || move.cognitive_action;
      families.set(family, [...(families.get(family) || []), move]);
    }
    const bounded: CandidateMove[] = [];
    while (bounded.length < kmax) {
      let added = false;
      for (const family of families.values()) {
        const next = family.shift();
        if (next && bounded.length < kmax) { bounded.push(next); added = true; }
      }
      if (!added) break;
    }
    activeCandidateMap = new Map(bounded.map(move => [move.candidate_id, move]));
    const unique = (items: Array<string | undefined>): string[] => [...new Set(items.filter((item): item is string => Boolean(item)))];
    envelope = freezeRegistry({
      bounded_set_revision,
      position: { stage: env.journey.stage, chapter: env.journey.currentChapterId, stop: env.journey.currentStopId, route: env.route, governed_position: env.positionRevision },
      vectors: {
        LEGAL_PATTERNS: unique(bounded.map(move => move.pattern_id)),
        LEGAL_DIMENSIONS: unique(bounded.map(move => move.decision_dimension)),
        LEGAL_STAGE_TRANSITIONS: [...new Set(bounded.flatMap(move => move.proposed_stage ? [move.proposed_stage] : []))],
        LEGAL_SEMANTIC_DESTINATIONS: unique(bounded.map(move => move.semantic_destination)),
        LEGAL_SPATIAL_TARGETS: unique(bounded.map(move => move.semantic_target)),
        LEGAL_ACTIONS: unique(bounded.flatMap(move => [move.cognitive_action, move.choreography, move.site_action])),
      },
      candidates: bounded,
    });
    return envelope;
  };

  const issue = (selection: unknown, suppliedRevision: string, semanticAnswer?: string): AgencyAuthorization | null => {
    const valid = validateCandidateSelection(selection);
    const current = refresh();
    if (!valid || current.bounded_set_revision !== suppliedRevision) return null;
    const candidate = activeCandidateMap.get(valid.selected_candidate_id);
    if (!candidate) return null;
    const authorization: AgencyAuthorization = freezeRegistry({
      nonce: `${identity}:${++nonceSequence}`, candidate_id: candidate.candidate_id, bounded_set_revision: suppliedRevision,
      stage: current.position.stage, chapter: current.position.chapter, stop: current.position.stop,
      governed_position: current.position.governed_position,
      authorized_action: JSON.stringify(candidate), ...(semanticAnswer ? { semantic_answer: semanticAnswer } : {}),
    });
    grants.clear(); // Only the latest selection can execute in this turn.
    grants.set(authorization.nonce, authorization);
    return authorization;
  };

  const consume = (authorization: AgencyAuthorization): CandidateMove | null => {
    // Execution Authority = Candidate Validity ∩ State Revision ∩ Permission ∩ Policy ∩ Live Environment.
    // refresh re-reads every boundary; Map membership alone is not complete validation.
    const current = refresh();
    const issued = grants.get(authorization.nonce);
    if (!issued || JSON.stringify(issued) !== JSON.stringify(authorization) || issued.bounded_set_revision !== current.bounded_set_revision) return null;
    grants.delete(authorization.nonce);
    const candidate = activeCandidateMap.get(issued.candidate_id);
    if (!candidate || JSON.stringify(candidate) !== issued.authorized_action) return null;
    // Consumption invalidates this whole bounded set, including any delayed model response.
    eventRevision += 1;
    return candidate;
  };

  return {
    refresh, issue, consume,
    invalidate: (_event: AgencyInvalidation) => { eventRevision += 1; grants.clear(); },
    async execute(authorization: AgencyAuthorization, run: (move: CandidateMove) => Promise<boolean>): Promise<boolean> {
      const move = consume(authorization);
      if (!move) return false;
      return run(move);
    },
  };
}
