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

const forbiddenParameter = /name|email|password|website|url|token|session|customer|project|address|phone|credential/i;

export function trackOnboardingEvent(name: OnboardingEventName, parameters: SafeEventParameters = {}) {
  const safeParameters = Object.fromEntries(
    Object.entries(parameters).filter(([key, value]) => !forbiddenParameter.test(key) && typeof value === 'string')
  );
  window.gtag?.('event', name, safeParameters);
}

