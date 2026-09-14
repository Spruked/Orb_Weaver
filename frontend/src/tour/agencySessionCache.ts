import type { TourJourneyStage, WebsiteJourneyStateV2 } from '../state/tourControllerStore';

/**
 * Mutable, visit-scoped continuity only. This cache is derived state and never
 * grants route/action authority; the Governor and live environment still do that.
 */
export const AGENCY_SESSION_CACHE_KEY = 'orbweaver-agency-short-term-cache-v1';
const MAX_VISITOR_CONTEXT = 1500;
const MAX_EVIDENCE_IDS = 16;
const MAX_EXCURSIONS = 2;
const MAX_SERIALIZED_BYTES = 16000;
const CACHE_TTL_MS = 30 * 60 * 1000;
const TOUR_ROUTE_ALLOWLIST = new Set(['/', '/features', '/lidar-guidance', '/how-it-works', '/preflight']);

export type AgencyExcursionStatus = 'PENDING_ARRIVAL' | 'ACTIVE';

export interface AgencyExcursionContract {
  excursionId: string;
  candidateId: string;
  boundedSetRevision: string;
  purpose: string;
  origin: {
    stage: TourJourneyStage;
    chapterId: string | null;
    stopId: string | null;
    route: string;
  };
  destinationRoute: string;
  semanticDestination: string;
  expectedCompletion: 'VERIFIED_DESTINATION_ACTION';
  status: AgencyExcursionStatus;
  createdAt: number;
}

export interface AgencyShortTermCache {
  version: 1;
  visitorContext: string;
  boundedSetRevision: string | null;
  activeCandidateId: string | null;
  recentEvidenceIds: string[];
  excursions: AgencyExcursionContract[];
  updatedAt: number;
}

type SessionStorageLike = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

const emptyCache = (): AgencyShortTermCache => ({
  version: 1,
  visitorContext: '',
  boundedSetRevision: null,
  activeCandidateId: null,
  recentEvidenceIds: [],
  excursions: [],
  updatedAt: Date.now(),
});

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);
const boundedString = (value: unknown, max = 500): value is string =>
  typeof value === 'string' && value.length > 0 && value.length <= max;
const nullableBoundedString = (value: unknown, max = 500): value is string | null =>
  value === null || boundedString(value, max);
const validRoute = (value: unknown): value is string =>
  typeof value === 'string' && TOUR_ROUTE_ALLOWLIST.has(value);
const validStage = (value: unknown): value is TourJourneyStage =>
  typeof value === 'string' && ['LANDING_TOUR', 'PREFLIGHT', 'ONBOARDING', 'PRODUCTION_SCAN'].includes(value);

const normalizeExcursion = (value: unknown): AgencyExcursionContract | null => {
  if (!isRecord(value) || !boundedString(value.excursionId, 240) || !boundedString(value.candidateId, 240) ||
    !boundedString(value.boundedSetRevision, 240) || !boundedString(value.purpose, 800) || !isRecord(value.origin) ||
    !validStage(value.origin.stage) || !nullableBoundedString(value.origin.chapterId, 240) ||
    !nullableBoundedString(value.origin.stopId, 240) || !validRoute(value.origin.route) ||
    !validRoute(value.destinationRoute) || !boundedString(value.semanticDestination, 240) ||
    value.expectedCompletion !== 'VERIFIED_DESTINATION_ACTION' ||
    !['PENDING_ARRIVAL', 'ACTIVE'].includes(String(value.status)) ||
    typeof value.createdAt !== 'number' || !Number.isFinite(value.createdAt) || value.createdAt <= 0) return null;
  return {
    excursionId: value.excursionId,
    candidateId: value.candidateId,
    boundedSetRevision: value.boundedSetRevision,
    purpose: value.purpose,
    origin: {
      stage: value.origin.stage as TourJourneyStage,
      chapterId: value.origin.chapterId as string | null,
      stopId: value.origin.stopId as string | null,
      route: value.origin.route,
    },
    destinationRoute: value.destinationRoute,
    semanticDestination: value.semanticDestination,
    expectedCompletion: 'VERIFIED_DESTINATION_ACTION',
    status: value.status as AgencyExcursionStatus,
    createdAt: value.createdAt,
  };
};

