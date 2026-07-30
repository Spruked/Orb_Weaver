const test = require('node:test');
const assert = require('node:assert/strict');
const { ProviderRouter } = require('../provider-router');

function response(payload, ok = true, status = 200) {
  return {
    ok,
    status,
    statusText: ok ? 'OK' : 'Error',
    json: async () => payload,
    text: async () => JSON.stringify(payload)
  };
}

test('routes the active profile to a local OpenAI-compatible model', async () => {
  const originalFetch = global.fetch;
  let captured = null;
  global.fetch = async (url, options) => {
    captured = { url, options };
    return response({ choices: [{ message: { content: 'Warm local answer.' } }] });
  };
  try {
    const router = new ProviderRouter({
      getRuntimeProfile: () => ({
        revision: 7,
        llm: {
          routingMode: 'local_only',
          primary: {
            provider: 'local_openai_compatible',
            model: 'qwen-local',
            baseUrl: 'http://127.0.0.1:40343/v1',
            apiKeyStored: false,
            timeoutMs: 45000
          },
          fallback: { enabled: false, provider: 'openai' }
        }
      }),
      getCredential: async () => null
    });
    const result = await router.generate({ prompt: 'Say hello.' });
    assert.equal(result.text, 'Warm local answer.');
    assert.equal(result.provider, 'local_openai_compatible');
    assert.equal(result.profileRevision, 7);
    assert.equal(captured.url, 'http://127.0.0.1:40343/v1/chat/completions');
  } finally {
    global.fetch = originalFetch;
  }
});

test('routes to Anthropic with an encrypted credential supplied by the main process', async () => {
  const originalFetch = global.fetch;
  let captured = null;
  global.fetch = async (url, options) => {
    captured = { url, options };
    return response({ content: [{ type: 'text', text: 'Confident Claude answer.' }] });
  };
  try {
    const router = new ProviderRouter({
      getRuntimeProfile: () => ({
        revision: 9,
        llm: {
          routingMode: 'api_only',
          primary: {
            provider: 'anthropic',
            model: 'claude-owner-choice',
            baseUrl: 'https://api.anthropic.com/v1',
            apiKeyStored: true,
            timeoutMs: 45000
          },
          fallback: { enabled: false, provider: 'local_openai_compatible' }
        }
      }),
      getCredential: async () => 'secret-key'
    });
    const result = await router.generate({ prompt: 'Explain the site.' });
    assert.equal(result.text, 'Confident Claude answer.');
    assert.equal(result.provider, 'anthropic');
    assert.equal(captured.url, 'https://api.anthropic.com/v1/messages');
    assert.equal(captured.options.headers['x-api-key'], 'secret-key');
  } finally {
    global.fetch = originalFetch;
  }
});

test('uses the configured fallback when the primary provider fails', async () => {
  const originalFetch = global.fetch;
  let call = 0;
  global.fetch = async () => {
    call += 1;
    if (call === 1) return response({ error: 'primary failed' }, false, 500);
    return response({ choices: [{ message: { content: 'Fallback answer.' } }] });
  };
  try {
    const router = new ProviderRouter({
      getRuntimeProfile: () => ({
        revision: 11,
        llm: {
          routingMode: 'api_primary',
          primary: {
            provider: 'openai',
            model: 'gpt-primary',
            baseUrl: 'https://api.openai.com/v1',
            apiKeyStored: true,
            timeoutMs: 45000
          },
          fallback: {
            enabled: true,
            provider: 'local_openai_compatible',
            model: 'qwen-fallback',
            baseUrl: 'http://127.0.0.1:40343/v1',
            apiKeyStored: false,
            timeoutMs: 45000
          }
        }
      }),
      getCredential: async () => 'openai-key'
    });
    const result = await router.generate({ prompt: 'Continue.' });
    assert.equal(result.text, 'Fallback answer.');
    assert.equal(result.slot, 'fallback');
    assert.equal(call, 2);
  } finally {
    global.fetch = originalFetch;
  }
});
