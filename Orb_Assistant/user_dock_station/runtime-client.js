const fs = require('fs');
const http = require('http');

class OrbDockRuntimeClient {
  constructor({
    tokenPath,
    host = '127.0.0.1',
    port = 17420,
    orb,
    pollIntervalMs = 2000,
    heartbeatIntervalMs = 30000
  }) {
    if (!tokenPath) throw new Error('Dock Station tokenPath is required');
    if (!orb?.id) throw new Error('ORB runtime id is required');
    this.tokenPath = tokenPath;
    this.host = host;
    this.port = port;
    this.orb = { ...orb };
    this.pollIntervalMs = Math.max(1000, Number(pollIntervalMs) || 2000);
    this.heartbeatIntervalMs = Math.max(10000, Number(heartbeatIntervalMs) || 30000);
    this.token = null;
    this.lastRevision = null;
    this.pollTimer = null;
    this.heartbeatTimer = null;
    this.running = false;
    this.pollInFlight = false;
  }

  loadToken() {
    const token = fs.readFileSync(this.tokenPath, 'utf8').trim();
    if (token.length < 32) throw new Error('Dock Station runtime token is invalid');
    this.token = token;
    return token;
  }

  request(method, route, payload = null) {
    const token = this.token || this.loadToken();
    const body = payload === null ? null : JSON.stringify(payload);
    return new Promise((resolve, reject) => {
      const request = http.request({
        host: this.host,
        port: this.port,
        method,
        path: route,
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
          ...(body ? {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(body)
          } : {})
        },
        timeout: 5000
      }, (response) => {
        let responseBody = '';
        response.setEncoding('utf8');
        response.on('data', (chunk) => { responseBody += chunk; });
        response.on('end', () => {
          let parsed = {};
          try { parsed = responseBody ? JSON.parse(responseBody) : {}; } catch {}
          if (response.statusCode >= 200 && response.statusCode < 300) return resolve(parsed);
          const error = new Error(parsed.error || `Dock Station request failed with ${response.statusCode}`);
          error.statusCode = response.statusCode;
          reject(error);
        });
      });
      request.on('timeout', () => request.destroy(new Error('Dock Station request timed out')));
      request.on('error', reject);
      if (body) request.write(body);
      request.end();
    });
  }

  async register() {
    return this.request('POST', '/v1/orbs/register', {
      id: this.orb.id,
      name: this.orb.name || this.orb.id,
      kind: this.orb.kind || 'website_orb',
      version: this.orb.version || '',
      site: this.orb.site || '',
      status: this.orb.status || 'connected'
    });
  }

  async heartbeat(status = 'connected') {
    try {
      return await this.request('POST', '/v1/orbs/heartbeat', { id: this.orb.id, status });
    } catch (error) {
      if (error.statusCode === 404) {
        await this.register();
        return this.request('POST', '/v1/orbs/heartbeat', { id: this.orb.id, status });
      }
      throw error;
    }
  }

  getRuntimeProfile() {
    return this.request('GET', '/v1/runtime-profile');
  }

  async getCredential(slot = 'primary') {
    if (!['primary', 'fallback'].includes(slot)) throw new Error('Invalid provider credential slot');
    const result = await this.request('GET', `/v1/runtime-credential/${slot}`);
    return result.apiKey || null;
  }

  async poll(onProfile, onError) {
    if (this.pollInFlight || !this.running) return;
    this.pollInFlight = true;
    try {
      const profile = await this.getRuntimeProfile();
      if (profile.revision !== this.lastRevision) {
        this.lastRevision = profile.revision;
        await onProfile(profile, this);
      }
    } catch (error) {
      if (typeof onError === 'function') onError(error);
    } finally {
      this.pollInFlight = false;
    }
  }

  async start(onProfile, onError = null) {
    if (typeof onProfile !== 'function') throw new Error('onProfile callback is required');
    if (this.running) return;
    this.running = true;
    try {
      await this.register();
      await this.poll(onProfile, onError);
    } catch (error) {
      if (typeof onError === 'function') onError(error);
    }
    this.pollTimer = setInterval(() => this.poll(onProfile, onError), this.pollIntervalMs);
    this.heartbeatTimer = setInterval(() => {
      this.heartbeat().catch((error) => {
        if (typeof onError === 'function') onError(error);
      });
    }, this.heartbeatIntervalMs);
  }

  stop() {
    this.running = false;
    if (this.pollTimer) clearInterval(this.pollTimer);
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    this.pollTimer = null;
    this.heartbeatTimer = null;
  }
}

module.exports = { OrbDockRuntimeClient };
