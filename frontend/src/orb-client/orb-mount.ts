import { OrbRuntimeClient } from './runtime-client';
import { FACTORY_SKIN, approvedSkinAssetUrl, factoryAssetUrl, prepareSkinAsset } from './factory-skin';
import { captureSiteSnapshot, observeSite } from './site-observer';
import type { OrbConnectionState, OrbLoaderConfig, OrbMountHandle, OrbPointerRecord, OrbRuntimeResponse, OrbSiteSnapshot, OrbSkinSelection } from './types';

const HOST_ID = 'orb-weaver-universal-root';
const STARTUP_SESSION_KEY = 'orbweaver-loader-startup-complete';
const STARTUP_GREETING = 'Hi, I am Weaver. I am here on this site, ready to listen and guide you to verified targets.';
const routeOf = (value?: string) => {
  try { return new URL(value || '/', window.location.href).pathname.replace(/\/+$/, '') || '/'; }
  catch { return '/'; }
};
const normalize = (value?: string | null) => (value || '').replace(/\s+/g, ' ').trim().toLowerCase();
const CSS = [
  ':host{all:initial}*{box-sizing:border-box}.shell{font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif;color:#eaf8ff}',
  '.toggle{pointer-events:auto;position:fixed;right:18px;bottom:18px;width:84px;height:84px;padding:0;border:0;border-radius:50%;cursor:pointer;background:transparent;filter:drop-shadow(0 14px 24px rgba(2,8,24,.55)) drop-shadow(0 0 12px rgba(44,220,245,.25));animation:pulse 2.7s ease-in-out infinite}',
  '.toggle:focus-visible,.action:focus-visible,.input:focus-visible{outline:3px solid #facc15;outline-offset:3px}.skin{display:block;width:100%;height:100%;object-fit:contain;border-radius:50%;user-select:none;pointer-events:none}',
  '.panel{pointer-events:auto;position:fixed;right:22px;bottom:100px;width:min(350px,calc(100vw - 28px));border:1px solid rgba(125,228,255,.28);border-radius:18px;background:linear-gradient(155deg,rgba(7,13,35,.97),rgba(11,31,60,.97));box-shadow:0 22px 70px rgba(2,8,25,.5);overflow:hidden;backdrop-filter:blur(16px)}',
  '.head{display:flex;align-items:center;justify-content:space-between;padding:15px 16px 12px;border-bottom:1px solid rgba(125,228,255,.14)}.title{font-size:14px;font-weight:800}.status{display:flex;align-items:center;gap:7px;color:#a9bfd1;font-size:11px}.dot{width:8px;height:8px;border-radius:50%;background:#f87171}.dot[data-state=online]{background:#4ade80}.dot[data-state=pending]{background:#facc15}.dot[data-state=loading]{background:#7dd3fc;animation:blink 1s infinite}',
  '.body{padding:14px 16px 16px}.output{min-height:54px;margin:0 0 12px;color:#dcecf8;font-size:13px;line-height:1.5}.form{display:flex;gap:8px}.input{min-width:0;flex:1;border:1px solid rgba(125,228,255,.22);border-radius:10px;padding:10px 11px;background:rgba(255,255,255,.07);color:#fff;font:inherit}.input::placeholder{color:#8fa8ba}.action{border:0;border-radius:10px;padding:9px 11px;background:#37bde8;color:#061629;font-size:12px;font-weight:800;cursor:pointer}.action[disabled]{opacity:.45}.voice{margin-top:9px;width:100%;background:rgba(125,228,255,.12);color:#c9f4ff;border:1px solid rgba(125,228,255,.22)}.foot{margin-top:10px;color:#7893a7;font-size:10px}',
  '.pointer{display:none;pointer-events:none;position:fixed;border:3px solid #5ee7ff;border-radius:12px;box-shadow:0 0 0 5px rgba(94,231,255,.2),0 0 30px rgba(94,231,255,.75);animation:pointer 1s ease-in-out infinite}.pointer[data-visible=true]{display:block}',
  '@keyframes pulse{50%{transform:translateY(-3px)}}@keyframes blink{50%{opacity:.35}}@keyframes pointer{50%{box-shadow:0 0 0 10px rgba(94,231,255,.08),0 0 38px rgba(94,231,255,.9)}}@media(prefers-reduced-motion:reduce){.toggle,.dot,.pointer{animation:none!important}}',
].join('');
const MARKUP = [
  '<style>', CSS, '</style><div class="shell">',
  '<button class="toggle" type="button" data-toggle aria-label="Open O.R.B.S. website guide" aria-expanded="false"><img class="skin" data-skin alt="" draggable="false"></button>',
  '<section class="panel" data-panel hidden role="dialog" aria-label="Orb Weaver website guide">',
  '<header class="head"><div class="title">Orb Weaver</div><div class="status"><span class="dot" data-dot data-state="loading"></span><span data-status>Connecting</span></div></header>',
  '<div class="body"><p class="output" data-output>I am connecting to this site guide.</p>',
  '<form class="form" data-form><input class="input" data-input maxlength="1000" aria-label="Ask the website guide" placeholder="Ask where to find something…"><button class="action" type="submit">Ask</button></form>',
  '<button class="action voice" type="button" data-voice>Start voice question</button>',
  '<div class="foot">Voice activates only after you choose it. Pointer targets are verified before guidance.</div></div>',
  '</section><div class="pointer" data-pointer aria-hidden="true"></div></div>',
].join('');

