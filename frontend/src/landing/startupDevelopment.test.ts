import { describe, expect, test } from '@jest/globals';
import { developmentFullTourOverride, developmentIntroVariant, developmentLlmScriptedTourOverride, entryRouteDecision, hasReturningVisitorMarker, markReturningVisitor, RETURNING_VISITOR_STORAGE_KEY, tourEligibleForAccount } from './startupDevelopment';

describe('development startup controls', () => {
  test('allows an authenticated account into the tour only under the development override', () => {
    expect(tourEligibleForAccount(true, false)).toBe(false);
    expect(tourEligibleForAccount(true, true)).toBe(true);
    expect(tourEligibleForAccount(false, false)).toBe(true);
  });

  test('uses authentication before the advisory returning-visitor marker', () => {
    expect(entryRouteDecision(true, false)).toBe('workspace');
    expect(entryRouteDecision(true, true)).toBe('workspace');
    expect(entryRouteDecision(false, true)).toBe('login');
    expect(entryRouteDecision(false, false)).toBe('landing');
  });

  test('persists only a returning-visitor hint and never an authentication grant', () => {
    window.localStorage.clear();
    expect(hasReturningVisitorMarker()).toBe(false);
    markReturningVisitor();
    expect(window.localStorage.getItem(RETURNING_VISITOR_STORAGE_KEY)).toBe('1');
    expect(hasReturningVisitorMarker()).toBe(true);
  });

  test('cannot activate the full-tour override in production', () => {
    expect(developmentFullTourOverride('?orbDevFullTour=1', 'development')).toBe(true);
    expect(developmentFullTourOverride('?orbDevFullTour=1', 'production')).toBe(false);
  });

  test('forces only a known intro variant in development', () => {
    const ids = ['am-echo', 'kokoro-af-bella', 'kokoro-host'] as const;
    expect(developmentIntroVariant(ids, '?orbIntroVariant=kokoro-af-bella', 'development')).toBe('kokoro-af-bella');
    expect(developmentIntroVariant(ids, '?orbIntroVariant=unknown', 'development')).toBeNull();
    expect(developmentIntroVariant(ids, '?orbIntroVariant=kokoro-af-bella', 'production')).toBeNull();
  });

  test('enables the authored-context LLM tour evaluation only in development', () => {
    expect(developmentLlmScriptedTourOverride('?orbLlmScriptedTour=1', 'development')).toBe(true);
    expect(developmentLlmScriptedTourOverride('?orbLlmScriptedTour=1', 'production')).toBe(false);
  });
});
