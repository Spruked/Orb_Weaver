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

test('the sales journey uses a natural ORIENT turn then a legal Nine-of-Clubs DISCOVER question', async () => {
  document.body.innerHTML = '<main><section id="beat-1">Current site content</section></main>';
  let state = createInitialJourneyState();
  const chosen: any[][] = [];
  const speech: string[] = [];
  const cognition = jest.spyOn(api, 'websiteOrbAgency').mockImplementation(async (operation: string, payload: any) => {
    if (operation === 'observe') return { event_id: 'evidence-sales', source: payload.source };
    if (operation === 'compile_question') throw new Error('Use the validated canonical fallback');
    chosen.push(payload.candidates);
    return { result: { selected_candidate_id: payload.candidates[0].candidate_id }, source: 'test-provider' };
  });
  const text = jest.spyOn(api, 'websiteOrbText').mockResolvedValue({
    spoken_output: 'Orb Weaver helps a business guide visitors toward the right next step with relevant website help.',
    tts_audio_url: '/orientation.wav',
  });
  const tts = jest.spyOn(api, 'websiteOrbTts').mockResolvedValue({ tts_audio_url: '/question.wav', tts_provider: 'test' });
  try {
    const runtime = createTourAgencyRuntime({
      read: () => state, save: next => { state = next; }, pointers: () => [], capsule: () => null,
      targetUrl: () => 'https://example.test/', worldRevision: () => 1,
      speak: async value => { speech.push(value); return true; }, guide: async () => false,
      navigate: () => { throw new Error('Task 1 does not authorize routing'); }, telemetry: () => undefined,
    });
    expect(await runtime.beginSalesJourney(new AbortController().signal)).toBe('awaiting_visitor');
    expect(state.salesPhase).toBe('DISCOVER');
    expect(state.interaction.pendingQuestionId).toMatch(/^NOC_\d{2}$/);
    expect(chosen).toHaveLength(2);
    expect(chosen[0]).toEqual([expect.objectContaining({ cognitive_action: 'EXPLAIN' })]);
    expect(chosen[0][0].pattern_id).toBeUndefined();
    expect(chosen[1].every(candidate => candidate.pattern_id && candidate.cognitive_action === 'REFINE')).toBe(true);
    expect(speech).toHaveLength(2);
    expect(text).toHaveBeenCalledWith(expect.stringContaining('outcome-focused orientation'), true, expect.anything(), expect.objectContaining({
      experience: expect.objectContaining({ phase: 'orientation' }),
    }));
    expect(state.completedTourConceptIds).toEqual([]);
    expect(state.currentStopId).toBe('stop-hero-meet');
  } finally { cognition.mockRestore(); text.mockRestore(); tts.mockRestore(); }
});

test('sales startup preserves its phase across cancellation, retries, and duplicate callbacks', async () => {
  window.sessionStorage.clear();
  document.body.innerHTML = '<main><section id="beat-1">Website outcomes</section></main>';
  let state = createInitialJourneyState();
  let controller = new AbortController();
  let cancelSpeech = true;
  const phases: string[] = [];
  const cognition = jest.spyOn(api, 'websiteOrbAgency').mockImplementation(async (operation: string, payload: any) => {
    if (operation === 'observe') return { event_id: 'sales-evidence' };
    if (operation === 'compile_question') return { result: {
      patternId: payload.pattern.id,
      choices: payload.pattern.choices.map((choice: any) => ({ semanticOutput: choice.semanticOutput, label: choice.fallbackLabel })),
    } };
    phases.push(state.salesPhase);
    return { result: { selected_candidate_id: payload.candidates[0].candidate_id } };
  });
  const text = jest.spyOn(api, 'websiteOrbText').mockResolvedValue({ spoken_output: 'Help visitors complete their next step.', tts_audio_url: '/orient.wav' });
  const tts = jest.spyOn(api, 'websiteOrbTts').mockResolvedValue({ tts_audio_url: '/question.wav' });
  const runtime = createTourAgencyRuntime({
    read: () => state, save: next => { state = next; }, pointers: () => [], capsule: () => null,
    targetUrl: () => 'https://example.test/', worldRevision: () => 1,
    speak: async () => {
      // Re-entry must not reset the in-flight orientation mode.
      expect(await runtime.beginSalesJourney(controller.signal)).toBe('awaiting_visitor');
      if (cancelSpeech) controller.abort();
      return true;
    },
    guide: async () => false, navigate: jest.fn(), telemetry: jest.fn(),
  });
  try {
    await expect(runtime.beginSalesJourney(controller.signal)).rejects.toMatchObject({ name: 'AbortError' });
    expect(state.salesPhase).toBe('ORIENT');
    expect(state.interaction.pendingQuestionId).toBeNull();
    controller = new AbortController();
    cancelSpeech = false;
    expect(await runtime.beginSalesJourney(controller.signal)).toBe('awaiting_visitor');
    expect(phases).toEqual(['ORIENT', 'ORIENT', 'DISCOVER']);
    expect(state.salesPhase).toBe('DISCOVER');
    const calls = cognition.mock.calls.length;
    await runtime.beginSalesJourney(controller.signal);
    expect(cognition.mock.calls).toHaveLength(calls); // Pending question is not repeated.
    expect(state.interaction.recentWeaverStatements).toContain('Help visitors complete their next step.');
  } finally { cognition.mockRestore(); text.mockRestore(); tts.mockRestore(); }
});

