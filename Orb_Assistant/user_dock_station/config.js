const fs = require('fs');
const path = require('path');

const PROVIDER_TYPES = Object.freeze([
  'local_openai_compatible',
  'openai',
  'anthropic',
  'google',
  'custom_openai_compatible'
]);

const DEFAULT_CONFIG = Object.freeze({
  schemaVersion: 'orb-dock-user-config/v1',
  revision: 1,
  updatedAt: null,
  activeProfileId: 'default',
  applyScope: {
    mode: 'all_orbs',
    orbIds: []
  },
  profiles: {
    default: {
      name: 'Confident Guide',
      llm: {
        routingMode: 'local_primary',
        primary: {
          provider: 'local_openai_compatible',
          model: 'Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M',
          baseUrl: 'http://127.0.0.1:40343/v1',
          apiKeyStored: false,
          timeoutMs: 45000
        },
        fallback: {
          enabled: false,
          provider: 'openai',
          model: '',
          baseUrl: '',
          apiKeyStored: false,
          timeoutMs: 45000
        }
      },
      voice: {
        enabled: true,
        provider: 'runtime_default',
        voiceId: 'weaver',
        volume: 0.9,
        rate: 0.94,
        pitch: 1,
        warmth: 88,
        energy: 76,
        styleDirection: 'Warm, assured, enthusiastic, conversational, never angry, never scolding, never impatient.'
      },
      behavior: {
        warmth: 88,
        enthusiasm: 82,
        salesmanship: 80,
        humor: 42,
        directness: 76,
        patience: 90,
        initiative: 82,
        verbosity: 38,
        greetOnArrival: true,
        speakFirst: true,
        autoListen: true,
        angryToneAllowed: false,
        hostilityAllowed: false,
        scoldingAllowed: false,
        selfDeprecationAllowed: false,
        diminishProductAllowed: false
      },
      motion: {
        enabled: true,
        speed: 0.32,
        expressive: true,
        avoidHeaderBand: true,
        remainClickable: true,
        sleepEnabled: true
      },
      memory: {
        enabled: true,
        requireVisitorApproval: true,
        rememberAcrossSessions: false
      },
      permissions: {
        voice: true,
        microphone: true,
        pointerGuidance: true,
        browserActions: true,
        requireApprovalForConsequentialActions: true
      },
      governance: {
        verifiedTargetsOnly: true,
        stageGovernorRequired: true,
        outcomeVerificationRequired: true,
        hiddenDecisionsProhibited: true,
        locked: true
      }
    }
  }
});

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function deepMerge(base, patch) {
  if (!isPlainObject(patch)) return clone(base);
  const out = clone(base);
  for (const [key, value] of Object.entries(patch)) {
    if (isPlainObject(value) && isPlainObject(out[key])) {
      out[key] = deepMerge(out[key], value);
    } else if (Array.isArray(value)) {
      out[key] = value.slice();
    } else if (value !== undefined) {
      out[key] = value;
    }
  }
  return out;
}

function clamp(value, min, max, fallback) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return Math.min(max, Math.max(min, numeric));
}

function cleanString(value, fallback = '', max = 500) {
  if (typeof value !== 'string') return fallback;
  return value.trim().slice(0, max);
}

function normalizeProvider(provider, fallback) {
  return PROVIDER_TYPES.includes(provider) ? provider : fallback;
}

function sanitizeProvider(provider, fallback) {
  return {
    provider: normalizeProvider(provider?.provider, fallback.provider),
    model: cleanString(provider?.model, fallback.model, 200),
    baseUrl: cleanString(provider?.baseUrl, fallback.baseUrl, 500),
    apiKeyStored: Boolean(provider?.apiKeyStored),
    timeoutMs: Math.round(clamp(provider?.timeoutMs, 5000, 180000, fallback.timeoutMs))
  };
}

