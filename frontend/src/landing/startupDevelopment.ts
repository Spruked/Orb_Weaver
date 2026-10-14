export const DEV_FULL_TOUR_QUERY_KEY = 'orbDevFullTour';
export const DEV_INTRO_VARIANT_QUERY_KEY = 'orbIntroVariant';
export const DEV_LLM_SCRIPTED_TOUR_QUERY_KEY = 'orbLlmScriptedTour';
export const DEV_REPLAY_QUERY_KEY = 'orbStartupReset';
export const DEV_REPLAY_SESSION_KEY = 'orbweaver-developer-replay-v1';
export const RETURNING_VISITOR_STORAGE_KEY = 'orbweaver-returning-visitor-v1';

export type EntryRouteDecision = 'landing' | 'login' | 'workspace';

export const entryRouteDecision = (
  authenticated: boolean,
  returningVisitor: boolean,
): EntryRouteDecision => authenticated ? 'workspace' : returningVisitor ? 'login' : 'landing';

export const replayAwareEntryRouteDecision = (
  authenticated: boolean,
  returningVisitor: boolean,
  replayRequested = false,
): EntryRouteDecision => replayRequested ? 'landing' : entryRouteDecision(authenticated, returningVisitor);

const REPLAY_SESSION_KEYS = [
  'orbweaver-landing-splash-played',
  'orbweaver-landing-splash-complete',
  'orbweaver-landing-startup-readiness',
  'orbweaver-scripted-orientation-v1',
  'orbweaver-scripted-orientation-v2',
  'orbweaver-scripted-orientation-progress-v2',
  'orbweaver-startup-greeting-played',
  'orbweaver-first-encounter-state',
  'orbweaver-website-journey',
  'orbweaver-last-intro-variant',
] as const;

export const developerReplayRequested = (
  search = typeof window === 'undefined' ? '' : window.location.search,
  environment = process.env.NODE_ENV,
): boolean => {
  if (new URLSearchParams(search).get(DEV_REPLAY_QUERY_KEY) === '1') return true;
  if (developmentFullTourOverride(search, environment)) return true;
  if (typeof window === 'undefined') return false;
  try {
    return window.sessionStorage.getItem(DEV_REPLAY_SESSION_KEY) === '1';
  } catch {
    return false;
  }
};

export const developerReplayResetRequested = (
  search = typeof window === 'undefined' ? '' : window.location.search,
): boolean => new URLSearchParams(search).get(DEV_REPLAY_QUERY_KEY) === '1';

export const beginDeveloperReplay = (): void => {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(DEV_REPLAY_SESSION_KEY, '1');
  } catch {
    // Replay still works for the current mount if session storage is blocked.
  }
};

export const finishDeveloperReplay = (): void => {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.removeItem(DEV_REPLAY_SESSION_KEY);
  } catch {
    // Storage cleanup must not interrupt a completed tour.
  }
};

export const resetDeveloperReplayState = (): void => {
  if (typeof window === 'undefined') return;
  try {
    REPLAY_SESSION_KEYS.forEach((key) => window.sessionStorage.removeItem(key));
    beginDeveloperReplay();
  } catch {
    // The in-memory startup reset remains usable if storage is unavailable.
  }
};

export const hasReturningVisitorMarker = (): boolean => {
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage.getItem(RETURNING_VISITOR_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
};

export const markReturningVisitor = (): void => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(RETURNING_VISITOR_STORAGE_KEY, '1');
  } catch {
    // A storage failure must not block a first-time visitor.
  }
};

export const cancelLandingExperience = (reason = 'entry_route_redirect'): void => {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent('orbweaver:cancel-landing-experience', { detail: { reason } }));
};

export const developmentFullTourOverride = (
  search = window.location.search,
  environment = process.env.NODE_ENV,
): boolean => environment !== 'production' && new URLSearchParams(search).get(DEV_FULL_TOUR_QUERY_KEY) === '1';

export const developmentIntroVariant = <T extends string>(
  allowed: readonly T[],
  search = window.location.search,
  environment = process.env.NODE_ENV,
): T | null => {
  if (environment === 'production') return null;
  const requested = new URLSearchParams(search).get(DEV_INTRO_VARIANT_QUERY_KEY);
  return requested && allowed.includes(requested as T) ? requested as T : null;
};

/** Development-only evaluation of the local LLM against authored tour context. */
export const developmentLlmScriptedTourOverride = (
  search = window.location.search,
  environment = process.env.NODE_ENV,
): boolean => environment !== 'production' && new URLSearchParams(search).get(DEV_LLM_SCRIPTED_TOUR_QUERY_KEY) === '1';

export const tourEligibleForAccount = (authenticated: boolean, developmentOverride: boolean): boolean =>
  !authenticated || developmentOverride;

export const emitDevelopmentStartupTrace = (state: string, detail: Record<string, unknown> = {}): void => {
  if (process.env.NODE_ENV === 'production') return;
  const payload = { state, timestamp: new Date().toISOString(), ...detail };
  console.info('[Weaver startup]', payload);
  window.dispatchEvent(new CustomEvent('orbweaver:startup-trace', { detail: payload }));
};
