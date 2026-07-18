const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
  const observations = [];
  const consoleErrors = [];
  const waitForObservations = async (count) => {
    const deadline = Date.now() + 5000;
    while (observations.length < count && Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 25));
    }
    assert(observations.length >= count, `expected ${count} bootstrap reports, received ${observations.length}`);
  };
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  await page.route('https://campaign.test/**', (route) => route.fulfill({
    contentType: 'text/html',
    body: '<!doctype html><title>Campaign Test</title><body style="margin:13px"><main><button id="start">Start campaign</button><a href="/about">About</a><div id="app"></div></main></body>',
  }));
  await page.route('https://runtime.test/api/orb/bootstrap', async (route) => {
    const request = route.request();
    const observation = JSON.parse(request.postData() || '{}');
    observations.push(observation);
    if (observation.page_context?.pathname === '/offline') {
      await route.fulfill({ contentType: 'application/json', body: '{' });
      return;
    }
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        schema: 'orb_weaver.loader_bootstrap.v1',
        status: 'ready',
        site: { site_id: 'orb-weaver-campaign', name: 'Campaign', domain: 'campaign.test', loader_version: '1' },
        site_world: { site_name: 'Campaign Test' },
        page_capsule: {},
        pointer_map: {
          record_count: 1,
          by_page: { '/': ['start'] },
          records: [{
            target_id: 'start',
            page_route: '/',
            semantic_locator: '#start',
            meaning: 'button: Start campaign',
            confidence_class: 'VERIFIED',
            runtime_policy: { may_point: true },
            structural_context: { tag: 'button' },
          }],
        },
        capabilities: {},
        endpoints: {},
      }),
    });
  });
  await page.route('https://runtime.test/api/orb/website-text', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ transcript: 'start campaign', spoken_output: 'I found it.', cognitive_pulse: { pointer_matches: [{ target_id: 'start' }] } }),
  }));
  const loaderPath = path.resolve(__dirname, '../public/orb-loader.js');
  const loaderSource = fs.readFileSync(loaderPath, 'utf8');
  const factoryAsset = fs.readFileSync(path.resolve(__dirname, '../public/orb-skins/tuxorb.png'));
  await page.route('https://runtime.test/orb-loader.js', (route) => route.fulfill({
    contentType: 'application/javascript',
    body: loaderSource,
  }));
  await page.route('https://runtime.test/orb-skins/tuxorb.png', (route) => route.fulfill({
    contentType: 'image/png', body: factoryAsset,
  }));
  await page.route('https://runtime.test/custom-skin.png', (route) => route.fulfill({
    contentType: 'image/png', headers: { 'Access-Control-Allow-Origin': '*' }, body: factoryAsset,
  }));
  await page.route('https://runtime.test/broken-custom-skin.png', (route) => route.fulfill({
    contentType: 'image/png', headers: { 'Access-Control-Allow-Origin': '*' }, body: Buffer.from('not-a-valid-png'),
  }));
  await page.goto('https://campaign.test/');
  await page.evaluate(() => {
    window.__fakeSocketStats = { created: 0, closed: 0 };
    class FakeWebSocket {
      static OPEN = 1;
      readyState = 0;
      listeners = {};
      constructor() { window.__fakeSocketStats.created += 1; setTimeout(() => { this.readyState = 1; (this.listeners.open || []).forEach((fn) => fn()); }, 0); }
      addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
      send() {}
      close() { this.readyState = 3; window.__fakeSocketStats.closed += 1; }
    }
    window.WebSocket = FakeWebSocket;
  });
  const installLoader = () => page.evaluate(() => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://runtime.test/orb-loader.js';
    script.dataset.orbSiteId = 'orb-weaver-campaign';
    script.dataset.orbRuntime = 'https://runtime.test/api/orb';
    script.dataset.orbWs = 'wss://runtime.test/ws/orb';
    script.dataset.orbVersion = '1';
    script.dataset.orbDebug = 'true';
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  }));

  await installLoader();
  await page.waitForFunction(() => window.OrbWeaver?.getStatus().online === true);
  await page.waitForFunction(() => document.querySelector('#orb-weaver-universal-root')?.shadowRoot?.querySelector('[data-skin]')?.naturalWidth === 512);
  assert.equal(await page.locator('#orb-weaver-universal-root').count(), 1, 'one script must mount one ORB');
  assert.equal(await page.evaluate(() => !!document.querySelector('#orb-weaver-universal-root').shadowRoot), true, 'mount must use Shadow DOM');
  assert.deepEqual(await page.evaluate(() => window.OrbWeaver.getStatus()), {
    mounted: true,
    online: true,
    route: '/',
    skinId: 'orb_factory_default_v1',
    customizationState: 'FACTORY_DEFAULT',
  }, 'Factory Default must be the first active identity');
  assert.equal(await page.evaluate(() => document.querySelector('#orb-weaver-universal-root').shadowRoot.querySelector('[data-skin]').src), 'https://runtime.test/orb-skins/tuxorb.png');
  assert.deepEqual(await page.evaluate(() => {
    const root = document.querySelector('#orb-weaver-universal-root').shadowRoot;
    const toggle = root.querySelector('[data-toggle]');
    const skin = root.querySelector('[data-skin]');
    const sizes = [48, 84, 128].map((size) => {
      toggle.style.width = `${size}px`;
      toggle.style.height = `${size}px`;
      const rect = skin.getBoundingClientRect();
      return { size, width: Math.round(rect.width), height: Math.round(rect.height) };
    });
    toggle.style.width = '';
    toggle.style.height = '';
    return { naturalWidth: skin.naturalWidth, naturalHeight: skin.naturalHeight, objectFit: getComputedStyle(skin).objectFit, sizes };
  }), {
    naturalWidth: 512,
    naturalHeight: 512,
    objectFit: 'contain',
    sizes: [{ size: 48, width: 48, height: 48 }, { size: 84, width: 84, height: 84 }, { size: 128, width: 128, height: 128 }],
  }, 'Factory artwork must preserve its full aspect inside every supported ORB size');
  assert.equal(await page.evaluate(() => {
    const root = document.querySelector('#orb-weaver-universal-root').shadowRoot;
    root.querySelector('[data-toggle]').click();
    return !root.querySelector('[data-panel]').hidden && !root.querySelector('[data-voice]').disabled;
  }), true, 'Factory ORB must remain clickable and voice-capable');
  assert.equal(observations[0].page_context.host, 'campaign.test');
  assert.equal(observations[0].page_context.pathname, '/');
  assert.equal(observations[0].page_context.title, 'Campaign Test');
  assert.equal(observations[0].page_context.viewport.width, 1200);
  assert(observations[0].page_context.visible_controls.some((item) => item.text === 'Start campaign'));

  await installLoader();
  assert.equal(await page.locator('#orb-weaver-universal-root').count(), 1, 'loading twice must not duplicate the ORB');

  await page.evaluate(() => history.pushState({}, '', '/next'));
  await page.waitForFunction(() => window.OrbWeaver?.getStatus().route === '/next');
  await waitForObservations(2);
  await page.evaluate(() => history.replaceState({}, '', '/final'));
  await page.waitForFunction(() => window.OrbWeaver?.getStatus().route === '/final');
  await waitForObservations(3);
  await page.goBack();
  await page.waitForFunction(() => window.location.pathname === '/');
  await waitForObservations(4);
  assert(observations.length >= 4, 'SPA route changes must be reported to bootstrap');

  await page.evaluate(() => history.pushState({}, '', '/offline'));
  await page.waitForFunction(() => window.OrbWeaver?.getStatus().online === false);
  await waitForObservations(5);
  assert.deepEqual(await page.evaluate(() => ({
    mounts: document.querySelectorAll('#orb-weaver-universal-root').length,
    skinId: window.OrbWeaver.getStatus().skinId,
    socketsClosed: window.__fakeSocketStats.closed,
  })), { mounts: 1, skinId: 'orb_factory_default_v1', socketsClosed: 0 }, 'offline state must retain one Factory ORB and the existing WebSocket');
  await page.evaluate(() => history.pushState({}, '', '/reconnected'));
  await page.waitForFunction(() => window.OrbWeaver?.getStatus().online === true);
  await waitForObservations(6);
  assert.equal(await page.evaluate(() => window.OrbWeaver.getStatus().skinId), 'orb_factory_default_v1', 'runtime reconnect must retain Factory Default');
  await page.evaluate(() => history.replaceState({}, '', '/'));
  await waitForObservations(7);

  assert.equal(await page.evaluate(() => {
    return window.OrbWeaver.pointTo('start');
  }), true, 'verified pointer target should guide');
  assert.equal(await page.evaluate(() => document.body.style.margin), '13px', 'loader must not modify host layout');

  const bootstrapReportsBeforeSkin = observations.length;
  const skinCheckpoint = await page.evaluate(() => {
    window.__orbHandleBeforeSkin = window.OrbWeaver;
    const root = document.querySelector('#orb-weaver-universal-root').shadowRoot;
    return {
      animationName: getComputedStyle(root.querySelector('[data-toggle]')).animationName,
      socketsCreated: window.__fakeSocketStats.created,
      socketsClosed: window.__fakeSocketStats.closed,
    };
  });
  assert.equal(await page.evaluate(() => window.OrbWeaver.setSkin({
    skinId: 'custom-proof', bodyAssetUrl: 'https://runtime.test/custom-skin.png', customizationState: 'CUSTOM',
  })), true, 'a valid custom skin should hot-swap without reinstalling');
  assert.equal(await page.evaluate(() => window.OrbWeaver.getStatus().skinId), 'custom-proof');
  assert.equal(await page.evaluate(() => window.OrbWeaver.setSkin({
    skinId: 'broken-proof', bodyAssetUrl: 'https://runtime.test/broken-custom-skin.png', customizationState: 'CUSTOM',
  })), false, 'a failed custom skin must be rejected');
  assert.deepEqual(await page.evaluate(() => ({
    skinId: window.OrbWeaver.getStatus().skinId,
    customizationState: window.OrbWeaver.getStatus().customizationState,
  })), { skinId: 'orb_factory_default_v1', customizationState: 'FACTORY_DEFAULT' }, 'custom failure must restore Factory Default');
  await page.evaluate(() => window.OrbWeaver.setSkin({
    skinId: 'custom-proof', bodyAssetUrl: 'https://runtime.test/custom-skin.png', customizationState: 'CUSTOM',
  }));
  await page.evaluate(() => window.OrbWeaver.restoreFactory());
  assert.equal(await page.evaluate(() => window.OrbWeaver.getStatus().skinId), 'orb_factory_default_v1', 'explicit rollback must restore Factory Default');
  assert.deepEqual(await page.evaluate(() => {
    const root = document.querySelector('#orb-weaver-universal-root').shadowRoot;
    return {
      sameRuntimeHandle: window.OrbWeaver === window.__orbHandleBeforeSkin,
      animationName: getComputedStyle(root.querySelector('[data-toggle]')).animationName,
      socketsCreated: window.__fakeSocketStats.created,
      socketsClosed: window.__fakeSocketStats.closed,
    };
  }), {
    sameRuntimeHandle: true,
    animationName: skinCheckpoint.animationName,
    socketsCreated: skinCheckpoint.socketsCreated,
    socketsClosed: 0,
  }, 'skin PATCH operations must not restart runtime, alter motion, or disconnect WebSocket');
  assert.equal(observations.length, bootstrapReportsBeforeSkin, 'skin PATCH operations must not rebuild Site World or Pointer Map');

  await page.evaluate(() => window.OrbWeaver.unmount());
  assert.equal(await page.locator('#orb-weaver-universal-root').count(), 0, 'unmount must remove the ORB');
  await installLoader();
  await page.waitForFunction(() => !!window.OrbWeaver);
  assert.equal(await page.locator('#orb-weaver-universal-root').count(), 1, 'loader must reinitialize after clean removal');
  if (consoleErrors.length) console.error('ORB smoke console errors:', consoleErrors);
  assert.deepEqual(consoleErrors, [], 'loader must not emit console security/runtime errors in the approved test');
  console.log(JSON.stringify({
    status: 'passed',
    checks: 25,
    bootstrap_reports: observations.length,
    console_errors: consoleErrors.length,
  }, null, 2));
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
