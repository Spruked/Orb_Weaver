import type { TourDestinationAuthorizationScope, WebsiteJourneyStateV2 } from '../state/tourControllerStore';
import type { TourDestinationRoute, TourEngagementQuestion, TourSemanticCategory } from '../types/tour';

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
