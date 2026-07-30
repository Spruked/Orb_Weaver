# ORB User Dock Station

The Dock Station is the owner-facing desktop control surface for installed ORBs.

It is not a developer-only settings page and it is not a second ORB runtime. It publishes one authoritative user profile that assigned ORBs consume through the authenticated local control plane.

## What the owner can change

- Primary and fallback LLM provider
- Local OpenAI-compatible model endpoint
- OpenAI / GPT provider selection
- Anthropic / Claude provider selection
- Google / Gemini provider selection
- Custom OpenAI-compatible provider selection
- Model name, base URL, timeout, and encrypted API credential
- Warmth, enthusiasm, salesmanship, humor, directness, patience, initiative, and response length
- Voice provider, voice ID, volume, speaking rate, pitch, warmth, energy, and voice direction
- Greeting, speak-first, and automatic-listening behavior
- Movement speed, expressive motion, header avoidance, and sleep availability
- Memory, speech, microphone, pointer guidance, and browser-action availability
- Apply-to-all or selected-ORB scope

## Locked rules

The Dock Station cannot disable:

- Verified pointer targets
- Stage Governor authority
- Visitor approval for consequential actions
- Outcome verification
- Visitor approval for retained or transferred memory
- ORB click/tap reachability while active
- Prohibition on angry, hostile, scolding, self-deprecating, or product-diminishing articulation

These are runtime laws, not personality preferences.

## Start

From `Orb_Assistant/user_dock_station`:

```bash
npm install
npm start
```

Or from `Orb_Assistant`:

```bash
npm run dock
```

Run configuration tests with:

```bash
npm test
```

## Runtime control plane

The Electron process binds only to:

```text
127.0.0.1:17420
```

The runtime token is generated at startup inside Electron's user-data directory:

```text
orb-dock-runtime.token
```

The profile and encrypted credentials are stored separately:

```text
orb-dock-config.json
orb-dock-credentials.json
```

API keys are encrypted with Electron `safeStorage`. When operating-system encryption is unavailable, the Dock Station refuses to save the key.

## Installed ORB integration

Use `runtime-client.js` from the installed native ORB bridge. The browser page itself must never receive the Dock Station token or provider credential.

```js
const path = require('path');
const { OrbDockRuntimeClient } = require('./runtime-client');

const client = new OrbDockRuntimeClient({
  tokenPath: path.join(dockUserDataPath, 'orb-dock-runtime.token'),
  orb: {
    id: 'customer-site-orb',
    name: 'Customer Website ORB',
    kind: 'website_orb',
    version: '1.0.0',
    site: 'https://customer.example'
  }
});

await client.start(async (profile, dock) => {
  runtime.applyBehavior(profile.behavior);
  runtime.applyVoice(profile.voice);
  runtime.applyMotion(profile.motion);
  runtime.applyPermissions(profile.permissions);

  const provider = profile.llm.primary;
  const apiKey = provider.apiKeyStored
    ? await dock.getCredential('primary')
    : null;

  runtime.selectModel({ ...provider, apiKey });
});
```

The ORB registers itself, heartbeats, polls profile revisions, and applies a new revision without exposing credentials to website JavaScript.

## Provider routing

The Dock Station publishes provider configuration; the installed ORB's existing model adapter remains responsible for invoking the selected provider. This prevents the Dock Station from becoming a competing reasoning runtime.

Routing modes:

- `local_primary`
- `api_primary`
- `local_only`
- `api_only`

## Current build boundary

The Dock Station application, profile persistence, encrypted credential storage, control plane, system-tray controls, and native runtime client are implemented.

Each production ORB package still needs to call the runtime client from its native bridge and map the received profile into that ORB's existing voice, motion, and model adapters.
