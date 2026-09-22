/* Standalone customer widget. No factory endpoints, identity or vocabulary. */
(() => {
  'use strict';
  const script = document.currentScript;
  if (!script || document.getElementById('website-orb-widget')) return;
  const api = new URL(script.src).origin;
  const host = document.createElement('div');
  host.id = 'website-orb-widget';
  const shadow = host.attachShadow({ mode: 'open' });
  shadow.innerHTML = `<style>
    :host { all: initial; position: fixed; right: 12px; bottom: 12px; z-index: 2147483000; font: 14px system-ui; }
    * { box-sizing: border-box; } button,input { font: inherit; }
    button,a { cursor: pointer; } button:focus-visible,input:focus-visible,a:focus-visible { outline: 3px solid #ffd166; }
    .orb { width: 64px; height: 64px; border: 2px solid #9acbff; border-radius: 50%; background: #122c49;
      opacity: .96; display: block; margin-left: auto; color: white; }
    .eye { display: block; margin: auto; width: 24px; height: 24px; border-radius: 50%; background: radial-gradient(white,#42a5ff); }
    .speaking .eye { animation: speech .36s ease-in-out infinite alternate; }
    @keyframes speech { to { transform: scale(1.3); box-shadow: 0 0 14px #6cd4ff; } }
    form { width: min(330px,calc(100vw - 24px)); max-height: 55vh; overflow: auto; padding: 12px; margin: 8px 0;
      color: white; border-radius: 12px; background: #142536; box-shadow: 0 4px 20px #0007; }
    [hidden] { display: none !important; } p { white-space: pre-wrap; line-height: 1.5; }
    input { width: 100%; padding: 8px; } button { padding: 8px; } a { display: block; color: #a3d9ff; padding: 6px; }
    .ping { position: fixed; pointer-events: none; border: 3px solid #3bafff; border-radius: 8px; box-shadow: 0 0 12px #3bafff; }
    @media (prefers-reduced-motion: reduce) { .speaking .eye { animation: none; box-shadow: 0 0 14px #6cd4ff; } }
  </style><form hidden><button type="button" class="close">Close</button>
    <p role="status" aria-live="polite">Loading this site's guide…</p><nav aria-label="Suggested destinations"></nav>
    <input required maxlength="8000" aria-label="Your question" placeholder="Ask about this site">
    <button type="submit">Ask</button><button type="button" class="voice">Speak</button>
    </form><button type="button" class="orb" aria-label="Open site guide" aria-expanded="false"><span class="eye"></span></button>
    <div class="ping" hidden></div>`;
  document.body.append(host);
  const form = shadow.querySelector('form'), orb = shadow.querySelector('.orb');
  const status = shadow.querySelector('p'), input = shadow.querySelector('input');
  const nav = shadow.querySelector('nav'), ping = shadow.querySelector('.ping'), voice = shadow.querySelector('.voice');
  let config, audio, recorder, stream, recordingTimer, pingTimer, target, controller, sequence = 0;
  const route = () => location.pathname + location.search + location.hash;
  let lastRoute = route();
  const norm = value => String(value || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const request = async (path, options = {}) => {
    const response = await fetch(api + path, { ...options, credentials: 'omit' });
    if (!response.ok) throw new Error(`Runtime request failed (${response.status})`);
    return response.json();
  };
  const cancel = () => {
    sequence++; controller?.abort(); audio?.pause(); orb.classList.remove('speaking');
    clearTimeout(recordingTimer); clearTimeout(pingTimer);
    if (recorder?.state === 'recording') { recorder.onstop = null; recorder.stop(); }
    stream?.getTracks().forEach(track => track.stop());
    voice.textContent = 'Speak'; target = null; ping.hidden = true;
  };
  const toggle = open => {
    form.hidden = !open; orb.setAttribute('aria-expanded', String(open));
    if (open) input.focus(); else cancel();
  };
  orb.onclick = () => toggle(form.hidden);
  shadow.querySelector('.close').onclick = () => toggle(false);
  const visible = el => {
    const rect = el.getBoundingClientRect(), css = getComputedStyle(el);
    return el.isConnected && !el.closest('[hidden],[inert],[aria-hidden="true"]') && css.visibility !== 'hidden'
      && css.display !== 'none' && Number(css.opacity) > 0 && rect.width > 0 && rect.height > 0
      && rect.top >= 0 && rect.left >= 0 && rect.bottom <= innerHeight && rect.right <= innerWidth;
  };
  const placePing = () => {
    if (!target || !visible(target)) { ping.hidden = true; return; }
    const rect = target.getBoundingClientRect();
    Object.assign(ping.style, { top: `${rect.top - 4}px`, left: `${rect.left - 4}px`,
      width: `${rect.width + 8}px`, height: `${rect.height + 8}px` }); ping.hidden = false;
  };
  const present = (response, atRoute) => {
    status.textContent = response.spoken_output || response.answer;
    const gate = response.governance_trace || {};
    if (gate.status !== 'approved' || gate.tpc_state !== 'passed' || gate.doctrine_checksum !== true) return;
    nav.replaceChildren();
    for (const candidate of (response.skg_context?.matched_candidates || []).slice(0, 4)) {
      if (!config.routes.includes(candidate.route) || candidate.route === atRoute) continue;
      const destination = new URL(candidate.route, location.origin);
      if (destination.origin !== location.origin) continue;
      const link = document.createElement('a'); link.href = destination.href;
      link.textContent = `Open ${candidate.label}`; nav.append(link); // User click is the confirmation.
    }
    for (const record of response.pointer_targets || []) {
      if (record.page_route !== atRoute || record.confidence < .55 || record.runtime_policy?.may_point !== true) continue;
      let matches = [];
      try { matches = [...document.querySelectorAll(record.semantic_locator || ':not(*)')]; } catch { continue; }
      const label = norm(record.meaning).replace(/^[^:]+:\s*/, '');
      matches = matches.filter(el => {
        const name = norm(el.getAttribute('aria-label') || el.textContent || el.getAttribute('placeholder'));
        return label && name && name.includes(label) && visible(el) && !host.contains(el);
      });
      if (matches.length !== 1) continue;
      target = matches[0]; placePing(); pingTimer = setTimeout(() => { target = null; ping.hidden = true; }, 2200); break;
    }
    if (response.tts_audio_url) {
      const url = new URL(response.tts_audio_url, api);
      if (url.origin !== api || !url.pathname.startsWith('/orb/audio/')) return;
      audio = new Audio(url.href);
      audio.onplaying = () => orb.classList.add('speaking');
      audio.onended = audio.onerror = audio.onpause = () => orb.classList.remove('speaking');
      audio.play().catch(() => { status.textContent += '\nAudio could not play; the answer is shown above.'; });
    } else if (response.tts_error) status.textContent += '\n' + response.tts_error;
  };
  const send = async (path, options, id, atRoute) => {
    controller = new AbortController(); status.textContent = 'Checking this site’s information…';
    try {
      const response = await request(path, { ...options, signal: controller.signal });
      if (sequence === id && route() === atRoute) present(response, atRoute);
    } catch (error) {
      if (sequence === id && error.name !== 'AbortError') status.textContent = 'The request could not complete. Please try text or retry shortly.';
    }
  };
  form.onsubmit = event => {
    event.preventDefault(); if (!config || !input.value.trim()) return;
    cancel(); nav.replaceChildren(); const message = input.value.trim(); input.value = '';
    void send('/orb/answer-text', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, route: route(), want_pointer: true }) }, sequence, route());
  };
  voice.onclick = async () => {
    if (recorder?.state === 'recording') { recorder.stop(); return; }
    if (!config) return;
    cancel(); const id = sequence, atRoute = route();
    try {
      const acquired = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (sequence !== id) { acquired.getTracks().forEach(track => track.stop()); return; }
      stream = acquired; const chunks = []; recorder = new MediaRecorder(stream);
      recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      recorder.onstop = () => {
        clearTimeout(recordingTimer); acquired.getTracks().forEach(track => track.stop()); voice.textContent = 'Speak';
        if (sequence !== id || route() !== atRoute) return;
        const data = new FormData(); data.append('audio', new Blob(chunks, { type: recorder.mimeType }), 'question.webm');
        data.append('route', atRoute); void send('/orb/website-voice', { method: 'POST', body: data }, id, atRoute);
      };
      recorder.start(); voice.textContent = 'Finish recording'; status.textContent = 'Listening. Press Finish recording when ready.';
      recordingTimer = setTimeout(() => { if (recorder.state === 'recording') recorder.stop(); }, 14000);
    } catch { stream?.getTracks().forEach(track => track.stop()); status.textContent = 'Microphone unavailable. You can type your question.'; }
  };
  const routeTimer = setInterval(() => {
    if (lastRoute !== route()) { lastRoute = route(); cancel(); nav.replaceChildren(); status.textContent = 'You can ask about this page.'; }
  }, 300);
  addEventListener('scroll', placePing, { passive: true }); addEventListener('resize', placePing);
  addEventListener('pagehide', () => { cancel(); clearInterval(routeTimer); }, { once: true });
  request('/orb/bootstrap').then(value => {
    if (!value.allowed_origins.includes(location.origin)) { host.remove(); cancel(); clearInterval(routeTimer); return; }
    config = value; orb.setAttribute('aria-label', `Open ${config.orb_name}`);
    status.textContent = `Ask me about ${config.site_name}. I can explain what is on this site and suggest where to go.`;
  }).catch(() => { status.textContent = 'This site’s guide is unavailable. Please try again shortly.'; });
})();
