# ORB Voice Runtime Replication Report

> 2026-09-06 source update: [Target One landing tour](TARGET_ONE_LANDING_TOUR.md) reuses the existing cognition, TTS and verified Pointer/LiDAR paths with controller-owned concept progression and an explicit terminal visitor choice. Integrated validation is deferred; historical verification below does not cover this new slice.

This is the gold-master implementation report for copying the repaired Orb Weaver Website ORB voice runtime into future ORBs. It documents the current live runtime, not older Desktop ORB experiments and not stale bundled code.

Last verified: July 6, 2026.

## 1. Purpose And Boundary

The Website ORB voice runtime provides one browser voice turn:

```text
one click -> microphone capture -> automatic end-of-speech stop -> server STT
-> answer selection -> backend TTS/cache -> one WAV playback -> idle
```

It does not use browser `SpeechRecognition` for the public voice path, does not require a second click to submit, does not use browser `speechSynthesis` as the ORB voice, and does not let old generated answers redefine the ORB identity.

Runtime boundaries:

- Browser: `frontend/src/landing/AutonomousOrb.tsx` owns capture, silence detection, duplicate-turn prevention, cancellation, playback, filler audio, and UI state.
- API client: `frontend/src/services/api.ts` owns `websiteOrbVoice()`, `websiteOrbText()`, `websiteOrbTts()`, and media URL resolution.
- Backend: `backend/main.py` owns STT, memory context, cognitive pulse, deterministic identity answers, local LLM answers, TTS synthesis/cache, WAV delivery, and timing logs.
- External services: Faster Whisper runs on `host.docker.internal:9000/stt`; Kokoro runs on `host.docker.internal:8880/speak`; local LLM runs on `host.docker.internal:11434/api/generate`.

## 2. Complete Voice-Turn Lifecycle

1. User clicks the live ORB mounted by `frontend/src/index.tsx`.
2. `AutonomousOrb.tsx` unlocks audio and starts capture with `navigator.mediaDevices.getUserMedia()` and `MediaRecorder`.
3. `monitorRecordingSilence()` samples RMS from an `AnalyserNode` every 120 ms.
4. Recording ends automatically after speech followed by 850 ms of silence, or after the 14 s absolute cap.
5. `recorder.onstop` creates an `audio/webm` blob and calls `processRecordedOrbAudio()` unless the turn was explicitly cancelled.
6. `processRecordedOrbAudio()` sets a ref-based single-flight lock, creates an `AbortController`, starts latency filler audio, and posts the blob to `POST /api/orb/website-voice`.
7. `website_orb_voice()` calls `_transcribe_with_faster_whisper()`, `_orb_memory_summary()`, `_orb_cognitive_pulse()`, `_llm_orb_spoken_output()`, `_synthesize_orb_tts()`, and `_update_orb_recent_context()`.
8. The backend returns `transcript`, `spoken_output`, `cognitive_pulse`, `llm_source`, memory context, `tts_audio_url`, provider, and any TTS error.
9. The browser stops filler audio, loads the returned WAV URL through `api.orbMediaUrl()`, plays exactly one `HTMLAudioElement`, and returns to idle in `onended`, `onerror`, rejected `play()`, or the `finally` finalizer.

## 3. Canonical Active Files

Live browser voice runtime:

- `frontend/src/landing/AutonomousOrb.tsx`
  - refs and guards: lines 47-69
  - filler/audio unlock/playback: lines 160-206 and 289-363
  - single-flight request path: lines 372-419
  - stop/cancel path: lines 421-445
  - silence detector: lines 447-506
  - recording start and `recorder.onstop`: lines 508-601
  - click semantics: lines 603-643
- `frontend/src/services/api.ts`
  - response type: lines 683-692
  - voice/text/TTS calls with `AbortSignal`: lines 794-811

Live backend runtime:

