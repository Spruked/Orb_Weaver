export const DEV_FULL_TOUR_QUERY_KEY = 'orbDevFullTour';
export const DEV_INTRO_VARIANT_QUERY_KEY = 'orbIntroVariant';
export const DEV_LLM_SCRIPTED_TOUR_QUERY_KEY = 'orbLlmScriptedTour';

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
