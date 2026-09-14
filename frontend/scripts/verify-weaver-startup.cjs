const assert = require('node:assert/strict');
const { chromium } = require('playwright');

const APP_URL = process.env.APP_URL || 'http://127.0.0.1:16667/';
const SESSION_TOKEN_KEY = 'orb_weaver_customer_session_token';
const LEGACY_TOKEN_KEY = 'orb_weaver_customer_token';
const INTRO_VARIANTS = ['am-echo', 'am-michael', 'kokoro-host'];
const REQUIRE_FIRST_TOUR_SPEECH = process.env.REQUIRE_FIRST_TOUR_SPEECH === '1';

const installProofRecorder = async (page, { blockFirstIntroPlayback = false } = {}) => {
  await page.route('**/api/auth/me', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ id: 'dev-account', email: 'bryan@development.local', name: 'Bryan' }),
  }));
  await page.addInitScript(({ sessionTokenKey, legacyTokenKey, blockFirstIntroPlayback }) => {
    window.sessionStorage.setItem(sessionTokenKey, 'development-browser-session-token');
    window.localStorage.removeItem(legacyTokenKey);
    window.__weaverProof = { startup: [], runtime: [], intro: [], media: [], blockedAttempts: 0 };

    window.addEventListener('orbweaver:startup-trace', (event) => {
      window.__weaverProof.startup.push({ ...event.detail, observedAt: performance.now() });
    });
    window.addEventListener('orbweaver:mounted-runtime', (event) => {
      window.__weaverProof.runtime.push({ ...event.detail, observedAt: performance.now() });
    });
    window.addEventListener('orbweaver:startup-intro', (event) => {
      window.__weaverProof.intro.push({ ...event.detail, observedAt: performance.now() });
    });

    const nativePlay = HTMLMediaElement.prototype.play;
    const observedMedia = new WeakSet();
    let shouldBlockIntro = blockFirstIntroPlayback;
    HTMLMediaElement.prototype.play = function patchedPlay() {
      const media = this;
      const source = media.currentSrc || media.src || '';
      const looksLikeAudibleIntro = !media.muted && (
        source.includes('weaver-showroom-intro') ||
        source.includes('/api/orb/tts/') ||
        source.includes('/api/orb/media/')
      );
      if (shouldBlockIntro && looksLikeAudibleIntro) {
        shouldBlockIntro = false;
        window.__weaverProof.blockedAttempts += 1;
        return Promise.reject(new DOMException('Deliberate startup autoplay denial', 'NotAllowedError'));
      }
      if (!observedMedia.has(media)) {
        observedMedia.add(media);
        media.addEventListener('playing', () => window.__weaverProof.media.push({
          phase: 'playing', source: media.currentSrc || media.src, currentTime: media.currentTime,
          duration: media.duration, muted: media.muted, volume: media.volume, observedAt: performance.now(),
        }));
        media.addEventListener('ended', () => window.__weaverProof.media.push({
          phase: 'ended', source: media.currentSrc || media.src, currentTime: media.currentTime,
          duration: media.duration, muted: media.muted, volume: media.volume, observedAt: performance.now(),
        }));
      }
      return nativePlay.call(media);
    };
  }, { sessionTokenKey: SESSION_TOKEN_KEY, legacyTokenKey: LEGACY_TOKEN_KEY, blockFirstIntroPlayback });
};

const startupState = (proof, state) => proof.startup.find((event) => event.state === state);
const runtimePhase = (proof, phase) => proof.runtime.find((event) => event.phase === phase);

const assertCompleteIntro = async (page, proof, variant) => {
  const selected = startupState(proof, 'selected_intro');
  const begun = startupState(proof, 'startup_begun');
  const orbMounted = startupState(proof, 'orb_mounted');
  const allCompleted = startupState(proof, 'all_intro_lines_completed');
  const introComplete = startupState(proof, 'intro_complete_set');
  const introStarted = proof.intro.find((event) => event.phase === 'INTRO_AUDIO_PLAYING');
  const introEnded = proof.intro.find((event) => event.phase === 'INTRO_AUDIO_ENDED');

  assert.equal(selected?.intro_id, variant, `selected ${variant}`);
  assert.ok(begun && orbMounted, 'landing and ORB startup were observed');
  assert.ok(introStarted && introEnded, 'intro media started and ended');
  assert.ok(introEnded.observedAt > introStarted.observedAt, 'intro completion followed playback start');
  assert.ok(allCompleted && introComplete, 'all intro lines completed before startup release');
  assert.ok(introComplete.observedAt >= allCompleted.observedAt, 'introComplete followed all line completion');
  assert.equal(await page.locator('.ow-v2-orb-body').count(), 1, 'exactly one ORB remained mounted');

  const lineCount = allCompleted.line_count;
  assert.equal(proof.startup.filter((event) => event.state === 'intro_line_synthesis_requested').length, lineCount);
  assert.equal(proof.startup.filter((event) => event.state === 'intro_line_audio_ready').length, lineCount);
  assert.equal(proof.startup.filter((event) => event.state === 'intro_line_playback_started').length, lineCount);
  assert.equal(proof.startup.filter((event) => event.state === 'intro_line_playback_ended').length, lineCount);
};