test('sales conversation does not depend on a legacy section, while lifecycle and pending work remain enforced', async () => {
  window.sessionStorage.clear();
  document.body.innerHTML = '';
  let state = createInitialJourneyState();
  const telemetry = jest.fn();
  const cognition = jest.spyOn(api, 'websiteOrbAgency').mockImplementation(async (operation: string, payload: any) => {
    if (operation === 'observe') return { event_id: 'sales-evidence' };
    if (operation === 'compile_question') throw new Error('Use canonical fallback');
    return { result: { selected_candidate_id: payload.candidates[0].candidate_id } };
  });
  const text = jest.spyOn(api, 'websiteOrbText').mockResolvedValue({ spoken_output: 'Weaver helps visitors reach the right next step.', tts_audio_url: '/orient.wav' });
  const tts = jest.spyOn(api, 'websiteOrbTts').mockResolvedValue({ tts_audio_url: '/question.wav' });
  const speak = jest.fn().mockResolvedValue(true);
  const runtime = createTourAgencyRuntime({
    read: () => state, save: next => { state = next; }, pointers: () => [], capsule: () => null,
    targetUrl: () => 'https://example.test/', worldRevision: () => 1,
    speak, guide: async () => false, navigate: jest.fn(), telemetry,
  });
  try {
    const signal = new AbortController().signal;
    expect(await runtime.beginSalesJourney(signal)).toBe('awaiting_visitor');
    expect(state.salesPhase).toBe('DISCOVER');
    expect(state.interaction.pendingQuestionId).toMatch(/^NOC_\d{2}$/);
    expect(speak).toHaveBeenCalledTimes(2);
    const callsAfterSalesStart = cognition.mock.calls.length;
    for (const stage of ['PREFLIGHT', 'ONBOARDING', 'PRODUCTION_SCAN'] as const) {
      state = { ...createInitialJourneyState(), stage };
      expect(await runtime.beginSalesJourney(signal)).toBe('continue');
    }
    state = createInitialJourneyState();
    state.interruptionState.isInterrupted = true;
    expect(await runtime.beginSalesJourney(signal)).toBe('continue');
    state = createInitialJourneyState();
    state.interaction.pendingQuestionId = 'NOC_01';
    expect(await runtime.beginSalesJourney(signal)).toBe('awaiting_visitor');
    expect(cognition.mock.calls).toHaveLength(callsAfterSalesStart);
    expect(telemetry).not.toHaveBeenCalledWith('sales_turn_no_legal_candidate', expect.anything());
  } finally { cognition.mockRestore(); text.mockRestore(); tts.mockRestore(); }
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

test('stop-how-to-talk completes once with hands-free proof and hands its next interaction to the governed agency', async () => {
  let state = createInitialJourneyState();
  state.currentStopId = 'stop-how-to-talk';
  const controller = new AbortController();
  let converseCalls = 0;
  let agencyCalls = 0;
  const result = await runTourController({
    read: () => state, save: next => { state = next; }, verifySection: async () => true, demonstrate: async () => true,
    converse: async (_chapter, _stop, missing) => {
      converseCalls += 1;
      expect(missing.map(concept => concept.id)).toEqual(['PRESENCE_AND_CONTROL', 'VERIFIED_GUIDANCE']);
      const speech = 'Speak naturally, hands-free. You remain in control of the interaction. When pointing is useful, I guide only to a verified target and ping the exact place I can prove is live.';
      return { spoken_output: speech, covered_concepts: missing.map(concept => ({ concept_id: concept.id, supporting_excerpt: speech })) };
    },
    agency: async (_chapter, stop) => {
      agencyCalls += 1;
      expect(stop.id).toBe('stop-how-to-talk');
      return 'awaiting_visitor';
    },
  }, controller.signal);
  expect(result).toBe('awaiting_visitor');
  expect(converseCalls).toBe(1);
  expect(agencyCalls).toBe(1);
  expect(state.completedTourConceptIds).toEqual(expect.arrayContaining(['PRESENCE_AND_CONTROL', 'VERIFIED_GUIDANCE']));
});
