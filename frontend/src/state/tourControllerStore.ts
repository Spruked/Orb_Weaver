import type { TourPreflightStatus } from "../types/tour";

export type TourJourneyStage =
  | "LANDING_TOUR"
  | "PREFLIGHT"
  | "ONBOARDING"
  | "PRODUCTION_SCAN";

export interface InterruptionState {
  isInterrupted: boolean;
  interruptedAtChapterId: string | null;
  interruptedAtStopId: string | null;
}

export interface WebsiteJourneyStateV2 {
  version: 2;
  stage: TourJourneyStage;
  currentChapterId: string | null;
  currentStopId: string | null;
  completedTourConceptIds: string[];
  currentStopCoveredConceptIds: string[];
  interruptionState: InterruptionState;
  preflightStatus: TourPreflightStatus;
  accountCreated: boolean;
}

export function createInitialJourneyState(): WebsiteJourneyStateV2 {
  return {
    version: 2,
    stage: "LANDING_TOUR",
    currentChapterId: "chapter-meet-weaver",
    currentStopId: "stop-hero-meet",
    completedTourConceptIds: [],
    currentStopCoveredConceptIds: [],
    interruptionState: {
      isInterrupted: false,
      interruptedAtChapterId: null,
      interruptedAtStopId: null,
    },
    preflightStatus: "NOT_STARTED",
    accountCreated: false,
  };
}

// Keep the production V1 storage identity. This module has no startup side effects.
export const WEBSITE_JOURNEY_STORAGE_KEY = "orbweaver-website-journey";

const LEGACY_SEGMENTS = [
  "opening", "host_proof", "relationships", "website_orb", "weave", "preflight",
] as const;
export type LegacyTourSegment = typeof LEGACY_SEGMENTS[number];
export interface TourPosition {
  chapterId: string;
  stopId: string;
}
export interface WebsiteJourneyStateV1 {
  version: 1;
  stage: "LANDING_TOUR" | "PREFLIGHT_PENDING" | "PREFLIGHT";
  nextSegmentIndex: number;
  currentSegment: LegacyTourSegment | null;
}

// Expand only when the corresponding canonical curriculum stops exist.
export const LEGACY_V1_POSITION_MAP: Readonly<Partial<Record<LegacyTourSegment, Readonly<TourPosition>>>> = {
  opening: { chapterId: "chapter-meet-weaver", stopId: "stop-hero-meet" },
  host_proof: { chapterId: "chapter-meet-weaver", stopId: "stop-how-to-talk" },
  relationships: { chapterId: "chapter-why-weaving", stopId: "stop-relationships" },
  website_orb: { chapterId: "chapter-trust", stopId: "stop-website-orb-outcome" },
  weave: { chapterId: "chapter-intelligence", stopId: "stop-28-weave" },
  preflight: { chapterId: "chapter-preflight", stopId: "stop-preflight-decision" },
};

// Preserve positional evidence from the superseded four-chapter construction.
// These are compatibility aliases, never active chapters or concept equivalences.
const PRE_TARGET_ONE_POSITIONS: Record<string, TourPosition> = {
  'meet-weaver/opening': { chapterId: 'chapter-meet-weaver', stopId: 'stop-hero-meet' },
  'meet-weaver/interaction': { chapterId: 'chapter-meet-weaver', stopId: 'stop-how-to-talk' },
  'why-weaving-exists/purpose': { chapterId: 'chapter-why-weaving', stopId: 'stop-crawl-vs-weave' },
  'why-weaving-exists/relationships': { chapterId: 'chapter-why-weaving', stopId: 'stop-relationships' },
  'why-weaving-exists/beyond-discovery': { chapterId: 'chapter-why-weaving', stopId: 'stop-relationships' },
  'why-weaving-exists/operational-structure': { chapterId: 'chapter-why-weaving', stopId: 'stop-relationships' },
  'why-weaving-exists/website-orb': { chapterId: 'chapter-trust', stopId: 'stop-website-orb-outcome' },
  'how-orb-weaver-builds/visitor-value': { chapterId: 'chapter-trust', stopId: 'stop-website-orb-outcome' },
  'how-orb-weaver-builds/trust': { chapterId: 'chapter-trust', stopId: 'stop-trust-security' },
  'how-orb-weaver-builds/assembly': { chapterId: 'chapter-intelligence', stopId: 'stop-28-weave' },
  'preflight-gate/preflight': { chapterId: 'chapter-preflight', stopId: 'stop-preflight-decision' },
};

