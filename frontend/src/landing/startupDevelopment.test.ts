import { developmentFullTourOverride, developmentIntroVariant, tourEligibleForAccount } from './startupDevelopment';

describe('development startup controls', () => {
  test('allows an authenticated account into the tour only under the development override', () => {
    expect(tourEligibleForAccount(true, false)).toBe(false);
    expect(tourEligibleForAccount(true, true)).toBe(true);
    expect(tourEligibleForAccount(false, false)).toBe(true);
  });

  test('cannot activate the full-tour override in production', () => {
    expect(developmentFullTourOverride('?orbDevFullTour=1', 'development')).toBe(true);
    expect(developmentFullTourOverride('?orbDevFullTour=1', 'production')).toBe(false);
  });

  test('forces only a known intro variant in development', () => {
    const ids = ['am-echo', 'am-michael', 'kokoro-host'] as const;
    expect(developmentIntroVariant(ids, '?orbIntroVariant=am-michael', 'development')).toBe('am-michael');
    expect(developmentIntroVariant(ids, '?orbIntroVariant=unknown', 'development')).toBeNull();
    expect(developmentIntroVariant(ids, '?orbIntroVariant=am-michael', 'production')).toBeNull();
  });
});