- `backend/main.py`
  - identity answer and memory constants: lines 789-821
  - identity detection and neutral visitor-intent line: lines 829-851
  - memory summary: lines 883-934
  - neutral recent-context writer: lines 973-1008
  - Faster Whisper STT: lines 1238-1269
  - fallback and LLM answer selection: lines 1625-1710
  - TTS provider call/cache/single-flight: lines 1810-1995
  - `POST /api/orb/website-voice`: lines 3229-3295
  - `POST /api/orb/website-text`: lines 3298-3315

Deployment files:

- `Dockerfile`: frontend build stage compiles `frontend/src`, then copies `/app/frontend/build` into the final image at lines 1-11 and 46-50.
- `docker-compose.yml`: exposes `16500` and `16510`, sets Faster Whisper, Kokoro, and local LLM URLs, and mounts persistent backend data at lines 7-59.
- `deploy/nginx/orb-weaver.conf`: serves static frontend from `/app/frontend/build` and proxies `/api/` to `127.0.0.1:16500`.
- `deploy/cloudflared/orbweaver.spruked.com.yml`: routes `/api/*` to local `16500` and the public app to local `16510`.
- `deploy/docker/start-orb-weaver.sh`: starts Uvicorn on `16500` and nginx on `16510`.

Legacy or non-live candidates:

- `frontend/src/orb/WebsiteFloatingOrb.tsx` is not the currently verified public runtime. Do not use it as proof of live ORB behavior unless it is explicitly mounted and verified in the served bundle.
- `Orb_Assistant/src/components/FloatingOrb.jsx`, `LivingOrb.jsx`, Electron/Desktop folders, and voice JSON assets are not browser runtime callers by themselves.
- Static diagnostic pages under `frontend/public` can call ORB routes for tests, but they are not the live landing ORB.

## 4. Voice-Turn State And Concurrency Contract

Mandatory state rules:

- `voiceRequestInFlightRef` is the hard single-flight guard. State alone is not enough.
- `activeVoiceAbortControllerRef` belongs to the active voice turn. Abort only on a new genuine turn, cancel, interrupt, or unmount.
- `voiceTurnIdRef` exists only for diagnostics.
- `recordingCancelledRef` must be true before a cancel-induced recorder stop. `recorder.onstop` must not submit cancelled audio.
- `recordingMonitorTimerRef`, `silenceStartedAtRef`, `speechDetectedRef`, and `recordingStartedAtRef` define automatic end-of-speech.
- `speechAudioRef` and `latencyAudioRef` must be paused/cleared before final playback or interruption.

Click contract:

- First click starts a turn.
- End-of-speech submits automatically.
- Second click while recording cancels.
- Click while speaking interrupts.
- No click is required to submit.

Finalizer contract:

- `onended`, `onerror`, rejected `play()`, abort, and request failure all clear busy/speaking/listening state.
- No effect may call `website-voice`, `website-text`, TTS, or playback merely because transcript, response text, audio URL, status, or voice state changed.
- One visitor turn may create one `website-voice` request, one TTS result, and one playback.

## 5. STT Implementation

Backend helper: `_transcribe_with_faster_whisper()` in `backend/main.py`.

Request:

```text
POST FASTER_WHISPER_STT_URL
multipart field: file
filename: original upload filename, usually website-orb.webm
content-type: uploaded browser MIME type
```

Default deployed URL:

```text
FASTER_WHISPER_STT_URL=http://host.docker.internal:9000/stt
```

The helper reads JSON and expects:

```json
{"text": "transcribed user speech"}
```

Failures:

- Empty uploaded audio: HTTP 400.
- STT provider request failure: HTTP 502.
- No transcript in provider response: HTTP 422.

Measured latency:

- Isolated short WAV STT probe: about 2.4 s.
- Controlled live route cached identity request: transcription 1891.7 ms.

## 6. Answer-Selection Policy

Foundational identity questions are deterministic before memory and LLM can redefine identity:

```text
I'm Orb Weaver. I help website owners scan, understand, and improve their websites, then build an ORB that can guide visitors through them.
```

Protected question examples:

- "Who are you?"
- "What is your purpose?"
- "What do you do?"
- "What can you do?"
- "Tell me about yourself."

Normal questions use:

```text
_orb_memory_summary()
-> _orb_cognitive_pulse()
-> _llm_orb_spoken_output()
```

Authenticated memory may include durable user preferences and neutral recent visitor intent. It must not replay raw generated answers. The recent-context writer stores bounded lines like:

```text
Visitor intent: Asked about scanning a website
```

It must not store:

```text
User asked: ... | ORB answered: ...
```

That old format caused a self-reinforcing observer-style loop where bad outputs beginning "The visitor is..." were fed back as context.

## 7. TTS Implementation

Backend TTS path:

```text
spoken_output -> _synthesize_orb_tts()
-> _cached_tts_result()
-> _run_tts_singleflight() on cache miss
-> _call_tts_provider()
-> write WAV under ORB_TTS_CACHE_DIR
-> return /api/orb/tts/<digest>.wav
```

Current provider:

```text
ORB_TTS_KOKORO_URL=http://host.docker.internal:8880/speak
ORB_TTS_KOKORO_MODEL=kokoro
ORB_TTS_KOKORO_VOICE=am_echo
ORB_TTS_KOKORO_FORMAT=wav
ORB_TTS_KOKORO_PAYLOAD_MODE=kokoro-direct
ORB_TTS_CACHE_DIR=/app/backend/data/tts_cache
```

Cache key:

```text
sha256("{provider}:{model}:{voice}:{clean_text}")[:24]
```

WAV route:

```text
GET /api/orb/tts/{audio_id}
```

Current verified identity digest:

```text
681888f2e7d1bc075c1c039b.wav
```

TTS timings:

- Kokoro cache hit: about 3 ms.
- Fresh Kokoro generation: about 6 s.
- Controlled live identity turn with cache hit: TTS 0.3 ms.

Fixed phrases that should be pre-generated:

- identity answer
- greeting
- listening acknowledgment
- latency fillers
- recovery lines
- confirmation/completion lines
- error lines
- goodbye

## 8. Measured Latency Profile

Component probes:

```text
Faster Whisper short WAV probe: ~2.4 s
memory summary: ~50 ms
cognitive pulse: ~113 ms
deterministic identity selection: ~0.2 ms
Kokoro cache hit: ~3 ms
fresh Kokoro generation: ~6.0 s
```

Controlled live-route timing for cached identity request:

```text
total:            1934.0 ms
transcription:    1891.7 ms
cognitive_pulse:    40.7 ms
answer_selection:    0.2 ms
tts:                0.3 ms
memory_summary:     0.0 ms
context_update:     0.0 ms
auth:               0.0 ms
```

Interpretation:

- Cold TTS dominates first-time fixed lines.
- Cached fixed lines are dominated by STT.
- Normal local-LLM turns add local model latency and must be measured separately.

## 9. Deployment Truth

Running `npm run build` in the workspace does not update the public app. The container serves the build copied into the image:

```text
Dockerfile frontend-build -> /app/frontend/build
nginx root /app/frontend/build
```

Required deployment action:

```bash
docker compose up -d --build orb-weaver
```

Asset verification procedure:

```bash
docker compose exec -T orb-weaver sh -lc \
  'ls -l /app/frontend/build/static/js/main.*.js && sha256sum /app/frontend/build/static/js/main.*.js'

curl -fsS http://127.0.0.1:16510/ \
  | rg -o 'static/js/main\.[a-z0-9]+\.js' | head -1

curl -fsS http://127.0.0.1:16510/static/js/<main>.js | sha256sum

curl -fsS https://orbweaver.spruked.com/ \
  | rg -o 'static/js/main\.[a-z0-9]+\.js' | head -1

curl -fsS https://orbweaver.spruked.com/static/js/<main>.js | sha256sum
```

All three hashes must match before browser testing.

## 10. Known Failure Modes And Lessons Learned

