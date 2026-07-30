# ORB User Dock Station

The Dock Station is the owner-facing desktop control surface for installed ORBs.

It publishes one authoritative owner profile and provides a local model gateway so assigned ORBs can change behavior, voice direction, and LLM provider without receiving provider credentials in website JavaScript.

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
- Prohibition on angry, hostile, scolding, impatient, self-deprecating, or product-diminishing articulation
- The distinction between confident product contract and verified live runtime claims

These are runtime laws, not personality preferences.

## Complete articulation contract

`articulation-contract.js` is inserted as the provider-level system instruction for local models, OpenAI, Anthropic, Google, and custom compatible providers. Owner sliders adjust delivery emphasis but cannot weaken identity, truth, permission, governance, or non-diminishment rules.

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

Run tests with:

```bash
npm test
```

Build Windows installer and portable packages with:

```bash
npm run dist:win
```

## Runtime control plane and model gateway

The Electron process binds to:

```text
127.0.0.1:17420
```

The local Ollama-compatible generation endpoint is:

```text
http://127.0.0.1:17420/api/generate
```

Orb Weaver can retain its existing Ollama-shaped request contract and point `LOCAL_LLM_URL` at this endpoint. The Dock Station then routes each request through the active owner-selected provider and applies the current behavior instruction.

Example backend configuration when the Dock Station and backend share the same loopback network:

```dotenv
LOCAL_LLM_URL=http://127.0.0.1:17420/api/generate
LOCAL_LLM_MODEL=dock-active
```

When the backend runs inside WSL and the Dock Station runs as a Windows application, the Windows-to-WSL network bridge must be configured before using the gateway URL. Do not expose the gateway to a LAN without an authenticated transport rule.

## Credential protection

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

Credentials are decrypted only inside the Electron main process. They are not returned to the Dock Station renderer or website JavaScript.

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

await client.start(async (profile) => {
  runtime.applyBehavior(profile.behavior);
  runtime.applyVoice(profile.voice);
  runtime.applyMotion(profile.motion);
  runtime.applyPermissions(profile.permissions);
});
```

The ORB registers itself, heartbeats, polls profile revisions, and applies a new revision without exposing credentials to the page.

## Provider routing

Routing modes:

- `local_primary`
- `api_primary`
- `local_only`
- `api_only`

The gateway supports:

- Local OpenAI-compatible servers, including llama.cpp-compatible chat endpoints
- OpenAI chat-completions-compatible APIs
- Anthropic Messages API
- Google Generative Language API
- Custom OpenAI-compatible APIs

A configured fallback is used only when the primary provider fails.

## Current build boundary

Implemented:

- Desktop Electron control panel
- System-tray controls
- Persistent owner profiles
- Encrypted provider credentials
- Live primary/fallback model routing
- Full provider-level ORB articulation contract
- Local Ollama-compatible gateway
- Native ORB profile client
- Windows installer and portable packaging definitions
- Tests and CI safeguards

Still requiring machine verification:

- Install dependencies and launch the Electron application
- Build the Windows installer
- Connect the current WSL Orb Weaver backend to the Windows gateway
- Verify a live local-model response, a live API-provider response, voice delivery, and profile revision switching
