# Standard Website ORB Rebuild Prompt

Use this prompt when asking Codex or another coding agent to rebuild the same basic ORB system in another site. Replace bracketed values before using.

```text
You are working in [TARGET_REPO_PATH]. Build a Standard Website ORB using the Orb Weaver deployment pattern. Do not copy the Orb Weaver page appearance or branding. Recreate the same core voice, motion, latency, backend route, and optional dock/MCP architecture.

Reference source repo:
[ORB_WEAVER_REPO_PATH]

Primary reference files:
- docs/STANDARD_WEBSITE_ORB_BLUEPRINT.md
- docs/ORB_VOICE_SETUP_PATTERN.md
- docs/ORB_VOICE_RUNTIME_REPLICATION_REPORT.md
- frontend/src/landing/AutonomousOrb.tsx
- frontend/src/landing/Orb.tsx
- frontend/src/services/api.ts
- backend/main.py
- backend/app/core/config.py
- backend/app/services/orb_desktop_mcp.py
- tools/orb_mcp_host_relay.py
- tools/start_orb_mcp_host_relay.sh
- tools/kokoro_openai_tts_server.py
- Orb_Assistant/electron_dock_adapter/main.js
- Orb_Assistant/electron_dock_adapter/preload_adapter.js
- Orb_Assistant/electron_dock_adapter/orb-bridge.js

Build target:
- A Website ORB, not a Desktop ORB.
- It should be visually adapted to this site, but structurally use the same ORB deployment pattern.
- It must float above the site, drift when idle, avoid the cursor, listen on click, show listening/thinking/speaking states, and update mood from backend cognitive pulse.

Frontend requirements:
- Add a reusable Website ORB component.
- Use MediaRecorder with getUserMedia({ audio: true }) and upload audio/webm to POST /api/orb/website-voice.
- Use automatic end-of-speech detection. Do not require a second click to submit.
- A second click should cancel recording or interrupt playback.
- Use a ref-based single-flight guard and one AbortController per voice turn.
- Keep POST /api/orb/website-text as transcript-only fallback.
- Add a single speakOutput helper that plays backend TTS through HTMLAudioElement.
- Always pause/stop current final audio before starting a new response.
- Always pause/stop latency filler before final answer audio.
- Do not use browser speechSynthesis for Website ORB voice.
- Add optional latency filler WAV playback from /orb/voice/latency-fillers/.
- Start filler only when a response is delayed by roughly 500-700 ms.
- Use one or two filler clips first: ack.wav and thinking.wav.
- Keep filler phrase text under six words.
- Add optional WebSocket handshake to ws://localhost:8000/ws/orb_assistant, but the Website ORB must work when that socket is offline.

Backend requirements:
- Preserve these routes and response shapes:
  - POST /api/orb/website-voice
  - POST /api/orb/website-text
  - POST /api/orb/tts
  - GET /api/orb/tts/{audio_id}
  - GET /api/orb/capabilities
  - GET /api/orb/tools/catalog, if authenticated owner tools exist
  - POST /api/orb/tools/run, if authenticated owner tools exist
- Voice route pipeline:
  audio upload -> faster-whisper STT -> ORB cognition/local pulse -> local LLM short answer -> backend TTS -> cached audio URL -> JSON response.
- Text route pipeline:
  transcript -> ORB cognition/local pulse -> local LLM short answer -> optional backend TTS -> JSON response.
- The JSON response must include:
  transcript, spoken_output, cognitive_pulse, llm_source, memory_context, tts_audio_url, tts_provider, tts_error.
- The local LLM prompt must ask for one short spoken sentence, no markdown, no private internals, no invented facts.
- Deterministic identity questions such as "Who are you?", "What is your purpose?", and "What do you do?" must be answered before memory/LLM assembly.
- Recent context must store neutral visitor intent only. Do not store raw `ORB answered:` generated text.
- If the LLM fails, return a useful local fallback sentence.
- If TTS fails, return text with tts_error and no browser speech fallback.

TTS requirements:
- Use Kokoro as the low-latency final response TTS unless this site already has a better configured final TTS.
- Keep env knobs compatible with:
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
- Use Qwen 3 TTS app outputs for short cloned voice filler WAVs, placed in public/orb/voice/latency-fillers/.
- Do not create empty WAV placeholders. If clips do not exist, fail silently and continue to final TTS.
- Cache generated final TTS files by digest.
- Prevent duplicate concurrent synthesis for identical text/provider/model/voice.

STT requirements:
- Use FASTER_WHISPER_STT_URL, default http://127.0.0.1:9000/stt.
- Expect JSON { "text": "..." }.
- Return clear HTTP errors for no audio, STT failure, or empty transcript.

Tesseract/OCR requirements:
- The backend must report local Tesseract availability in GET /api/orb/capabilities.
- In WSL, use the root-installed binary, usually /usr/bin/tesseract.
- Prefer detecting with shutil.which("tesseract") and allow TESSERACT_CMD=/usr/bin/tesseract for processes that need an explicit path.
- OCR operations must go through backend/MCP tools, never directly from browser to host OCR.

R-drive MCP/MPC server requirements:
- Treat the existing server as /mnt/r/mpc_server/orb_mcp_server.py.
- Add or reuse an ORBDesktopMCPClient that supports direct stdio and optional HTTP relay.
- Env:
  ORB_DESKTOP_MCP_ENABLED=true
  ORB_DESKTOP_MCP_ROOT=/mnt/r/mpc_server
  ORB_DESKTOP_MCP_PYTHON=python3.12
  ORB_DESKTOP_MCP_TIMEOUT_SECONDS=20
  ORB_DESKTOP_MCP_URL=http://host.docker.internal:8765
  ORB_DESKTOP_MCP_TOKEN=
- The browser must never call the MCP server directly.
- The backend should expose MCP capability/status and authenticated owner tool execution only.
- Use a read-only clamp by default for relay-hosted MCP calls. Mutating actions require explicit enablement.

Electron adapter requirements:
- Keep the Electron/Desktop dock adapter as a separate optional adapter, not part of the Website ORB bundle.
- Include or preserve a dock adapter capable of:
  transparent always-on-top desktop ORB window,
  Python bridge start/stop,
  cognitive_pulse and speech_pulse handoff,
  safe IPC for status and cursor messages.
- The Website ORB may handshake with the dock over ws://localhost:8000/ws/orb_assistant and continue normally if offline.

Implementation style:
- Read the target repo first and match its frontend/backend conventions.
- Keep edits scoped.
- Add no unrelated redesign or marketplace changes.
- Preserve dirty user changes.
- Add a short README or docs file in the target repo explaining the ORB modules, env vars, routes, and test commands.

Verification:
- Run the target repo's lint/typecheck/tests where available.
- Start the backend/frontend if practical.
- Verify:
  GET /api/orb/capabilities returns JSON, not the frontend HTML shell.
  POST /api/orb/website-text returns spoken_output and tts_audio_url or a clear tts_error.
  POST /api/orb/tts returns a playable audio URL.
  Website ORB click records audio and sends website-orb.webm.
  Filler audio does not overlap final TTS.
  Tesseract status reflects WSL /usr/bin/tesseract.
  MCP status reflects /mnt/r/mpc_server or the HTTP relay.
```

## Quick Filler Script For Qwen 3 TTS Clone

Use these as the first two cloned filler clips:

```text
One second.
Let me check that.
```

Suggested filenames:

```text
public/orb/voice/latency-fillers/ack.wav
public/orb/voice/latency-fillers/thinking.wav
```

Voice direction:

```text
Warm, confident adult male assistant voice. Clear, calm, lightly theatrical, friendly, concise, and close to the active ORB voice. These are tiny latency fillers, not full answers.
```
