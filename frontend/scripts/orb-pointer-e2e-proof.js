const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
  const consoleErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });

  await page.route('https://campaign.test/**', (route) => route.fulfill({
    contentType: 'text/html',
    body: `<!doctype html>
      <title>ORB Pointer Proof</title>
      <body style="margin:13px">
        <main>
          <div style="height:1300px">Proof spacer</div>
          <section id="approved"><button class="start-action">Start campaign</button></section>
        </main>
      </body>`,
  }));

  await page.route('https://runtime.test/api/orb/bootstrap', (route) => route.fulfill({
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
          target_type: 'button',
          semantic_locator: '.start-action',
          meaning: 'button: Start campaign',
          content_fingerprint: 'start-campaign-proof',
          allowed_actions: ['point'],
          confidence: 0.99,
          confidence_class: 'VERIFIED',
          pointer_health: 'OWNER_VERIFIED',
          runtime_policy: { may_point: true, may_click: false, may_navigate: false },
          structural_context: { tag: 'button', parent_locator: '#approved' },
        }],
      },
      pointer_guidance: {
        status: 'COMPLETE',
        target_guidance_available: true,
        safe_pointer_count: 1,
        blocked_pointer_count: 0,
        map_recovery_required: true,
        automatic_recovery_attempts_maximum: 1,
      },
      capabilities: {},
      endpoints: {},
    }),
  }));

  let textRequests = 0;
  await page.route('https://runtime.test/api/orb/website-text', async (route) => {
    textRequests += 1;
    const request = JSON.parse(route.request().postData() || '{}');
    assert.equal(request.transcript, 'start campaign', 'visitor question must reach Website ORB runtime');
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        transcript: 'start campaign',
        spoken_output: 'I found it.',
        llm_source: 'site-world-route',
        suggested_route: '/',
        cognitive_pulse: { pointer_matches: [{ target_id: 'start' }] },
      }),
    });
  });

  const loaderSource = fs.readFileSync(path.resolve(__dirname, '../public/orb-loader.js'), 'utf8');
  const factoryAsset = fs.readFileSync(path.resolve(__dirname, '../public/orb-skins/tuxorb.png'));
  await page.route('https://runtime.test/orb-loader.js', (route) => route.fulfill({
    contentType: 'application/javascript', body: loaderSource,
  }));
  await page.route('https://runtime.test/orb-skins/tuxorb.png', (route) => route.fulfill({
    contentType: 'image/png', body: factoryAsset,
  }));

  await page.goto('https://campaign.test/');
  await page.evaluate(() => {
    window.__pointerProof = { clicks: 0 };
    document.querySelector('.start-action').addEventListener('click', () => { window.__pointerProof.clicks += 1; });
    class FakeWebSocket {
      static OPEN = 1;
      readyState = 0;
      listeners = {};
      constructor() { setTimeout(() => { this.readyState = 1; (this.listeners.open || []).forEach((fn) => fn()); }, 0); }
      addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
      send() {}
      close() { this.readyState = 3; }
    }
    window.WebSocket = FakeWebSocket;
  });

  await page.evaluate(() => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://runtime.test/orb-loader.js';
    script.dataset.orbSiteId = 'orb-weaver-campaign';
    script.dataset.orbRuntime = 'https://runtime.test/api/orb';
    script.dataset.orbWs = 'wss://runtime.test/ws/orb';
    script.dataset.orbVersion = '1';
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  }));

  await page.waitForFunction(() => window.OrbWeaver?.getStatus().online === true);
  const locationBefore = page.url();
  await page.evaluate(() => window.OrbWeaver.ask('start campaign'));
  await page.waitForFunction(() => {
    const root = document.querySelector('#orb-weaver-universal-root')?.shadowRoot;
    return root?.querySelector('[data-pointer]')?.dataset.visible === 'true';
  });

  const proof = await page.evaluate(() => {
    const root = document.querySelector('#orb-weaver-universal-root').shadowRoot;
    const pointer = root.querySelector('[data-pointer]').getBoundingClientRect();
    const target = document.querySelector('#approved .start-action').getBoundingClientRect();
    const orb = root.querySelector('[data-toggle]').getBoundingClientRect();
    return {
      pointerAligned: Math.abs(pointer.left - (target.left - 7)) < 2 && Math.abs(pointer.top - (target.top - 7)) < 2,
      orbTraveled: orb.left < window.innerWidth - orb.width - 18,
      scrolledToTarget: window.scrollY > 400,
      clicks: window.__pointerProof.clicks,
      output: root.querySelector('[data-output]').textContent,
    };
  });
  assert.deepEqual(proof, {
    pointerAligned: true,
    orbTraveled: true,
    scrolledToTarget: true,
    clicks: 0,
    output: 'I found it.',
  }, 'question → runtime target → live DOM → scroll → geometry → ORB travel → pointer ping must complete without click');
  assert.equal(textRequests, 1, 'question must execute exactly one Website ORB text request');
  assert.equal(page.url(), locationBefore, 'guidance must not navigate or click');

  const artifactDir = path.resolve(__dirname, '../test-artifacts');
  fs.mkdirSync(artifactDir, { recursive: true });
  await page.screenshot({ path: path.join(artifactDir, 'orb-pointer-e2e-proof.png') });

  await page.evaluate(() => document.querySelector('#approved .start-action').remove());
  await page.evaluate(() => window.OrbWeaver.ask('start campaign'));
  await page.waitForFunction(() => {
    const root = document.querySelector('#orb-weaver-universal-root')?.shadowRoot;
    return root?.querySelector('[data-output]')?.textContent.includes('could not verify that target');
  });
  const lossProof = await page.evaluate(() => {
    const root = document.querySelector('#orb-weaver-universal-root').shadowRoot;
    return {
      pointerVisible: root.querySelector('[data-pointer]').dataset.visible === 'true',
      clicks: window.__pointerProof.clicks,
      output: root.querySelector('[data-output]').textContent,
    };
  });
  assert.equal(lossProof.pointerVisible, false, 'target loss must suppress Point/Ping');
  assert.equal(lossProof.clicks, 0, 'target loss must never click');
  assert.equal(lossProof.output, 'I could not verify that target on this page, so I will not point to it or take action.');
  assert.equal(consoleErrors.length, 0, `browser console errors: ${consoleErrors.join(' | ')}`);

  console.log('ORB_POINTER_E2E_PROOF_OK');
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
