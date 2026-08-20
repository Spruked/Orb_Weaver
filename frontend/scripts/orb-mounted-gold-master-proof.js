const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const FRONTEND_URL = process.env.ORB_PROOF_FRONTEND_URL || 'http://127.0.0.1:16511';
const AUDIO_FIXTURE = process.env.ORB_PROOF_AUDIO_FIXTURE || '/tmp/orb-weaver-question-with-silence.wav';

const position = async (orb) => orb.evaluate((element) => {
  const rect = element.getBoundingClientRect();
  return { x: rect.left, y: rect.top, opacity: Number(getComputedStyle(element).opacity) };
});

const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

(async () => {
  assert(fs.existsSync(AUDIO_FIXTURE), `Audio fixture missing: ${AUDIO_FIXTURE}`);
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--autoplay-policy=no-user-gesture-required',
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      `--use-file-for-fake-audio-capture=${AUDIO_FIXTURE}`,
    ],
  });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 820 },
    permissions: ['microphone'],
  });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  await page.addInitScript(() => {
    const originalNow = Date.now.bind(Date);
    window.__orbProofTimeOffset = 0;
    Date.now = () => originalNow() + window.__orbProofTimeOffset;
    window.__orbProof = { events: [], logoClicks: 0, mountToken: null };
    window.addEventListener('orbweaver:mounted-runtime', (event) => {
      window.__orbProof.events.push(event.detail);
    });
    sessionStorage.setItem('orbweaver-startup-greeting-played', '1');
    sessionStorage.setItem('orbweaver-landing-splash-played', '1');
    sessionStorage.setItem('orbweaver-first-encounter-state', JSON.stringify({
      voice_ready: true,
      entrance_complete: true,
      communication_orientation_complete: true,
      understanding_complete: true,
      orientation_pointer_proof_complete: true,
      agency_complete: true,
      visitor_first_turn_complete: true,
      personal_relevance_complete: true,
      responsive_guidance_complete: true,
      relevant_continuation_complete: true,
      controller_handoff_complete: true,
    }));
  });

  await page.goto(FRONTEND_URL, { waitUntil: 'networkidle', timeout: 120000 });
  const orb = page.locator('.ow-v2-orb-position');
  await orb.waitFor({ state: 'visible' });
  await page.waitForFunction(() => window.__orbProof.events.some((event) => event.phase === 'pointer_map_ready'));
  await page.evaluate(() => {
    const orbElement = document.querySelector('.ow-v2-orb-position');
    const logo = document.querySelector('[data-orb-target="orb-weaver-suite-logo"]');
    window.__orbProof.mountToken = `mount-${Math.random()}`;
    orbElement.dataset.proofMountToken = window.__orbProof.mountToken;
    logo.addEventListener('click', () => { window.__orbProof.logoClicks += 1; });
    window.__orbProofOriginalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  });

  const initial = await position(orb);
  await page.waitForTimeout(1300);
  const gliding = await position(orb);
  assert(distance(initial, gliding) > 2, 'ORB must visibly glide during normal active use');
  assert(Math.abs(gliding.opacity - 0.94) < 0.02, `active opacity must be approximately .94, got ${gliding.opacity}`);
  assert.equal(await orb.evaluate((element) => getComputedStyle(element).pointerEvents), 'auto');

  await page.waitForFunction(() => window.__orbProof.events.some((event) => event.phase === 'recording_started'));
  await page.waitForFunction(() => window.__orbProof.events.some((event) => event.phase === 'recording_stopped'), null, { timeout: 20000 });
  await page.waitForFunction(() => window.__orbProof.events.some((event) => event.phase === 'canonical_response'), null, { timeout: 120000 });
  await page.waitForFunction(() => window.__orbProof.events.some((event) => event.phase === 'playback_started'), null, { timeout: 20000 });
  const speechStart = await position(orb);
  await page.waitForTimeout(450);
  const speechHeld = await position(orb);
  assert(distance(speechStart, speechHeld) < 1.5, 'ORB must hold position during actual speech playback');
  await page.waitForFunction(() => window.__orbProof.events.some((event) => event.phase === 'playback_ended'), null, { timeout: 30000 });

  await page.waitForSelector('.ow-v2-pointer-bloom[data-orb-pointer-target="orb-weaver-suite-logo"]', { timeout: 30000 });
  await page.waitForFunction(() => {
    const morb = document.querySelector('.ow-v2-morb-pointer.visible:not(.dissolving)');
    return Boolean(morb && Number(getComputedStyle(morb).opacity) > 0.5 && document.querySelector('.ow-v2-pointer-bloom'));
  }, null, { timeout: 5000 });
  const guidanceProof = await page.evaluate(() => {
    const bloom = document.querySelector('.ow-v2-pointer-bloom');
    const target = document.querySelector('[data-orb-target="orb-weaver-suite-logo"]');
    const morb = document.querySelector('.ow-v2-morb-pointer');
    const orbElement = document.querySelector('.ow-v2-orb-position');
    const bloomRect = bloom.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    return {
      aligned: Math.abs((bloomRect.left + bloomRect.width / 2) - (targetRect.left + targetRect.width / 2)) < 2 &&
        Math.abs((bloomRect.top + bloomRect.height / 2) - (targetRect.top + targetRect.height / 2)) < 2,
      bloomRect: { left: bloomRect.left, top: bloomRect.top, width: bloomRect.width, height: bloomRect.height },
      targetRect: { left: targetRect.left, top: targetRect.top, width: targetRect.width, height: targetRect.height },
      morbVisible: getComputedStyle(morb).opacity !== '0',
      targetId: orbElement.dataset.orbLastGuidedTarget,
      geometrySource: orbElement.dataset.orbGuidanceSource,
      logoClicks: window.__orbProof.logoClicks,
    };
  });
  assert.equal(guidanceProof.aligned, true, `MORB pointer bloom must align to the verified live target: ${JSON.stringify(guidanceProof)}`);
  assert.equal(guidanceProof.morbVisible, true, 'MORB guidance must be visible');
  assert.equal(guidanceProof.targetId, 'orb-weaver-suite-logo');
  assert(['lidar_cache', 'live_dom'].includes(guidanceProof.geometrySource));
  assert.equal(guidanceProof.logoClicks, 0, 'guidance must not click or navigate');
  await page.waitForFunction(() => window.__orbProof.events.some((event) => event.phase === 'guidance_complete'), null, { timeout: 15000 });
  const afterGuidance = await position(orb);
  await page.waitForTimeout(2200);
  const resumed = await position(orb);
  const recoveryEvents = await page.evaluate(() => window.__orbProof.events.filter((event) => event.phase.startsWith('autonomous_resume')));
  assert(distance(afterGuidance, resumed) > 1.5, `autonomous movement must resume after guidance: ${JSON.stringify({ afterGuidance, resumed, recoveryEvents })}`);

  await page.waitForFunction(() => window.__orbProof.events.filter((event) => event.phase === 'recording_started').length >= 2, null, { timeout: 10000 });
  await page.waitForFunction(() => document.querySelector('.ow-v2-orb-position')?.dataset.orbVoiceState === 'listening');
  await page.evaluate(() => {
    navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('Proof pause', 'NotAllowedError'); };
  });
  await orb.locator('.ow-v2-orb-body').click({ position: { x: 70, y: 70 }, force: true });
  await page.waitForFunction(() => window.__orbProof.events.some((event) => event.phase === 'recording_cancelled'));

  await page.evaluate(() => { window.__orbProofTimeOffset = 5 * 60 * 1000 + 1000; });
  await page.waitForFunction(() => document.querySelector('.ow-v2-orb-position')?.dataset.orbResting === 'true', null, { timeout: 10000 });
  await page.waitForTimeout(1900);
  const resting = await position(orb);
  assert(Math.abs(resting.opacity - 0.55) < 0.02, `rest opacity must be .55, got ${resting.opacity}`);
  assert(resting.x > 1000 && resting.y < 180, 'rest destination must be upper-right');
  await page.evaluate(() => {
    window.__orbProofTimeOffset = 0;
    window.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
  });
  await page.waitForFunction(() => document.querySelector('.ow-v2-orb-position')?.dataset.orbResting === 'false');

  const mountToken = await orb.getAttribute('data-proof-mount-token');
  await page.getByLabel('Public site navigation').getByRole('link', { name: 'Features', exact: true }).click();
  await page.waitForURL('**/features');
  await page.waitForFunction(() => document.querySelector('.ow-v2-orb-position')?.dataset.orbRoute === '/features');
  assert.equal(await orb.getAttribute('data-proof-mount-token'), mountToken, 'ORB must remain mounted across public route transitions');
  const startupPlaybackCount = await page.evaluate(() => window.__orbProof.events.filter((event) => event.phase === 'playback_started').length);
  await page.getByRole('link', { name: 'Orb Weaver home', exact: true }).first().click();
  await page.waitForURL(`${FRONTEND_URL}/`);
  assert.equal(await orb.getAttribute('data-proof-mount-token'), mountToken);
  assert.equal(
    await page.evaluate(() => window.__orbProof.events.filter((event) => event.phase === 'playback_started').length),
    startupPlaybackCount,
    'route navigation must not replay startup speech',
  );

  if (await orb.getAttribute('data-orb-voice-state') === 'listening') {
    await orb.locator('.ow-v2-orb-body').click({ position: { x: 70, y: 70 }, force: true });
    await page.waitForFunction(() => document.querySelector('.ow-v2-orb-position')?.dataset.orbVoiceState !== 'listening');
  }
  const targetRecoveryBaseline = await page.evaluate(() => ({
    guidance: window.__orbProof.events.filter((event) => event.phase === 'guidance_complete').length,
    recovery: window.__orbProof.events.filter((event) => event.phase === 'guidance_recovery').length,
    recordings: window.__orbProof.events.filter((event) => event.phase === 'recording_started').length,
  }));
  await page.evaluate(() => {
    navigator.mediaDevices.getUserMedia = window.__orbProofOriginalGetUserMedia;
    document.querySelector('[data-orb-target="orb-weaver-suite-logo"]').style.display = 'none';
  });
  await orb.locator('.ow-v2-orb-body').click({ position: { x: 70, y: 70 }, force: true });
  await page.waitForFunction(
    (baseline) => window.__orbProof.events.filter((event) => event.phase === 'recording_started').length > baseline,
    targetRecoveryBaseline.recordings,
    { timeout: 15000 },
  );
  await page.waitForFunction(
    (baseline) => window.__orbProof.events.filter((event) => event.phase === 'guidance_recovery').length > baseline,
    targetRecoveryBaseline.recovery,
    { timeout: 120000 },
  );
  const lostTargetProof = await page.evaluate(() => ({
    recovery: window.__orbProof.events.filter((event) => event.phase === 'guidance_recovery').at(-1),
    logoClicks: window.__orbProof.logoClicks,
  }));
  assert(
    ['hidden', 'runtime_target_not_live_on_route', 'target_lost_before_arrival', 'target_lost_before_ping'].includes(lostTargetProof.recovery.reason),
    `target loss must report a verified recovery reason: ${JSON.stringify(lostTargetProof.recovery)}`,
  );
  assert.equal(lostTargetProof.logoClicks, 0, 'target loss must not trigger a click or navigation');
  await page.evaluate(() => {
    document.querySelector('[data-orb-target="orb-weaver-suite-logo"]').style.display = '';
  });
  await page.waitForFunction(
    (baseline) => window.__orbProof.events.filter((event) => event.phase === 'recording_started').length >= baseline + 2,
    targetRecoveryBaseline.recordings,
    { timeout: 15000 },
  );
  await page.waitForFunction(
    (baseline) => window.__orbProof.events.filter((event) => event.phase === 'guidance_complete').length > baseline,
    targetRecoveryBaseline.guidance,
    { timeout: 120000 },
  );
  const recoveredAt = await position(orb);
  await page.waitForTimeout(1300);
  assert(distance(recoveredAt, await position(orb)) > 1.2, 'normal movement must resume after target recovery guidance');
  await page.evaluate(() => {
    navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('Proof pause', 'NotAllowedError'); };
  });
  await page.waitForFunction(
    (baseline) => window.__orbProof.events.filter((event) => event.phase === 'recording_started').length >= baseline + 3,
    targetRecoveryBaseline.recordings,
    { timeout: 15000 },
  );
  await orb.locator('.ow-v2-orb-body').click({ position: { x: 70, y: 70 }, force: true });
  await page.waitForFunction(() => document.querySelector('.ow-v2-orb-position')?.dataset.orbVoiceState !== 'listening');

  await page.evaluate(() => {
    navigator.mediaDevices.getUserMedia = window.__orbProofOriginalGetUserMedia;
  });
  const beforeManual = await position(orb);
  await page.waitForTimeout(500);
  const movingBeforeManual = await position(orb);
  assert(distance(beforeManual, movingBeforeManual) > 0.8, 'ORB must be moving before optional manual engagement');
  await orb.locator('.ow-v2-orb-body').click({ position: { x: 70, y: 70 }, force: true });
  await page.waitForFunction(() => window.__orbProof.events.filter((event) => event.phase === 'recording_started').length >= 3);
  await page.waitForFunction(() => window.__orbProof.events.filter((event) => event.phase === 'playback_started').length >= 2, null, { timeout: 120000 });
  await orb.locator('.ow-v2-orb-body').click({ position: { x: 70, y: 70 }, force: true });
  await page.waitForFunction(() => window.__orbProof.events.some((event) => event.phase === 'playback_interrupted'));
  await page.evaluate(() => {
    navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('Proof complete', 'NotAllowedError'); };
  });
  const interruptedAt = await position(orb);
  await page.waitForTimeout(1100);
  const resumedAfterInterrupt = await position(orb);
  assert(distance(interruptedAt, resumedAfterInterrupt) > 1.5, 'movement must resume after manual speech interruption');

  const artifactDir = path.resolve(__dirname, '../test-artifacts');
  fs.mkdirSync(artifactDir, { recursive: true });
  await page.screenshot({ path: path.join(artifactDir, 'orb-mounted-gold-master.png'), fullPage: true });
  const evidence = await page.evaluate(() => ({
    events: window.__orbProof.events,
    finalRoute: location.pathname,
    mountToken: window.__orbProof.mountToken,
    logoClicks: window.__orbProof.logoClicks,
  }));
  fs.writeFileSync(path.join(artifactDir, 'orb-mounted-gold-master.json'), `${JSON.stringify(evidence, null, 2)}\n`);
  assert.equal(consoleErrors.length, 0, `browser console errors: ${consoleErrors.join(' | ')}`);
  console.log('ORB_MOUNTED_GOLD_MASTER_PROOF_OK');
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
