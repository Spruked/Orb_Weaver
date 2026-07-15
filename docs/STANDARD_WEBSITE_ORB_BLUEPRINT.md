# Standard Website ORB Blueprint

This is the reusable ORB deployment pattern from Orb Weaver, separated from this site's visual branding. Use it when building a new Website ORB that should feel like the same living voice-and-motion system, without copying the exact page design.

## Goal

Build a deployable Website ORB, distinct from the Desktop ORB.

The Website ORB is a browser resident assistant that:

- floats above the site UI
- moves with idle drift and cursor avoidance
- records short user speech
- sends audio or text to the backend
- receives a short spoken answer
- plays backend-generated TTS audio
- uses short filler clips to cover response latency
- can report local capability status for STT, TTS, pointer cache, and optional dockstation handoff
- can optionally handshake with the Electron/Desktop dock adapter

The Desktop ORB is separate. It owns desktop overlay behavior, host control, screen automation, and deeper local machine access. The Website ORB may hand off to it, but should not become it.

Basic customer Website ORBs do not inherit Orb Weaver showcase Desktop MCP tools. They run from the installed site package, pointer plot map, runtime intent manifest, voice manifest, static tool cache, and approved website context. Advanced adapters require explicit configuration.

## Current Repo Modules

### Frontend Website ORB

Current live component:

```text
frontend/src/landing/AutonomousOrb.tsx
frontend/src/services/api.ts
```

Core behavior:

```text
click orb
-> unlock browser audio
-> getUserMedia({ audio: true })
-> MediaRecorder records audio/webm
-> automatic end-of-speech detection stops recording
-> play one latency filler clip while the backend prepares the response
-> POST /api/orb/website-voice
-> receive transcript, spoken_output, cognitive_pulse, llm_source, tts_audio_url
-> stop filler clip
-> play backend TTS with HTMLAudioElement
-> return to idle
```

Important UI states:

- `idle`
- `learning` / listening
- `assisting` / thinking or speaking
- `avoiding` / cursor evasion
- `dockStatus`: `searching`, `linked`, or `offline`

The frontend must not use browser `speechSynthesis` for the Website ORB voice. It can display text if audio fails, but the spoken voice should come from backend TTS so voice identity stays consistent.

Do not copy `frontend/src/orb/WebsiteFloatingOrb.tsx` as the live runtime unless it is explicitly mounted and verified in the served bundle. The current public runtime is line-referenced in `docs/ORB_VOICE_RUNTIME_REPLICATION_REPORT.md`.

### Frontend Movement

Current movement is simple and portable:

```text
idle drift:
  target = upper-right anchor + sine/cosine offset

cursor avoidance:
  if cursor is within avoidance radius
  choose a constrained target away from cursor
  lerp position toward target

state speed:
  avoiding > assisting > idle
```

Reusable movement helpers also exist:

```text
frontend/src/orb/kineticTransit.ts
frontend/src/orb/targetValidation.ts
```

For a new site, reuse the behavior contract, not the exact colors or label text.

### Voice Packs And Latency Fillers

Mirrored voice pack roots:

```text
frontend/public/orb/voice/
Orb_Assistant/src/voice/
```

Important files:

```text
latency_fillers.json
fallback_responses.json
recovery_and_status.json
latency-fillers/README.md
```

Current expected filler clip filenames:

```text
frontend/public/orb/voice/latency-fillers/ack.wav
frontend/public/orb/voice/latency-fillers/thinking.wav
frontend/public/orb/voice/latency-fillers/working.wav
```

Target filler behavior:

- Keep one or two approved phrases available as pre-rendered WAV files.
- Generate or clone these clips in the Qwen 3 TTS app using the same voice identity the ORB is using.
- Keep clips under about 1.5 seconds.
- Start a filler only when the final response is not ready quickly, roughly after 500-700 ms.
- Stop the filler before playing final Kokoro/Qwen response audio.
- Never overlap filler audio and final answer audio.

Good starter filler phrases:

```text
One second.
Let me check that.
```

### Backend API Contract

Primary backend file:

```text
backend/main.py
```

Routes to preserve:

