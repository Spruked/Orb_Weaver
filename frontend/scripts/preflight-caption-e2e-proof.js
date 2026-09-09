const assert = require('assert');
const { chromium } = require('playwright');

const APP_URL = process.env.APP_URL || 'http://127.0.0.1:16667';
const SCAN_URL = process.env.PREFLIGHT_URL || 'https://www.spruked.com';
const INTERRUPT_PLAYBACK = process.env.CAPTION_INTERRUPT === '1';

const waitForPhase = (page, phase, timeout = 90000) => page.waitForFunction(
  (expected) => (window.__orbCaptionEvents || []).some((event) => event.phase === expected),
  phase,
  { timeout },
);

let diagnosticPage;
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  diagnosticPage = page;
  const errors = [];
  await page.addInitScript(() => {
    window.__orbCaptionEvents = [];
    window.addEventListener('orbweaver:mounted-runtime', (event) => {
      window.__orbCaptionEvents.push({ at: Date.now(), ...event.detail });
    });
  });
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  page.on('pageerror', (error) => errors.push(error.message));

  await page.goto(`${APP_URL}/preflight`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.getByLabel('Website URL').fill(SCAN_URL);
  await page.getByRole('button', { name: 'Run Preflight' }).click();
  await page.locator('[data-preflight-result="true"]').waitFor({ state: 'visible', timeout: 90000 });

  await waitForPhase(page, 'preflight_articulation_received');
  await waitForPhase(page, 'caption_started');
  assert.equal(await page.locator('.ow-v2-orb-speech').count(), 0, 'no future narration may render at audio start');

  await waitForPhase(page, 'caption_progressed');
  const whileSpeaking = await page.locator('.ow-v2-orb-speech').evaluate((node) => ({
    text: node.textContent || '',
    state: node.getAttribute('data-orb-caption-state'),
    lineClamp: getComputedStyle(node.querySelector('span')).webkitLineClamp,
  }));
  assert.equal(whileSpeaking.state, 'speaking');
  assert(whileSpeaking.text.trim().length > 0, 'the caption must reveal spoken progress');
  assert.equal(whileSpeaking.lineClamp, '4', 'the live caption may occupy no more than four readable lines');

  if (INTERRUPT_PLAYBACK) {
    await page.locator('.ow-v2-orb-body').click({ force: true });
    await waitForPhase(page, 'caption_stopped', 10000);
    const interruption = await page.evaluate(() => {
      const events = window.__orbCaptionEvents || [];
      const stoppedAt = events.findLastIndex((event) => event.phase === 'caption_stopped');
      return {
        captionState: document.querySelector('.ow-v2-orb-speech')?.getAttribute('data-orb-caption-state'),
        completedAfterStop: events.slice(stoppedAt + 1).some((event) => event.phase === 'caption_completed'),
        stopped: events[stoppedAt],
      };
    });
    assert.equal(interruption.captionState, 'interrupted', 'an interrupted narration must never become a complete transcript');
    assert.equal(interruption.completedAfterStop, false, 'interruption must stop caption progression immediately');
    assert(interruption.stopped.revealedCharacters < interruption.stopped.fullCharacters, 'only already-spoken text may remain after interruption');
    assert.equal(errors.length, 0, `browser console errors: ${errors.join(' | ')}`);
    console.log('PREFLIGHT_CAPTION_INTERRUPT_E2E_PROOF_OK');
    await browser.close();
    return;
  }

  await waitForPhase(page, 'caption_completed', 120000);
  await page.getByRole('button', { name: 'Read complete Weaver transcript' }).waitFor({ state: 'visible', timeout: 10000 });
  await page.getByRole('button', { name: 'Read complete Weaver transcript' }).click();
  const expandedText = await page.locator('.ow-v2-orb-speech span').textContent();
  const completedCaption = await page.evaluate(() => (window.__orbCaptionEvents || []).findLast((event) => event.phase === 'caption_completed'));
  assert((expandedText || '').trim().length === completedCaption.fullCharacters, 'the complete transcript must require deliberate expansion');
  assert.equal(errors.length, 0, `browser console errors: ${errors.join(' | ')}`);

  console.log('PREFLIGHT_CAPTION_E2E_PROOF_OK');
  await browser.close();
})().catch(async (error) => {
  console.error(error);
  if (diagnosticPage && !diagnosticPage.isClosed()) {
    console.error('PREFLIGHT_CAPTION_E2E_DIAGNOSTICS', JSON.stringify(await diagnosticPage.evaluate(() => ({
      route: window.location.pathname + window.location.search,
      caption: document.querySelector('.ow-v2-orb-speech')?.textContent || null,
      captionState: document.querySelector('.ow-v2-orb-speech')?.getAttribute('data-orb-caption-state') || null,
      events: window.__orbCaptionEvents || [],
    }))));
  }
  process.exit(1);
});
