const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('../../frontend/node_modules/jsdom');
const source = fs.readFileSync(path.resolve(__dirname, '../../manufacturing/templates/Website_Orb_Final/frontend/widget.js'), 'utf8');
const flush = () => new Promise(resolve => setTimeout(resolve, 5));

test('customer-only network, governed unique pointers, no clicks, route cancellation', async () => {
  const dom = new JSDOM('<button id="buy">Orchid Atlas</button><script src="https://runtime.garden.example/orb/widget.js"></script>', {
    url: 'https://garden.example/product', runScripts: 'outside-only', pretendToBeVisual: true,
  });
  const w = dom.window, calls = [];
  Object.defineProperty(w.document, 'currentScript', { value: w.document.querySelector('script') });
  let response = {
    answer: 'Orchid Atlas is $49.', route: '/product',
    governance_trace: { status: 'approved', tpc_state: 'passed', doctrine_checksum: true },
    pointer_targets: [{ page_route: '/product', semantic_locator: '#buy', meaning: 'Orchid Atlas', confidence: 1,
      runtime_policy: { may_point: true } }], skg_context: { matched_candidates: [] },
  };
  w.fetch = async url => {
    calls.push(url);
    return { ok: true, json: async () => url.endsWith('/bootstrap') ? {
      site_id: 'garden', site_name: 'Garden', orb_name: 'Garden guide',
      allowed_origins: ['https://garden.example'], routes: ['/', '/product'],
    } : response };
  };
  const target = w.document.querySelector('#buy');
  target.style.opacity = '1';
  target.getBoundingClientRect = () => ({ top: 50, left: 100, bottom: 90, right: 240, width: 140, height: 40 });
  let clicks = 0; target.onclick = () => clicks++;
  try {
    w.eval(source); await flush();
    const shadow = w.document.querySelector('#website-orb-widget').shadowRoot;
    const send = async () => {
      shadow.querySelector('input').value = 'Orchid Atlas';
      shadow.querySelector('form').dispatchEvent(new w.Event('submit', { cancelable: true })); await flush();
    };
    shadow.querySelector('.orb').click();
    assert.match(shadow.querySelector('p').textContent, /Garden/);
    await send(); assert.equal(shadow.querySelector('.ping').hidden, false); assert.equal(clicks, 0);
    response.governance_trace.status = 'rejected';
    await send(); assert.equal(shadow.querySelector('.ping').hidden, true);
    response.governance_trace.status = 'approved';
    response.pointer_targets[0].semantic_locator = '#missing';
    await send(); assert.equal(shadow.querySelector('.ping').hidden, true);
    response.pointer_targets[0].semantic_locator = 'button';
    const duplicate = target.cloneNode(true); duplicate.getBoundingClientRect = target.getBoundingClientRect;
    w.document.body.append(duplicate);
    await send(); assert.equal(shadow.querySelector('.ping').hidden, true); duplicate.remove();
    response.pointer_targets[0].semantic_locator = '#buy';
    await send(); assert.equal(shadow.querySelector('.ping').hidden, false);
    w.history.pushState({}, '', '/unknown'); await new Promise(resolve => setTimeout(resolve, 350));
    assert.equal(shadow.querySelector('.ping').hidden, true);
    await send(); assert.equal(shadow.querySelector('.ping').hidden, true); assert.equal(clicks, 0);
    assert(calls.every(url => url.startsWith('https://runtime.garden.example/orb/')));
    assert.equal(w.location.pathname, '/unknown');
  } finally { w.dispatchEvent(new w.Event('pagehide')); w.close(); }
});