```text
POST /api/orb/website-voice
POST /api/orb/website-text
POST /api/orb/tts
GET  /api/orb/tts/{audio_id}
GET  /api/orb/capabilities
GET  /api/orb/tools/catalog
POST /api/orb/tools/run
```

Shared Website ORB response shape:

```json
{
  "transcript": "user text",
  "spoken_output": "short spoken answer",
  "cognitive_pulse": {
    "cognitive_mode": "READY",
    "glow_intensity": 0.86
  },
  "llm_source": "local-llm",
  "memory_context": null,
  "tts_audio_url": "/api/orb/tts/<id>.wav",
  "tts_provider": "kokoro",
  "tts_error": null
}
```

### Backend Pipeline

Voice path:

```text
audio upload
-> _transcribe_with_faster_whisper()
-> _orb_memory_summary()
-> _orb_cognitive_pulse()
-> _llm_orb_spoken_output()
-> _synthesize_orb_tts()
-> _update_orb_recent_context()
-> JSON response with tts_audio_url
```

Identity questions are answered deterministically before memory or the local LLM can redefine the public ORB identity. Recent context stores neutral visitor intent only; raw generated `ORB answered:` text must not be fed back into later prompts.

Text path:

```text
transcript JSON
-> _orb_memory_summary()
-> _orb_cognitive_pulse()
-> _llm_orb_spoken_output()
-> optional _synthesize_orb_tts()
-> _update_orb_recent_context()
-> JSON response
```

### STT

Environment variable:

```text
FASTER_WHISPER_STT_URL=http://127.0.0.1:9000/stt
```

Expected STT response:

```json
{ "text": "transcribed user speech" }
```

### Local LLM

Environment variables:

```text
LOCAL_LLM_URL=
LOCAL_LLM_MODEL=
LOCAL_LLM_TIMEOUT_SECONDS=60
LOCAL_LLM_NUM_CTX=512
LOCAL_LLM_NUM_PREDICT=32
LOCAL_LLM_TEMPERATURE=0.35
```

The LLM should return one short spoken sentence. No markdown, no exposed internals, no invented facts.

### TTS

Current standard env knobs:

```text
ORB_TTS_CACHE_DIR=data/tts_cache
ORB_TTS_TIMEOUT_SECONDS=45

ORB_TTS_KOKORO_URL=http://127.0.0.1:8880/speak
ORB_TTS_KOKORO_MODEL=kokoro
ORB_TTS_KOKORO_VOICE=am_echo
ORB_TTS_KOKORO_FORMAT=wav
ORB_TTS_KOKORO_PAYLOAD_MODE=kokoro-direct

ORB_TTS_QWEN_URL=
ORB_TTS_QWEN_MODEL=qwen-tts
ORB_TTS_QWEN_VOICE=OrbWeaver
ORB_TTS_QWEN_LANGUAGE=English
ORB_TTS_QWEN_INSTRUCT=A warm, confident adult male assistant voice. Clear, calm, lightly theatrical, friendly, and concise.
ORB_TTS_QWEN_FORMAT=wav
ORB_TTS_QWEN_PAYLOAD_MODE=qwen-custom
```

Recommended standard:

- Use Qwen 3 TTS app to clone/generate the short latency filler WAV files in the matching ORB voice.
- Use Kokoro for the warm final ORB answer when it is the active low-latency backend.
- If Qwen is wired as a provider route later, keep provider order explicit and do not let browser speech become a hidden third voice.
- Cache TTS by text/provider/model/voice digest.
- Use singleflight locking so duplicate requests do not trigger duplicate synthesis.

### Tesseract OCR

Orb Weaver's own showcase ORB can report and use Tesseract through backend or Desktop MCP tools. A Basic customer Website ORB should not depend on local OCR at runtime.

The showcase backend currently checks Tesseract through:

```py
shutil.which("tesseract")
```

In WSL, keep Tesseract available on PATH or set the process environment so the backend can find it.

Recommended WSL target:

```text
TESSERACT_CMD=/usr/bin/tesseract
```

For OCR work, the backend capability route should say:

```json
{
  "tesseract": {
    "available": true,
    "binary": "/usr/bin/tesseract"
  }
}
```