function sanitizeConfig(input) {
  const defaults = clone(DEFAULT_CONFIG);
  const merged = deepMerge(defaults, input || {});
  const profileId = cleanString(merged.activeProfileId, 'default', 80) || 'default';
  const candidate = merged.profiles?.[profileId] || merged.profiles?.default || defaults.profiles.default;
  const base = defaults.profiles.default;

  const profile = {
    name: cleanString(candidate.name, base.name, 80),
    llm: {
      routingMode: ['local_primary', 'api_primary', 'local_only', 'api_only'].includes(candidate.llm?.routingMode)
        ? candidate.llm.routingMode
        : base.llm.routingMode,
      primary: sanitizeProvider(candidate.llm?.primary, base.llm.primary),
      fallback: {
        ...sanitizeProvider(candidate.llm?.fallback, base.llm.fallback),
        enabled: Boolean(candidate.llm?.fallback?.enabled)
      }
    },
    voice: {
      enabled: candidate.voice?.enabled !== false,
      provider: cleanString(candidate.voice?.provider, base.voice.provider, 100),
      voiceId: cleanString(candidate.voice?.voiceId, base.voice.voiceId, 100),
      volume: clamp(candidate.voice?.volume, 0, 1, base.voice.volume),
      rate: clamp(candidate.voice?.rate, 0.6, 1.5, base.voice.rate),
      pitch: clamp(candidate.voice?.pitch, 0.6, 1.5, base.voice.pitch),
      warmth: Math.round(clamp(candidate.voice?.warmth, 0, 100, base.voice.warmth)),
      energy: Math.round(clamp(candidate.voice?.energy, 0, 100, base.voice.energy)),
      styleDirection: cleanString(candidate.voice?.styleDirection, base.voice.styleDirection, 600)
    },
    behavior: {
      warmth: Math.round(clamp(candidate.behavior?.warmth, 0, 100, base.behavior.warmth)),
      enthusiasm: Math.round(clamp(candidate.behavior?.enthusiasm, 0, 100, base.behavior.enthusiasm)),
      salesmanship: Math.round(clamp(candidate.behavior?.salesmanship, 0, 100, base.behavior.salesmanship)),
      humor: Math.round(clamp(candidate.behavior?.humor, 0, 100, base.behavior.humor)),
      directness: Math.round(clamp(candidate.behavior?.directness, 0, 100, base.behavior.directness)),
      patience: Math.round(clamp(candidate.behavior?.patience, 0, 100, base.behavior.patience)),
      initiative: Math.round(clamp(candidate.behavior?.initiative, 0, 100, base.behavior.initiative)),
      verbosity: Math.round(clamp(candidate.behavior?.verbosity, 0, 100, base.behavior.verbosity)),
      greetOnArrival: candidate.behavior?.greetOnArrival !== false,
      speakFirst: candidate.behavior?.speakFirst !== false,
      autoListen: candidate.behavior?.autoListen !== false,
      angryToneAllowed: false,
      hostilityAllowed: false,
      scoldingAllowed: false,
      selfDeprecationAllowed: false,
      diminishProductAllowed: false
    },
    motion: {
      enabled: candidate.motion?.enabled !== false,
      speed: clamp(candidate.motion?.speed, 0.05, 1, base.motion.speed),
      expressive: candidate.motion?.expressive !== false,
      avoidHeaderBand: candidate.motion?.avoidHeaderBand !== false,
      remainClickable: true,
      sleepEnabled: candidate.motion?.sleepEnabled !== false
    },
    memory: {
      enabled: candidate.memory?.enabled !== false,
      requireVisitorApproval: true,
      rememberAcrossSessions: Boolean(candidate.memory?.rememberAcrossSessions)
    },
    permissions: {
      voice: candidate.permissions?.voice !== false,
      microphone: candidate.permissions?.microphone !== false,
      pointerGuidance: candidate.permissions?.pointerGuidance !== false,
      browserActions: candidate.permissions?.browserActions !== false,
      requireApprovalForConsequentialActions: true
    },
    governance: {
      verifiedTargetsOnly: true,
      stageGovernorRequired: true,
      outcomeVerificationRequired: true,
      hiddenDecisionsProhibited: true,
      locked: true
    }
  };

  const mode = merged.applyScope?.mode === 'selected_orbs' ? 'selected_orbs' : 'all_orbs';
  const orbIds = Array.isArray(merged.applyScope?.orbIds)
    ? merged.applyScope.orbIds.map((id) => cleanString(id, '', 120)).filter(Boolean).slice(0, 100)
    : [];

  return {
    schemaVersion: DEFAULT_CONFIG.schemaVersion,
    revision: Math.max(1, Math.round(Number(merged.revision) || 1)),
    updatedAt: merged.updatedAt || null,
    activeProfileId: profileId,
    applyScope: { mode, orbIds },
    profiles: { [profileId]: profile }
  };
}

function buildRuntimeProfile(config) {
  const safe = sanitizeConfig(config);
  const profile = safe.profiles[safe.activeProfileId];
  return {
    schemaVersion: safe.schemaVersion,
    revision: safe.revision,
    updatedAt: safe.updatedAt,
    profileId: safe.activeProfileId,
    applyScope: safe.applyScope,
    llm: profile.llm,
    voice: profile.voice,
    behavior: profile.behavior,
    motion: profile.motion,
    memory: profile.memory,
    permissions: profile.permissions,
    governance: profile.governance,
    articulationContract: {
      identity: 'Embodied Website ORB',
      requiredTone: 'confident, warm, enthusiastic, commercially capable, never angry',
      productContractMayBeStatedConfidently: true,
      liveClaimsMustMatchRuntimeEvidence: true,
      selfDeprecationProhibited: true,
      productDiminishmentProhibited: true,
      demonstrationTransition: "And that's just the start. When it's all said and done, I will amaze the skeptics. So let me show you what I can do today. Follow me."
    }
  };
}

class ConfigStore {
  constructor(filePath) {
    this.filePath = filePath;
  }

  load() {
    try {
      const parsed = JSON.parse(fs.readFileSync(this.filePath, 'utf8'));
      return sanitizeConfig(parsed);
    } catch (error) {
      if (error.code !== 'ENOENT') {
        console.warn('Dock Station config load failed; restoring defaults:', error.message);
      }
      const defaults = sanitizeConfig(DEFAULT_CONFIG);
      this.save(defaults, { incrementRevision: false });
      return defaults;
    }
  }

  save(nextConfig, options = {}) {
    const safe = sanitizeConfig(nextConfig);
    const current = options.incrementRevision === false ? null : this.tryLoadCurrent();
    safe.revision = current ? current.revision + 1 : safe.revision;
    safe.updatedAt = new Date().toISOString();
    fs.mkdirSync(path.dirname(this.filePath), { recursive: true });
    const temporary = `${this.filePath}.tmp`;
    fs.writeFileSync(temporary, `${JSON.stringify(safe, null, 2)}\n`, 'utf8');
    fs.renameSync(temporary, this.filePath);
    return safe;
  }

  tryLoadCurrent() {
    try {
      return sanitizeConfig(JSON.parse(fs.readFileSync(this.filePath, 'utf8')));
    } catch {
      return null;
    }
  }
}

module.exports = {
  PROVIDER_TYPES,
  DEFAULT_CONFIG,
  ConfigStore,
  sanitizeConfig,
  buildRuntimeProfile
};
