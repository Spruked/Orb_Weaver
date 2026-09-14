import { createInitialJourneyState } from '../state/tourControllerStore';
import {
  AGENCY_SESSION_CACHE_KEY,
  activeAgencyExcursion,
  beginAgencyExcursion,
  consumeAgencyExcursionReturn,
  markAgencyExcursionArrived,
  patchAgencySessionCache,
  readAgencySessionCache,
  rememberAgencyEvidence,
} from './agencySessionCache';

declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;

class MemoryStorage implements Pick<Storage, 'getItem' | 'setItem' | 'removeItem'> {
  private values = new Map<string, string>();
  getItem(key: string) { return this.values.get(key) ?? null; }
  setItem(key: string, value: string) { this.values.set(key, value); }
  removeItem(key: string) { this.values.delete(key); }
}

test('short-term cache survives a governed excursion and consumes the return contract once', () => {
  const storage = new MemoryStorage();
  const state = createInitialJourneyState();
  const contract = beginAgencyExcursion({
    candidateId: 'move:navigate:lidar',
    boundedSetRevision: 'set:4',
    purpose: 'Demonstrate verified LiDAR guidance.',
    origin: { stage: state.stage, chapterId: state.currentChapterId, stopId: state.currentStopId, route: '/' },
    destinationRoute: '/lidar-guidance',
    semanticDestination: 'destination:lidar',
  }, storage);
  expect(contract).not.toBeNull();
  state.interaction.activeDestinationRoute = '/lidar-guidance';
  const arrived = markAgencyExcursionArrived('/lidar-guidance', state, storage);
  expect(arrived?.status).toBe('ACTIVE');
  const resumed = consumeAgencyExcursionReturn(arrived!.excursionId, '/lidar-guidance', state, storage);
  expect(resumed?.origin.route).toBe('/');
  expect(activeAgencyExcursion(storage)).toBeNull();
  expect(consumeAgencyExcursionReturn(arrived!.excursionId, '/lidar-guidance', state, storage)).toBeNull();
});

test('cached excursion cannot authorize return after governed position changes', () => {
  const storage = new MemoryStorage();
  const state = createInitialJourneyState();
  beginAgencyExcursion({
    candidateId: 'move:navigate:lidar', boundedSetRevision: 'set:4', purpose: 'LiDAR demo',
    origin: { stage: state.stage, chapterId: state.currentChapterId, stopId: state.currentStopId, route: '/' },
    destinationRoute: '/lidar-guidance', semanticDestination: 'destination:lidar',
  }, storage);
  state.interaction.activeDestinationRoute = '/lidar-guidance';
  const arrived = markAgencyExcursionArrived('/lidar-guidance', state, storage)!;
  state.currentStopId = 'stop-how-to-talk';
  expect(consumeAgencyExcursionReturn(arrived.excursionId, '/lidar-guidance', state, storage)).toBeNull();
  expect(activeAgencyExcursion(storage)?.excursionId).toBe(arrived.excursionId);
});

test('working cache remains bounded and rejects corrupted authority-like state', () => {
  const storage = new MemoryStorage();
  patchAgencySessionCache({ visitorContext: 'x'.repeat(4000), boundedSetRevision: 'set:9', activeCandidateId: 'move:explain' }, storage);
  for (let index = 0; index < 30; index += 1) rememberAgencyEvidence(`evidence-${index}`, storage);
  const cache = readAgencySessionCache(storage);
  expect(cache.visitorContext.length).toBe(1500);
  expect(cache.recentEvidenceIds.length).toBe(16);
  expect(cache.recentEvidenceIds[0]).toBe('evidence-14');
  storage.setItem(AGENCY_SESSION_CACHE_KEY, JSON.stringify({ version: 1, visitorContext: '', boundedSetRevision: null, activeCandidateId: null,
    recentEvidenceIds: [], excursions: [{ origin: { route: 'https://evil.test/' } }], updatedAt: Date.now() }));
  expect(readAgencySessionCache(storage).excursions).toEqual([]);
});

test('stale short-term cache expires instead of resuming an abandoned excursion', () => {
  const storage = new MemoryStorage();
  storage.setItem(AGENCY_SESSION_CACHE_KEY, JSON.stringify({
    version: 1,
    visitorContext: 'old visitor context',
    boundedSetRevision: 'old:set',
    activeCandidateId: 'move:old',
    recentEvidenceIds: ['evidence-old'],
    excursions: [],
    updatedAt: Date.now() - (31 * 60 * 1000),
  }));
  const cache = readAgencySessionCache(storage);
  expect(cache.visitorContext).toBe('');
  expect(cache.activeCandidateId).toBeNull();
  expect(storage.getItem(AGENCY_SESSION_CACHE_KEY)).toBeNull();
});
