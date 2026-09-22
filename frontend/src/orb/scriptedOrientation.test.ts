import { describe, expect, test } from '@jest/globals';
import { LANDING_FULL_TOUR_SCRIPT, SITE_TOUR_SCRIPT, scriptedPageOrientation } from './scriptedOrientation';

describe('scripted orientation', () => {
  test('covers every landing-tour section before handing off to questions', () => {
    expect(LANDING_FULL_TOUR_SCRIPT.map((step) => step.selector)).toEqual([
      '#beat-1', '#weaver-first-encounter', '#beat-2', '#beat-3', '#beat-4',
      '#beat-5', '#beat-6', '#beat-7',
      '#beat-8', '#beat-9', '#weave-business-outcomes', '#beat-10',
    ]);
    expect(LANDING_FULL_TOUR_SCRIPT[0].text).toMatch(/answer any questions/i);
    expect(LANDING_FULL_TOUR_SCRIPT.at(-1)?.text).toMatch(/rest of the public site/i);
    expect(LANDING_FULL_TOUR_SCRIPT.flatMap((step) => step.pointerTargetIds || [])).toEqual([
      'orb-weaver-suite-logo', 'what_weaver_does', 'what_to_say', 'watch_weaver_guide',
      'interrupt_or_guide', 'run-free-preflight',
    ]);
  });

  test('uses the authored LiDAR orientation', () => {
    expect(scriptedPageOrientation('/lidar-guidance')?.text).toMatch(/LiDAR-inspired two-dimensional visual navigation system/i);
  });

  test('visits every native public explainer before account creation', () => {
    expect(SITE_TOUR_SCRIPT.map((step) => step.route).filter(Boolean)).toEqual([
      '/features', '/lidar-guidance', '/how-it-works', '/security', '/weaving',
      '/web-weave', '/now/desktop-orb', '/founding-beta', '/investor-contact',
      '/preflight', '/privacy', '/terms', '/signup',
    ]);
    expect(SITE_TOUR_SCRIPT.at(-1)).toMatchObject({ route: '/signup', handoffToLiveConversation: true });
    expect(SITE_TOUR_SCRIPT.at(-1)?.text).toBeUndefined();
  });

  test('keeps every routed demo stop pointer-backed and keeps research non-destructive', () => {
    const routedStops = SITE_TOUR_SCRIPT.filter((step) => step.route);
    expect(routedStops.filter((step) => !step.handoffToLiveConversation)
      .every((step) => (step.pointerTargetIds?.length || 0) > 0)).toBe(true);
    expect(SITE_TOUR_SCRIPT.some((step) => step.route?.startsWith('/marketplace'))).toBe(false);
    expect(SITE_TOUR_SCRIPT.find((step) => step.simulation === 'product_price_research')?.route).toBeUndefined();
    expect(SITE_TOUR_SCRIPT.at(-1)?.route).toBe('/signup');
    expect(scriptedPageOrientation('/signup')).toBeNull();
  });

  test('guides an owner-controlled Preflight scan and defers review until after account creation', () => {
    const preflight = SITE_TOUR_SCRIPT.find((step) => step.route === '/preflight');
    expect(preflight).toMatchObject({
      pointerTargetIds: ['preflight-website-url', 'run-preflight-scan'],
      scrollToEndDuringSpeech: true,
    });
    expect(preflight?.text).toMatch(/account creation comes next/i);
    expect(preflight?.text).toMatch(/optionally review.*before.*full-site scan/i);
  });

  test('uses single-function MORBs only for prime-sized research and diagnostic audits', () => {
    const simulations = SITE_TOUR_SCRIPT.filter((step) => step.simulation);
    expect(simulations.map((step) => [step.simulation, step.auditTaskCount])).toEqual([
      ['product_price_research', 3],
      ['desktop_diagnostics', 5],
    ]);
    expect(simulations.every((step) => [3, 5, 7, 11].includes(step.auditTaskCount || 0))).toBe(true);
  });

  test('provides a concise orientation for an otherwise unmapped route', () => {
    expect(scriptedPageOrientation('/account-settings')?.text).toContain('Account Settings page');
  });
});