type JourneyStorage = Pick<Storage, "getItem" | "setItem">;
export type JourneyLoadResult =
  | { status: "initial" | "loaded" | "migrated"; state: WebsiteJourneyStateV2 }
  | { status: "needs_mapping" | "invalid" | "unsupported_version" | "storage_unavailable"; state: null };

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
const isId = (value: unknown): value is string =>
  typeof value === "string" && value.trim().length > 0;
const isNullableId = (value: unknown) => value === null || isId(value);
const isIdList = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every(isId);

function normalizeV2(value: Record<string, unknown>): WebsiteJourneyStateV2 | null {
  const interruption = value.interruptionState;
  if (
    typeof value.stage !== "string" ||
    !["LANDING_TOUR", "PREFLIGHT", "ONBOARDING", "PRODUCTION_SCAN"].includes(value.stage) ||
    typeof value.preflightStatus !== "string" ||
    !["NOT_STARTED", "DEFERRED", "RUNNING", "COMPLETED_UNREVIEWED", "COMPLETED_REVIEWED"].includes(value.preflightStatus) ||
    !isNullableId(value.currentChapterId) || !isNullableId(value.currentStopId) ||
    (value.currentChapterId === null) !== (value.currentStopId === null) ||
    !isIdList(value.completedTourConceptIds) || !isIdList(value.currentStopCoveredConceptIds) ||
    typeof value.accountCreated !== "boolean" || !isRecord(interruption) ||
    typeof interruption.isInterrupted !== "boolean" ||
    !isNullableId(interruption.interruptedAtChapterId) || !isNullableId(interruption.interruptedAtStopId) ||
    (interruption.interruptedAtChapterId === null) !== (interruption.interruptedAtStopId === null)
  ) return null;
  // Explicit projection excludes utterances, derived flags, and unknown fields.
  const state = createInitialJourneyState();
  state.stage = value.stage as TourJourneyStage;
  state.currentChapterId = state.stage === "LANDING_TOUR" ? value.currentChapterId as string | null : null;
  state.currentStopId = state.stage === "LANDING_TOUR" ? value.currentStopId as string | null : null;
  state.completedTourConceptIds = [...new Set(value.completedTourConceptIds)];
  state.currentStopCoveredConceptIds = state.stage === "LANDING_TOUR" ? [...new Set(value.currentStopCoveredConceptIds)] : [];
  state.interruptionState = {
    isInterrupted: interruption.isInterrupted,
    interruptedAtChapterId: interruption.interruptedAtChapterId as string | null,
    interruptedAtStopId: interruption.interruptedAtStopId as string | null,
  };
  const mappedPosition = PRE_TARGET_ONE_POSITIONS[`${state.currentChapterId}/${state.currentStopId}`];
  if (state.stage === 'LANDING_TOUR' && mappedPosition) {
    state.currentChapterId = mappedPosition.chapterId;
    state.currentStopId = mappedPosition.stopId;
    // Earlier taxonomy is not evidence of Target One concept coverage.
    state.completedTourConceptIds = [];
    state.currentStopCoveredConceptIds = [];
  }
  const interruptedPosition = PRE_TARGET_ONE_POSITIONS[`${state.interruptionState.interruptedAtChapterId}/${state.interruptionState.interruptedAtStopId}`];
  if (interruptedPosition) {
    state.interruptionState.interruptedAtChapterId = interruptedPosition.chapterId;
    state.interruptionState.interruptedAtStopId = interruptedPosition.stopId;
  }
  state.preflightStatus = value.preflightStatus as TourPreflightStatus;
  state.accountCreated = value.accountCreated;
  return state;
}

