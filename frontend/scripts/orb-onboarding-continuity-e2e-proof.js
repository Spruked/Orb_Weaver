const assert = require('assert');
const { chromium } = require('playwright');

const APP_URL = process.env.APP_URL || 'http://127.0.0.1:16667';

const waitForPhase = async (page, phase, timeout = 30000) => {
  await page.waitForFunction((expected) =>
    (window.__orbContinuityEvents || []).some((event) => event.phase === expected), phase, { timeout });
};

let diagnosticPage;
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  diagnosticPage = page;
  const errors = [];
  await page.addInitScript(() => {
    window.__orbContinuityEvents = [];
    window.addEventListener('orbweaver:mounted-runtime', (event) => {
      window.__orbContinuityEvents.push(event.detail);
    });
  });
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  page.on('pageerror', (error) => errors.push(error.message));

  await page.goto(`${APP_URL}/preflight`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.getByLabel('Website URL').waitFor({ state: 'visible', timeout: 30000 });
  await page.getByLabel('Website URL').fill('https://www.spruked.com');
  await page.getByRole('button', { name: 'Run Preflight' }).click();

  const onboardingLink = page.getByRole('link', { name: 'Continue to onboarding' });
  await onboardingLink.waitFor({ state: 'visible', timeout: 60000 });
  await onboardingLink.click();
  await page.waitForURL(/\/signup\?intent=site_onboarding/, { timeout: 15000 });

  const orb = page.locator('.ow-v2-orb-position');
  await orb.waitFor({ state: 'visible', timeout: 30000 });
  await page.getByLabel('Full name').waitFor({ state: 'visible', timeout: 15000 });
  await waitForPhase(page, 'onboarding_continuation_recorded');
  await waitForPhase(page, 'pointer_map_ready');
  await waitForPhase(page, 'route_spatial_state_ready');
  await waitForPhase(page, 'onboarding_lidar_target_mapped');
  await waitForPhase(page, 'onboarding_route_ready');
  await waitForPhase(page, 'guidance_point_ping', 35000);
  await waitForPhase(page, 'onboarding_first_target_guided', 35000);

  const arrival = await page.evaluate(() => {
    const journey = JSON.parse(sessionStorage.getItem('orbweaver-website-journey') || 'null');
    const continuation = JSON.parse(sessionStorage.getItem('orbweaver-onboarding-continuation') || 'null');
    const orbNodes = [...document.querySelectorAll('.ow-v2-orb-position')];
    const target = document.querySelector('[data-orb-target="full-name-field"]');
    const ping = document.querySelector('[data-orb-pointer-target="full-name-field"]');
    return {
      journey,
      continuation,
      orbCount: orbNodes.length,
      orbVisible: orbNodes.length === 1 && getComputedStyle(orbNodes[0]).display !== 'none',
      targetConnected: Boolean(target && document.body.contains(target)),
      pingTarget: ping?.getAttribute('data-orb-pointer-target') || null,
      introAfterContinuation: window.__orbContinuityEvents.some((event) => event.phase === 'intro_started' && event.at > continuation.approvedAt),
      events: window.__orbContinuityEvents,
    };
  });

  assert.equal(arrival.journey.stage, 'ONBOARDING', 'journey must remain in the onboarding continuation state');
  assert.equal(arrival.continuation.destination, '/signup?intent=site_onboarding');
  assert.equal(arrival.continuation.firstTargetId, 'full-name-field');
  assert.equal(arrival.orbCount, 1, 'one logical Weaver mount must remain');
  assert.equal(arrival.orbVisible, true, 'Weaver must not be CSS-hidden on onboarding');
  assert.equal(arrival.targetConnected, true, 'the first onboarding target must be live');
  assert.equal(arrival.pingTarget, 'full-name-field', 'Point/Ping must use the verified live onboarding target');
  assert.equal(arrival.introAfterContinuation, false, 'onboarding continuation must not replay a fresh greeting');

  await page.goBack({ waitUntil: 'domcontentloaded' });
  await page.waitForURL(/\/preflight/, { timeout: 15000 });
  await page.goForward({ waitUntil: 'domcontentloaded' });
  await page.waitForURL(/\/signup\?intent=site_onboarding/, { timeout: 15000 });
  await orb.waitFor({ state: 'visible', timeout: 30000 });
  assert.equal(await orb.count(), 1, 'back/forward must not create duplicate Weaver instances');
  assert.equal(errors.length, 0, `browser console errors: ${errors.join(' | ')}`);

  console.log('ORB_ONBOARDING_CONTINUITY_E2E_PROOF_OK');
  await browser.close();
})().catch(async (error) => {
  console.error(error);
  if (diagnosticPage && !diagnosticPage.isClosed()) {
    console.error('ORB_ONBOARDING_CONTINUITY_E2E_DIAGNOSTICS', JSON.stringify(await diagnosticPage.evaluate(() => ({
      route: window.location.pathname + window.location.search,
      events: window.__orbContinuityEvents || [],
      journey: sessionStorage.getItem('orbweaver-website-journey'),
      continuation: sessionStorage.getItem('orbweaver-onboarding-continuation'),
      target: Boolean(document.querySelector('[data-orb-target="full-name-field"]')),
      orb: Boolean(document.querySelector('.ow-v2-orb-position')),
      ping: Boolean(document.querySelector('[data-orb-pointer-target="full-name-field"]')),
    }))));
  }
  process.exit(1);
});
