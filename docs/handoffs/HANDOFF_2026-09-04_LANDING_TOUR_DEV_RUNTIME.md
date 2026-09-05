# Handoff — Landing Tour Dev Runtime

Date: 2026-09-04

## Resume from here

Work in `/home/bryan/projects/Orb_Weaver`.

The current bounded product packet is:

```text
INTRO_COMPLETE -> LANDING_TOUR -> PREFLIGHT
```

Do not start Account, full scan, review, checkout, package build, download, or install work.

## Non-negotiable product behavior

Orb Weaver is demonstrating a Website ORB by hosting its own site. After the existing introduction ends, it must not become idle or offer a Start Tour choice. It must begin a persistent landing-page tour, explain the actual sections it reaches, scroll the real page, use verified movement/Point/Ping behavior, accept interruption, answer from whole-site knowledge, then resume and enter the real `/preflight` route.

The distinction is:

```text
Site World       = what Weaver knows about the entire verified website.
Current DOM/page = what Weaver is physically showing now.
Journey state    = where Weaver is in the guided encounter.
```

Page copy is evidence, not a prerecorded script. Weaver may quote, read, summarize, compare, or skip it as the current conversation warrants.

Do not add a microphone button, push-to-talk, Chrome SpeechRecognition path, or any floating voice control. The existing lower-right `Volume2` / `VolumeX` control in `AutonomousOrb.tsx` is a mobile speaker/audio-unlock control and must remain unchanged. Existing listening is the ORB interaction plus browser MediaRecorder -> `/api/orb/website-voice` -> Faster Whisper -> governed Qwen -> Kokoro.

Do not modify Faster Whisper, Qwen, Kokoro, CUDA, firewall, or other voice infrastructure unless a direct regression is observed.

## Use only the isolated dev runtime

Do not iterate on reviewed `16510/16500`.

Current intended dev processes:

```text
Frontend source/hot reload: http://127.0.0.1:16667
Dev API:                    http://127.0.0.1:19667
Dev inference gateway:      http://127.0.0.1:19620
```

At handoff the frontend is a source `react-scripts start` process on `16667`; the API and gateway are dev-only containers named `orb-weaver-dev-api` and `orb-weaver-dev-gateway`. The API mounts the working `backend/` source and is configured to use the gateway; the gateway uses the existing Qwen service at `172.18.176.1:8009`. Faster Whisper and Kokoro remain the existing host services at `9000` and `8880`.

Useful proof commands:

```bash
ss -ltnp | rg ':(16667|19667|19620)\b'
curl -fsS http://127.0.0.1:19667/
curl -fsS http://127.0.0.1:19667/api/orb/startup-readiness \
  -X POST -H 'content-type: application/json' \
  --data '{"site_id":"orb-weaver","target_url":"https://orbweaver.spruked.com/"}'
curl -fsS http://127.0.0.1:16667/static/js/bundle.js | rg '19667'
```

The dev API readiness is expected to be `WARMING` only because `SITE_WORLD_READY` lacks a fresh customer crawl. The landing-tour startup gate deliberately accepts the other five proofs: STT, cognition, Kokoro, pointers, governance. Do not make a fake Site World crawl just to clear the state.

## Implemented source change

Changed files already present in the dirty worktree:

```text
backend/app/inference_gateway/config.py
backend/app/inference_gateway/contracts.py
docker-compose.yml
frontend/src/landing/LandingPage.tsx
frontend/src/landing/AutonomousOrb.tsx
```

The first three backend/compose changes are the completed voice-repair work. Do not revisit them for this packet.

`AutonomousOrb.tsx` now has:

* persisted `WebsiteJourneyState` under `orbweaver-website-journey`;
* stages `LANDING_TOUR`, `PREFLIGHT_PENDING`, `PREFLIGHT`;
* `runLandingTour`, which verifies actual sections (`beat-1`, `weaver-first-encounter`, `beat-3`, `beat-6`, `beat-9`, `beat-10`), requests a generated conversational explanation via the governed Website ORB text path, and reuses the current verified pointer/movement system for `watch_weaver_guide` and `run-free-preflight`;
* real `window.location.assign('/preflight')` only after the final real pointer target succeeds;
* route-side confirmation that `/preflight` actually mounted before state becomes `PREFLIGHT`;
* interruption that aborts only the tour controller; following recorded-audio response resumes the saved segment.

Important: `runGeneratedAct` already calls the whole-site canonical resolver with Site World and page capsule context. It is intentionally used for dynamic tour explanations instead of a fixed text-to-speech script. The result must be reviewed in the browser for quality.

## What passed

* `npm run typecheck` passed after the tour work.
* `git diff --check` passed.
* Dev source bundle contains `19667`, and live page requests observed in Chromium were all against `19667`.
* Dev API validates live Faster Whisper, Qwen/gateway, Kokoro, pointer map, and governance.
* Chromium reached `http://127.0.0.1:16667/?orbStartupReset=1`, mounted Weaver and the speaker/audio-unlock button, and made requests to dev startup-readiness, capabilities, pointer map, page capsule, and TTS.

## What did not pass yet

Do not claim any of these until directly observed:

* Intro-to-tour handoff: the headless browser had no user gesture/microphone permission, so the existing splash remained at its proper startup gate with `permission_state: blocked`. It never reached `landing_tour_started`.
* Actual section scrolling plus generated explanations.
* Glide + verified Point/Ping during the tour.
* Visitor interruption with an off-screen, whole-site question.
* Correct saved-segment resumption after that answer.
* Real transition and retained state at `/preflight`.
* Physical browser microphone and audible Kokoro acceptance.

For the next browser test, use the existing splash's `Start with Weaver` user gesture in a real browser or an automated click; that is not a microphone button. Then capture the `orbweaver:mounted-runtime` events and browser visuals. An off-screen question should be sent through the actual ORB recording lifecycle, not by a direct API call.

## Acceptance sequence

1. Reload dev `16667` with `?orbStartupReset=1`.
2. Use the existing Start-with-Weaver/audio-unlock interaction when required by browser policy.
3. Confirm the intro completes with no idle gap.
4. Confirm `LANDING_TOUR` starts automatically.
5. Confirm several real sections scroll into view and receive conversational explanations.
6. Confirm at least one verified live target is glided to, Pointed, and Pinged.
7. Interrupt Weaver mid-tour with a spoken question about another site area; confirm the whole-site answer through Faster Whisper -> Qwen -> Kokoro.
8. Confirm the saved segment resumes.
9. Confirm final verified target enters actual `/preflight` and journey state becomes `PREFLIGHT` only after that route mounts.
10. Only after the entire dev packet passes, build/redeploy reviewed production once and test `16510`.

## Repository status at handoff

The worktree is intentionally dirty with only the five files listed above. No commit, push, or production rebuild is needed next. Update `docs/DEV_LOG.md` after any material change or test result.
