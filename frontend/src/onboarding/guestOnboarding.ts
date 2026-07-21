import { api, OrbsGuestSession } from '../services/api';
import { trackOnboardingEvent } from '../services/analytics';

const GUEST_REFERENCE_KEY = 'orb_weaver_guest_session_reference';
const MERGE_KEY_PREFIX = 'orb_weaver_guest_merge_key:';

export type LandingIntent = 'preflight' | 'package' | 'enterprise' | 'dashboard';

export interface OnboardingIntent {
  intent: LandingIntent;
  tier: 'basic' | 'enhanced' | 'premium' | null;
  originalDestination: string;
}

export function intentFromLocation(location: Pick<Location, 'pathname' | 'search'> = window.location): OnboardingIntent {
  const search = new URLSearchParams(location.search);
  const rawIntent = search.get('intent');
  const intent: LandingIntent =
    rawIntent === 'package' || rawIntent === 'enterprise' || rawIntent === 'dashboard'
      ? rawIntent
      : 'preflight';
  const rawTier = search.get('tier');
  const tier = rawTier === 'basic' || rawTier === 'enhanced' || rawTier === 'premium' ? rawTier : null;
  return { intent, tier, originalDestination: `${location.pathname}${location.search}` };
}

export function currentGuestReference() {
  return window.localStorage.getItem(GUEST_REFERENCE_KEY);
}

function saveGuestReference(session: OrbsGuestSession) {
  window.localStorage.setItem(GUEST_REFERENCE_KEY, session.guest_session_id);
}

export async function createIntentGuestSession(
  target: string,
  intent: LandingIntent,
  tier: OnboardingIntent['tier'] = null,
  websiteUrl: string | null = null,
  step = 'landing'
) {
  const session = await api.createOrbsGuestSession({
    landing_intent: intent,
    selected_tier_interest: tier,
    website_url: websiteUrl,
    original_cta_destination: target,
    current_onboarding_step: step,
    completed_onboarding_steps: step === 'landing' ? ['landing_cta'] : ['landing_cta', 'account_details', 'website_confirmed'],
    non_sensitive_questionnaire_answers: {},
  });
  saveGuestReference(session);
  trackOnboardingEvent('guest_session_created', { intent, ...(tier ? { tier } : {}), step });
  return session;
}

export function mergeIdempotencyKey(guestSessionId: string) {
  const storageKey = `${MERGE_KEY_PREFIX}${guestSessionId}`;
  const existing = window.localStorage.getItem(storageKey);
  if (existing) return existing;
  const generated = window.crypto.randomUUID();
  window.localStorage.setItem(storageKey, generated);
  return generated;
}

export function clearMergedGuestReference(guestSessionId: string) {
  if (currentGuestReference() === guestSessionId) {
    window.localStorage.removeItem(GUEST_REFERENCE_KEY);
  }
  window.localStorage.removeItem(`${MERGE_KEY_PREFIX}${guestSessionId}`);
}