export function migrateJourneyState(value: unknown): JourneyLoadResult {
  if (!isRecord(value)) return { status: "invalid", state: null };
  if (value.version === 2) {
    const state = normalizeV2(value);
    return state ? { status: "loaded", state } : { status: "invalid", state: null };
  }
  if (value.version !== 1) return { status: "unsupported_version", state: null };
  if (
    typeof value.stage !== "string" ||
    !["LANDING_TOUR", "PREFLIGHT_PENDING", "PREFLIGHT"].includes(value.stage) ||
    typeof value.nextSegmentIndex !== "number" || !Number.isInteger(value.nextSegmentIndex) ||
    value.nextSegmentIndex < 0 || value.nextSegmentIndex > LEGACY_SEGMENTS.length ||
    (value.currentSegment !== null && !LEGACY_SEGMENTS.includes(value.currentSegment as LegacyTourSegment))
  ) return { status: "invalid", state: null };

  const state = createInitialJourneyState();
  if (value.stage === "PREFLIGHT") {
    state.stage = "PREFLIGHT";
    state.currentChapterId = null;
    state.currentStopId = null;
  } else {
    // Pending navigation becomes a landing decision position, never a scan action.
    const segment = value.stage === "PREFLIGHT_PENDING" ? "preflight" :
      (value.currentSegment as LegacyTourSegment | null) ||
      LEGACY_SEGMENTS[Math.min(value.nextSegmentIndex, LEGACY_SEGMENTS.length - 1)];
    const position = LEGACY_V1_POSITION_MAP[segment];
    if (!position || !isId(position.chapterId) || !isId(position.stopId)) {
      return { status: "needs_mapping", state: null };
    }
    state.currentChapterId = position.chapterId;
    state.currentStopId = position.stopId;
  }
  // V1 has no concept, interruption, account, or scan-completion evidence.
  return { status: "migrated", state };
}

/** Read/migrate in memory only: the existing V1 reader can continue unchanged. */
export function loadJourneyState(storage?: JourneyStorage): JourneyLoadResult {
  try {
    const raw = (storage || window.sessionStorage).getItem(WEBSITE_JOURNEY_STORAGE_KEY);
    if (raw === null) return { status: "initial", state: createInitialJourneyState() };
    let value: unknown;
    try { value = JSON.parse(raw); } catch { return { status: "invalid", state: null }; }
    return migrateJourneyState(value);
  } catch {
    return { status: "storage_unavailable", state: null };
  }
}

/** For the future V2 owner. Refuse to silently overwrite an existing V1 session. */
export function saveJourneyState(state: WebsiteJourneyStateV2, storage?: JourneyStorage): boolean {
  try {
    const target = storage || window.sessionStorage;
    const existing = target.getItem(WEBSITE_JOURNEY_STORAGE_KEY);
    if (existing !== null && migrateJourneyState(JSON.parse(existing)).status !== "loaded") return false;
    const result = migrateJourneyState(state);
    if (result.status !== "loaded") return false;
    target.setItem(WEBSITE_JOURNEY_STORAGE_KEY, JSON.stringify(result.state));
    return true;
  } catch { return false; }
}

/** Explicit cutover only, after the V1 reader is retired. Never called on import. */
export function migrateStoredJourneyState(storage?: JourneyStorage): JourneyLoadResult {
  const result = loadJourneyState(storage);
  if (result.status !== "migrated") return result;
  try {
    (storage || window.sessionStorage).setItem(WEBSITE_JOURNEY_STORAGE_KEY, JSON.stringify(result.state));
    return result;
  } catch { return { status: "storage_unavailable", state: null }; }
}

export function isProductionScanUnlocked(state: WebsiteJourneyStateV2): boolean {
  return state.accountCreated && state.preflightStatus === "COMPLETED_REVIEWED";
}

/** Null means the legacy position must remain untouched until it can be mapped. */
export function migrateWebsiteJourneyV1ToV2(legacy: WebsiteJourneyStateV1): WebsiteJourneyStateV2 | null {
  const result = migrateJourneyState(legacy);
  return result.status === "migrated" ? result.state : null;
}
