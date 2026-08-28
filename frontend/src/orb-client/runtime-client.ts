import type { OrbBootstrapResponse, OrbLoaderConfig, OrbRuntimeResponse, OrbSiteSnapshot } from './types';

const localHost = (hostname: string) => hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]';

function approvedUrl(raw: string, secureProtocol: 'https:' | 'wss:'): URL {
  const url = new URL(raw, window.location.href);
  const localProtocol = secureProtocol === 'https:' ? 'http:' : 'ws:';
  if (url.protocol !== secureProtocol && !(url.protocol === localProtocol && localHost(url.hostname))) {
    throw new Error(`ORB endpoint must use ${secureProtocol.replace(':', '').toUpperCase()}`);
  }
  return url;
}

export class OrbRuntimeClient {
  readonly config: Required<Pick<OrbLoaderConfig, 'siteId' | 'runtime' | 'version'>> & OrbLoaderConfig;
  private socket?: WebSocket;

  constructor(config: OrbLoaderConfig) {
    const runtime = approvedUrl(config.runtime.replace(/\/+$/, ''), 'https:').toString().replace(/\/+$/, '');
    if (config.ws) approvedUrl(config.ws, 'wss:');
    this.config = { ...config, runtime, version: config.version || '1' };
  }

  private endpoint(path: string) {
    return `${this.config.runtime}${path.startsWith('/') ? path : `/${path}`}`;
  }

  private async json<T>(url: string, init?: RequestInit): Promise<T> {
    const response = await fetch(url, { mode: 'cors', credentials: 'omit', ...init });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `ORB runtime returned ${response.status}`);
    }
    return response.json();
  }

  bootstrap(snapshot: OrbSiteSnapshot, signal?: AbortSignal) {
    return this.json<OrbBootstrapResponse>(this.endpoint('/bootstrap'), {
      method: 'POST',
      signal,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        site_id: this.config.siteId,
        target_url: snapshot.url,
        loader_version: this.config.version,
        page_context: snapshot,
      }),
    });
  }

  ask(transcript: string) {
    return this.json<OrbRuntimeResponse>(this.endpoint('/website-text'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        transcript,
        synthesize_tts: false,
        target_url: window.location.href,
        site_id: this.config.siteId,
      }),
    });
  }

  askVoice(audio: Blob, filename = 'orb-question.webm') {
    const form = new FormData();
    form.append('audio', audio, filename);
    form.append('target_url', window.location.href);
    form.append('site_id', this.config.siteId);
    return this.json<OrbRuntimeResponse>(this.endpoint('/website-voice'), { method: 'POST', body: form });
  }

  mediaUrl(path: string) {
    return new URL(path, new URL(this.config.runtime).origin).toString();
  }

  connect(snapshot: OrbSiteSnapshot, onEvent?: (event: unknown) => void) {
    let wsUrl = this.config.ws;
    if (!wsUrl) {
      const derived = new URL(this.config.runtime);
      derived.protocol = derived.protocol === 'https:' ? 'wss:' : 'ws:';
      derived.pathname = '/ws/orb';
      derived.search = '';
      wsUrl = derived.toString();
    }
    const url = approvedUrl(wsUrl, 'wss:');
    url.searchParams.set('site_id', this.config.siteId);
    url.searchParams.set('loader_version', this.config.version);
    this.socket = new WebSocket(url.toString());
    this.socket.addEventListener('open', () => this.reportRoute(snapshot));
    this.socket.addEventListener('message', (event) => {
      try { onEvent?.(JSON.parse(event.data)); } catch { onEvent?.(event.data); }
    });
    return this.socket;
  }

  reportRoute(snapshot: OrbSiteSnapshot) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: 'orb.route', target_url: snapshot.url, page_context: snapshot }));
    }
  }

  destroy() {
    this.socket?.close(1000, 'ORB removed');
    this.socket = undefined;
  }
}
