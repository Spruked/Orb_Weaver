import { api } from '../services/api';
import { createIntentGuestSession, intentFromLocation } from './guestOnboarding';

declare const jest: any;
declare const describe: (name: string, suite: () => void) => void;
declare const beforeEach: (setup: () => void) => void;
declare const it: (name: string, test: () => void | Promise<void>) => void;
declare const expect: any;

jest.mock('../services/api');
jest.mock('../services/analytics');

const createGuest = api.createOrbsGuestSession as any;

describe('guest onboarding intent', () => {
  beforeEach(() => {
    window.localStorage.clear();
    createGuest.mockReset();
    createGuest.mockResolvedValue({
      guest_session_id: 'guest-reference-without-customer-data',
    });
  });

  it('parses only supported package intent and tiers', () => {
    expect(intentFromLocation({ pathname: '/signup', search: '?intent=package&tier=enhanced' } as Location)).toEqual({
      intent: 'package',
      tier: 'enhanced',
      originalDestination: '/signup?intent=package&tier=enhanced',
    });
    expect(intentFromLocation({ pathname: '/signup', search: '?intent=unknown&tier=platinum' } as Location)).toEqual({
      intent: 'preflight',
      tier: null,
      originalDestination: '/signup?intent=unknown&tier=platinum',
    });
  });

  it('creates narrow guest state without password or customer fields', async () => {
    await createIntentGuestSession('/signup?intent=preflight', 'preflight', null, 'https://example.com', 'website_confirmed');
    expect(createGuest).toHaveBeenCalledTimes(1);
    const payload = createGuest.mock.calls[0][0];
    expect(payload.website_url).toBe('https://example.com');
    expect(JSON.stringify(payload)).not.toMatch(/password|email|full_name|business_name/i);
  });
});