Tesseract belongs behind backend or MCP tools. The browser should not call local OCR directly. Customer deployments only receive OCR-backed behavior when an advanced adapter is deliberately configured.

### Desktop MCP / MPC Server Boundary

For Orb Weaver showcase/development, the repo-local MCP server slot is:

```text
.runtime/rdrive_mpc_server/orb_mcp_server.py
```

The legacy Desktop ORB/R-drive fallback may still exist at `/mnt/r/mpc_server/orb_mcp_server.py`.

Relevant backend client:

```text
backend/app/services/orb_desktop_mcp.py
```

Relevant host relay:

```text
tools/orb_mcp_host_relay.py
tools/start_orb_mcp_host_relay.sh
```

Environment variables:

```text
ORB_DESKTOP_MCP_ENABLED=true
ORB_DESKTOP_MCP_ROOT=.runtime/rdrive_mpc_server
ORB_DESKTOP_MCP_PYTHON=python3.12
ORB_DESKTOP_MCP_TIMEOUT_SECONDS=20
ORB_DESKTOP_MCP_URL=http://host.docker.internal:8765
ORB_DESKTOP_MCP_TOKEN=
```

Preferred architecture:

```text
Orb Weaver showcase ORB browser
-> Orb Weaver backend
-> ORBDesktopMCPClient
-> HTTP relay on host or direct stdio
-> repo-local .runtime/rdrive_mpc_server/orb_mcp_server.py
-> allowed ORB MCP tools
```

The browser must not call the MCP server directly.

The host relay has a read-only clamp by default. Mutating tools require explicit relay startup with mutation enabled.

Basic customer Website ORB architecture:

```text
Website ORB browser
-> installed static package
-> pointer_plot_map.json
-> runtime_intent_manifest.json
-> voice_manifest.json
-> tool_cache.json
-> optional backend answer route
```

No MCP relay is required for this path.

### Electron Dock Adapter

Desktop adapter root:

```text
Orb_Assistant/electron_dock_adapter/
```

Important files:

```text
main.js
preload_adapter.js
orb-bridge.js
README.md
```

Role:

- create transparent always-on-top desktop ORB window
- start or skip the Python bridge
- pass cognitive pulses, speech pulses, and verbal commands into the renderer
- expose safe IPC for cursor movement and status
- provide a desktop dockstation bridge that the Website ORB can handshake with

Website ORB handshake:

```text
ws://localhost:8000/ws/orb_assistant
```

The Website ORB treats this as optional. If unavailable, it remains online as a website assistant.

## Standard Copy Checklist

1. Recreate the current `AutonomousOrb` voice-turn behavior in the target frontend; use `docs/ORB_VOICE_RUNTIME_REPLICATION_REPORT.md` as the contract.
2. Add `websiteOrbVoice`, `websiteOrbText`, `websiteOrbTts`, `orbMediaUrl`, and `websiteOrbCapabilities` API helpers.
3. Preserve the backend route names and response shape.
4. Wire faster-whisper STT.
5. Add deterministic public identity answers before memory/LLM assembly.
6. Wire Kokoro final-answer TTS and cache generated audio.
7. Add Qwen-generated filler WAVs in `public/orb/voice/latency-fillers/`.
8. Add capability checks for Tesseract and MCP.
9. Use R-drive MCP through backend client or HTTP relay only.
10. Keep Electron dock adapter optional and separate from Website ORB.
11. Store only neutral visitor-intent recent context; never replay raw generated ORB answers.
12. Test no overlapping audio, no browser speech voice fallback, no duplicate request storm, and no HTML-shell responses from `/api/orb/*`.

## Acceptance Tests

Run these after cloning to a new site:

```text
GET  /api/orb/capabilities
POST /api/orb/website-text {"transcript":"Say one short status line."}
POST /api/orb/tts {"text":"One second."}
POST /api/orb/website-voice with website-orb.webm
GET  returned tts_audio_url
```

Manual browser checks:

- click ORB and grant mic permission
- filler plays quickly only if needed
- final audio stops filler and uses one voice identity
- ORB moves, avoids cursor, and does not cover essential UI
- `cognitive_pulse.glow_intensity` changes mood
- dockstation offline does not break the Website ORB
- capabilities report Tesseract and MCP truthfully
