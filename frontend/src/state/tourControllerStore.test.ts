import {
  createInitialJourneyState, isProductionScanUnlocked, loadJourneyState,
  migrateStoredJourneyState, migrateWebsiteJourneyV1ToV2, saveJourneyState,
  WEBSITE_JOURNEY_STORAGE_KEY, WebsiteJourneyStateV1,
} from './tourControllerStore';

declare const describe: (name: string, suite: () => void) => void;
declare const it: (name: string, test: () => void) => void;
declare const expect: any;

const legacy = (patch: Partial<WebsiteJourneyStateV1> = {}): WebsiteJourneyStateV1 => ({
  version: 1, stage: 'LANDING_TOUR', nextSegmentIndex: 0, currentSegment: null, ...patch,
});
function memoryStorage(value: string | null = null) {
  const data = new Map<string, string>();
  if (value !== null) data.set(WEBSITE_JOURNEY_STORAGE_KEY, value);
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, next: string) => { data.set(key, next); },
  };
}

describe('tour controller migration and persistence', () => {
  it('creates independent mutable initial states', () => {
    const first = createInitialJourneyState();
    first.completedTourConceptIds.push('test');
    first.interruptionState.isInterrupted = true;
    expect(createInitialJourneyState().completedTourConceptIds).toEqual([]);
    expect(createInitialJourneyState().interruptionState.isInterrupted).toBe(false);
  });

  it('maps only known opening evidence and infers no accomplishments', () => {
    expect(migrateWebsiteJourneyV1ToV2(legacy())).toEqual(createInitialJourneyState());
    expect(migrateWebsiteJourneyV1ToV2(legacy({ currentSegment: 'opening' }))).toEqual(createInitialJourneyState());
  });

  it('preserves every unmapped legacy position byte-for-byte', () => {
    const segments = ['host_proof', 'relationships', 'website_orb', 'weave', 'preflight'] as const;
    segments.forEach((segment, offset) => {
      [legacy({ currentSegment: segment, nextSegmentIndex: offset + 1 }),
        legacy({ currentSegment: null, nextSegmentIndex: offset + 1 })].forEach((value) => {
        const raw = JSON.stringify(value);
        const storage = memoryStorage(raw);
        expect(migrateWebsiteJourneyV1ToV2(value)).toBeNull();
        expect(loadJourneyState(storage).status).toBe('needs_mapping');
        expect(migrateStoredJourneyState(storage).status).toBe('needs_mapping');
        expect(saveJourneyState(createInitialJourneyState(), storage)).toBe(false);
        expect(storage.getItem(WEBSITE_JOURNEY_STORAGE_KEY)).toBe(raw);
      });
    });
  });

  it('does not reset an exhausted landing sequence or pending navigation', () => {
    for (const stage of ['LANDING_TOUR', 'PREFLIGHT_PENDING'] as const) {
      expect(migrateWebsiteJourneyV1ToV2(legacy({ stage, nextSegmentIndex: 6 }))).toBeNull();
    }
  });

  it('preserves Preflight route arrival without claiming scan progress', () => {
    const state = migrateWebsiteJourneyV1ToV2(legacy({ stage: 'PREFLIGHT', nextSegmentIndex: 6 }));
    expect(state).toEqual({ ...createInitialJourneyState(), stage: 'PREFLIGHT', currentChapterId: null, currentStopId: null });
  });

  it('reads V1 without writes and only converts on explicit cutover', () => {
    const raw = JSON.stringify(legacy());
    const storage = memoryStorage(raw);
    expect(loadJourneyState(storage).status).toBe('migrated');
    expect(storage.getItem(WEBSITE_JOURNEY_STORAGE_KEY)).toBe(raw);
    expect(migrateStoredJourneyState(storage).status).toBe('migrated');
    expect(loadJourneyState(storage)).toEqual({ status: 'loaded', state: createInitialJourneyState() });
    expect(migrateStoredJourneyState(storage).status).toBe('loaded');
  });

  it('round-trips V2 facts while removing conversation and derived flags', () => {
    const state = createInitialJourneyState();
    state.completedTourConceptIds = ['concept-a'];
    state.currentStopCoveredConceptIds = ['concept-b'];
    state.interruptionState = { isInterrupted: true, interruptedAtChapterId: 'meet-weaver', interruptedAtStopId: 'opening' };
    const storage = memoryStorage();
    expect(saveJourneyState({ ...state, productionScanUnlocked: true,
      interruptionState: { ...state.interruptionState, visitorQuestion: 'private utterance' },
    } as typeof state, storage)).toBe(true);
    expect(loadJourneyState(storage)).toEqual({ status: 'loaded', state });
    expect(storage.getItem(WEBSITE_JOURNEY_STORAGE_KEY)).not.toMatch(/private utterance|visitorQuestion|productionScanUnlocked/);
  });

  it('clears current landing location after leaving the curriculum', () => {
    const storage = memoryStorage();
    expect(saveJourneyState({ ...createInitialJourneyState(), stage: 'ONBOARDING', currentStopCoveredConceptIds: ['old'] }, storage)).toBe(true);
    const result = loadJourneyState(storage);
    expect(result.state?.currentChapterId).toBeNull();
    expect(result.state?.currentStopId).toBeNull();
    expect(result.state?.currentStopCoveredConceptIds).toEqual([]);
  });

  it('preserves corrupt, unknown-version, and malformed stored state', () => {
    for (const raw of ['{', 'null', '{"version":3}', JSON.stringify({ ...createInitialJourneyState(), accountCreated: 'true' }), JSON.stringify(legacy({ nextSegmentIndex: -1 }))]) {
      const storage = memoryStorage(raw);
      expect(migrateStoredJourneyState(storage).state).toBeNull();
      expect(saveJourneyState(createInitialJourneyState(), storage)).toBe(false);
      expect(storage.getItem(WEBSITE_JOURNEY_STORAGE_KEY)).toBe(raw);
    }
  });

  it('handles unavailable storage without throwing', () => {
    const storage = { getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); } };
    expect(loadJourneyState(storage).status).toBe('storage_unavailable');
    expect(saveJourneyState(createInitialJourneyState(), storage)).toBe(false);
    const writeBlocked = { getItem: () => JSON.stringify(legacy()), setItem: storage.setItem };
    expect(migrateStoredJourneyState(writeBlocked).status).toBe('storage_unavailable');
  });

  it('derives the production gate from both authoritative facts', () => {
    for (const accountCreated of [false, true]) {
      for (const preflightStatus of ['NOT_STARTED', 'DEFERRED', 'RUNNING', 'COMPLETED_UNREVIEWED', 'COMPLETED_REVIEWED'] as const) {
        expect(isProductionScanUnlocked({ ...createInitialJourneyState(), accountCreated, preflightStatus }))
          .toBe(accountCreated && preflightStatus === 'COMPLETED_REVIEWED');
      }
    }
  });
});
