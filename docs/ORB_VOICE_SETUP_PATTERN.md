# ORB Voice Setup Pattern

This document captures the working voice setup in this Orb Weaver orb so the same pattern can be applied to other orbs.

The setup is not a polished full voice platform yet. It works because it keeps the voice chain simple:

1. The browser listens.
2. The backend transcribes recorded audio when using the deployable website orb.
3. The backend runs ORB cognition and optional local LLM articulation.
4. The browser speaks the final text with `speechSynthesis`.

## Active Voice Surfaces

There are two active voice surfaces in this repo.

### Landing showcase orb

File: `frontend/src/landing/AutonomousOrb.tsx`

This is mounted globally by `frontend/src/index.tsx`:

```tsx
<AutonomousOrb size={214} />
```

It is the showcase orb visible across the React app. It uses browser speech recognition for input when available:

```text
click orb
-> browser SpeechRecognition / webkitSpeechRecognition
-> transcript
-> POST /api/orb/website-text
-> backend ORB cognition / local LLM fallback
-> browser speechSynthesis speaks spoken_output
```

If browser speech recognition is unavailable, it falls back to a text prompt and sends that text to the same backend route.

### Reusable website floating orb

File: `frontend/src/orb/WebsiteFloatingOrb.tsx`

This is the better pattern to copy into other deployable website orbs because it records microphone audio directly and sends it to the backend:

```text
click orb
-> getUserMedia({ audio: true })
-> MediaRecorder records audio/webm
-> POST /api/orb/website-voice
-> backend faster-whisper transcription
-> backend ORB cognition / local LLM fallback
-> browser speechSynthesis speaks spoken_output
```

It also has a dockstation WebSocket handoff:

```text
ws://localhost:8000/ws/orb_assistant
```

The WebSocket is optional for the voice chain. If the dockstation is offline, the website orb still records, sends to the API, and speaks.

## Output Voice

The current output voice is browser-native TTS:

```ts
const utterance = new SpeechSynthesisUtterance(text);
window.speechSynthesis.cancel();
window.speechSynthesis.speak(utterance);
```

There is no active backend TTS provider in the primary path. No Qwen, Kokoro, Coqui, ElevenLabs, or prerecorded WAV path is currently driving normal responses.

The landing showcase orb chooses a preferred local browser voice if one matches:

```text
female | zira | samantha | google us english | natural
```

Then it sets:

```text
rate: 0.98
pitch: 1.04
volume: 0.9
```

The reusable `WebsiteFloatingOrb` does not currently select a named browser voice. It sets:

```text
rate: 0.96
pitch: 1.04
```

When applying this to other orbs, copy one consistent `speak()` helper and use it for normal responses, fallback responses, route failures, and dockstation speech pulses. The most important behavior is:

```text
cancel current speech before starting the next utterance
```

That prevents overlapping utterances and helps avoid the impression that the voice changed mid-response.

## Input Voice

There are two input modes.

### Browser speech recognition

Used by `AutonomousOrb.tsx`.

```text
SpeechRecognition / webkitSpeechRecognition
language: en-US
continuous: false
interimResults: false
maxAlternatives: 1
```

This path does not send audio to the backend. The browser creates the transcript, then the frontend sends text to:

```text
POST /api/orb/website-text
```

### Recorded audio transcription

Used by `WebsiteFloatingOrb.tsx`.

```text
navigator.mediaDevices.getUserMedia({ audio: true })
MediaRecorder
preferred mime type: audio/webm
max record window: 6500 ms
```

The frontend uploads the recorded blob as:

```text
field: audio
filename: website-orb.webm
endpoint: POST /api/orb/website-voice
```

The backend forwards that audio to faster-whisper.

## Backend Voice Routes

File: `backend/main.py`

The two routes return the same response shape:

```py
class WebsiteOrbVoiceResponse(BaseModel):
    transcript: str
    spoken_output: str
    cognitive_pulse: Optional[Dict[str, Any]] = None
    llm_source: str = "local-fallback"
    memory_context: Optional[Dict[str, Any]] = None
```

### `POST /api/orb/website-voice`

This is the full voice path:

```text
audio upload
-> _transcribe_with_faster_whisper()
-> _orb_memory_summary()
-> _orb_cognitive_pulse()
-> _llm_orb_spoken_output()
-> _update_orb_recent_context()
-> JSON response
```

### `POST /api/orb/website-text`

This is the low-latency text path:

```text
transcript JSON
-> _orb_memory_summary()
-> _orb_cognitive_pulse()
-> _llm_orb_spoken_output()
-> _update_orb_recent_context()
-> JSON response
```

It is useful as a fallback for browsers without speech recognition or when another orb already has a transcript.

## Faster-Whisper STT

The backend transcription helper is `_transcribe_with_faster_whisper()`.

It reads the uploaded audio, then posts it to:

```text
FASTER_WHISPER_STT_URL
```

Default:

```text
http://127.0.0.1:9000/stt
```

There is a built-in fallback only when the default is used:

```text
http://127.0.0.1:9880/stt
```

Expected faster-whisper response:

```json
{
  "text": "transcribed user speech"
}
```

If no audio is received, the route returns `400`. If faster-whisper fails, the route returns `502`. If faster-whisper returns no transcript, the route returns `422`.