const runOverrideEnabledVariant = async (browser, variant, blockFirstIntroPlayback = false) => {
  const page = await browser.newPage();
  await installProofRecorder(page, { blockFirstIntroPlayback });
  const url = new URL(APP_URL);
  url.searchParams.set('orbStartupReset', '1');
  url.searchParams.set('orbIntroVariant', variant);
  url.searchParams.set('orbDevFullTour', '1');
  await page.goto(url.toString(), { waitUntil: 'domcontentloaded' });

  if (blockFirstIntroPlayback) {
    await page.waitForFunction(() => window.__weaverProof.intro.some((event) => event.phase === 'INTRO_AUTOPLAY_BLOCKED'));
    assert.equal((await page.evaluate(() => window.__weaverProof)).startup.some((event) => event.state === 'intro_complete_set'), false);
    await page.locator('.ow-v2-orb-speaker').dispatchEvent('click');
  }

  await page.waitForFunction(() => window.__weaverProof.startup.some((event) => event.state === 'intro_complete_set'), null, { timeout: 90000 });
  await page.waitForFunction(() => window.__weaverProof.startup.some((event) => event.state === 'first_governed_tour_request'), null, { timeout: 30000 });
  await page.waitForTimeout(1200);
  const proof = await page.evaluate(() => window.__weaverProof);
  await assertCompleteIntro(page, proof, variant);

  const overrideState = startupState(proof, 'full_tour_development_override');
  const eligibility = startupState(proof, 'tour_eligibility_result');
  const tourInitialized = startupState(proof, 'tour_initialization');
  assert.equal(overrideState?.active, true, 'development override was active');
  assert.equal(eligibility?.authenticated, true, 'current browser session was authenticated');
  assert.equal(eligibility?.eligible, true, 'authenticated session was admitted only by override');
  assert.ok(tourInitialized, 'governed tour initialized');
  assert.ok(tourInitialized.observedAt >= startupState(proof, 'intro_complete_set').observedAt, 'tour initialized after intro completion');
  assert.ok(runtimePhase(proof, 'target_one_tour_controller_initialized'), 'existing governed Target One controller initialized');

  const tourSpeechStarted = Boolean(startupState(proof, 'first_tour_speech_started'));
  if (REQUIRE_FIRST_TOUR_SPEECH) assert.equal(tourSpeechStarted, true, 'first governed tour speech started');
  const result = {
    variant,
    autoplayRecovery: blockFirstIntroPlayback,
    blockedAttempts: proof.blockedAttempts,
    introLineCount: startupState(proof, 'all_intro_lines_completed').line_count,
    oneOrb: true,
    overrideActive: true,
    governedTourInitialized: true,
    firstTourRequest: true,
    firstTourAudioReady: Boolean(startupState(proof, 'first_tour_audio_ready')),
    firstTourSpeechStarted: tourSpeechStarted,
  };
  await page.close();
  return result;
};

const runOverrideDisabledAccountCheck = async (browser) => {
  const page = await browser.newPage();
  await installProofRecorder(page);
  const url = new URL(APP_URL);
  url.searchParams.set('orbStartupReset', '1');
  url.searchParams.set('orbIntroVariant', 'am-echo');
  await page.goto(url.toString(), { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.__weaverProof.startup.some((event) => event.state === 'intro_complete_set'), null, { timeout: 90000 });
  await page.waitForFunction(() => window.__weaverProof.runtime.some((event) => event.phase === 'landing_tour_skipped_authenticated'), null, { timeout: 10000 });
  const proof = await page.evaluate(() => window.__weaverProof);
  await assertCompleteIntro(page, proof, 'am-echo');
  assert.equal(startupState(proof, 'full_tour_development_override')?.active, false);
  assert.equal(runtimePhase(proof, 'target_one_tour_controller_initialized'), undefined);
  assert.equal(startupState(proof, 'tour_initialization'), undefined);
  assert.equal(await page.evaluate((key) => window.localStorage.getItem(key), LEGACY_TOKEN_KEY), null);
  await page.close();
  return { authenticated: true, overrideActive: false, introCompleted: true, governedTourSkipped: true, oneOrb: true };
};

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--autoplay-policy=no-user-gesture-required'] });
  try {
    const results = [];
    for (const variant of INTRO_VARIANTS) results.push(await runOverrideEnabledVariant(browser, variant));
    results.push(await runOverrideEnabledVariant(browser, 'am-echo', true));
    results.push(await runOverrideDisabledAccountCheck(browser));
    console.log(JSON.stringify({ result: 'PASS', requireFirstTourSpeech: REQUIRE_FIRST_TOUR_SPEECH, cases: results }, null, 2));
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
