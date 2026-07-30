const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('os');
const fs = require('fs');
const path = require('path');
const { DEFAULT_CONFIG, ConfigStore, sanitizeConfig, buildRuntimeProfile } = require('../config');

test('owner may tune behavior while prohibited tone remains locked off', () => {
  const config = sanitizeConfig({
    ...DEFAULT_CONFIG,
    profiles: {
      default: {
        ...DEFAULT_CONFIG.profiles.default,
        behavior: {
          ...DEFAULT_CONFIG.profiles.default.behavior,
          warmth: 12,
          enthusiasm: 99,
          angryToneAllowed: true,
          hostilityAllowed: true,
          selfDeprecationAllowed: true,
          diminishProductAllowed: true
        }
      }
    }
  });
  const behavior = config.profiles.default.behavior;
  assert.equal(behavior.warmth, 12);
  assert.equal(behavior.enthusiasm, 99);
  assert.equal(behavior.angryToneAllowed, false);
  assert.equal(behavior.hostilityAllowed, false);
  assert.equal(behavior.selfDeprecationAllowed, false);
  assert.equal(behavior.diminishProductAllowed, false);
});

test('provider selection supports local and API models', () => {
  const config = sanitizeConfig({
    ...DEFAULT_CONFIG,
    profiles: {
      default: {
        ...DEFAULT_CONFIG.profiles.default,
        llm: {
          routingMode: 'api_primary',
          primary: {
            provider: 'anthropic',
            model: 'owner-selected-claude-model',
            baseUrl: 'https://provider.example/v1',
            timeoutMs: 60000
          },
          fallback: {
            enabled: true,
            provider: 'local_openai_compatible',
            model: 'local-model',
            baseUrl: 'http://127.0.0.1:40343/v1',
            timeoutMs: 30000
          }
        }
      }
    }
  });
  assert.equal(config.profiles.default.llm.primary.provider, 'anthropic');
  assert.equal(config.profiles.default.llm.fallback.provider, 'local_openai_compatible');
  assert.equal(config.profiles.default.llm.fallback.enabled, true);
});

test('governance boundaries cannot be disabled by a profile write', () => {
  const config = sanitizeConfig({
    ...DEFAULT_CONFIG,
    profiles: {
      default: {
        ...DEFAULT_CONFIG.profiles.default,
        governance: {
          verifiedTargetsOnly: false,
          stageGovernorRequired: false,
          outcomeVerificationRequired: false,
          hiddenDecisionsProhibited: false,
          locked: false
        },
        permissions: {
          ...DEFAULT_CONFIG.profiles.default.permissions,
          requireApprovalForConsequentialActions: false
        }
      }
    }
  });
  const profile = config.profiles.default;
  assert.deepEqual(profile.governance, {
    verifiedTargetsOnly: true,
    stageGovernorRequired: true,
    outcomeVerificationRequired: true,
    hiddenDecisionsProhibited: true,
    locked: true
  });
  assert.equal(profile.permissions.requireApprovalForConsequentialActions, true);
});

test('config store writes atomically and increments revision', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'orb-dock-test-'));
  const file = path.join(directory, 'config.json');
  const store = new ConfigStore(file);
  const first = store.load();
  const second = store.save(first);
  assert.equal(second.revision, first.revision + 1);
  assert.equal(fs.existsSync(file), true);
  fs.rmSync(directory, { recursive: true, force: true });
});

test('runtime profile carries the non-diminishment articulation contract', () => {
  const runtime = buildRuntimeProfile(DEFAULT_CONFIG);
  assert.equal(runtime.articulationContract.selfDeprecationProhibited, true);
  assert.equal(runtime.articulationContract.productDiminishmentProhibited, true);
  assert.match(runtime.articulationContract.demonstrationTransition, /amaze the skeptics/i);
});
