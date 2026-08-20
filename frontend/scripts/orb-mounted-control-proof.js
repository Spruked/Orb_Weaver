const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const FRONTEND_URL = process.env.ORB_PROOF_FRONTEND_URL || 'http://127.0.0.1:16511';
const AUDIO_FIXTURE = process.env.ORB_CONTROL_AUDIO_FIXTURE || '/tmp/orb-weaver-move-command-with-silence.wav';
const position = (orb) => orb.evaluate((element) => {
  const rect = element.getBoundingClientRect();
  return { x: rect.left, y: rect.top };
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
  const context = await browser.newContext({ viewport: { width: 1280, height: 820 }, permissions: ['microphone'] });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  await page.addInitScript(() => {
    window.__orbControlProof = { events: [], manualClicks: 0 };
    window.addEventListener('orbweaver:mounted-runtime', (event) => window.__orbControlProof.events.push(event.detail));
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
  await page.waitForFunction(() => window.__orbControlProof.events.some((event) => event.phase === 'recording_started'));
  assert.equal(await page.evaluate(() => window.__orbControlProof.manualClicks), 0, 'primary control turn must begin without a click');
  await page.waitForFunction(() => window.__orbControlProof.events.some((event) => event.phase === 'canonical_response'), null, { timeout: 120000 });
  const canonical = await page.evaluate(() => window.__orbControlProof.events.find((event) => event.phase === 'canonical_response'));
  assert.equal(canonical.transcript.replace(/[^a-z ]/gi, '').toLowerCase(), 'weaver move out of the way');
  assert.equal(canonical.sourceLane, 'control');
  assert.equal(canonical.controlCommand, 'move_out_of_way');
  assert.equal(canonical.ttsProvider, 'kokoro');
  await page.waitForFunction(() => window.__orbControlProof.events.some((event) => event.phase === 'playback_ended'), null, { timeout: 30000 });
  await page.waitForFunction(() => window.__orbControlProof.events.some((event) => event.phase === 'control_motion_complete'), null, { timeout: 10000 });
  const afterMove = await position(orb);
  const controlEvents = await page.evaluate(() => window.__orbControlProof.events);
  const started = controlEvents.find((event) => event.phase === 'control_motion_started');
  const completed = controlEvents.find((event) => event.phase === 'control_motion_complete');
  assert(started && completed && completed.at > started.at, 'control motion must complete cleanly');
  const moved = distance(started.current, completed.destination);
  assert(moved >= 55 && moved <= 165, `move-out command must be a short local glide, got ${moved}px`);
  assert(distance(afterMove, completed.destination) < 3, 'rendered ORB must finish at the commanded destination');
  assert(afterMove.x >= 8 && afterMove.y >= 96 && afterMove.x <= 1280 - 156 - 8 && afterMove.y <= 820 - 156 - 8);
  assert(completed.at - started.at >= 1000 && completed.at - started.at <= 2600, 'control glide must be smooth and brief');
  await page.waitForFunction(() => window.__orbControlProof.events.some((event) => event.phase === 'autonomous_resume_started'), null, { timeout: 5000 });
  await page.waitForFunction(() => window.__orbControlProof.events.filter((event) => event.phase === 'recording_started').length >= 2, null, { timeout: 10000 });

  const artifactDir = path.resolve(__dirname, '../test-artifacts');
  fs.mkdirSync(artifactDir, { recursive: true });
  await page.screenshot({ path: path.join(artifactDir, 'orb-mounted-control-proof.png') });
  fs.writeFileSync(path.join(artifactDir, 'orb-mounted-control-proof.json'), `${JSON.stringify({ canonical, moved, events: controlEvents }, null, 2)}\n`);
  assert.equal(consoleErrors.length, 0, `browser console errors: ${consoleErrors.join(' | ')}`);
  console.log('ORB_MOUNTED_CONTROL_PROOF_OK');
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