const normalizeCache = (value: unknown): AgencyShortTermCache | null => {
  if (!isRecord(value) || value.version !== 1 || typeof value.visitorContext !== 'string' ||
    value.visitorContext.length > MAX_VISITOR_CONTEXT ||
    !nullableBoundedString(value.boundedSetRevision, 240) || !nullableBoundedString(value.activeCandidateId, 240) ||
    !Array.isArray(value.recentEvidenceIds) || value.recentEvidenceIds.length > MAX_EVIDENCE_IDS ||
    !value.recentEvidenceIds.every(item => boundedString(item, 240)) || !Array.isArray(value.excursions) ||
    value.excursions.length > MAX_EXCURSIONS || typeof value.updatedAt !== 'number' || !Number.isFinite(value.updatedAt) ||
    value.updatedAt <= 0) return null;
  const excursions = value.excursions.map(normalizeExcursion);
  if (excursions.some(item => item === null)) return null;
  return {
    version: 1,
    visitorContext: value.visitorContext,
    boundedSetRevision: value.boundedSetRevision as string | null,
    activeCandidateId: value.activeCandidateId as string | null,
    recentEvidenceIds: [...new Set(value.recentEvidenceIds as string[])].slice(-MAX_EVIDENCE_IDS),
    excursions: excursions as AgencyExcursionContract[],
    updatedAt: value.updatedAt,
  };
};

const defaultStorage = (): SessionStorageLike | null => {
  try { return window.sessionStorage; } catch { return null; }
};

export function readAgencySessionCache(storage: SessionStorageLike | null = defaultStorage()): AgencyShortTermCache {
  if (!storage) return emptyCache();
  try {
    const raw = storage.getItem(AGENCY_SESSION_CACHE_KEY);
    if (!raw) return emptyCache();
    const normalized = normalizeCache(JSON.parse(raw));
    if (!normalized) return emptyCache();
    const age = Date.now() - normalized.updatedAt;
    if (age > CACHE_TTL_MS || age < -60_000) {
      storage.removeItem(AGENCY_SESSION_CACHE_KEY);
      return emptyCache();
    }
    return normalized;
  } catch { return emptyCache(); }
}

export function writeAgencySessionCache(cache: AgencyShortTermCache, storage: SessionStorageLike | null = defaultStorage()): boolean {
  if (!storage) return false;
  const normalized = normalizeCache({ ...cache, updatedAt: Date.now() });
  if (!normalized) return false;
  const serialized = JSON.stringify(normalized);
  // Match agencyBudget.ts: Blob gives UTF-8 byte size in browser/jsdom without
  // depending on TextEncoder being present in every Jest environment.
  if (new Blob([serialized]).size > MAX_SERIALIZED_BYTES) return false;
  try { storage.setItem(AGENCY_SESSION_CACHE_KEY, serialized); return true; } catch { return false; }
}

export function patchAgencySessionCache(
  patch: Partial<Pick<AgencyShortTermCache, 'visitorContext' | 'boundedSetRevision' | 'activeCandidateId'>>,
  storage: SessionStorageLike | null = defaultStorage(),
): AgencyShortTermCache {
  const current = readAgencySessionCache(storage);
  const next: AgencyShortTermCache = {
    ...current,
    ...patch,
    visitorContext: String(patch.visitorContext ?? current.visitorContext).slice(-MAX_VISITOR_CONTEXT),
    updatedAt: Date.now(),
  };
  writeAgencySessionCache(next, storage);
  return readAgencySessionCache(storage);
}

