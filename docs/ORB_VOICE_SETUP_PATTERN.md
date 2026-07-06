# ORB Voice Setup Pattern

This is the short setup note for the current Orb Weaver Website ORB voice runtime. The canonical, line-referenced implementation report is:

```text
docs/ORB_VOICE_RUNTIME_REPLICATION_REPORT.md
```

Use that report as the gold master before moving this voice system into another ORB.

## Current Live Runtime

The live public Website ORB voice implementation is:

```text
frontend/src/landing/AutonomousOrb.tsx
frontend/src/services/api.ts
backend/main.py
```

The active public browser behavior is:

```text
one click
-> getUserMedia({ audio })
-> MediaRecorder audio/webm
-> automatic silence stop
-> POST /api/orb/website-voice
-> Faster Whisper STT
-> deterministic identity answer or local LLM answer
-> Kokoro TTS/cache
-> GET /api/orb/tts/<audio_id>.wav
-> one browser playback
-> idle
```

Browser `SpeechRecognition` is not the canonical public input path. Browser `speechSynthesis` is not the canonical output voice path.

## Runtime Contract

Every future Website ORB should preserve these rules:

- One click starts a voice turn.
- The browser detects end of speech and submits automatically.
- A second click cancels recording or interrupts playback; it is not required to submit.
- A ref-based single-flight guard prevents duplicate request turns.
- Each turn owns one `AbortController`.
- Cancelled recorder stops must not call the backend.
- One successful turn may create one `website-voice` request, one TTS/cache result, and one final playback.
- Playback `onended`, `onerror`, rejected `play()`, abort, and route failure must all return the ORB to idle.
- No effect hook should invoke answer generation or TTS merely because UI state, transcript, response text, or audio URL changed.

## Backend Contract

Preserve these endpoints and response fields:

```text
POST /api/orb/website-voice
POST /api/orb/website-text
POST /api/orb/tts
GET  /api/orb/tts/{audio_id}
GET  /api/orb/capabilities
```

`/api/orb/website-voice` returns:

```json
{
  "transcript": "What is your purpose?",
  "spoken_output": "I'm Orb Weaver...",
  "cognitive_pulse": {},
  "llm_source": "deterministic-identity",
  "memory_context": null,
  "tts_audio_url": "/api/orb/tts/<id>.wav",
  "tts_provider": "kokoro",
  "tts_error": null
}
```

Identity questions are answered deterministically before memory or the local LLM can influence the public ORB identity. Ordinary product/site questions use the local LLM path.

Recent context stores neutral visitor intent only. Do not store or replay raw generated `ORB answered:` text.

## Required Services

The Docker/compose defaults expect:

```text
Backend API:                 http://127.0.0.1:16500
Frontend/nginx:              http://127.0.0.1:16510
Faster Whisper STT:          http://host.docker.internal:9000/stt
Kokoro TTS:                  http://host.docker.internal:8880/speak
Local LLM:                   http://host.docker.internal:11434/api/generate
TTS cache in container:      /app/backend/data/tts_cache
TTS cache mounted on host:   backend/data/tts_cache
```

## Deployment Warning

The public app is served from the Docker image, not directly from the workspace React build. Rebuild the container before public testing:

```bash
docker compose up -d --build orb-weaver
```

Then verify the main JS bundle name and SHA match inside the container, local `16510`, and the public domain before testing voice.

## Measured Baseline

Current verified measurements:

```text
Faster Whisper probe: ~2.4 s
Controlled live cached identity route: total ~1.93 s, transcription ~1.89 s
memory summary: ~50 ms
cognitive pulse: ~113 ms
deterministic identity answer: ~0.2 ms
Kokoro cache hit: ~3 ms
fresh Kokoro generation: ~6 s
```

Cold fixed phrases should be pre-generated so visitor-facing identity, greeting, and recovery lines do not wait on Kokoro.