## ORB Cognition

The backend loads the ORB controller from:

```text
ORB_ASSISTANT_ROOT=../Orb_Assistant
```

The loader imports:

```py
from Orb_Assistant.src.orb_controller import SF_ORB_Controller
```

Then voice/text input is passed into:

```py
controller.cognitively_emerge({
    "type": "website_voice_query",
    "content": transcript,
    "coordinates": [0, 0],
    "velocity": 0.0,
    "intent": "visitor_voice_assistance",
})
```

If cognition fails, the backend returns a fallback pulse instead of breaking the whole response:

```json
{
  "cognitive_mode": "FALLBACK",
  "error": "...",
  "glow_intensity": 0.62
}
```

The frontend uses `glow_intensity` to adjust orb mood/color.

## LLM Articulation

The backend can optionally send the transcript, cognitive pulse, and safe account memory to a local LLM.

Environment variables:

```text
LOCAL_LLM_URL=
LOCAL_LLM_MODEL=
```

If either variable is missing, the backend skips the LLM and uses `_fallback_orb_spoken_output()`.

The local LLM prompt asks for:

```text
one short spoken sentence
no markdown
no chat UI language
do not invent facts
do not expose private internals
```

The response source is returned as:

```text
local-llm
local-fallback
```

## Fallback Spoken Output

The backend fallback handles common terms directly:

```text
remember / know me / who am i / my name
preflight / scan
tool / mcp / tesseract
basic / premium
market / product
```

If none match, it says:

```text
I am online in {mode} mode. I can demonstrate public Preflight, ORB cognition, voice, and deployment readiness.
```

This fallback is why the orb can still answer reasonably even without the local LLM.

## Voice Text Packs

There are mirrored voice text packs in:

```text
frontend/public/orb/voice/
Orb_Assistant/src/voice/
```

Files:

```text
latency_fillers.json
fallback_responses.json
recovery_and_status.json
README.md
```

These are text packs and planned clip manifests. They are not currently wired into the primary React voice path. The `clip_slots` entries intentionally use:

```json
"asset": null
```

Do not add empty audio files. When approved WAV clips exist, set `asset` to a real relative WAV path.

## Environment Variables To Copy

For another orb, copy these settings first:

```text
FASTER_WHISPER_STT_URL=http://127.0.0.1:9000/stt
ORB_ASSISTANT_ROOT=../Orb_Assistant
LOCAL_LLM_URL=
LOCAL_LLM_MODEL=
```

Docker currently overrides:

```text
ORB_ASSISTANT_ROOT=/app/Orb_Assistant
FASTER_WHISPER_STT_URL=http://host.docker.internal:9000/stt
```

## Frontend API Methods To Copy

File: `frontend/src/services/api.ts`

```ts
websiteOrbVoice: (audio: Blob) => {
  const formData = new FormData();
  formData.append('audio', audio, 'website-orb.webm');
  return uploadForm<WebsiteOrbVoiceResponse>('/api/orb/website-voice', formData);
}
```

```ts
websiteOrbText: (transcript: string) =>
  request<WebsiteOrbVoiceResponse>('/api/orb/website-text', {
    method: 'POST',
    body: JSON.stringify({ transcript })
  })
```

For a new orb, keep the same response shape unless there is a strong reason to change it. The UI expects `spoken_output`, optional `cognitive_pulse`, and `llm_source`.

## Minimal Copy Pattern For Another Orb

Use this as the setup checklist:

1. Add a frontend `speak(text)` helper using `SpeechSynthesisUtterance`.
2. Always call `window.speechSynthesis.cancel()` before `speak()`.
3. Add click-to-record using `getUserMedia` and `MediaRecorder`.
4. Record short WebM audio, around 6.5 seconds max.
5. Upload the blob to `POST /api/orb/website-voice`.
6. Speak `result.spoken_output`.
7. Show `result.transcript` or `result.spoken_output` in a visible status bubble.
8. Use `result.cognitive_pulse.glow_intensity` to update orb mood or animation.
9. On error, use the same `speak()` helper for the recovery message.
10. Keep `POST /api/orb/website-text` available as a transcript-only fallback.

## Known Imperfections

These are part of the current setup and should be considered when cloning it:

1. Browser voices vary by operating system and browser, so the same orb can sound different on different machines.
2. `WebsiteFloatingOrb` does not select the same preferred voice logic as `AutonomousOrb`.
3. Voice packs exist but are not wired into the live voice path.
4. There is no backend-generated TTS audio in the normal path.
5. Faster-whisper must be running separately or `/api/orb/website-voice` fails.
6. If API routing returns the frontend HTML shell instead of JSON, the frontend will treat the voice route as unavailable.
7. The two frontend orb surfaces use different input strategies: browser transcript versus recorded audio upload.

## Recommended Next Cleanup

Before applying this to many more orbs, centralize the frontend voice helper:

```text
select preferred browser voice
set rate/pitch/volume
cancel current utterance
speak normal output
speak recovery output
handle onend consistently
```

Then make both `AutonomousOrb` and `WebsiteFloatingOrb` use that helper. That would keep the working setup intact while making cloned orbs more consistent.
