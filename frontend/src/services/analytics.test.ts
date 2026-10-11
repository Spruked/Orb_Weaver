import {
  ANALYTICS_CONSENT_STORAGE_KEY,
  GA4_MEASUREMENT_ID,
  getAnalyticsConsent,
  isAnalyticsPublicRoute,
  sanitizedPagePath,
  setAnalyticsConsent,
  trackOnboardingEvent,
  trackPageView,
} from './analytics';

declare const describe: (name: string, suite: () => void) => void;
declare const beforeEach: (setup: () => void) => void;
declare const test: (name: string, run: () => void) => void;
declare const jest: any;
declare const expect: any;

describe('frontend analytics privacy boundary', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.head.querySelector('#orbweaver-google-tag')?.remove();
    window.gtag = undefined;
  });

  test('keeps analytics disabled until explicit consent', () => {
    const gtag = jest.fn();
    window.gtag = gtag;

    trackPageView('/features?token=secret#private', 'Features');

    expect(getAnalyticsConsent()).toBe('unknown');
    expect(gtag).not.toHaveBeenCalled();
    expect(document.head.querySelector('#orbweaver-google-tag')).toBeNull();
  });

  test('tracks only an approved public route after consent and strips URL state', () => {
    const gtag = jest.fn();
    window.gtag = gtag;
    setAnalyticsConsent('granted');

    trackPageView('/features?project=private-id#secret', 'Features');

    expect(gtag).toHaveBeenCalledWith('event', 'page_view', {
      page_title: 'Features',
      page_location: `${window.location.origin}/features`,
      page_path: '/features',
    });
    expect(JSON.stringify(gtag.mock.calls)).not.toMatch(/private-id|secret|token/i);
    expect(GA4_MEASUREMENT_ID).toBe('G-5BR1CYDQGS');
  });

  test('blocks private routes and collection after consent is withdrawn', () => {
    const gtag = jest.fn();
    window.gtag = gtag;
    setAnalyticsConsent('granted');
    trackPageView('/features', 'Features');
    const callsBeforeWithdrawal = gtag.mock.calls.length;

    setAnalyticsConsent('denied');
    trackPageView('/dashboard?customer=private-id', 'Dashboard');

    expect(getAnalyticsConsent()).toBe('denied');
    expect(gtag.mock.calls.filter(([method]: [string]) => method === 'event').length).toBe(1);
    expect(gtag).toHaveBeenLastCalledWith('consent', 'update', expect.objectContaining({ analytics_storage: 'denied' }));
    expect(gtag.mock.calls.length).toBe(callsBeforeWithdrawal + 1);
    expect(isAnalyticsPublicRoute('/dashboard')).toBe(false);
    expect(window.localStorage.getItem(ANALYTICS_CONSENT_STORAGE_KEY)).toBe('denied');
  });

  test('custom events remain consent-gated and transmit only approved fields', () => {
    const gtag = jest.fn();
    window.gtag = gtag;

    trackOnboardingEvent('account_created', { email: 'person@example.com' } as any);
    expect(gtag).not.toHaveBeenCalled();

    setAnalyticsConsent('granted');
    trackOnboardingEvent('account_created', {
      intent: 'preflight',
      step: 'account_created',
      email: 'person@example.com',
      project_id: 'private-project-id',
    } as any);

    expect(gtag).toHaveBeenLastCalledWith('event', 'account_created', {
      intent: 'preflight',
      step: 'account_created',
    });
  });

  test('normalizes paths without transmitting query or fragment data', () => {
    expect(sanitizedPagePath('features?email=person@example.com#account')).toBe('/features');
    expect(sanitizedPagePath('/')).toBe('/');
  });
});
