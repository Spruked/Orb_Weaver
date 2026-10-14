import { describe, expect, test } from '@jest/globals';
import { developerReplayRequested, developmentFullTourOverride, developmentIntroVariant, developmentLlmScriptedTourOverride, entryRouteDecision, finishDeveloperReplay, hasReturningVisitorMarker, markReturningVisitor, replayAwareEntryRouteDecision, resetDeveloperReplayState, RETURNING_VISITOR_STORAGE_KEY, DEV_REPLAY_SESSION_KEY, tourEligibleForAccount } from './startupDevelopment';

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

  test('replay mode sends authenticated and returning visitors to the landing page', () => {
    expect(replayAwareEntryRouteDecision(true, true, true)).toBe('landing');
    expect(replayAwareEntryRouteDecision(false, true, true)).toBe('landing');
    expect(replayAwareEntryRouteDecision(true, true, false)).toBe('workspace');
    expect(replayAwareEntryRouteDecision(false, true, false)).toBe('login');
  });

  test('orbStartupReset is an explicit replay request in every build, while the dev flag remains dev-only', () => {
    window.sessionStorage.removeItem(DEV_REPLAY_SESSION_KEY);
    expect(developerReplayRequested('?orbStartupReset=1', 'production')).toBe(true);
    expect(developerReplayRequested('?orbDevFullTour=1', 'production')).toBe(false);
    expect(developerReplayRequested('?orbDevFullTour=1', 'development')).toBe(true);
  });

  test('replay reset clears tour state without clearing authentication or account hints', () => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    window.localStorage.setItem(RETURNING_VISITOR_STORAGE_KEY, '1');
    window.sessionStorage.setItem('orb_weaver_customer_session_token', 'account-session');
    window.sessionStorage.setItem('orbweaver-website-journey', '{"stage":"PREFLIGHT"}');
    window.sessionStorage.setItem('orbweaver-first-encounter-state', '{"entrance_complete":true}');

    resetDeveloperReplayState();

    expect(window.localStorage.getItem(RETURNING_VISITOR_STORAGE_KEY)).toBe('1');
    expect(window.sessionStorage.getItem('orb_weaver_customer_session_token')).toBe('account-session');
    expect(window.sessionStorage.getItem('orbweaver-website-journey')).toBeNull();
    expect(window.sessionStorage.getItem('orbweaver-first-encounter-state')).toBeNull();
    expect(window.sessionStorage.getItem(DEV_REPLAY_SESSION_KEY)).toBe('1');

    finishDeveloperReplay();
    expect(window.sessionStorage.getItem(DEV_REPLAY_SESSION_KEY)).toBeNull();
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
