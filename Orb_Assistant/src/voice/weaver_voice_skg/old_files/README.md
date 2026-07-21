# ORB Latency Language Pack

This pack gives the ORB natural short responses while the real answer, voice
engine, or model path is still working.

The canonical editable language files live here:

- `latency_fillers.json`
- `fallback_responses.json`
- `recovery_and_status.json`

Future local audio clips are declared as `clip_slots` with `asset: null`.
Do not add empty WAV files. When approved voice-pack renders exist, set each
slot's `asset` to a real relative WAV path.

The LLM is only the articulation path. Reasoning remains in
`Orb_Assistant/src/components/core_4_minds`.
