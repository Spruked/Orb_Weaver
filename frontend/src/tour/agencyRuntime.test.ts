import { webcrypto } from 'crypto';
import { api } from '../services/api';
import { createInitialJourneyState } from '../state/tourControllerStore';
import { createTourAgencyRuntime } from './agencyRuntime';
import { runTourController } from './controller';
import { LANDING_TOUR_CHAPTERS } from './curriculum';

declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;
declare const jest: any;
Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });

test('mounted-tour adapter executes a chosen non-question through speech and records AIMS evidence', async () => {
  document.body.innerHTML = '<main><section id="beat-1">Current site content</section></main>';
  let state = createInitialJourneyState();
  let spoke = 0;
  const observations: any[] = [];
  const cognition = jest.spyOn(api, 'websiteOrbAgency').mockImplementation(async (operation: string, payload: any) => {
    if (operation === 'observe') { observations.push(payload); return { event_id: 'evidence-1', source: payload.source }; }
    expect(payload.candidates.some((candidate: any) => candidate.pattern_id)).toBe(true);
    return { result: { selected_candidate_id: 'move:explain-current' }, source: 'test-provider' };
  });
  const text = jest.spyOn(api, 'websiteOrbText').mockResolvedValue({ spoken_output: 'Here is the relevant detail.', tts_audio_url: '/speech.wav' });
  try {
    const runtime = createTourAgencyRuntime({
      read: () => state, save: next => { state = next; }, pointers: () => [], capsule: () => null,
      targetUrl: () => 'https://example.test/', worldRevision: () => 1,
      speak: async () => { spoke += 1; return true; }, guide: async () => false, navigate: () => { throw new Error('No navigation chosen'); }, telemetry: () => undefined,
    });
    expect(await runtime.turn(new AbortController().signal)).toBe('continue');
    expect(spoke).toBe(1);
    expect(state.interaction.pendingQuestionId).toBeNull();
    expect(observations).toEqual([expect.objectContaining({ candidate_id: 'move:explain-current', source: 'LIVE_BEHAVIOR', outcome: 'completed' })]);
  } finally { cognition.mockRestore(); text.mockRestore(); }
});

test('state movement during cognition blocks speech and navigation before execution', async () => {
  document.body.innerHTML = '<main><section id="beat-1">Content</section></main>';
  const state = createInitialJourneyState();
  const cognition = jest.spyOn(api, 'websiteOrbAgency').mockImplementation(async () => {
    state.currentStopId = 'stop-how-to-talk';
    return { result: { selected_candidate_id: 'move:explain-current' }, source: 'test-provider' };
  });
  try {
    const runtime = createTourAgencyRuntime({ read: () => state, save: () => undefined, pointers: () => [], capsule: () => null,
      targetUrl: () => 'https://example.test/', worldRevision: () => 1,
      speak: async () => { throw new Error('Speech must not execute'); }, guide: async () => false, navigate: () => { throw new Error('Navigation must not execute'); }, telemetry: () => undefined });
    await expect(runtime.turn(new AbortController().signal)).rejects.toThrow('legal context changed');
  } finally { cognition.mockRestore(); }
});

test('the existing scheduler defers question choice to agency after verified stop speech', async () => {
  let state = createInitialJourneyState();
  const controller = new AbortController();
  let agencyCalls = 0;
  const result = await runTourController({
    read: () => state, save: next => { state = next; }, verifySection: async () => true, demonstrate: async () => true,
    converse: async (_chapter, _stop, missing, engagement) => {
      expect(engagement).toBeNull();
      const speech = 'Website ORB host understands this website with verified knowledge and the right place to show and explain.';
      return { spoken_output: speech, covered_concepts: missing.map(concept => ({ concept_id: concept.id, supporting_excerpt: speech })) };
    },
    agency: async (_chapter, stop) => { agencyCalls += 1; expect(stop.id).toBe(LANDING_TOUR_CHAPTERS[0].stops[0].id); return 'awaiting_visitor'; },
  }, controller.signal);
  expect(result).toBe('awaiting_visitor');
  expect(agencyCalls).toBe(1);
  expect(state.completedTourConceptIds).toContain('WEAVER_IDENTITY');
});
