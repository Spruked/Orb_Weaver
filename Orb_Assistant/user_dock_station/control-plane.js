const http = require('http');
const crypto = require('crypto');

function sendJson(response, statusCode, payload) {
  const body = JSON.stringify(payload);
  response.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff'
  });
  response.end(body);
}

function readJson(request, maxBytes = 64 * 1024) {
  return new Promise((resolve, reject) => {
    let body = '';
    request.setEncoding('utf8');
    request.on('data', (chunk) => {
      body += chunk;
      if (Buffer.byteLength(body) > maxBytes) {
        reject(new Error('Request body too large'));
        request.destroy();
      }
    });
    request.on('end', () => {
      if (!body) return resolve({});
      try {
        resolve(JSON.parse(body));
      } catch {
        reject(new Error('Invalid JSON'));
      }
    });
    request.on('error', reject);
  });
}

function safeEqual(left, right) {
  const a = Buffer.from(String(left || ''));
  const b = Buffer.from(String(right || ''));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function isLoopback(request) {
  const address = String(request.socket?.remoteAddress || '').toLowerCase();
  return address === '127.0.0.1' || address === '::1' || address === '::ffff:127.0.0.1';
}

class OrbDockControlPlane {
  constructor({
    host = '127.0.0.1',
    port = 17420,
    token,
    getRuntimeProfile,
    getRuntimeCredential = null,
    generate = null
  }) {
    if (!token) throw new Error('Dock control-plane token is required');
    if (typeof getRuntimeProfile !== 'function') throw new Error('getRuntimeProfile callback is required');
    this.host = host;
    this.port = port;
    this.token = token;
    this.getRuntimeProfile = getRuntimeProfile;
    this.getRuntimeCredential = getRuntimeCredential;
    this.generate = generate;
    this.server = null;
    this.orbs = new Map();
  }

  authenticate(request) {
    const authorization = String(request.headers.authorization || '');
    const supplied = authorization.startsWith('Bearer ') ? authorization.slice(7) : '';
    return safeEqual(supplied, this.token);
  }

  pruneOrbs() {
    const cutoff = Date.now() - 90_000;
    for (const [orbId, orb] of this.orbs.entries()) {
      if (orb.lastSeenAt < cutoff) this.orbs.delete(orbId);
    }
  }

  listOrbs() {
    this.pruneOrbs();
    return Array.from(this.orbs.values())
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((orb) => ({
        id: orb.id,
        name: orb.name,
        kind: orb.kind,
        version: orb.version,
        site: orb.site,
        status: orb.status,
        lastSeenAt: new Date(orb.lastSeenAt).toISOString()
      }));
  }

  async handleGenerate(request, response) {
    if (!isLoopback(request)) {
      return sendJson(response, 403, { error: 'loopback_only' });
    }
    if (typeof this.generate !== 'function') {
      return sendJson(response, 503, { error: 'provider_gateway_unavailable' });
    }
    try {
      const payload = await readJson(request, 1024 * 1024);
      const prompt = String(payload.prompt || '').trim();
      if (!prompt) return sendJson(response, 400, { error: 'prompt is required' });
      const startedAt = Date.now();
      const result = await this.generate({
        prompt,
        model: payload.model,
        options: payload.options || {}
      });
      return sendJson(response, 200, {
        model: result.model,
        response: result.text,
        done: true,
        done_reason: 'stop',
        provider: result.provider,
        provider_slot: result.slot,
        profile_revision: result.profileRevision,
        total_duration_ms: Date.now() - startedAt
      });
    } catch (error) {
      return sendJson(response, 502, {
        error: String(error?.message || error).slice(0, 500),
        attempts: Array.isArray(error?.attempts) ? error.attempts : []
      });
    }
  }

  async handle(request, response) {
    const url = new URL(request.url, `http://${this.host}:${this.port}`);

    if (request.method === 'GET' && url.pathname === '/health') {
      return sendJson(response, 200, {
        status: 'ok',
        service: 'orb-user-dock-station',
        host: this.host,
        port: this.port,
        provider_gateway: typeof this.generate === 'function'
      });
    }

    if (request.method === 'POST' && url.pathname === '/api/generate') {
      return this.handleGenerate(request, response);
    }

    if (!this.authenticate(request)) {
      return sendJson(response, 401, { error: 'unauthorized' });
    }

    if (request.method === 'GET' && url.pathname === '/v1/runtime-profile') {
      return sendJson(response, 200, this.getRuntimeProfile());
    }

    const credentialMatch = url.pathname.match(/^\/v1\/runtime-credential\/(primary|fallback)$/);
    if (request.method === 'GET' && credentialMatch) {
      if (typeof this.getRuntimeCredential !== 'function') {
        return sendJson(response, 501, { error: 'runtime credential service unavailable' });
      }
      const apiKey = this.getRuntimeCredential(credentialMatch[1]);
      if (!apiKey) return sendJson(response, 404, { error: 'credential_not_configured' });
      return sendJson(response, 200, { slot: credentialMatch[1], apiKey });
    }

    if (request.method === 'GET' && url.pathname === '/v1/orbs') {
      return sendJson(response, 200, { orbs: this.listOrbs() });
    }

    if (request.method === 'POST' && url.pathname === '/v1/orbs/register') {
      try {
        const payload = await readJson(request);
        const id = String(payload.id || '').trim().slice(0, 120);
        if (!id) return sendJson(response, 400, { error: 'orb id is required' });
        this.orbs.set(id, {
          id,
          name: String(payload.name || id).trim().slice(0, 120),
          kind: String(payload.kind || 'website_orb').trim().slice(0, 80),
          version: String(payload.version || '').trim().slice(0, 80),
          site: String(payload.site || '').trim().slice(0, 300),
          status: String(payload.status || 'connected').trim().slice(0, 80),
          lastSeenAt: Date.now()
        });
        return sendJson(response, 200, {
          registered: true,
          revision: this.getRuntimeProfile().revision
        });
      } catch (error) {
        return sendJson(response, 400, { error: error.message });
      }
    }

    if (request.method === 'POST' && url.pathname === '/v1/orbs/heartbeat') {
      try {
        const payload = await readJson(request);
        const id = String(payload.id || '').trim().slice(0, 120);
        const existing = this.orbs.get(id);
        if (!existing) return sendJson(response, 404, { error: 'orb is not registered' });
        existing.lastSeenAt = Date.now();
        existing.status = String(payload.status || existing.status).trim().slice(0, 80);
        return sendJson(response, 200, {
          ok: true,
          revision: this.getRuntimeProfile().revision
        });
      } catch (error) {
        return sendJson(response, 400, { error: error.message });
      }
    }

    return sendJson(response, 404, { error: 'not_found' });
  }

  start() {
    if (this.server) return Promise.resolve({ host: this.host, port: this.port });
    this.server = http.createServer((request, response) => {
      this.handle(request, response).catch((error) => {
        console.error('Dock control-plane request failed:', error);
        if (!response.headersSent) sendJson(response, 500, { error: 'internal_error' });
        else response.end();
      });
    });

    return new Promise((resolve, reject) => {
      const onError = (error) => {
        this.server = null;
        reject(error);
      };
      this.server.once('error', onError);
      this.server.listen(this.port, this.host, () => {
        this.server.off('error', onError);
        const address = this.server.address();
        this.port = typeof address === 'object' && address ? address.port : this.port;
        resolve({ host: this.host, port: this.port });
      });
    });
  }

  stop() {
    if (!this.server) return Promise.resolve();
    const server = this.server;
    this.server = null;
    return new Promise((resolve) => server.close(resolve));
  }
}

module.exports = { OrbDockControlPlane };