export function mountOrb(config: OrbLoaderConfig): OrbMountHandle {
  if (window.__ORB_WEAVER_LOADER_V1__?.mounted) {
    if (config.debug) console.info('[Orb Weaver] No duplicate instance', { siteId: config.siteId });
    return window.__ORB_WEAVER_LOADER_V1__.handle;
  }
  if (document.getElementById(HOST_ID)) throw new Error('An unmanaged Orb Weaver mount already exists');
  const log = (event: string, detail: unknown = {}) => {
    if (config.debug) console.info('[Orb Weaver] ' + event, detail);
    window.dispatchEvent(new CustomEvent('orbweaver:' + event, { detail }));
  };
  log('Loader executed', { siteId: config.siteId, version: config.version || '1' });

  const client = new OrbRuntimeClient(config);
  const host = document.createElement('div');
  host.id = HOST_ID;
  host.dataset.orbSiteId = config.siteId;
  host.dataset.orbLoaderVersion = config.version || '1';
  host.style.cssText = 'position:fixed;inset:0;z-index:2147483000;pointer-events:none;overflow:visible;';
  const shadow = host.attachShadow({ mode: 'open' });
  shadow.innerHTML = MARKUP;
  document.documentElement.appendChild(host);

  let mounted = true;
  let online = false;
  let open = false;
  const factoryUrl = factoryAssetUrl(config);
  let currentSkinId = FACTORY_SKIN.skinId;
  let customizationState: 'FACTORY_DEFAULT' | 'CUSTOM' = 'FACTORY_DEFAULT';
  let disposeCustomAsset: (() => void) | undefined;
  let pointers: OrbPointerRecord[] = [];
  let abortController: AbortController | undefined;
  let recorder: MediaRecorder | undefined;
  let mediaStream: MediaStream | undefined;
  let chunks: BlobPart[] = [];
  let pointerTimer = 0;
  let travelTimer = 0;
  let startupStarted = false;
  const element = <T extends HTMLElement>(selector: string) => shadow.querySelector<T>(selector)!;
  const skinImage = element<HTMLImageElement>('[data-skin]');
  const restoreFactory = () => {
    disposeCustomAsset?.();
    disposeCustomAsset = undefined;
    currentSkinId = FACTORY_SKIN.skinId;
    customizationState = 'FACTORY_DEFAULT';
    skinImage.src = factoryUrl;
    skinImage.dataset.skinId = currentSkinId;
    host.dataset.orbSkinId = currentSkinId;
    host.dataset.orbCustomizationState = customizationState;
    log('Factory skin restored', { skinId: currentSkinId, bodyAssetUrl: factoryUrl });
  };
  const setSkin = async (skin: OrbSkinSelection) => {
    if (skin.skinId === FACTORY_SKIN.skinId || skin.customizationState === 'FACTORY_DEFAULT') {
      restoreFactory();
      return true;
    }
    const candidateUrl = approvedSkinAssetUrl(skin.bodyAssetUrl);
    if (!candidateUrl) {
      restoreFactory();
      log('Custom skin rejected', { skinId: skin.skinId, reason: 'invalid_asset_url' });
      return false;
    }
    const prepared = await prepareSkinAsset(candidateUrl);
    if (!prepared) {
      restoreFactory();
      log('Custom skin fallback', { skinId: skin.skinId, reason: 'asset_load_failed' });
      return false;
    }
    currentSkinId = skin.skinId;
    customizationState = 'CUSTOM';
    disposeCustomAsset?.();
    disposeCustomAsset = prepared.dispose;
    skinImage.src = prepared.url;
    skinImage.dataset.skinId = currentSkinId;
    host.dataset.orbSkinId = currentSkinId;
    host.dataset.orbCustomizationState = customizationState;
    log('Custom skin applied', { skinId: currentSkinId, bodyAssetUrl: candidateUrl });
    return true;
  };
  skinImage.addEventListener('error', () => {
    if (customizationState === 'CUSTOM') {
      const failedSkinId = currentSkinId;
      restoreFactory();
      log('Custom skin fallback', { skinId: failedSkinId, reason: 'render_load_failed' });
    } else {
      log('Factory skin unavailable', { skinId: FACTORY_SKIN.skinId, bodyAssetUrl: factoryUrl });
    }
  });
  restoreFactory();
  const setStatus = (state: OrbConnectionState, text: string) => {
    element('[data-status]').textContent = text;
    element('[data-dot]').dataset.state = state;
    online = state === 'online' || state === 'pending';
    log('Runtime status', { state, text });
  };
  const setMessage = (text: string) => { element('[data-output]').textContent = text.slice(0, 700); };
  const setOpen = (next: boolean) => {
    open = next;
    element('[data-panel]').hidden = !open;
    element('[data-toggle]').setAttribute('aria-expanded', String(open));
  };
  const aliases = (record: OrbPointerRecord) => [
    (record.meaning || '').replace(/^[^:]+:\s*/, ''),
    ...(record.direct_aliases || []), ...(record.intent_aliases || []), ...(record.topic_aliases || []),
  ].map(normalize).filter((value) => value.length >= 2);
  const mayPoint = (record: OrbPointerRecord) => {
    if (record.confidence_class === 'UNCERTAIN' || record.confidence_class === 'BLOCKED') return false;
    if (record.runtime_policy?.may_point !== true) return false;
    if (record.pointer_health === 'OWNER_REJECTED' || record.pointer_health === 'DEPRECATED' || record.pointer_health === 'REMOVED') return false;
    return record.confidence_class === 'VERIFIED' || record.confidence_class === 'STABLE';
  };
  const pointRecord = (record: OrbPointerRecord) => {
    if (!mayPoint(record) || routeOf(record.page_route) !== routeOf(window.location.href)) return false;
    let searchRoot: ParentNode = document;
    const parentLocator = record.structural_context?.parent_locator?.trim();
    if (parentLocator) {
      try {
        const parent = document.querySelector<HTMLElement>(parentLocator);
        if (!parent) return false;
        searchRoot = parent;
      } catch { return false; }
    }
    let targets: NodeListOf<HTMLElement>;
    try { targets = searchRoot.querySelectorAll<HTMLElement>(record.semantic_locator); } catch { return false; }
    const target = Array.from(targets).find((candidate) => {
      const rect = candidate.getBoundingClientRect();
      const tag = normalize(record.structural_context?.tag);
      const text = normalize(candidate.getAttribute('aria-label') || candidate.textContent);
      const identityMatches = aliases(record).some((value) => {
        if (text === value) return true;
        if (text.length < 5 || value.length < 5) return false;
        return (text.includes(value) || value.includes(text))
          && Math.min(text.length, value.length) / Math.max(text.length, value.length) >= 0.65;
      });
      return document.body.contains(candidate) && rect.width > 0 && rect.height > 0
        && (!tag || candidate.tagName.toLowerCase() === tag)
        && (!aliases(record).length || identityMatches);
    });
    if (!target) return false;
    target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
    window.clearTimeout(travelTimer);
    window.setTimeout(() => {
      if (!mounted || !document.body.contains(target)) return;
      const rect = target.getBoundingClientRect();
      const toggle = element<HTMLButtonElement>('[data-toggle]');
      const orbSize = toggle.getBoundingClientRect().width || 84;
      const desiredLeft = rect.right + orbSize + 18 <= window.innerWidth
        ? rect.right + 12
        : rect.left - orbSize - 12;
      Object.assign(toggle.style, {
        left: Math.max(8, Math.min(window.innerWidth - orbSize - 8, desiredLeft)) + 'px',
        top: Math.max(8, Math.min(window.innerHeight - orbSize - 8, rect.top + (rect.height - orbSize) / 2)) + 'px',
        right: 'auto', bottom: 'auto',
        transition: window.matchMedia('(prefers-reduced-motion: reduce)').matches
          ? 'none'
          : 'left 520ms cubic-bezier(.2,.8,.2,1), top 520ms cubic-bezier(.2,.8,.2,1)',
      });
      log('ORB traveled to verified target', { targetId: record.target_id });
      travelTimer = window.setTimeout(() => {
        if (!mounted || !document.body.contains(target)) return;
        const verifiedRect = target.getBoundingClientRect();
        const pointer = element('[data-pointer]');
        Object.assign(pointer.style, {
          left: Math.max(0, verifiedRect.left - 7) + 'px', top: Math.max(0, verifiedRect.top - 7) + 'px',
          width: verifiedRect.width + 14 + 'px', height: verifiedRect.height + 14 + 'px',
        });
        pointer.dataset.visible = 'true';
        window.clearTimeout(pointerTimer);
        pointerTimer = window.setTimeout(() => delete pointer.dataset.visible, 2600);
        log('Pointer target discovered', { targetId: record.target_id, confidenceClass: record.confidence_class });
      }, 540);
    }, 380);
    return true;
  };
  const guide = (intent: string, preferred?: string) => {
    const query = normalize(intent);
    let best: { record: OrbPointerRecord; score: number } | undefined;
    pointers.forEach((record) => {
      if (!mayPoint(record) || routeOf(record.page_route) !== routeOf(window.location.href)) return;
      let score = record.target_id === preferred ? 10 : 0;
      aliases(record).forEach((value) => {
        if (query === value) score = Math.max(score, 1);
        else if (query.includes(value)) score = Math.max(score, value.length / Math.max(query.length, 1));
        else if (query.length >= 4 && value.includes(query)) score = Math.max(score, query.length / value.length);
      });
      if (score >= 0.35 && (!best || score > best.score)) best = { record, score };
    });
    return best ? pointRecord(best.record) : false;
  };
  const handleResponse = (response: OrbRuntimeResponse, intent: string) => {
    setStatus('online', 'Connected');
    setMessage(response.spoken_output || 'I am ready.');
    const preferredTarget = response.cognitive_pulse?.pointer_matches?.[0]?.target_id;
    const guided = guide(intent, preferredTarget);
    if (preferredTarget && !guided) {
      const verificationFailure = 'I could not verify that target on this page, so I will not point to it or take action.';
      setMessage(verificationFailure);
      const pointer = element('[data-pointer]');
      delete pointer.dataset.visible;
      window.clearTimeout(pointerTimer);
      log('Pointer verification blocked guidance', { targetId: preferredTarget });
      return;
    }
    if (response.tts_audio_url) void new Audio(client.mediaUrl(response.tts_audio_url)).play().catch(() => undefined);
  };
  const ask = async (text: string) => {
    const transcript = text.trim();
    if (!transcript) return;
    const localGuided = guide(transcript);
    if (localGuided) {
      setStatus('online', 'Guiding');
      setMessage('I found a verified target for that. I am moving there now.');
      log('Local verified guidance started', { transcript });
      return;
    }
    setStatus('loading', 'Thinking');
    try { handleResponse(await client.ask(transcript), transcript); }
    catch (error) {
      setStatus('offline', 'Offline');
      setMessage('I could not answer that right now. The rest of the site is unaffected.');
      log('Runtime failure', { stage: 'text', message: error instanceof Error ? error.message : String(error) });
    }
  };
  const speakStartupGreeting = () => {
    try {
      if (!('speechSynthesis' in window) || typeof window.SpeechSynthesisUtterance !== 'function') return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(STARTUP_GREETING);
      utterance.rate = 0.96;
      utterance.pitch = 1.02;
      window.speechSynthesis.speak(utterance);
      log('Startup greeting spoken', { provider: 'browser-speech-synthesis' });
    } catch {
      log('Startup greeting unavailable', { provider: 'browser-speech-synthesis' });
    }
  };
  const startVoiceQuestion = async (source: 'startup' | 'button') => {
    const button = element<HTMLButtonElement>('[data-voice]');
    if (recorder?.state === 'recording') { recorder.stop(); return true; }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setMessage('Voice recording is not supported here. You can still type a question.');
      log('Voice initialization available', { available: false, source });
      return false;
    }
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks = [];
      recorder = new MediaRecorder(mediaStream);
      recorder.addEventListener('dataavailable', (event) => { if (event.data.size) chunks.push(event.data); });
      recorder.addEventListener('stop', async () => {
        button.textContent = 'Start voice question';
        mediaStream?.getTracks().forEach((track) => track.stop());
        mediaStream = undefined;
        setStatus('loading', 'Understanding');
        try {
          const response = await client.askVoice(new Blob(chunks, { type: recorder?.mimeType || 'audio/webm' }));
          handleResponse(response, response.transcript || '');
        } catch (error) {
          setStatus('offline', 'Voice unavailable');
          setMessage('Voice could not connect. You can still type a question.');
          log('Runtime failure', { stage: 'voice', message: error instanceof Error ? error.message : String(error), source });
        }
      });
      recorder.start();
      button.textContent = 'Finish voice question';
      setStatus('online', 'Listening');
      setMessage(source === 'startup'
        ? 'I am listening. Speak naturally, then pause when your question is complete.'
        : 'I am listening. Choose Finish when your question is complete.');
      log('Voice initialization available', { available: true, permissionRequested: true, source });
      window.setTimeout(() => { if (recorder?.state === 'recording') recorder.stop(); }, 12000);
      return true;
    } catch {
      setMessage('Microphone permission was not granted. You can still type a question.');
      log('Voice initialization available', { available: true, permission: 'denied', source });
      return false;
    }
  };
  const runStartupEncounter = (siteName: string) => {
    if (startupStarted || routeOf(window.location.href) !== '/') return;
    if (window.sessionStorage.getItem(STARTUP_SESSION_KEY) === '1') return;
    startupStarted = true;
    window.sessionStorage.setItem(STARTUP_SESSION_KEY, '1');
    setOpen(true);
    setStatus('online', 'Listening');
    setMessage(`Hi, I am Weaver. I am connected to ${siteName} and I am listening.`);
    speakStartupGreeting();
    window.setTimeout(() => {
      if (!mounted || recorder?.state === 'recording') return;
      void startVoiceQuestion('startup');
    }, 650);
  };
  const load = async (snapshot: OrbSiteSnapshot) => {
    abortController?.abort();
    abortController = new AbortController();
    setStatus('loading', 'Connecting');
    try {
      const response = await client.bootstrap(snapshot, abortController.signal);
      pointers = response.pointer_map.records || [];
      if (response.orb_identity?.customization_state === 'CUSTOM') {
        await setSkin({
          skinId: response.orb_identity.skin_id,
          displayName: response.orb_identity.display_name,
          bodyAssetUrl: new URL(response.orb_identity.asset_path, window.location.origin).toString(),
          customizationState: 'CUSTOM',
        });
      } else if (currentSkinId !== FACTORY_SKIN.skinId) {
        restoreFactory();
      }
      const ready = response.status === 'ready';
      const recoveringPointers = response.pointer_guidance?.map_recovery_required === true;
      const targetGuidanceAvailable = response.pointer_guidance?.target_guidance_available === true;
      setStatus(
        ready ? 'online' : 'pending',
        ready ? (recoveringPointers ? 'Connected · pointer recovery' : 'Connected')
          : targetGuidanceAvailable ? 'Connected · verified guidance' : 'Connected · scan pending',
      );
      const name = String(response.site_world.site_name || response.site_world.brand || response.site.name || 'this site');
      setMessage(ready
        ? recoveringPointers
          ? 'I am connected to ' + name + '. I can answer questions while the pointer map completes recovery; only verified guidance is enabled.'
          : 'I am connected to ' + name + ' and ready to guide you.'
        : targetGuidanceAvailable
          ? 'I am connected to ' + name + '. Verified target guidance is available while broader pointer coverage remains under review.'
          : 'The loader is connected. This published site still needs verified Orb Weaver guidance evidence.');
      log('Runtime connected', {
        status: response.status,
        pointerGuidance: response.pointer_guidance?.status,
        pointerTargets: pointers.length,
        policyVersion: response.operating_policy?.version,
        skinId: response.orb_identity?.skin_id,
        page: snapshot,
      });
      log('Pointer targets discovered', { count: pointers.length });
      client.reportRoute(snapshot);
      runStartupEncounter(name);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      setStatus('offline', 'Offline');
      setMessage('I cannot reach the Orb Weaver runtime right now. The website remains fully usable.');
      log('Runtime failure', { stage: 'bootstrap', message: error instanceof Error ? error.message : String(error) });
    }
  };
  const stopObserving = observeSite((snapshot) => {
    log('Route change detected', {
      host: snapshot.host, pathname: snapshot.pathname, title: snapshot.title,
      viewport: snapshot.viewport, visibleControls: snapshot.visible_controls,
    });
    void load(snapshot);
  });

  element('[data-toggle]').addEventListener('click', () => {
    setOpen(!open);
  });
  element<HTMLFormElement>('[data-form]').addEventListener('submit', (event) => {
    event.preventDefault();
    const input = element<HTMLInputElement>('[data-input]');
    const value = input.value;
    input.value = '';
    void ask(value);
  });
  element('[data-voice]').addEventListener('click', async () => {
    void startVoiceQuestion('button');
  });

  const unmount = () => {
    if (!mounted) return;
    mounted = false;
    abortController?.abort();
    stopObserving();
    client.destroy();
    if (recorder?.state === 'recording') recorder.stop();
    mediaStream?.getTracks().forEach((track) => track.stop());
    disposeCustomAsset?.();
    window.clearTimeout(pointerTimer);
    window.clearTimeout(travelTimer);
    host.remove();
    log('ORB unmounted', { siteId: config.siteId });
    delete window.__ORB_WEAVER_LOADER_V1__;
    delete window.OrbWeaver;
  };
  const handle: OrbMountHandle = {
    unmount, ask, pointTo: (targetId) => guide('', targetId), setSkin, restoreFactory,
    getStatus: () => ({ mounted, online, route: routeOf(window.location.href), skinId: currentSkinId, customizationState }),
  };
  window.__ORB_WEAVER_LOADER_V1__ = { mounted: true, handle };
  window.OrbWeaver = { ...handle, version: config.version || '1', siteId: config.siteId, mount: () => mountOrb(config) };
  log('ORB mounted', { isolated: !!host.shadowRoot, hostLayoutModified: false });
  log('Current route detected', captureSiteSnapshot());
  log('Voice initialization available', {
    available: typeof navigator.mediaDevices?.getUserMedia === 'function'
      && typeof window.MediaRecorder === 'function',
    permissionRequested: false,
  });
  void load(captureSiteSnapshot());
  try { client.connect(captureSiteSnapshot()); }
  catch (error) { log('Runtime failure', { stage: 'websocket', message: error instanceof Error ? error.message : String(error) }); }
  return handle;
}
