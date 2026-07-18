'use strict';

const fs = require('fs');
const path = require('path');

function loadPlaywright() {
  const candidates = ['playwright', '/app/node_modules/playwright', path.resolve(__dirname, '../../../frontend/node_modules/playwright')];
  for (const candidate of candidates) {
    try { return require(candidate); } catch (_) { /* try next installation */ }
  }
  throw new Error('Playwright is not installed for pointer recovery');
}

const { chromium } = loadPlaywright();
const urls = JSON.parse(process.argv[2] || '[]');
const outputFile = process.argv[3];
const renderPasses = Math.max(2, Number(process.argv[4] || 2));
const outputDir = process.argv[5];
const viewports = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
];

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function stabilize(page) {
  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready.catch(() => undefined);
    const animations = document.getAnimations().filter((item) => item.playState === 'running');
    await Promise.race([
      Promise.allSettled(animations.map((item) => item.finished)),
      new Promise((resolve) => setTimeout(resolve, 2500)),
    ]);
  });
  let previous = '';
  for (let attempt = 0; attempt < 8; attempt += 1) {
    const signature = await page.evaluate(() => `${document.documentElement.scrollHeight}:${document.body?.getBoundingClientRect().height || 0}`);
    if (signature === previous) return;
    previous = signature;
    await sleep(250);
  }
}

async function inspectSegment(page, route, segmentIndex) {
  return page.evaluate(({ route, segmentIndex }) => {
    const normalize = (value) => String(value || '').replace(/\s+/g, ' ').trim();
    const escape = (value) => CSS.escape(String(value));
    const fingerprint = (value) => {
      let hash = 2166136261;
      for (const character of normalize(value).toLowerCase()) {
        hash ^= character.charCodeAt(0);
        hash = Math.imul(hash, 16777619);
      }
      return (hash >>> 0).toString(16).padStart(8, '0');
    };
    const accessibleName = (element) => normalize(
      element.getAttribute('aria-label')
      || element.getAttribute('alt')
      || (element.labels ? Array.from(element.labels).map((label) => label.textContent).join(' ') : '')
      || element.textContent
      || element.getAttribute('title')
    ).slice(0, 300);
    const durableLocator = (element) => {
      if (element.id) return { locator: `#${escape(element.id)}`, method: 'id', durable: true };
      const href = element.getAttribute('href');
      if (element.tagName === 'A' && href) return { locator: `a[href="${escape(href)}"]`, method: 'href', durable: true };
      const role = element.getAttribute('role');
      const name = accessibleName(element);
      if (role && name) return { locator: `[role="${escape(role)}"][aria-label="${escape(element.getAttribute('aria-label') || name)}"]`, method: 'role_name', durable: !!element.getAttribute('aria-label') };
      if (element.getAttribute('aria-label')) return { locator: `${element.tagName.toLowerCase()}[aria-label="${escape(element.getAttribute('aria-label'))}"]`, method: 'accessible_name', durable: true };
      const parent = element.closest('[id],main,nav,header,footer,section,article');
      if (parent?.id && name) return { locator: `#${escape(parent.id)} ${element.tagName.toLowerCase()}`, method: 'durable_ancestry', durable: true };
      return { locator: '', method: 'none', durable: false };
    };
    const selector = 'a[href],button,input:not([type="hidden"]),select,textarea,[role="button"],h1,h2,h3,section[id],[id]:target';
    const seen = new Set();
    return Array.from(document.querySelectorAll(selector)).flatMap((element) => {
      if (!(element instanceof HTMLElement)) return [];
      if (element.closest('[aria-hidden="true"],[hidden],[inert],template,noscript')) return [];
      if (['presentation', 'none'].includes(element.getAttribute('role'))) return [];
      if (/^(svg|path|canvas)$/i.test(element.tagName)) return [];
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      const visible = style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) > 0.02
        && rect.width > 1 && rect.height > 1 && rect.bottom > 0 && rect.top < innerHeight;
      if (!visible) return [];
      const name = accessibleName(element);
      const href = element.getAttribute('href') || '';
      if (!name && !element.id && !href.startsWith('#')) return [];
      if (/^(react|next|vite|webpack|radix)-/i.test(element.id || '')) return [];
      const located = durableLocator(element);
      const role = element.getAttribute('role') || (element.tagName === 'A' ? 'link' : element.tagName === 'BUTTON' ? 'button' : '');
      const identityKey = [route, element.tagName.toLowerCase(), role, name.toLowerCase(), href].join('|');
      if (seen.has(identityKey)) return [];
      seen.add(identityKey);
      return [{
        identity_key: identityKey,
        route,
        segment_index: segmentIndex,
        tag: element.tagName.toLowerCase(),
        role,
        accessible_name: name,
        text: normalize(element.textContent).slice(0, 500),
        text_fingerprint: fingerprint(element.textContent),
        href,
        locator: located.locator,
        locator_method: located.method,
        durable: located.durable,
        rect: { x: rect.x, y: rect.y + scrollY, width: rect.width, height: rect.height },
      }];
    });
  }, { route, segmentIndex });
}

(async () => {
  const executable = process.env.CHROME_PATH || process.env.CHROME_BIN || (fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined);
  const browser = await chromium.launch({ headless: true, executablePath: executable, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const observations = [];
  try {
    for (const url of urls) {
      const route = new URL(url).pathname.replace(/\/+$/, '') || '/';
      for (const viewport of viewports) {
        for (let pass = 1; pass <= renderPasses; pass += 1) {
          const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, reducedMotion: 'reduce' });
          const page = await context.newPage();
          await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
          await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => undefined);
          await stabilize(page);
          const height = await page.evaluate(() => Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight || 0));
          const step = Math.max(1, Math.floor(viewport.height * 0.8));
          const positions = [];
          for (let y = 0; y < height; y += step) positions.push(Math.min(y, Math.max(0, height - viewport.height)));
          if (!positions.length) positions.push(0);
          const uniquePositions = [...new Set(positions)];
          const candidates = [];
          for (let segment = 0; segment < uniquePositions.length; segment += 1) {
            const y = uniquePositions[segment];
            await page.evaluate((top) => window.scrollTo({ top, behavior: 'instant' }), y);
            await sleep(180);
            candidates.push(...await inspectSegment(page, route, segment));
            const screenshot = path.join(outputDir, `route-${route.replace(/[^a-z0-9]+/gi, '_') || 'root'}-${viewport.name}-pass${pass}-segment${segment}.png`);
            await page.screenshot({ path: screenshot, fullPage: false });
          }
          const deduped = [...new Map(candidates.map((candidate) => [candidate.identity_key, candidate])).values()];
          observations.push({
            render_id: `${route}:${viewport.name}:${pass}`,
            url,
            route,
            viewport: viewport.name,
            viewport_size: { width: viewport.width, height: viewport.height },
            document_height: height,
            segment_count: uniquePositions.length,
            candidates: deduped,
          });
          await context.close();
        }
      }
    }
    fs.writeFileSync(outputFile, JSON.stringify({ schema: 'orb_weaver.pointer_browser_capture.v1', observations }, null, 2));
  } finally {
    await browser.close();
  }
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
