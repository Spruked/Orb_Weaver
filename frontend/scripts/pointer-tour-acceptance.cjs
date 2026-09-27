const assert = require('node:assert/strict');
const { chromium } = require('playwright');

const APP_URL = process.env.APP_URL || 'http://127.0.0.1:16667/';
const EXPECTED_TARGETS = [
  'relationship-structure',
  'business-outcomes',
  'security-governance-proof',
  'pointer-intelligence-proof',
  'run-free-preflight',
  'tour-features',
  'use-case-3',
  'use-case-4',
  'tour-lidar-guidance',
  'tour-how-it-works',
  'tour-security',
  'tour-weaving',
  'tour-account-creation',
  'tour-desktop-orb',
  'tour-founding-beta',
  'preflight-website-url',
  'run-preflight-scan',
];

const REQUIRED_STAGES = [
  'TARGET_RESOLVING',
  'TARGET_VERIFIED',
  'MOTION_STARTED',
  'END_EFFECTOR_ACTIVE',
  'ARRIVAL_CONFIRMED',
  'PING_RENDER_REQUESTED',
];

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.route('**/api/auth/me', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ id: 'dev-account', email: 'bryan@development.local', name: 'Bryan' }),
  }));
  await page.addInitScript(() => {
    window.sessionStorage.setItem('orb_weaver_customer_session_token', 'dev-browser-session-token');
    window.localStorage.removeItem('orb_weaver_customer_token');
    window.__pointerTourAcceptance = [];
    window.addEventListener('orbweaver:mounted-runtime', (event) => {
      const detail = event.detail || {};
      if (detail.phase) window.__pointerTourAcceptance.push(detail);
    });
  });

  const url = new URL(APP_URL);
  url.searchParams.set('orbStartupReset', '1');
  url.searchParams.set('orbIntroVariant', 'am-echo');
  url.searchParams.set('orbDevFullTour', '1');
  await page.goto(url.toString(), { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(
    () => document.querySelector('.ow-v2-orb-position') || document.querySelector('[data-orb-guidance-source]'),
    null,
    { timeout: 60000 },
  );
  let completionObserved = false;
  try {
    await page.waitForFunction(
      () => window.__pointerTourAcceptance?.some((event) => event.phase === 'scripted_orientation_completed'),
      null,
      { timeout: Number(process.env.POINTER_TOUR_TIMEOUT_MS || 360000) },
    );
    completionObserved = true;
  } catch (error) {
    console.error(`pointer tour did not complete: ${error.message}`);
  }

  const events = await page.evaluate(() => window.__pointerTourAcceptance);
  const pings = [...new Set(events.filter((event) => event.phase === 'guidance_point_ping').map((event) => event.targetId))];
  const skipped = events
    .filter((event) => event.phase === 'scripted_orientation_pointer_skipped')
    .map((event) => ({ targetId: event.targetId, reason: event.reason }));
  const stagesByTarget = {};
  for (const event of events.filter((item) => item.phase === 'pointer_execution_stage')) {
    (stagesByTarget[event.targetId] ||= []).push(event.stage);
  }

  const targetResults = EXPECTED_TARGETS.map((targetId) => {
    const stages = stagesByTarget[targetId] || [];
    const pingIndex = pings.indexOf(targetId);
    const stageIndexes = REQUIRED_STAGES.map((stage) => stages.indexOf(stage));
    const complete = pingIndex >= 0 && stageIndexes.every((index) => index >= 0);
    const ordered = complete && stageIndexes.every((index, position) => position === 0 || index > stageIndexes[position - 1]);
    return { targetId, pingIndex, ordered, stages };
  });

  console.log(JSON.stringify({
    completionObserved,
    phases: events.map((event) => event.phase),
    recentEvents: events.slice(-12),
    pings,
    targetResults,
    skipped,
  }, null, 2));
  assert.ok(completionObserved, 'scripted orientation did not complete');
  assert.equal(skipped.length, 0, `declared pointer stops were skipped: ${JSON.stringify(skipped)}`);
  assert.ok(targetResults.every((result) => result.ordered), `pointer execution proof failed: ${JSON.stringify(targetResults, null, 2)}`);
  const observedExpectedOrder = pings.filter((targetId) => EXPECTED_TARGETS.includes(targetId));
  assert.deepEqual(observedExpectedOrder, EXPECTED_TARGETS.filter((targetId) => pings.includes(targetId)), 'observed target order changed');

  console.log(JSON.stringify({ result: 'PASS', url: page.url(), pings, targetResults, skipped }, null, 2));
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
