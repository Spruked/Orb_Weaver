# Orb Weaver Handoff: Live ORB Route + Voice Consistency

Current focus: live Website ORB on `https://orbweaver.spruked.com/`.

## What Was Observed

The live showcase ORB accepts user text, but the ORB response route fails fast with:

```text
Unexpected token '<', "<!doctype "... is not valid JSON
```

This means the frontend expected JSON but received the React HTML app shell.

Confirmed live with curl:

```text
GET https://orbweaver.spruked.com/api/orb/capabilities
-> HTTP 200
-> content-type: text/html; charset=utf-8
-> body starts with <!doctype html>

POST https://orbweaver.spruked.com/api/orb/website-text
-> HTTP 200
-> content-type: text/html; charset=utf-8
-> body starts with <!doctype html>
```

The expected backend endpoint exists in `backend/main.py`:

```text
POST /api/orb/website-text
POST /api/orb/website-voice
GET  /api/orb/capabilities
```

Expected deployment routing from repo docs/config:

```text
orbweaver.spruked.com /api/* -> http://localhost:16500
orbweaver.spruked.com *      -> http://localhost:16510
```

But live `/api/orb/website-text` is currently reaching the frontend SPA fallback instead.

## Files Recently Touched

Do not assume these are the only dirty files; the worktree had a lot of pre-existing churn.

Touched for the route/parser hardening:

```text
deploy/nginx/orb-weaver.conf
frontend/src/services/api.ts
frontend/src/landing/AutonomousOrb.tsx
```

Important route fix already added:

```text
deploy/nginx/orb-weaver.conf
```

Now includes:

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:16500;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

This helps if Cloudflare points all traffic to the combined nginx/frontend service.

Frontend JSON hardening added in:

```text
frontend/src/services/api.ts
```

Key behavior:

```text
Check response.ok.
Check Content-Type.
If expected JSON but content type is not JSON, throw calm reconnect message.
In development, log request URL, status, and content type.
```

Landing ORB catch path changed in:

```text
frontend/src/landing/AutonomousOrb.tsx
```

It now speaks a calm recovery message instead of the raw parser error:

```text
I am reconnecting to my response service. Please try again in a moment.
```

## Build Result

Frontend build passed:

```text
npm run build
Compiled with warnings.
```

Known warning:

```text
src/landing/AutonomousOrb.tsx
React Hook useEffect has missing dependencies:
clampPosition, nextDestination, playLocalPresence
```

Do not spend the next pass on that warning unless asked.

## Live Runtime Issue Still To Verify After Deploy

After deploying the nginx/API hardening, verify:

```bash
curl -i https://orbweaver.spruked.com/api/orb/capabilities
curl -i -X POST https://orbweaver.spruked.com/api/orb/website-text \
  -H 'Content-Type: application/json' \
  --data '{"transcript":"hello"}'
```

Expected:

```text
content-type: application/json
JSON body from backend
```

If it still returns `index.html`, the live Cloudflare Tunnel ingress order/config is wrong or not using the repo config. Keep `/api/*` above `*`.

## Voice Problem Reported By User

User observed the live ORB failed quickly and changed voice during the response/error sequence.

Do not add latency WAV playback yet.
Do not change providers, voices, latency assets, Marketplace, skins, memory, Electron, posteriori, or old Orb Assistant files yet.

Next pass should inspect and report evidence only before editing:

1. Every place the active Website ORB can speak text.
2. Whether it uses browser `speechSynthesis`, backend TTS, Qwen, Kokoro, prerecorded clips, or more than one path.
3. The exact primary voice path for a normal successful ORB answer.
4. The exact fallback/error voice path when the ORB API route fails.
5. Whether route failure causes browser speech fallback or a second TTS provider to take over.
6. The exact point where the voice switches mid-response.
7. Whether an old response/error handler is speaking parser errors or route-unavailable messages.

Likely active files to inspect:

```text
frontend/src/landing/AutonomousOrb.tsx
frontend/src/orb/WebsiteFloatingOrb.tsx
frontend/src/services/api.ts
backend/main.py
```

Update after the July 6, 2026 voice repair: the verified public Website ORB voice runtime is `frontend/src/landing/AutonomousOrb.tsx`. Treat `frontend/src/orb/WebsiteFloatingOrb.tsx` as legacy/non-live unless a served bundle initiator proves it is mounted. The canonical replication report is `docs/ORB_VOICE_RUNTIME_REPLICATION_REPORT.md`.

Known active showcase mount:

```text
frontend/src/index.tsx
-> <AutonomousOrb size={214} />
```

Previously suspected reusable/deployable website ORB surface:

```text
frontend/src/orb/WebsiteFloatingOrb.tsx
```

This component has its own historical voice code and must not be treated as the live runtime without fresh browser initiator evidence.

Known landing showcase ORB path:

```text
frontend/src/landing/AutonomousOrb.tsx
askOrb()
-> api.websiteOrbText(cleanTranscript)
-> speak(result.spoken_output)
```

This also uses browser `speechSynthesis`.

Possible voice-switch cause to verify:

```text
Normal answer path and error path may both call browser speechSynthesis,
but a previous utterance may already have started before the error/fallback
message is spoken.
```

Smallest likely future fix, after evidence:

```text
Centralize Website ORB speech into one speak function/provider path.
Cancel any active utterance before speaking fallback.
Do not let parser errors or route errors use a different speech function.
Always speak the calm recovery message with the same voice selection logic.
```

## Static Demo Pages Added

Two standalone HTML demo pages were placed into the frontend public surface:

```text
frontend/public/circus-page.html
frontend/public/diagnostic-bay.html
```

They should be reachable after the frontend build/deploy at:

```text
/circus-page.html
/diagnostic-bay.html
```

Source files at the repo root were not edited:

```text
circus-page.html
diagnostic-bay.html
```

`diagnostic-bay.html` is a separate proving-ground page. It currently uses a temporary page gate and a local audit trail, but its ORB/tool stages now call real backend routes where the backend has routes available:

```text
POST /api/orb/website-text
POST /api/public/preflight
GET  /api/orb/capabilities
POST /api/public/browser-review   only if public Chrome DevTools review is enabled
```

It does not connect to durable backend auth yet, and it does not write durable audit records yet.

`circus-page.html` now hands into Diagnostic Bay in two places:

```text
The moving circus ORB is an accessible link to diagnostic-bay.html.
The closing section has an "Enter Diagnostic Bay" CTA to diagnostic-bay.html.
```

This is demo-page wiring only. It does not change the production landing-page ORB, WebsiteFloatingOrb, Marketplace, backend ORB APIs, or MCP execution.

Important boundary:

```text
This is a static proving-ground page with real public ORB/backend calls.
Do not treat its temporary page gate or local audit trail as production auth/audit wiring.
Do not overwrite circus-page.html when iterating on Diagnostic Bay.
```

## Also Observed: Splash / ORB Position

User screenshot showed the ORB overlapping hero copy.

Recent narrow splash fix already made:

```text
frontend/src/landing/AutonomousOrb.tsx
frontend/src/landing/Landing.css
```

Changes:

```text
Pulse visible duration increased.
Pulse z-index changed from -1 to 0.
```

Do not continue visual work unless the user asks. The immediate next issue is voice-chain inspection.
