import { createInitialJourneyState } from '../state/tourControllerStore';
import { destinationAuthorizationScope, eligibleDestinationsForQuestion, resolveGovernedDestination } from './governor';
import { engagementById } from './interaction';

declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;

test('the governor alone maps a semantic category to the current legal route', () => {
  const state = createInitialJourneyState();
  const question = engagementById('discovery-or-guidance')!;
  state.interaction.eligibleDestinationRoutes = eligibleDestinationsForQuestion(state, question);
  state.interaction.eligibleDestinationScope = destinationAuthorizationScope(state, question);
  expect(state.interaction.eligibleDestinationRoutes).toEqual(['/how-it-works', '/lidar-guidance']);
  expect(resolveGovernedDestination(state, question, 'SITE_DISCOVERY')).toBe('/how-it-works');
  expect(resolveGovernedDestination(state, question, 'VERIFIED_GUIDANCE')).toBe('/lidar-guidance');
});

test('a route cannot be selected when it was not issued by the governor', () => {
  const state = createInitialJourneyState();
  const question = engagementById('discovery-or-guidance')!;
  state.interaction.eligibleDestinationRoutes = ['/lidar-guidance'];
  state.interaction.eligibleDestinationScope = destinationAuthorizationScope(state, question);
  expect(resolveGovernedDestination(state, question, 'SITE_DISCOVERY')).toBeNull();
});

test('an issued route expires when its governing tour position changes', () => {
  const state = createInitialJourneyState();
  const question = engagementById('discovery-or-guidance')!;
  state.interaction.eligibleDestinationRoutes = eligibleDestinationsForQuestion(state, question);
  state.interaction.eligibleDestinationScope = destinationAuthorizationScope(state, question);
  state.currentStopId = 'stop-how-to-talk';
  expect(resolveGovernedDestination(state, question, 'SITE_DISCOVERY')).toBeNull();
});

test('interrupted or deferred states expose no conversational destinations', () => {
  const question = engagementById('discovery-or-guidance')!;
  const interrupted = createInitialJourneyState();
  interrupted.interruptionState = { isInterrupted: true, interruptedAtChapterId: 'chapter-meet-weaver', interruptedAtStopId: 'stop-how-to-talk' };
  expect(eligibleDestinationsForQuestion(interrupted, question)).toEqual([]);
  const deferred = createInitialJourneyState();
  deferred.preflightStatus = 'DEFERRED';
  expect(eligibleDestinationsForQuestion(deferred, question)).toEqual([]);
});
