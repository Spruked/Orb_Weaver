import { createInitialJourneyState } from '../../state/tourControllerStore';
import { DISCOVERY_DIMENSIONS } from '../../types/discovery';
import {
  eligibleDiscoveryPatterns, selectDiscoveryPattern, resolveDiscoveryCandidate,
  resolveDiscoveryInterpretation,
} from '../governor';
import type { DiscoveryAcquisitionContext } from '../governor';
import { DISCOVERY_PATTERNS, discoveryPatternById } from './registry';

declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;

function acquisition(): DiscoveryAcquisitionContext {
  return {
    confidenceByDimension: {}, askedPatternIds: [], remainingAcquisitions: 3,
    availableCandidateActionIds: DISCOVERY_PATTERNS.flatMap(pattern => pattern.choices.map(choice => choice.candidateAction.id)),
  };
}

test('covered dimensions collapse and ranking does not follow question numbering', () => {
  const state = createInitialJourneyState();
  const context = acquisition();
  context.confidenceByDimension.GOAL_DISCOVERY = 0.95;
  const choices = eligibleDiscoveryPatterns(state, context);
  expect(choices.some(pattern => pattern.dimension === 'GOAL_DISCOVERY')).toBe(false);
  expect(choices.findIndex(pattern => pattern.id === 'NOC_18')).toBeLessThan(choices.findIndex(pattern => pattern.id === 'NOC_03'));
  context.askedPatternIds = choices.map(pattern => pattern.id);
  expect(selectDiscoveryPattern(state, context)).toBeNull();
});

test('budget, interruption, pending interaction and missing action bindings prevent questions', () => {
  const state = createInitialJourneyState();
  const context = acquisition();
  context.remainingAcquisitions = 0;
  expect(selectDiscoveryPattern(state, context)).toBeNull();
  context.remainingAcquisitions = Number.NaN;
  expect(selectDiscoveryPattern(state, context)).toBeNull();
  context.remainingAcquisitions = 3;
  state.interruptionState.isInterrupted = true;
  expect(selectDiscoveryPattern(state, context)).toBeNull();
  state.interruptionState.isInterrupted = false;
  state.interaction.pendingQuestionId = 'discovery-or-guidance';
  expect(selectDiscoveryPattern(state, context)).toBeNull();
  state.interaction.pendingQuestionId = null;
  context.availableCandidateActionIds = [];
  expect(selectDiscoveryPattern(state, context)).toBeNull();
});

test('commercial fit and commitment cannot skip required coverage', () => {
  const state = createInitialJourneyState();
  const context = acquisition();
  expect(eligibleDiscoveryPatterns(state, context).some(pattern => ['NOC_46', 'NOC_47', 'NOC_50'].includes(pattern.id))).toBe(false);
  for (const dimension of discoveryPatternById('NOC_50')!.requiredDimensions) context.confidenceByDimension[dimension] = 0.9;
  expect(eligibleDiscoveryPatterns(state, context).some(pattern => pattern.id === 'NOC_50')).toBe(true);
  for (const dimension of DISCOVERY_DIMENSIONS) context.confidenceByDimension[dimension] = 1;
  expect(selectDiscoveryPattern(state, context)).toBeNull();
});

test('candidate resolution is bound to the pending question and exact existing tour position', () => {
  const state = createInitialJourneyState();
  const context = acquisition();
  state.interaction.pendingQuestionId = 'NOC_01';
  state.interaction.eligibleDestinationScope = {
    questionId: 'NOC_01', stage: state.stage, chapterId: state.currentChapterId, stopId: state.currentStopId,
  };
  expect(resolveDiscoveryCandidate(state, 'GUIDANCE', context)?.id).toBe('EXPLAIN:GUIDANCE');
  expect(resolveDiscoveryCandidate(state, 'SITE_SCAN', context)).toBeNull();
  const response = 'guidance';
  const interpretation = { patternId: 'NOC_01', categories: [{ semanticOutput: 'GUIDANCE', confidence: 0.9, supportingExcerpt: response }] };
  expect(resolveDiscoveryInterpretation(state, response, interpretation, context)?.topic).toBe('GUIDANCE');
  expect(resolveDiscoveryInterpretation(state, response, { ...interpretation, categories: [{ ...interpretation.categories[0], confidence: 0.4 }] }, context)).toBeNull();
  expect(resolveDiscoveryInterpretation(state, 'guidance support', { ...interpretation, categories: [...interpretation.categories, { semanticOutput: 'SUPPORT', confidence: 0.9, supportingExcerpt: 'support' }] }, context)).toBeNull();
  state.currentStopId = 'stop-how-to-talk';
  expect(resolveDiscoveryCandidate(state, 'GUIDANCE', context)).toBeNull();
  state.currentStopId = state.interaction.eligibleDestinationScope.stopId;
  state.stage = 'ONBOARDING';
  expect(resolveDiscoveryCandidate(state, 'GUIDANCE', context)).toBeNull();
  state.stage = 'LANDING_TOUR';
  context.availableCandidateActionIds = [];
  expect(resolveDiscoveryCandidate(state, 'GUIDANCE', context)).toBeNull();
});

test('a next-step preference stays a consent-requiring candidate rather than executing a scan', () => {
  const state = createInitialJourneyState();
  const context = acquisition();
  for (const dimension of discoveryPatternById('NOC_50')!.requiredDimensions) context.confidenceByDimension[dimension] = 0.9;
  state.interaction.pendingQuestionId = 'NOC_50';
  state.interaction.eligibleDestinationScope = {
    questionId: 'NOC_50', stage: state.stage, chapterId: state.currentChapterId, stopId: state.currentStopId,
  };
  const before = JSON.stringify(state);
  expect(resolveDiscoveryCandidate(state, 'SITE_SCAN', context)).toMatchObject({ kind: 'REQUEST_SITE_SCAN', requiresExplicitConsent: true });
  expect(JSON.stringify(state)).toBe(before);
});
