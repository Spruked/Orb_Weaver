const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const APP_URL = process.env.APP_URL || 'http://localhost:16667/';

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--autoplay-policy=no-user-gesture-required'] });
  try {
    for (const [last, random, blocked] of [['am-michael', 0, false], ['am-echo', 0, false], ['am-echo', .99, false], ['am-michael', 0, true]]) {
      const page = await browser.newPage();
      await page.addInitScript(({ last, random, blocked }) => {
        sessionStorage.setItem('orbweaver-last-intro-variant', last);
        Math.random = () => random;
        window.proof = { events: [], media: [], positions: [], captions: [], violations: [] };
        for (const name of ['orbweaver:startup-intro', 'orbweaver:mounted-runtime', 'orbweaver:startup-gate-complete']) {
          window.addEventListener(name, e => proof.events.push({ ...e.detail, t: performance.now() }));
        }
        const play = HTMLMediaElement.prototype.play;
        window.blockPlayback = blocked;
        HTMLMediaElement.prototype.play = function () {
          if (window.blockPlayback) return Promise.reject(new DOMException('Deliberate autoplay test', 'NotAllowedError'));
          const media = this;
          media.addEventListener('playing', () => proof.media.push({ phase: 'playing', src: media.currentSrc, rate: media.playbackRate, pitch: media.preservesPitch, duration: media.duration, t: performance.now() }), { once: true });
          media.addEventListener('ended', () => proof.media.push({ phase: 'ended', src: media.currentSrc, t: performance.now() }), { once: true });
          return play.call(this);
        };
        setInterval(() => {
          const orb = document.querySelector('.ow-v2-orb-position');
          if (orb) { const r = orb.getBoundingClientRect(); proof.positions.push({ x:r.x, y:r.y, t:performance.now() }); }
          const caption = document.querySelector('.ow-v2-orb-speech');
          if (caption) {
            proof.captions.push(caption.textContent);
            if (!orb?.contains(caption) || caption.querySelector('button,input,textarea') || getComputedStyle(caption).overflowY === 'auto') proof.violations.push('caption detached, interactive, or scrollable');
          }
          if (document.querySelector('.ow-tour-controls, .ow-v2-orb-speech-minimize')) proof.violations.push('legacy panel');
        }, 200);
      }, { last, random, blocked });
      await page.goto(APP_URL);
      if (blocked) {
        await page.locator('.ow-cut-startup-button').waitFor({ state: 'visible', timeout: 30000 });
        await page.evaluate(() => { window.blockPlayback = false; });
        await page.locator('.ow-cut-startup-button').click();
      }
      await page.waitForFunction(() => proof.events.some(e => e.phase === 'INTRO_AUDIO_ENDED'), null, { timeout: 60000 });
      await page.waitForFunction(() => proof.events.some(e => e.phase === 'tour_converse_received'), null, { timeout: 60000 });
      await page.waitForFunction(() => proof.events.some(e => e.phase === 'caption_completed'), null, { timeout: 60000 });
      const proof = await page.evaluate(() => window.proof);
      const start = proof.events.find(e => e.phase === 'INTRO_AUDIO_PLAYING');
      const end = proof.events.find(e => e.phase === 'INTRO_AUDIO_ENDED');
      const media = proof.media.find(e => e.phase === 'playing' && e.src === end.asset);
      assert.equal(media.rate, .9);
      assert.equal(media.pitch, true);
      assert.ok((end.t - start.t) / 1000 >= end.duration / .9 - .7, 'effective intro rate');
      assert.ok(!proof.events.some(e => e.phase === 'movement_policy_authorized' && e.t < end.t), 'startup motion must be held');
      assert.deepEqual(proof.violations, []);
      assert.equal(await page.locator('.ow-v2-orb-body').count(), 1);
      assert.equal(await page.locator('.ow-cut-startup-button').count(), 0);
      console.log(JSON.stringify({ variant: proof.events.find(e => e.phase === 'INTRO_AUDIO_REQUESTED').variant, blocked, introSeconds: (end.t-start.t)/1000, duration:end.duration, media:proof.media, captions: [...new Set(proof.captions)].slice(0,12), result:'PASS' }));
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