export function rememberAgencyEvidence(eventId: string, storage: SessionStorageLike | null = defaultStorage()): void {
  if (!boundedString(eventId, 240)) return;
  const current = readAgencySessionCache(storage);
  writeAgencySessionCache({
    ...current,
    recentEvidenceIds: [...new Set([...current.recentEvidenceIds, eventId])].slice(-MAX_EVIDENCE_IDS),
    updatedAt: Date.now(),
  }, storage);
}

export function activeAgencyExcursion(storage: SessionStorageLike | null = defaultStorage()): AgencyExcursionContract | null {
  const cache = readAgencySessionCache(storage);
  return cache.excursions.length ? cache.excursions[cache.excursions.length - 1] : null;
}

export function beginAgencyExcursion(
  input: Omit<AgencyExcursionContract, 'excursionId' | 'expectedCompletion' | 'status' | 'createdAt'>,
  storage: SessionStorageLike | null = defaultStorage(),
): AgencyExcursionContract | null {
  if (!validRoute(input.origin.route) || !validRoute(input.destinationRoute) || input.origin.route === input.destinationRoute) return null;
  const contract: AgencyExcursionContract = {
    ...input,
    excursionId: `${input.candidateId}:${Date.now()}`,
    expectedCompletion: 'VERIFIED_DESTINATION_ACTION',
    status: 'PENDING_ARRIVAL',
    createdAt: Date.now(),
  };
  if (!normalizeExcursion(contract)) return null;
  const current = readAgencySessionCache(storage);
  const next = { ...current, excursions: [...current.excursions, contract].slice(-MAX_EXCURSIONS), updatedAt: Date.now() };
  if (!writeAgencySessionCache(next, storage)) return null;
  return activeAgencyExcursion(storage);
}

export function markAgencyExcursionArrived(
  currentRoute: string,
  state: WebsiteJourneyStateV2,
  storage: SessionStorageLike | null = defaultStorage(),
): AgencyExcursionContract | null {
  const current = readAgencySessionCache(storage);
  const active = current.excursions[current.excursions.length - 1];
  if (!active || active.status !== 'PENDING_ARRIVAL' || currentRoute !== active.destinationRoute ||
    state.stage !== active.origin.stage || state.currentChapterId !== active.origin.chapterId ||
    state.currentStopId !== active.origin.stopId || state.interaction.activeDestinationRoute !== active.destinationRoute) return null;
  const arrived = { ...active, status: 'ACTIVE' as const };
  writeAgencySessionCache({
    ...current,
    excursions: [...current.excursions.slice(0, -1), arrived],
    activeCandidateId: null,
    boundedSetRevision: null,
    updatedAt: Date.now(),
  }, storage);
  return activeAgencyExcursion(storage);
}

/**
 * A cached return path is not authority by itself. It is consumable only while
 * the live journey still matches the governed origin and destination that
 * created it. The contract is removed before the caller performs navigation.
 */
export function consumeAgencyExcursionReturn(
  excursionId: string,
  currentRoute: string,
  state: WebsiteJourneyStateV2,
  storage: SessionStorageLike | null = defaultStorage(),
): AgencyExcursionContract | null {
  const current = readAgencySessionCache(storage);
  const active = current.excursions[current.excursions.length - 1];
  if (!active || active.excursionId !== excursionId || active.status !== 'ACTIVE' ||
    currentRoute !== active.destinationRoute || state.interaction.activeDestinationRoute !== active.destinationRoute ||
    state.stage !== active.origin.stage || state.currentChapterId !== active.origin.chapterId ||
    state.currentStopId !== active.origin.stopId || !validRoute(active.origin.route)) return null;
  writeAgencySessionCache({
    ...current,
    excursions: current.excursions.slice(0, -1),
    boundedSetRevision: null,
    activeCandidateId: null,
    updatedAt: Date.now(),
  }, storage);
  return active;
}

export function clearAgencySessionCache(storage: SessionStorageLike | null = defaultStorage()): void {
  try { storage?.removeItem(AGENCY_SESSION_CACHE_KEY); } catch { /* best effort */ }
}
