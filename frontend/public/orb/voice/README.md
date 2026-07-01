# Browser ORB Voice Pack

These files mirror the active ORB latency language pack so the website ORB can
fetch the text and local WAV clips without waiting on the backend.

Future WAV files are declared in `latency_fillers.json` as `clip_slots` with
`asset: null`. Do not add empty audio files. When approved clips exist, set the
slot asset to the real relative WAV path.
