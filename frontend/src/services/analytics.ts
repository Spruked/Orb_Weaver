export type OnboardingEventName =
  | 'landing_signup_cta_clicked'
  | 'guest_session_created'
  | 'onboarding_started'
  | 'onboarding_step_completed'
  | 'account_created'
  | 'guest_merge_completed'
  | 'website_project_created'
  | 'onboarding_completed'
  | 'preflight_selected'
  | 'packages_selected'
  | 'dashboard_selected'
  | 'marketplace_selected';

type SafeEventParameters = {
  intent?: string;
  tier?: string;
  step?: string;
  action?: string;
  outcome?: string;
};

export const GA4_MEASUREMENT_ID = 'G-5BR1CYDQGS';
export const ANALYTICS_CONSENT_STORAGE_KEY = 'orbweaver-analytics-consent';

export type AnalyticsConsent = 'granted' | 'denied' | 'unknown';

const PUBLIC_ANALYTICS_ROUTES = new Set([
  '/', '/features', '/use-cases', '/lidar-guidance', '/how-it-works',
  '/security', '/orb-weaver', '/now/desktop-orb', '/preflight',
  '/founding-beta', '/investor-contact', '/privacy', '/terms', '/weaving',
]);

const forbiddenParameter = /name|email|password|website|url|token|session|customer|project|address|phone|credential/i;

export function getAnalyticsConsent(): AnalyticsConsent {
  if (typeof window === 'undefined') return 'unknown';
  const value = window.localStorage.getItem(ANALYTICS_CONSENT_STORAGE_KEY);
  return value === 'granted' || value === 'denied' ? value : 'unknown';
}

export function setAnalyticsConsent(consent: Exclude<AnalyticsConsent, 'unknown'>) {
  window.localStorage.setItem(ANALYTICS_CONSENT_STORAGE_KEY, consent);
  window.gtag?.('consent', 'update', {
    analytics_storage: consent === 'granted' ? 'granted' : 'denied',
    ad_storage: consent === 'granted' ? 'granted' : 'denied',
    ad_user_data: consent === 'granted' ? 'granted' : 'denied',
    ad_personalization: consent === 'granted' ? 'granted' : 'denied',
  });
  window.dispatchEvent(new CustomEvent('orbweaver-analytics-consent-change', { detail: consent }));
}

export function isAnalyticsPublicRoute(pathname: string): boolean {
  return PUBLIC_ANALYTICS_ROUTES.has(pathname);
}

export function sanitizedPagePath(pathname: string): string {
  const path = pathname.split(/[?#]/, 1)[0] || '/';
  return path.startsWith('/') ? path : `/${path}`;
}

let analyticsScriptRequested = false;

export function initializeAnalytics() {
  if (typeof window === 'undefined' || analyticsScriptRequested) return;
  if (getAnalyticsConsent() !== 'granted') return;

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || ((...args: unknown[]) => window.dataLayer?.push(args));
  window.gtag('js', new Date());
  window.gtag('config', GA4_MEASUREMENT_ID, {
    send_page_view: false,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
  });

  const script = document.createElement('script');
  script.id = 'orbweaver-google-tag';
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA4_MEASUREMENT_ID}`;
  document.head.appendChild(script);
  analyticsScriptRequested = true;
}

export function trackPageView(pathname: string, pageTitle: string) {
  const pagePath = sanitizedPagePath(pathname);
  if (getAnalyticsConsent() !== 'granted' || !isAnalyticsPublicRoute(pagePath)) return;
  initializeAnalytics();
  window.gtag?.('event', 'page_view', {
    page_title: pageTitle,
    page_location: `${window.location.origin}${pagePath}`,
    page_path: pagePath,
  });
}

export function trackOnboardingEvent(name: OnboardingEventName, parameters: SafeEventParameters = {}) {
  if (getAnalyticsConsent() !== 'granted') return;
  initializeAnalytics();
  const safeParameters = Object.fromEntries(
    Object.entries(parameters).filter(([key, value]) => !forbiddenParameter.test(key) && typeof value === 'string')
  );
  window.gtag?.('event', name, safeParameters);
}
