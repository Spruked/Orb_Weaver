function trimSlash(value) {
  return String(value || '').trim().replace(/\/+$/, '');
}

function joinUrl(baseUrl, suffix) {
  const base = trimSlash(baseUrl);
  if (!base) return suffix;
  if (base.endsWith(suffix)) return base;
  return `${base}${suffix.startsWith('/') ? '' : '/'}${suffix}`;
}

function extractOpenAIText(payload) {
  return String(
    payload?.choices?.[0]?.message?.content ||
    payload?.choices?.[0]?.text ||
    payload?.output_text ||
    ''
  ).trim();
}

function extractAnthropicText(payload) {
  const blocks = Array.isArray(payload?.content) ? payload.content : [];
  return blocks
    .filter((block) => block?.type === 'text' && block?.text)
    .map((block) => String(block.text))
    .join('\n')
    .trim();
}

function extractGoogleText(payload) {
  const parts = payload?.candidates?.[0]?.content?.parts;
  return Array.isArray(parts)
    ? parts.map((part) => String(part?.text || '')).join('\n').trim()
    : '';
}

async function readFailure(response) {
  const text = await response.text().catch(() => '');
  return text.slice(0, 600) || response.statusText || `HTTP ${response.status}`;
}

async function postJson(url, headers, body, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...headers
      },
      body: JSON.stringify(body),
      signal: controller.signal
    });
    if (!response.ok) {
      throw new Error(await readFailure(response));
    }
    return response.json();
  } finally {
    clearTimeout(timer);
  }
}

class ProviderRouter {
  constructor({ getRuntimeProfile, getCredential }) {
    if (typeof getRuntimeProfile !== 'function') throw new Error('getRuntimeProfile is required');
    if (typeof getCredential !== 'function') throw new Error('getCredential is required');
    this.getRuntimeProfile = getRuntimeProfile;
    this.getCredential = getCredential;
  }

  orderedSlots(profile) {
    const mode = profile.llm.routingMode;
    const primary = { slot: 'primary', config: profile.llm.primary };
    const fallback = { slot: 'fallback', config: profile.llm.fallback };
    if (mode === 'local_only') {
      return [primary, fallback].filter((entry) => entry.config.provider === 'local_openai_compatible');
    }
    if (mode === 'api_only') {
      return [primary, fallback].filter((entry) => entry.config.provider !== 'local_openai_compatible');
    }
    return profile.llm.fallback.enabled ? [primary, fallback] : [primary];
  }

  async invokeSlot(slot, config, prompt, requestOptions = {}) {
    const provider = config.provider;
    const model = String(config.model || requestOptions.model || '').trim();
    if (!model) throw new Error(`${slot} model is not configured`);
    const apiKey = config.apiKeyStored ? await this.getCredential(slot) : null;
    const timeoutMs = Number(config.timeoutMs || 45000);
    const temperature = Number.isFinite(Number(requestOptions.temperature))
      ? Math.max(0, Math.min(1.5, Number(requestOptions.temperature)))
      : 0.35;
    const maxTokens = Number.isFinite(Number(requestOptions.maxTokens))
      ? Math.max(16, Math.min(2048, Number(requestOptions.maxTokens)))
      : 180;

    if (provider === 'anthropic') {
      if (!apiKey) throw new Error('Anthropic API key is not configured');
      const baseUrl = trimSlash(config.baseUrl) || 'https://api.anthropic.com/v1';
      const payload = await postJson(
        joinUrl(baseUrl, '/messages'),
        {
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01'
        },
        {
          model,
          max_tokens: maxTokens,
          temperature,
          messages: [{ role: 'user', content: prompt }]
        },
        timeoutMs
      );
      const text = extractAnthropicText(payload);
      if (!text) throw new Error('Anthropic returned no text');
      return { text, provider, model };
    }

    if (provider === 'google') {
      if (!apiKey) throw new Error('Google API key is not configured');
      const baseUrl = trimSlash(config.baseUrl) || 'https://generativelanguage.googleapis.com/v1beta';
      const endpoint = `${joinUrl(baseUrl, `/models/${encodeURIComponent(model)}:generateContent`)}?key=${encodeURIComponent(apiKey)}`;
      const payload = await postJson(
        endpoint,
        {},
        {
          contents: [{ role: 'user', parts: [{ text: prompt }] }],
          generationConfig: {
            temperature,
            maxOutputTokens: maxTokens
          }
        },
        timeoutMs
      );
      const text = extractGoogleText(payload);
      if (!text) throw new Error('Google returned no text');
      return { text, provider, model };
    }

    const baseUrl = trimSlash(config.baseUrl) || (provider === 'openai' ? 'https://api.openai.com/v1' : 'http://127.0.0.1:40343/v1');
    if (provider !== 'local_openai_compatible' && !apiKey) {
      throw new Error(`${provider} API key is not configured`);
    }
    const payload = await postJson(
      joinUrl(baseUrl, '/chat/completions'),
      apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
      {
        model,
        messages: [{ role: 'user', content: prompt }],
        temperature,
        max_tokens: maxTokens,
        stream: false
      },
      timeoutMs
    );
    const text = extractOpenAIText(payload);
    if (!text) throw new Error(`${provider} returned no text`);
    return { text, provider, model };
  }

  async generate({ prompt, model, options = {} }) {
    const cleanPrompt = String(prompt || '').trim();
    if (!cleanPrompt) throw new Error('Prompt is required');
    const profile = this.getRuntimeProfile();
    const attempts = [];
    for (const entry of this.orderedSlots(profile)) {
      if (entry.slot === 'fallback' && !profile.llm.fallback.enabled) continue;
      try {
        const result = await this.invokeSlot(entry.slot, entry.config, cleanPrompt, {
          model,
          temperature: options.temperature,
          maxTokens: options.num_predict
        });
        return {
          ...result,
          slot: entry.slot,
          profileRevision: profile.revision
        };
      } catch (error) {
        attempts.push({
          slot: entry.slot,
          provider: entry.config.provider,
          error: String(error?.message || error).slice(0, 500)
        });
      }
    }
    const failure = new Error('No configured model provider completed the request');
    failure.attempts = attempts;
    throw failure;
  }
}

module.exports = {
  ProviderRouter,
  extractOpenAIText,
  extractAnthropicText,
  extractGoogleText
};