- Stale Docker bundle served old frontend behavior even after workspace code was fixed.
- Fixed 5.2/6.5 s recording timers made the public ORB feel like a required two-click recorder.
- Missing single-flight guards created repeated request storms.
- Recovery TTS and playback paths must not retry automatically.
- Browser "speech recognition unavailable" text was stale runtime behavior, not proof of the live source.
- Raw `ORB answered:` memory summaries created a self-reinforcing "The visitor is..." personality loop.
- Repeated `website-text` and TTS calls can exhaust database/backend resources and show as Cloudflare 504 host errors.
- Repeated WAV loads pointed to the loaded bundle initiator, not necessarily to the source file most recently edited.
- A 200 from repeated TTS calls proves the frontend/backend kept asking for audio; it does not prove Kokoro failed.

## 11. Replication Contract For Other ORBs

Reuse unchanged:

- one-click start
- automatic end-of-speech stop
- ref-based single-flight guard
- abort controller per turn
- cancelled-recording flag
- no browser `SpeechRecognition` dependency
- no browser `speechSynthesis` for final ORB voice
- backend STT -> answer -> TTS/cache response shape
- TTS single-flight/cache behavior
- one final playback and clean finalization

Configure per ORB:

- visual shell, movement style, and voice assets
- deterministic identity answer
- local LLM role prompt
- voice provider/model/voice
- site-specific fixed phrases
- authenticated memory categories

Never copy blindly:

- old `WebsiteFloatingOrb.tsx` behavior without proving it is mounted
- Desktop/Electron ORB files into a Website ORB
- raw generated answer memory loops
- fixed recording stop timers as submit logic
- retry loops around text/TTS/playback

## 12. Voice Asset Manifest

Pre-cache required:

- Greeting: "Hi, I'm Orb Weaver. What would you like to check?"
- Identity: "I'm Orb Weaver. I help website owners scan, understand, and improve their websites, then build an ORB that can guide visitors through them."
- Listening acknowledgment: short nonverbal tone or "I'm listening."
- Latency filler: "One second."
- Latency filler: "Let me check that."
- Recovery: "I am reconnecting to my response service. Please try again in a moment."
- TTS unavailable: "Voice is temporarily unavailable, but I can still help here in text."
- Completion: "Done."
- Error: "I could not complete that request."
- Goodbye: "I'll be here when you need me."

Optional:

- Site-specific greeting
- Site-specific identity sentence
- Premium/extra voice purchase confirmation
- Checkout/order confirmation
- Tool-start and tool-finished cues

Dynamic only:

- Page-specific analysis
- Crawl findings
- Customer/account-specific answers
- Local LLM answers
- Anything containing user data or fresh scan results

## 13. Verification Test Plan

Browser Network tests:

1. Hard refresh public page. Idle for 10 seconds. Expect no `website-text`, no `website-voice`, no `tts`, no WAV.
2. One identity voice turn. Expect one `website-voice`, one WAV load, `llm_source=deterministic-identity`, one playback, then idle.
3. One normal product question: "How does Orb Weaver help a website owner?" Expect one `website-voice`, one TTS/WAV, and `llm_source=local-llm` or fallback if local LLM is unavailable.
4. Cancellation: click to start, click again while recording. Expect no `website-voice`.
5. Interrupt: click while speaking. Expect audio stops and no new request.
6. STT unavailable: stop Faster Whisper or point `FASTER_WHISPER_STT_URL` to a dead route. Expect one visible error and no retries.
7. TTS failure: stop Kokoro or use a dead `ORB_TTS_KOKORO_URL`. Expect text response, one visible TTS error, no retry storm.
8. Cache hit: repeat identity after pre-cache. Expect TTS cache hit and server wait dominated by STT.
9. Cache miss: use a unique fixed phrase in a controlled test. Expect one Kokoro generation and one cached WAV.
10. No duplicate playback: after `onended`, no additional WAV requests or replay.

Backend checks:

```bash
docker compose logs --tail=120 orb-weaver | rg 'ORB voice timing|website-voice|tts/'
```

Public deployment checks:

```bash
docker compose ps
curl -i --max-time 15 http://127.0.0.1:16500/docs
curl -i --max-time 15 http://127.0.0.1:16510/
```

This report is the canonical voice runtime reference until superseded by a newer verified live deployment report.
