import { OrbRuntimeClient } from './runtime-client';
import { FACTORY_SKIN, approvedSkinAssetUrl, factoryAssetUrl, prepareSkinAsset } from './factory-skin';
import { captureSiteSnapshot, observeSite } from './site-observer';
import type { OrbConnectionState, OrbLoaderConfig, OrbMountHandle, OrbPointerRecord, OrbRuntimeResponse, OrbSiteSnapshot, OrbSkinSelection } from './types';

const HOST_ID = 'orb-weaver-universal-root';
const STARTUP_SESSION_KEY = 'orbweaver-loader-startup-complete';
const RECORDING_MAX_MS = 14000;
const RECORDING_MIN_MS = 650;
const SILENCE_AFTER_SPEECH_MS = 850;
const SILENCE_SAMPLE_MS = 120;
const SPEECH_RMS_THRESHOLD = 0.025;
const SILENCE_RMS_THRESHOLD = 0.018;
const recorderMimeType = () => {
  const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4;codecs=mp4a.40.2', 'audio/mp4', 'audio/ogg;codecs=opus', 'audio/ogg'];
  return types.find((type) => MediaRecorder.isTypeSupported(type)) || '';
};
const recordingFileName = (type: string) => type.includes('mp4') ? 'orb-question.m4a' : type.includes('ogg') ? 'orb-question.ogg' : 'orb-question.webm';
const routeOf = (value?: string) => {
  try { return new URL(value || '/', window.location.href).pathname.replace(/\/+$/, '') || '/'; }
  catch { return '/'; }
};
const normalize = (value?: string | null) => (value || '').replace(/\s+/g, ' ').trim().toLowerCase();
const CSS = [
  ':host{all:initial}*{box-sizing:border-box}.shell{font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif;color:#eaf8ff}',
  '.toggle{pointer-events:auto;position:fixed;left:max(12px,min(68vw,calc(100vw - 190px)));top:38vh;width:164px;height:164px;padding:0;border:0;border-radius:0;cursor:pointer;background:transparent;filter:drop-shadow(0 18px 28px rgba(2,8,24,.4)) drop-shadow(0 0 34px rgba(255,255,255,.72));animation:pulse 2.7s ease-in-out infinite}',
  '.toggle:focus-visible,.action:focus-visible,.input:focus-visible{outline:3px solid #facc15;outline-offset:3px}.skin{display:block;width:100%;height:100%;object-fit:contain;border-radius:0;user-select:none;pointer-events:none}',
  '.sr-status{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}',
  '.pointer{display:none;pointer-events:none;position:fixed;border:3px solid #5ee7ff;border-radius:12px;box-shadow:0 0 0 5px rgba(94,231,255,.2),0 0 30px rgba(94,231,255,.75);animation:pointer 1s ease-in-out infinite}.pointer[data-visible=true]{display:block}',
  '@keyframes pulse{50%{transform:translateY(-3px)}}@keyframes pointer{50%{box-shadow:0 0 0 10px rgba(94,231,255,.08),0 0 38px rgba(94,231,255,.9)}}@media(prefers-reduced-motion:reduce){.toggle,.pointer{animation:none!important}}',
].join('');
const MARKUP = [
  '<style>', CSS, '</style><div class="shell">',
  '<button class="toggle" type="button" data-toggle aria-label="Engage Weaver and start a voice question" aria-pressed="false"><img class="skin" data-skin alt="Weaver website presence" draggable="false"></button>',
  '<span class="sr-status" data-status role="status" aria-live="polite">Connecting</span><span class="sr-status" data-dot data-state="loading"></span>',
  '<span class="sr-status" data-output aria-live="polite">Weaver is connecting to this site.</span>',
  '<div class="pointer" data-pointer aria-hidden="true"></div></div>',
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
  const factoryUrl = factoryAssetUrl(config);
  let currentSkinId = FACTORY_SKIN.skinId;
  let customizationState: 'FACTORY_DEFAULT' | 'CUSTOM' = 'FACTORY_DEFAULT';
  let disposeCustomAsset: (() => void) | undefined;
  let pointers: OrbPointerRecord[] = [];
  let abortController: AbortController | undefined;
  let recorder: MediaRecorder | undefined;
  let mediaStream: MediaStream | undefined;
  let audioContext: AudioContext | undefined;
  let analyser: AnalyserNode | undefined;
  let recordingStartedAt = 0;
  let silenceStartedAt: number | undefined;
  let speechDetected = false;
  let recordingMonitor = 0;
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
  const stopRecordingMonitor = () => { window.clearTimeout(recordingMonitor); recordingMonitor = 0; };
  const releaseMicrophone = () => {
    stopRecordingMonitor();
    mediaStream?.getTracks().forEach((track) => track.stop());
    mediaStream = undefined;
    if (audioContext && audioContext.state !== 'closed') void audioContext.close().catch(() => undefined);
    audioContext = undefined;
    analyser = undefined;
  };
  const monitorSilence = () => {
    if (!recorder || recorder.state !== 'recording' || !analyser) return;
    const samples = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(samples);
    const rms = Math.sqrt(samples.reduce((sum, value) => sum + (((value - 128) / 128) ** 2), 0) / samples.length);
    const now = Date.now();
    const elapsed = now - recordingStartedAt;
    if (rms >= SPEECH_RMS_THRESHOLD) { speechDetected = true; silenceStartedAt = undefined; }
    else if (speechDetected && rms <= SILENCE_RMS_THRESHOLD) {
      silenceStartedAt ??= now;
      if (elapsed >= RECORDING_MIN_MS && now - silenceStartedAt >= SILENCE_AFTER_SPEECH_MS) { recorder.stop(); return; }
    } else silenceStartedAt = undefined;
    if (elapsed >= RECORDING_MAX_MS) { recorder.stop(); return; }
    recordingMonitor = window.setTimeout(monitorSilence, SILENCE_SAMPLE_MS);
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
  const startVoiceQuestion = async (source: 'orb-engagement') => {
    const button = element<HTMLButtonElement>('[data-toggle]');
    if (recorder?.state === 'recording') { recorder.stop(); return true; }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setMessage('Voice recording is not supported in this browser.');
      log('Voice initialization available', { available: false, source });
      return false;
    }
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContext = new AudioContext();
      const sourceNode = audioContext.createMediaStreamSource(mediaStream);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 1024;
      sourceNode.connect(analyser);
      chunks = [];
      const mimeType = recorderMimeType();
      recorder = mimeType ? new MediaRecorder(mediaStream, { mimeType }) : new MediaRecorder(mediaStream);
      recordingStartedAt = Date.now();
      silenceStartedAt = undefined;
      speechDetected = false;
      recorder.addEventListener('dataavailable', (event) => { if (event.data.size) chunks.push(event.data); });
      recorder.addEventListener('stop', async () => {
        button.setAttribute('aria-pressed', 'false');
        button.setAttribute('aria-label', 'Engage Weaver and start a voice question');
        stopRecordingMonitor();
        const firstChunk = chunks[0];
        const recordedType = recorder?.mimeType || (firstChunk instanceof Blob ? firstChunk.type : '') || 'audio/webm';
        releaseMicrophone();
        setStatus('loading', 'Understanding');
        try {
          const response = await client.askVoice(new Blob(chunks, { type: recordedType }), recordingFileName(recordedType));
          handleResponse(response, response.transcript || '');
        } catch (error) {
          setStatus('offline', 'Voice unavailable');
          setMessage('Voice could not connect. Please try engaging Weaver again.');
          log('Runtime failure', { stage: 'voice', message: error instanceof Error ? error.message : String(error), source });
        }
      });
      recorder.start();
      button.setAttribute('aria-pressed', 'true');
      button.setAttribute('aria-label', 'Finish voice question');
      setStatus('online', 'Listening');
      setMessage('I am listening. Choose Finish when your question is complete.');
      log('Voice initialization available', { available: true, permissionRequested: true, source });
      monitorSilence();
      return true;
    } catch {
      setMessage('Microphone permission was not granted. Allow access, then engage Weaver again.');
      log('Voice initialization available', { available: true, permission: 'denied', source });
      return false;
    }
  };
  const runStartupEncounter = (siteName: string) => {
    if (startupStarted || routeOf(window.location.href) !== '/') return;
    if (window.sessionStorage.getItem(STARTUP_SESSION_KEY) === '1') return;
    startupStarted = true;
    window.sessionStorage.setItem(STARTUP_SESSION_KEY, '1');
    setStatus('online', 'Present');
    setMessage(`Weaver is present on ${siteName}. Engage Weaver to speak.`);
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
          // Installed sites may be cross-origin from the ORB runtime. Resolve
          // published skin assets from the runtime host, not the embedding
          // site's origin, while retaining support for absolute asset URLs.
          bodyAssetUrl: new URL(response.orb_identity.asset_path, new URL(config.runtime).origin).toString(),
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
    void startVoiceQuestion('orb-engagement');
  });

  const unmount = () => {
    if (!mounted) return;
    mounted = false;
    abortController?.abort();
    stopObserving();
    client.destroy();
    if (recorder?.state === 'recording') recorder.stop();
    releaseMicrophone();
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
