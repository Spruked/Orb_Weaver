# Orb Weaver Development Log

## 2026-09-23 — Campaign Website ORB runtime publication and design artifact integration

* Rebuilt and restarted the production Docker service after the campaign
  installer exposed stale runtime behavior. The campaign origin is now bound
  explicitly to `orb-weaver-campaign` for API/CORS and WebSocket access; the
  campaign install snippet was not changed.
* Removed the external loader's legacy chatbot housing: no panel, text box,
  Ask button, or conventional voice window. Engaging Weaver starts the
  microphone/STT path directly; spoken responses and verified Pointer/LiDAR
  guidance remain in the shared governed runtime.
* Published the current campaign identity as `orb_weaver_current_v2` using the
  white-collar/cyan-lens `weaver-blue-eye.png` skin. Added narrow cross-origin
  access for `/orb-skins/` and versioned the skin URL to prevent a stale CDN
  response from forcing the tuxedo factory fallback.
* Added the supplied compiled React design export at
  `frontend/public/orb-weaver.html` and exposed it through the native React
  route `/orb-weaver` using `PublicOrbWeaverArtifact`. This preserves the
  design while allowing later section-by-section migration into editable
  React components.
* Validation: loader build passed; loader smoke passed with 35 checks and
  zero console errors; frontend development compilation passed; production
  CORS preflight passed; campaign bootstrap returned the current skin; and
  the versioned skin request returned `200` with cross-origin headers.
* Remaining external issue: the campaign's own Vinext deployment requests
  missing Geist font files under `.vinext/fonts/`. Those 404s are separate
  from Orb Weaver and require a Campaign-site build/path repair.

## 2026-09-22 — Customer download isolation and installable runtime

* Removed unversioned context overlays and excluded seeded template data,
  factory examples/audio and the Dock Station app from customer downloads.
  Packages contain their own canonical Vault, standalone widget, launcher and
  installation instructions; the existing host runtime remains separate.
* Added manifest-bound chunks/index/lexicon, permission envelope and witnessed
  site-goal topic choices. Startup validates all required approved artifacts,
  identities and hashes. Unknown routes cannot borrow home-page pointers.
* Wired the explicit customer approval/build action and authenticated download
  to the manufactured runtime; legacy pack creation cannot silently substitute
  a data-only ZIP. Kept payment/entitlement/review gates.
* Verified two unrelated customer archives, zero known factory marker findings,
  independent offline text runtime, modified-payload rejection, no-click DOM
  pointer behavior, and confirmed build/download through the API. Focused
  backend suite: 41 passed; follow-up isolation/SKG: 13 passed; widget DOM test
  and frontend TypeScript check passed.
* This is package/runtime verification, not production browser/voice acceptance.
  No Docker operation or model change. Exact inputs, archive contents, lineage,
  evidence and limitations: `docs/architecture/CUSTOMER_ORB_PACKAGE_AUDIT.md`.

## 2026-09-22 — Separate host/customer SKGs and shared lexical layer

* Revised the supplied Nine of Clubs draft into a bounded, host-only guidance
  contract consumed by live speech and Agency prompts. Preserved the canonical
  discovery registry and Governor. Account setup is distinct from the earlier
  pointer-proof act; interruptions and signup use short typed guidance cues.
* Added the agnostic graph compiler and lexicon to the golden clone template.
  All manufactured payloads now require `apriori/site_skg.json`, including its
  source fingerprint, witnesses, serialized alias index and per-route context.
  Owner-approved goals get precompiled next hops; destination popularity is
  advisory. Unknown evidence, unmatched language and disconnected goals stay
  explicit rather than generating fictitious choices or actions.
* Wired actual stored scan text/links/pointers and lexical data into canonical
  manufacturing evidence. Stale evidence from a different scan is no longer
  silently reused. Populated `site_world.routes` from the same graph so the
  installed runtime can look up each compiled route.
* The clone validates the required graph at startup and uses lexical context
  in route lookup, TPC input and answer fallback. Host and clone vocabularies
  remain site-scoped; alias collisions preserve all candidate identities.
* Corrected frontend API-boundary issues: oversized account objectives and
  duplicate tour text in the short transcript, and signup/paused-tour voice
  being diverted to legacy transcription-only handling.
* Validation: 35 backend tests passed (compiler, guidance, lexicon, package
  runtime and existing sales/Agency), plus 34 frontend discovery, Agency and
  journey-store tests. The package probe exercised real route lookup, lexical
  context in answers, required-graph startup rejection and TTS governance.
  A read-only in-memory compile of the stored 30-page Weaver crawl produced
  22 eligible visitor routes. Its lexical source contains 114 canonical terms,
  320 alias keys and 3,797 alias phrases; no draft estimates were treated as
  measured results. Ambiguous/unmatched keys and alias-cap truncation remain
  reported, not silently resolved. The evidence snapshots were not rewritten.
* Deployment boundary:
  No inference-model change, Docker rebuild/restart, deployment, commit or
  push was performed. Source changes are not a claim of live browser-tour
  acceptance. Detailed contract: `docs/architecture/SITE_SKG_AND_LEXICON.md`.

## 2026-09-17 — Startup-proof deduplication and local inference portability

* The startup-readiness endpoint now overlaps independent local-LLM warmup and
  the Kokoro probe, then records cognition proof after the warmup completes.
  This reduces opening-gate latency without changing readiness criteria,
  Pointer/LiDAR authority, tour progression, or fallback behavior.
* `LandingPage` shares one in-flight startup-readiness promise across React
  Strict Mode development remounts. A remount therefore observes the same
  proof instead of issuing a competing live inference/speech warmup.
* The LiDAR coordinate cache now leaves a ready cache intact when the incoming
  Pointer records have the same ordered identity, semantic locator, and anchor
  strategy. Changed records still trigger the existing rebuild path.
* Local inference tooling now supports an explicitly remote
  `LLAMACPP_BASE_URL`: `verify_local_llm_runtime.py` does not require a local
  GGUF in that configuration, and `orb-inference-profile.sh` launches managed
  services in a detached session so they survive a short-lived WSL/automation
  shell.
* Scope: source and documentation only. The untracked
  `tour_dialogue_transcript.txt` is a local runtime artifact and is deliberately
  excluded from the repository. Focused validation and GitHub publication are
  recorded with the corresponding commit.

## 2026-09-16 — Automatic splash → warmup → ORIENT handoff repair

* After a power interruption, `16666` and `16667` could restart while the
  separate Qwen/llama.cpp inference profile on `16520` remained down. The
  splash greeting could then finish but its first governed ORIENT turn had no
  live cognition path. This was a runtime-startup dependency failure, not a
  Pointer, LiDAR, Governor, or tour-content failure.
* `scripts/start-dev-runtime.sh` now starts the existing local inference
  profile (`llama.cpp` then the inference gateway) when `16520` is absent,
  before starting the API and frontend. It does not replace the existing
  profile or change its model configuration.
* The startup contract is frozen to the last known-good visitor lifecycle:
  the full-screen historical `OrbBurst` splash starts immediately and covers
  the original recorded Michael showroom introduction (including its existing
  cue timing). The mounted ORB remains continuous. Existing llama inference
  warmup starts in parallel, and the original handoff is released only after
  the complete intro and a real cognition-ready proof. There is no readiness
  screen, second intro, pause narration, or desktop activation step. The
  speaker control remains a mobile browser audio-activation control only; it
  is not part of desktop splash, warmup, curriculum, or tour handoff.
* The splash intro now writes its real post-`audio.play()` playback state to a
  short-lived document state before emitting the existing intro event. The
  already-mounted `AutonomousOrb` reads that state if its event subscription
  races the splash effect, then uses its existing `voiceState === "speaking"`
  core animation. This preserves one ORB and one blue/white core visual across
  the recorded splash intro, ORIENT, DISCOVER, and later speech; no
  splash-only pulse was added.
* Corrected the legacy landing-route callback that could see the intro-complete
  session flag while the splash was still covering the page. It is now gated by
  the existing splash-release state, so it cannot start ORIENT during the
  intro. The mounted startup sequence remains the sole handoff and invokes the
  governed tour immediately when the gate releases.
* Aligned generated Website ORB speech with the historical showroom recording:
  the existing Kokoro configuration now defaults to `am_michael` rather than
  `am_echo`, including the example and Compose defaults. This is one existing
  provider path, not a second voice system.
* Verification: frontend TypeScript `--noEmit` passed; focused startup-control
  tests passed (3/3); backend configuration compiled; and `git diff --check`
  passed. Live browser acceptance remains pending after the restored inference
  profile reaches `COGNITION_READY`; the TTS-default change requires the next
  normal backend reload to become live.

## 2026-09-16 — Crawl #3 canonical-Vault verification

* Corrected an earlier path diagnosis: `substrate/clients` is a compatibility
  symlink to `vault_system/clients`, not a second persistence root. Crawl #3
  therefore wrote its 30-page semantic package into the canonical Vault as
  required; no copy, migration, or storage-root code change is appropriate.
* Read-only runtime verification on `16666` confirms the loader now consumes
  Crawl #3 for `orbweaver.spruked.com`: Site World is loaded, the pointer-map
  source crawl ID is `3`, the map has 740 runtime records after owner records
  are merged, and the root page capsule has a summary, five likely tasks, and
  three ranked targets. The compiled context contains page knowledge, lexical
  and retrieval indexes, knowledge chunks, graph, route, validation, and
  catalog fields.
* The existing canonical-storage regression already asserts that
  `substrate/clients` resolves to `vault_system/clients` in
  `backend/tests/test_canonical_storage.py`. No backend reload was required
  for Crawl #3 consumption. Pointer recovery remains separately blocked by
  its reported route/locator conflicts; that is not a storage condition.

## 2026-09-16 — Track A Milestone 2 live-evidence inventory (read-only)

* Milestone 2 candidate-constructor work is paused pending evidence review. No
  Pointer/LiDAR, Governor, Agency, A.I.M.S., Site World, deployment, Docker,
  or runtime-service change was made in this inventory.
* The live `16666` API path used by local `16667` currently resolves the
  `orbweaver.spruked.com` Pointer map to six owner-showcase records on `/`.
  Only three are guidance-eligible in the quality report: the suite logo,
  `Run Free Preflight`, and `Launch Dashboard`. The other three are speech
  orientation/reference material. There is no live support, lead-generation,
  pricing, product-comparison, checkout, or form target in that runtime map.
* Live Pointer records do carry useful spatial and identity evidence:
  route, target type/class, visible-text-derived meaning, direct/intent/topic
  aliases, semantic locator, structural context (landmark, parent locator,
  nearest heading, ordinal, tag), content fingerprint, confidence/health,
  and runtime policy. `validateOrbPointerTarget` rechecks locator, expected
  text/tag, DOM attachment, visibility, and geometry immediately before
  guidance. That proves live existence and position; it does not establish
  commercial purpose on its own.
* Correction after Crawl #3 verification: the active Site World loader does
  consume this exact domain's canonical Vault package. It has page knowledge,
  chunks, lexical/retrieval indexes, route classifications, entities, and
  graph evidence. Agency candidate construction still receives only the
  Pointer map plus a minimal page capsule; the richer records are used by
  `/website-text` articulation retrieval and are not exposed as target-linked
  evidence to `frontend/src/tour/agencyRuntime.ts`.
* Therefore the present runtime cannot honestly derive meaningfully distinct
  SUPPORT, LEAD_GENERATION, or PRICING demonstration sets without either
  hardcoded labels/target IDs or new target-linked semantic evidence. The
  smallest plausible next boundary is an evidence bridge that retrieves a
  bounded current-page semantic slice from Site World and joins it to current
  Pointer identities, while Pointer validation continues to certify live DOM
  existence and the Governor continues to certify legality. That bridge is
  deliberately not implemented in this pass.

## 2026-09-14 — Website Weaver startup-chain repair on 16667

### Scope and root causes

- Work remained on the isolated development lane (`127.0.0.1:16667` →
  `127.0.0.1:16666`). Request-queueing work stayed paused. Site World,
  Pointer/LiDAR, movement, Stage Governor, authorization, account ownership,
  and customer data were not changed.
- The incomplete-intro defect came from treating media/source failure as a
  valid completion path: it hid the intro visual and released the startup gate
  without an actual `HTMLMediaElement.ended` event. A separate 30-second gate
  timeout then continued into another startup path. Together these paths could
  report startup progress after incomplete or absent playback.
- The authenticated-account rule then legitimately suppressed the governed
  tour. That made Bryan's signed-in development session unable to exercise the
  new-visitor chain, even when the intro succeeded.

### Repair

- Intro playback failure and browser autoplay denial now leave startup held.
  The existing Weaver speaker control is the recovery gesture; only complete
  playback releases the gate. A readiness timeout records a blocked state and
  stops instead of manufacturing a second/fallback intro handoff.
- Added development-only query controls:
  `orbIntroVariant=am-echo|am-michael|kokoro-host` selects a known intro for a
  repeatable fresh-start test, and `orbDevFullTour=1` admits an authenticated
  current-session account to the governed tour. Both controls are inert in a
  production build. The full-tour flag affects only tour eligibility; the
  account remains authenticated and all backend permissions remain unchanged.
- Added development-only timestamped startup events for landing/ORB mount,
  selected intro, each required line's request/readiness/playback boundaries,
  true all-lines completion, account/override eligibility, tour initialization,
  first governed request, first tour audio readiness, and first tour media
  playback. Recorded intro variants remain one complete prerecorded asset;
  their line boundaries are observed through the existing timed caption cues.
- Replaced the stale browser startup script with a repeatable matrix covering
  all three intro variants, one mounted ORB, actual intro media completion,
  deliberate autoplay denial followed by the existing speaker control,
  authenticated override enabled, and authenticated override disabled.

### Verification

- Focused frontend tests: **30/30 passed** across startup controls, login
  handoff, voice lifecycle, tour evaluator, Stage Governor, and interaction.
- Frontend TypeScript no-emit check passed; `git diff --check` passed.
- The first clean Docker build exposed a test-only dependency declaration
  gap hidden by the long-lived workspace: the production compiler could not
  resolve implicit Jest globals in `startupDevelopment.test.ts`. The test now
  imports `describe`, `expect`, and `test` explicitly from the existing
  `@jest/globals` package; no runtime dependency or product behavior changed.
- The development backend health endpoint and frontend document both returned
  HTTP **200** on `16666` and `16667`.
- Browser matrix **passed 5/5 cases** on `16667`: `am-echo` (6/6 cue lines),
  `am-michael` (6/6), and `kokoro-host` (1/1 synthesized line) each reached
  actual media `ended` before `introComplete`, retained exactly one ORB,
  detected the authenticated development override, initialized the existing
  governed Target One controller, and issued its first governed request. The
  deliberate autoplay-denial case remained held, recovered through the
  existing speaker control, then completed all 6/6 `am-echo` lines and made
  the same governed handoff. With the override absent, the authenticated
  session still received the complete intro and then skipped the tour.
- Known external boundary: `127.0.0.1:16520` currently refuses connections.
  This does not prevent proof of intro playback, override eligibility,
  governed-controller initialization, or the first governed request, but a
  first-tour audio/voice success is **not proven in this pass**: all four tour
  cases reached the governed request, but none received a tour audio URL or
  began first-tour speech while cognition was unavailable.
- Docker runtime follow-up: the running `orb-weaver` container retained the
  obsolete `172.18.176.1:8009/v1` llama.cpp default and therefore returned
  governed-tour HTTP 503 after the intro. The verified local model endpoint is
  reachable from Docker at `http://host.docker.internal:8080/v1/models`.
  Docker's compose default now points there. Recreate `orb-weaver` after this
  commit; no Site World, Pointer/LiDAR, movement, or Stage Governor logic was
  changed.

## 2026-09-11 — Intended local cognition service restored

- Restored the supported local inference lane without Docker changes or a
  provider/model substitution. The exact official Qwen 2.5 1.5B Instruct
  GGUF (`Q4_K_M`) is installed at
  `/home/bryan/substrate/llm/models/qwen2.5-1.5b-instruct-q4_k_m.gguf` and is
  served by the existing substrate llama.cpp binary on `127.0.0.1:8080`.
- The local inference gateway is alive at `127.0.0.1:16520`; its ready check
  reports the `llamacpp` provider ready and as the only eligible runtime
  provider. Kokoro retains the RTX for live speech; llama.cpp is configured
  CPU-side rather than competing for its VRAM.
- The profile launcher must run in a detached session in this development
  shell environment. Current persistent processes are the profile-managed
  `llama` and `gateway` entries; `bash tools/orb-inference-profile.sh status`
  reports both running.
- Live endpoint proof after restoration: direct `16520/api/generate` returned
  `cognition ready`; governed landing-tour `website-text` returned **200**
  with `llm_source=llamacpp-tour` and `tts_provider=kokoro`; first-visitor
  `website-text` and multipart `website-voice` each returned **200** with
  `llm_source=llamacpp-qwen2.5-1.5b-instruct-q4_k_m` and Kokoro audio.
- Repaired an unrelated reachability ordering defect discovered during that
  proof: non-tour first-visitor acts were reaching the generic canonical
  resolver before their existing choreography handler, producing a false 503
  even when cognition was healthy. They now reach the existing first-visitor
  handler first. Governed Target One tour acts remain on their controller path.
- The isolated source runtime was restarted cleanly on `16666` / `16667`
  (`/tmp/orb-weaver-dev.DIMpbv`). The landing splash is deliberately once per
  browser session; use `?orbStartupReset=1` in the local development URL to
  replay it during verification. This resets only startup/tour session state.

## 2026-09-11 — Target One first-stop articulation evidence repair

- Captured the first governed stop (`chapter-meet-weaver/stop-hero-meet`): its
  sole required concept is `WEAVER_IDENTITY` — Weaver is the Website ORB host,
  understands the site, answers from verified knowledge, and guides when
  showing is faster than explaining. The Site World slice for the self-hosted
  landing page is intentionally sparse; the verified concept and visible hero
  copy are the factual evidence supplied to articulation.
- Root cause was not cognition availability or the frontend evaluator. Qwen
  produced accurate natural speech but as plain prose rather than the required
  JSON `covered_concepts` envelope. The prior prompt also buried the required
  concept among broad instructions, allowing vague metaphorical output.
- The articulation prompt now supplies concise semantic proof targets. A
  strict secondary **evidence-only** live-cognition pass runs only if the
  speech response omitted claims. It cannot alter visitor speech, select a
  route, or advance state; it may return a concept only with an exact
  contiguous excerpt from the already-final speech. Backend and frontend still
  require that exact excerpt, so generic/fallback speech cannot advance.
- Live first-stop proof now returns `llamacpp-tour` and Kokoro audio. Raw
  speech states Weaver's host role, website understanding, verified knowledge,
  and show-versus-explain guidance. The evidence pass returns
  `WEAVER_IDENTITY` with the exact excerpt “I am Weaver, the Website ORB
  host.” The final evaluator accepts it, so the controller may advance from
  genuine coverage.
- The existing Nine-of-Clubs discovery-versus-guidance question is now asked
  immediately after the hero identity explanation at `stop-hero-meet`. Its
  semantic categories and Stage Governor mappings are unchanged; the move
  makes the first verified articulation end in the intended engagement turn.
  No destination, Governor rule, movement behavior, inference configuration,
  or Docker surface changed in this repair.

## 2026-09-11 — Paused handoff: visitor-driven conversational controller

> **Development intentionally stopped by owner direction.** The isolated
> source runtime on `127.0.0.1:16666` / `127.0.0.1:16667` and the in-progress
> production build were terminated cleanly. Docker was not started, changed,
> or stopped. Resume only after the user restarts this work.

### Locked behavioral acceptance

- A tour that merely scrolls, speaks, and reaches Preflight fails Target One
  if the visitor did not participate in selecting the route. Nine-of-Clubs
  questions are control-loop inputs, not decorative tour copy.
- Generic/fallback speech must never satisfy a required concept or advance the
  controller. Current source behavior enforces this: an unavailable `16520`
  cognition service produces HTTP **503** — `Dynamic tour cognition is
  unavailable; the stop was not advanced` — rather than a false advancement.
- The intended narrow implementation order is: (1) conservative concept
  evaluation, (2) governed branching, (3) session interaction state, (4)
  cross-page continuation with fresh Pointer/LiDAR context, (5) evidence-rich
  articulation, then (6) one uninterrupted browser proof.

### Current source state and next implementation target

- Implemented so far: exact-excerpt concept checks; unavailable-model
  non-advancement; compact Site World/current objective/recent context passed
  to articulation; raw/sanitized/delivered articulation trace; session fields
  for pending/asked questions, answer signals, visited routes, active route,
  and recent Weaver speech; a small authored question set; and selected-route
  conversational arrival continuation.
- **Authority split completed in this resumed pass:** question wording now
  defines only a bounded answer space; deterministic classification returns a
  stable semantic category; and `frontend/src/tour/governor.ts` is the single
  Website Tour Stage Governor that maps that category to the current finite
  legal destination set. The saved state records the issued set for the
  pending question and rejects a selection not issued by the governor. That
  authorization is bound to the pending question plus its exact
  stage/chapter/stop scope; it expires on any state-position transition and is
  cleared when consumed. The model may vary wording, never routes, controls,
  facts, or completion.
- **Do not call this full acceptance.** The remaining work is live
  destination/Pointer/DOM reacquisition and browser proof, not another hidden
  branching layer.
- Fresh retained-worktree validation after the authority split: frontend
  TypeScript passed; frontend **51/51** tests passed; focused tour-evaluation
  tests **16/16** passed; backend regression suite **210/210** passed; and the
  production build passed. The isolated source lane has been restarted on
  `16666` / `16667` (`/tmp/orb-weaver-dev.DpVCmi`); Docker remains untouched.
  With `16520` still unavailable, the live dynamic-tour request was re-proven
  to fail closed with HTTP **503**, not a false progression.
- Finish that pass with live destination/Pointer/DOM reacquisition, no startup
  replay or introduction repetition across pages, and an observed browser run:
  explanation → question → visitor answer → deterministic category → different
  authorized branch → verified guidance → route transition → contextual
  continuation. Keep unknown-answer, interruption, and permission safeguards
  intact. `16520` must be restored before this can become acceptance evidence.

### Motion handoff (not a Gate 1 expansion)

- Retune ambient movement to slow, smooth, bounded roaming with modest travel,
  natural pauses, and no sharp reversals, sudden acceleration, viewport
  bouncing, or cursor-escape behavior. Cursor proximity may be acknowledged
  subtly but is not movement authority. While speaking or asking a question,
  settle/reduce translation; resume gentle roaming after the turn. Governed
  Pointer/LiDAR guidance remains a distinct, deliberate glide to a verified
  target.
- Make the motion contract 3D-ready now: `intent → target vector → orient →
  travel → arrive → point/ping → reorient to visitor`. V1 remains the existing
  2D/2.5D renderer with heading/look/pointer/travel-direction cues (inner-core,
  highlight, shell, or shadow offsets). A true 3D ORB is V2, not a Gate 1
  requirement, so its eventual renderer swap must not require a motion/control
  architecture rewrite.

## 2026-09-11 — Live cognition pause and ambient-motion repair

### Browser evidence and exact boundary

- Live `16667 → 16666` evidence confirms page-side startup is healthy:
  `capabilities`, `page-capsule`, and `pointer-map` each returned **200**;
  LiDAR progressed from an initial `0` targets to **4** live targets. This is
  initialization/reacquisition evidence, not the current Target One blocker.
- The first governed Target One request then reached the cognition boundary:
  `/api/orb/website-text` returned **503**, followed by `/api/orb/website-voice`
  returning **503**. Backend logs identify the same concrete cause:
  `ConnectError: All connection attempts failed` while contacting
  `http://127.0.0.1:16520/api/generate`.
- The live UI now makes the governed condition explicit: “Weaver’s guided
  tour is paused because live cognition is unavailable. Your place is saved.”
  It holds the persisted tour state rather than falsely covering a concept or
  advancing the stop. A deliberate retry control invokes resume from that
  saved state rather than intro/startup state. The required live proof that it
  resumes the exact paused stop is blocked until cognition returns.
- The voice-turn path now recognizes the same 503 as a cognition pause,
  disables hands-free rearming, and holds instead of cycling through failed
  “start turn → 503 → finalized → start turn” retries. Other transient voice
  failures remain independently recoverable.

### Inference-service status — owner/service action required

- `127.0.0.1:16520` currently refuses connections. The supported local
  inference profile reports `gateway: stopped`, `llama: stopped`,
  `aphrodite: stopped`, and `tensorrt: stopped`. No local `.env.inference`
  model configuration or expected llama.cpp GGUF model file is present, so the
  source lane cannot safely restore this service on its own.
- Docker was inspected only and remains untouched. The existing container does
  not expose `16520`; changing Docker or substituting another model/provider
  would violate the locked fail-closed cognition contract. Restore the intended
  local gateway/model service, then prove: retry saved place → first governed
  articulation → Nine-of-Clubs question → answer classification → governor
  route → Pointer/LiDAR verification → cross-page continuation without intro
  replay.

### Motion and voice scope

- Ambient translation no longer reads cursor coordinates. It now uses a slow
  bounded roam (26 px/s), short moves, a 5.2-second initial dwell, 7.8–12.4
  second rests between moves, and a 3.6-second post-conversation dwell.
  Speaking, listening, and thinking settle Weaver in place. Governed
  Pointer/LiDAR travel remains intentionally distinct and authoritative.
- The current Kokoro development voice is frozen as the temporary V1 voice.
  **Custom Weaver Voice** remains backlog work required before final brand
  polish (release-polish versus V2 scheduling is still an owner decision), and
  is not a blocker for this repair.

### Validation in this pass

- Frontend TypeScript and frontend **51/51** tests pass, including the
  explicit assertion that hands-free voice cannot rearm once disabled.
  Focused backend tour-evaluation tests pass **16/16**. The production build
  passes, and the isolated source lane was restarted cleanly at
  `127.0.0.1:16666` / `127.0.0.1:16667` from
  `/tmp/orb-weaver-dev.yTvc16`; backend health and frontend HTTP both return
  **200**. A fresh governed `website-text` request returns the expected 503
  with `tour_cognition_unavailable` logged against `16520`, proving the
  boundary is still fail-closed after restart.

## 2026-09-11 — Isolated development lane and release-candidate regression closeout

> **Current runtime authority:** the isolated source lane is backend
> `127.0.0.1:16666` and frontend `127.0.0.1:16667`. The reviewed Docker lane
> remains `16500` / `16510` and was not changed. Any earlier references below
> to `19667`, `16600`, or `16610` are historical evidence only; do not use
> them for current development.

- Repaired frontend API/telemetry port resolution to `16667 -> 16666` and
  started the isolated source runtime without building, restarting, or
  modifying Docker. The launcher now keeps disposable development database,
  logs, and PID state outside the worktree while preserving the governed TTS
  cache inside the canonical Vault.
- Restricted credentialed CORS to explicit public and local frontend origins.
  Live preflight accepts `http://127.0.0.1:16667` and rejects an untrusted
  origin. Added `/health`; the isolated backend returns an operational status
  and canonical Vault identity.
- Repaired the canonical TTS-cache resolution, catalog variant traversal,
  pointer recovery normalization, deterministic visitor-tool visibility, and
  bounded authenticated-memory resolution without weakening Stage Governor or
  unknown-answer controls.
- Current validation on commit `2636522` (`Prepare isolated development
  runtime and launch hardening`): backend **210 passed**; frontend **43/43
  passed**; frontend TypeScript and production build passed; the four-case
  startup/browser proof passed, including alternate intro assets and
  deliberate autoplay recovery. The clean source commit was pushed to
  `checkpoint/target-one-working-2026-09-07`.
- The current release-evidence command sheet remains the Gate 1 authority.
  Historical Docker/public success below does **not** close Gate 1. Gate 1 is
  open until one identified release candidate is tagged, deployed, and
  reproves the complete security, regression, health/readiness, voice/STT,
  pointer positive/negative, two-site weave/install, latency, and evidence
  bundle requirements together.
- Current local caveat: the optional model endpoint on `127.0.0.1:16520` was
  unavailable during launcher warm-up. Deterministic resolution and verified
  startup/TTS paths remained operational; model-escalation acceptance must be
  captured in the later same-RC voice evidence bundle.
- Established `DOCUMENT_AUTHORITY.md`, a current isolated-runtime guide, and
  corrected deployment/Vault documentation. Historical port generations,
  snapshots, and rebuild prompts are explicitly non-authoritative rather than
  being silently rewritten as current proof.
- Target One review found a release-blocking acceptance defect: the linear
  frontend evaluator currently treats any non-empty spoken response as coverage
  for every missing concept, while local-model fallback returns a usable tour
  envelope. Generic fallback speech can therefore advance visual progression.
  The local model at `16520` is optional only for degraded runtime survival;
  it is required for dynamic-tour acceptance. The new Visitor Interaction
  Doctrine records the required governed question/answer and cross-page
  destination model. No movement, pointer, or unknown-answer guard was
  loosened during diagnosis.
- **Owner direction updated later on 2026-09-11:** the focused Target One
  behavioral pass is now implemented in the source lane. The evaluator no
  longer converts any non-empty response into coverage; accepted claims need
  an exact excerpt in final sanitized visitor speech. The backend supplies a
  compact Site World slice, preserves raw/sanitized/delivered articulation
  telemetry, and rejects unavailable-model fallback with HTTP 503 without
  advancing the stop. The frontend persists a bounded Nine-of-Clubs question
  state, deterministic authored answer mapping, selected route, answer signal,
  visited routes, and recent Weaver context; selected-route arrival provides a
  governed continuation instead of resetting the visit. This is a partial
  implementation, not completion evidence: `16520` is currently unavailable,
  and the complete cross-page graph, pointer/DOM proof, STT journey, and
  same-RC browser evidence are still required. Dynamic Target One articulation
  remains RED and Gate 1 remains open.

## 2026-09-09 — Live Preflight captions, visitor articulation, and presentation repair

- Replaced the immediate full-response transcript in the root-mounted public
  `AutonomousOrb` with audio-clock-driven captions. Nothing is rendered when
  Kokoro begins; complete natural phrases appear only after the corresponding
  playback position is reached. Pausing, interruption, audio failure, and a
  superseding turn cancel caption progression and preserve no future text.
- Normal captions are a dedicated page-level overlay, not a child of the
  moving ORB. They are capped at four readable lines, remain above report
  content, and do not change the result-page layout. After speech finishes,
  the caption becomes a compact transcript control. A visitor can deliberately
  expand the complete transcript and minimize it again.
- Added a final visitor-speech sanitation boundary to the governed
  `experience.tour` response path. It rejects tour/controller/curriculum,
  internal-state, and status-stop language before delivery, without treating
  ordinary phrases such as “stop by the front desk” as private language. An
  empty post-sanitization result fails closed with no visitor speech.
- Removed `stop.purpose` from the visitor-facing tour control. The control now
  uses concise visitor copy, so authoring instructions such as “introduces
  himself using the actual branded lines” cannot leak into the page.
- The original Weaver image skin remains the active asset. Its presentation is
  now given a restrained 3D glass/parallax, depth, and core-layer treatment;
  the experimental plasma video supplied for review was intentionally not
  wired into the runtime.
- Focused tests passed: four caption unit tests; four backend visitor-speech
  sanitation tests; `ORB_POINTER_E2E_PROOF_OK`; and
  `ORB_ONBOARDING_CONTINUITY_E2E_PROOF_OK`. Frontend type checking, production
  build, and `git diff --check` passed.
- Real dev browser acceptance against `16667 → 19667` submitted
  `https://www.spruked.com` through the public form. Evidence recorded a
  real report, report-card identity, `preflight_lidar_target_mapped`, live
  LiDAR cache verification, final `guidance_point_ping` with
  `geometrySource: live_refresh`, fresh `website-text`, `llamacpp-tour`,
  Kokoro audio, `caption_started`, audio-time `caption_progressed`, and
  `caption_completed`. `PREFLIGHT_CAPTION_E2E_PROOF_OK` proved the compact and
  deliberate full-transcript states. The separate live interruption run
  returned `PREFLIGHT_CAPTION_INTERRUPT_E2E_PROOF_OK`: only already-spoken
  text remained and no completion event followed.

### Remaining follow-up

1. Do a human visual review of the 3D Weaver skin and four-line caption at
   desktop and mobile widths; the build is available locally at
   `http://localhost:16667/` after a hard refresh.
2. The Preflight explanation can still be made more concise in a later content
   pass; this repair changes delivery timing and visitor-safe language, not
   the evidence or Pointer/LiDAR doctrine.
3. Docker/public deployment is complete. The rebuilt service serves
   `main.c0843634.js` locally and through `https://orbweaver.spruked.com`;
   both bundles contain `caption_started` and the explicit transcript control.
   Local public Preflight returned HTTP 200, local startup-readiness returned
   HTTP 200, and the public capabilities endpoint returned HTTP 200. Do not
   alter the primary llama.cpp service.

## 2026-09-08 — Cross-page Weaver continuity and MORB trajectories

- Root cause of the missing onboarding Weaver was twofold: the single global
  `AutonomousOrb` mount survived inside `BrowserRouter`, but an
  `onboarding-safe-mode` CSS rule hid it on `/signup` and the Preflight offer
  used a document-loading anchor instead of a React route transition.
- The approved onboarding offer now records a session-scoped destination and
  journey state, then uses a React `Link`. The one mounted Weaver stays
  visible, preserves its session without replaying a greeting, waits for
  signup hydration, refreshes the route Pointer/LiDAR state, and guides only
  to the live `[data-orb-target="full-name-field"]` locator.
- That route-local locator is not a crawl-map mutation or action authority.
  It enters the existing LiDAR channel as ephemeral geometry and is still
  required to pass the existing live identity, visibility, current-geometry,
  arrival, and final-before-Ping checks.
- Route-transition cleanup now completes before continuation guidance begins;
  ambient movement cannot interrupt that verified handoff. An approved
  navigation also aborts the former Preflight walkthrough so removed report
  cards cannot continue producing guidance attempts after leaving the page.
- Added a real Playwright acceptance script:
  `frontend/scripts/orb-onboarding-continuity-e2e-proof.js`. It submits a
  Preflight, chooses onboarding, verifies one visible Weaver and preserved
  `ONBOARDING` session state, observes the live onboarding LiDAR map and
  authorized final `guidance_point_ping`, and verifies back/forward does not
  duplicate the ORB. Result: `ORB_ONBOARDING_CONTINUITY_E2E_PROOF_OK`.
- MORB travel now has three deterministic visual patterns: direct, broad
  S-curve swirl, and dart-with-target-relative orbit. The visual path never
  alters Pointer/LiDAR authority; every pattern keeps the existing fresh final
  target recheck before Point/Ping. Reduced-motion users retain a static
  travel surface.
- Validation: `npm run typecheck`, production frontend build, `git diff
  --check`, and the browser continuity proof passed. The frontend build has
  pre-existing ESLint warnings; no new TypeScript error was introduced.
- Deployment: rebuilt the authorized `orb-weaver` Compose service from commit
  `9fd133d`. Local `16510` and the public Cloudflare hostname serve
  `main.baa45f36.js`; local API startup-readiness returned HTTP 200. The same
  real continuity Playwright proof passed against deployed `16510 → 16500`.
  Readiness reports `WARMING` only because its contract includes Site World
  prerequisites; it reports the llama.cpp cognition and Kokoro proofs ready.

## 2026-09-08 — Target One and manufactured single-Vault marker

- Committed and pushed marker `d9e4387` on `checkpoint/target-one-working-2026-09-07`: `Complete Target One vault and guidance integration`.
- The live public `AutonomousOrb` now consumes report-scoped rendered Preflight cards through the existing Pointer/LiDAR path. `data-orb-target` locates a card; it does not grant authority. The runtime resolves current DOM geometry, uses ephemeral LiDAR evidence, rechecks at arrival, and only then allows Point/Ping.
- Browser acceptance evidence covered the positive path (real form/report card → live target verification → `website-text` → `llamacpp-tour` response → Kokoro → verified Point/Ping), reflow/resize reacquisition, and the negative target-loss path (removed card → no stale movement, speech, Point, or Ping).
- Landing articulation now strips markdown/private controller language, avoids repeated “I am Weaver”/gender wording outside the identity stop, and avoids presenting intended outcomes as customer-measured results.
- Repaired the confirmed manufactured-package dual-store defect. New packages retain one physical runtime store at `runtime/vault_system`; the builder strips copied SKG `vaults/` and inactive vendor TPC persistence/API surfaces. SKG receives explicit paths beneath the package Vault; A Priori, A Posteriori, ledger, and glyph/provenance writes remain there.
- The manufactured resolver rejects missing, alternate, legacy, vendor, parent-escape, and symlinked roots. Package relocation remains valid as long as its internal `runtime/vault_system` remains the one root.
- Verification: focused manufactured-storage, canonical-storage, and tour suite: **25 passed**; Python compilation and `git diff --check` passed. The manufacture test builds a temporary package, performs deterministic cognition, creates posteriori/ledger/provenance state, restarts against that same Vault, and proves prohibited roots fail closed.
- No source legacy/template data was migrated or deleted. The repair governs newly manufactured packages only.
- Preserved the Phase-A pre-repair failure: `pending`, `rejected`, and
  `errored` tour traces formerly returned HTTP 200 and invoked mocked TTS.
  Repaired the live `experience.tour` path to run its factual/TPC lane,
  llama.cpp articulation, Doctrine V1 evaluation, and final governance trace
  before returning delivery. Only final `approved` reaches TTS.
- Added a canonical-Vault `TTS_WITHHELD` audit event for live non-approved
  delivery, containing correlation ID, final state, and reason without
  retaining unnecessary visitor content. Automated negative coverage now
  proves `pending`, `rejected`, and `errored` return HTTP 409, invoke no TTS,
  and record the event; the approved companion proves TTS is reached only after
  final approval.
- The manufactured Website ORB is an independent answer runtime, not a copied
  `experience.tour` controller. Its answer engine and text/voice endpoints now
  finalize and require their own approval trace and record `tts_withheld` in
  the package's canonical Vault. A temporary manufactured-package endpoint
  test proves a pending voice response returns HTTP 409, makes no `speak` call,
  and writes the diagnostic audit event. This is package-level automated proof,
  not commercial-environment or live-browser acceptance.
- Post-repair verification: **22 focused live governance/tour tests passed**;
  **1 manufactured-package endpoint test passed**; Python compilation and
  `git diff --check` passed.
- Repaired the public Preflight Vault write regression without moving storage:
  the root-owned canonical client report subtree for `www.spruked.com` was
  narrowly reassigned to the service UID/GID (`1000:1000`). A `bryan` process
  performed an atomic replacement write, then the real dev public Preflight
  returned HTTP 200 and wrote the canonical report as `bryan:bryan` mode `600`.
- Rebuilt the public Docker Compose stack from the current working tree. The
  new `orb-weaver` container runs as UID/GID `1000:1000`; Redis was retained.
  Local public ports `16510` and `16500` return HTTP 200, Docker's real public
  Preflight returned HTTP 200 and replaced the canonical report, and the
  Cloudflare hostname plus public `startup-readiness` endpoint each returned
  HTTP 200. This is deployment smoke evidence, not complete visitor-journey
  acceptance.
- Removed an unsolicited microphone-permission request from the generic
  Website ORB loader; voice recording now begins only from its explicit button.
  Rebuilt `public/orb-loader.js`. Its Playwright proof now passes a real
  `website-text` request → live geometry → ORB travel → Point/Ping path and
  the removed-target no-Ping path; loader smoke passed 35 checks with no console
  errors.

### Outstanding evidence / next work

1. Prove the corrected real browser Preflight path under one correlation identity, then if practical force a controlled rejection and prove no Kokoro/no delivery plus a withholding audit event. In a separate post-repair browser pass, measure Glide timing: acquire → glide → cognition → TTS prep → final refresh → Point/Ping → speech.
2. Determine which process created the former root-owned
   `vault_system/clients/www.spruked.com/preflight/` subtree and prevent a
   recurrence. Ownership is currently repaired; do not use `chmod -R 777` or
   redirect the Vault.
3. Treat Outcomes factual elevation, `You're at the outcomes status stop.` leakage, and public rendering of internal `stop.purpose` as known open defects. Repair and recheck Why Weaving Exists, Trust, 28-Weave, Outcomes, and Preflight Decision individually.
4. Then run the complete fresh-start nine-stop Target One acceptance, including interruption/resume, mobile permission gate, microphone/audio, explicit decision, actual Preflight/dynamic result explanation, and governance-approved speech.
5. After Target One acceptance but before commercial installer/productization acceptance, continue the Vault audit and neutralize remaining manufactured vendor TPC persistence capability. Do not rebuild Docker or alter the established Windows llama.cpp service during isolated development acceptance.

## 2026-09-07 — Dynamic Preflight result walkthrough

- Connected the public Preflight completion event to the live `AutonomousOrb` runtime after the result DOM renders.
- Weaver now derives its explanation from the persisted report, discovers only the result sections actually rendered, resolves their live geometry, and guides through them with the existing verified pointer path.
- Added the three explicit next-step offers: onboarding, full scans/data for $49.95, or ORB production. No offer starts automatically.
- Added a narration fallback when a result page exposes no guideable sections.
- Tesseract remains supplemental OCR capability for visual/image/canvas surfaces; it does not replace the persisted Preflight report as factual authority.

Purpose: preserve implementation context, decisions, verification results, and next steps between development sessions.

Update this file after meaningful code, configuration, runtime, testing, or doctrine changes. Keep entries concise and newest-first. Never record credentials or secrets.

---

## 2026-09-07 — Target One visual pass: ORB core and MORB readability

- Strengthened the active `AutonomousOrb` presentation after deployment screenshots showed a translucent main ORB and an under-rendered first MORB.
- Increased active/resting opacity, enlarged the MORB, added an opaque fallback surface and border, and made the launch phase visibly resolve before travel.
- Reworked the speaking white-core animation into a layered rotating/swirl motion with changing cloud contours.
- Added the current five-symbol two-color tool-center language: question mark, smile, dollar sign, check mark, and exclamation mark. Later versions may expand the set and semantics.
- Preserved the current Preflight boundary: after the user runs Preflight, Weaver explains the resulting Preflight evidence and answers Preflight-related questions only at this stage.

## 2026-09-07 — Target One runtime fixes and presentation boundary

- Kept the existing five-chapter, nine-stop landing walkthrough as Target One. Froze future page targets as Features, LiDAR Guidance, How It Works, and Preflight; no cross-page controller was added.
- Normalized fenced cognition JSON and the observed `id` claim alias while preserving exact spoken-excerpt and canonical-concept checks. Strengthened the prompt so every required concept must be spoken and evidenced.
- Made Pointer/LiDAR and section waits abortable, preserved the active controller until it settles, and prevented microphone rearming after a manual tour interruption.
- Updated the stale `watch_weaver_guide` pointer identity to match the live landing paragraph. Development-browser proof reached live Kokoro playback, advanced beyond the first stop, paused in 477 ms, resumed from the saved stop, and completed the corrected pointer demonstration.
- Replaced the hardcoded 20-second Faster-Whisper request timeout with a bounded configurable 60-second setting after live logs showed several recordings timing out at 20 seconds.
- Focused checks passed: seven backend tour-evidence tests and 21 frontend evaluator, voice-lifecycle, and pointer-validation tests. A long full-tour run was stopped by user direction to prioritize construction. Physical microphone acceptance remains outstanding.
- No commit or push was made. The reviewed `16500`/`16510` runtime was not touched.

## 2026-09-06 — Target One curriculum alignment and GitHub handoff

- Aligned the active landing tour to the supplied five chapters, nine stops and twelve canonical concept IDs. Trust is separate; removed the four-chapter taxonomy and extra beat-by-beat lessons.
- Retained V2 state/migration, cognition and concept-evidence transport, controller progression, TTS, DOM extraction, Pointer/LiDAR and interruption/resume. Mapped legacy positions without inventing Target One concept completion.
- Terminal choice: Run a Free Preflight Scan or Continue Exploring / Onboarding. Only the visitor's explicit Run action routes to Preflight; deferral leaves the visitor on the page. No later workflow was added.
- Native DOM IDs replace browser-tool selectors. Grouped evidence supports the narrative stops; the hero does not initiate scrolling. Static assembly-status illustration is not represented as live scan evidence.
- Updated the root/documentation READMEs, current Target One reference, and relevant voice/pointer/LiDAR and historical tour handoff notices.
- Validation intentionally deferred: no integrated tests, TypeScript checks, browser proof, builds, service restarts or deployment changes. Earlier isolated checks are not acceptance of this slice. Existing migration-test expectations need updating in the dedicated validation pass.
- User authorized committing and pushing this source/documentation handoff to GitHub, then standing by. No further architecture expansion is authorized by this handoff.
- Canonical scope, exact IDs, files and next steps: [TARGET_ONE_LANDING_TOUR.md](TARGET_ONE_LANDING_TOUR.md).


## 2026-09-03 — Website ORB Startup Splash / Voice Regression (in progress)

### Development-port directive

* The isolated development port pair used before this note was frontend `16610` and API `16600`.
* The requested frontend development port was subsequently updated to `16667`; use `16667` for the isolated frontend and `19667` for the isolated API from now on.
* Do not use or disrupt the reviewed runtime on frontend `16510` and API `16500`.

### 2026-09-04 — Persistent Landing Tour development (in progress)

* Do all remaining journey iteration in the isolated runtime: source frontend `http://127.0.0.1:16667` -> dev API `http://127.0.0.1:19667`. Do not rebuild or restart reviewed `16510/16500` while iterating.
* Restored the isolated runtime with a hot-reload React source server on `16667`, a dev-only API container on `19667` with `/app/backend` mounted from source, and a dev-only inference gateway on `19620`. The dev gateway reaches the already-working Windows Qwen service at `172.18.176.1:8009`; dev API startup readiness proves Faster Whisper, governed cognition, Kokoro, pointer mapping, and governance. `SITE_WORLD_READY` remains false only because a fresh customer crawl belongs to the forthcoming Preflight step.
* Verified the source frontend bundle resolves API traffic to `http://127.0.0.1:19667`; it does not target reviewed `16500`.
* In `frontend/src/landing/AutonomousOrb.tsx`, replaced the post-introduction idle first-encounter ending with persisted `WebsiteJourneyState`: `LANDING_TOUR`, `PREFLIGHT_PENDING`, and `PREFLIGHT`. State is stored under `orbweaver-website-journey`, survives reload/route handoff, resets only through the existing startup reset, and marks `/preflight` only after the route has actually mounted.
* The landing tour is a live generated conversation, not fixed narration. It live-verifies and scrolls the actual landing sections, asks the existing governed Website ORB path to explain each section conversationally, and permits relevant page copy to be quoted or read when useful. The current Site World remains the answer authority for the whole site; the current DOM section is only what Weaver is showing.
* Reused existing `guideToPointerRecord` rather than a slideshow. It verifies the live DOM target, scrolls as necessary, glides Weaver, and Point/Pings the verified `watch_weaver_guide` and `run-free-preflight` targets. The final target leads through real `window.location.assign('/preflight')`, not timed/fake navigation.
* A visitor interruption aborts only the active landing-tour segment, retains its persisted index, sends the visitor's normal recorded-audio turn through Faster Whisper -> governed resolver -> Kokoro, then schedules the saved tour segment to resume. No microphone button was added or changed. The existing lower-right `Volume2`/`VolumeX` speaker/audio-unlock control remains intact and is still separate from recording.
* `npm run typecheck` and `git diff --check` pass after the landing-tour changes.
* Dev Chromium evidence: the page loaded from `16667`, mounted Weaver and the speaker control, and all observed API requests went to `19667` (`startup-readiness`, capabilities, pointer map, page capsule, and TTS). The headless run did not have a real user gesture/microphone permission, so the splash stayed at the expected startup gate (`permission_state: blocked`); no landing-tour, interruption/resumption, browser-audible, or Preflight completion may be claimed yet.
* One production rebuild was performed before this development-port directive was recovered. Do not repeat it during this packet. Reviewed `16510/16500` are now left running and untouched.

### Follow-up — splash observation and login persistence

* Screenshot evidence from the reviewed site shows the older `Audio presentation unavailable.` splash state. That exact text is from the pre-repair bundle; the current source's audio-error path releases the gate and the autoplay-blocked path offers `Start with Weaver`.
* The observed `Loading account...` flash and automatic account restoration came from `authStore` persisting `orb_weaver_customer_token` in browser `localStorage` and `App.tsx` checking it at every load.
* Changed `frontend/src/services/api.ts` to clear the legacy stored token on application load and retain a token only in module memory for the active page session. A reload, new tab, or browser restart now requires an explicit login.
* Changed `frontend/src/App.tsx` so an unauthenticated visitor does not render the `Loading account...` screen while no active in-memory token exists.
* Added the mandated local port pairing `16666` frontend -> `19667` API in the development API resolver.
* Restarted the isolated source frontend successfully at `http://127.0.0.1:16667`, configured for API `http://127.0.0.1:19667`. Frontend tests remain 20/20 passing.
* Clarified the first-visit autoplay-blocked message and separated the `Start with Weaver` control from the status text. Audible startup must be visitor-initiated when the browser rejects automatic playback.
* Measured the intro WAV at 23.225 seconds. The prior caption cues ended at 30.575 seconds, making the final captions substantially late. Replaced the cue boundaries with measured speech/silence boundaries; `Just call me Weaver` now begins at 16.374s and `Let's get started` at 21.632s.
* Updated the active ORB skin's inner core: its blue/white current now drifts while idle and becomes a brighter moving/pulsing blue-white bloom during actual voice playback. The speaking animation is gated by the existing `speaking` voice state.
* Removed the whole-orb `x`/`y` oscillation from the ambient presence layer. It was launched before and after each ambient glide and caused the reported periodic down-left tick. Ambient presence is now centered scale/rotation only; guided travel remains the only source of ORB position changes.
* The first core-motion pass was too subtle over the image skin. Reworked it into three high-contrast, clipped blue/white current layers that visibly rotate and contract/expand toward the center, producing the requested alive, folding-in-on-itself motion while the outer shell stays anchored.
* Follow-up visual correction: the layered current still read as a surface reflection. Rebuilt the center as an opaque, recessed blue cavity with internal rotating currents and a separately moving white nucleus; the motion now has a foreground, middle current, and visibly deeper center rather than an overlay-only sheen.

### Context reviewed

* Reviewed the current Website ORB architecture, runtime topology, gold-master migration source, voice replication report, pointer runtime model, live-pointer validation doctrine, current handoff notes, and the active frontend/backend startup path.
* The root-mounted public runtime remains `frontend/src/index.tsx` -> `frontend/src/landing/AutonomousOrb.tsx`; `WebsiteFloatingOrb.tsx` and `orb-client/orb-mount.ts` are not the live Website ORB path.

### Diagnosis

* `LandingPage.tsx` still contained the intended first-encounter splash and prerecorded Kokoro `am_michael` introduction asset.
* The regression was browser audible-autoplay policy: an automatic `HTMLAudioElement.play()` rejection either left the old gate open forever or, in the pre-existing uncommitted recovery change, immediately dismissed the splash without speaking the scripted introduction.
* Startup readiness previously started only after the intro audio ended, reducing the splash's ability to hide runtime warmup.

### Implemented so far

* Preserved the existing first-encounter storage keys and deterministic `?orbStartupReset=1` reset method.
* Changed the autoplay-blocked state into an explicit `Start with Weaver` visitor gesture, which retries the same scripted audio rather than silently skipping speech.
* Kept hard media failures non-blocking so a missing/corrupt asset cannot trap the visitor on the cover.
* Started the governed `/api/orb/startup-readiness` warmup concurrently with the splash and made the transition await its already-running result.
* Added `STARTUP_WARMUP_STARTED`, `STARTUP_WARMUP_READY`, and `STARTUP_WARMUP_BLOCKED` runtime events for acceptance evidence.

### Verification in progress

* `git diff --check` passed after the startup changes.
* An initial dev-log read was accidentally issued from `frontend/`; no test executed in that command. Corrected to repository-root paths before continuing.
* `npm run typecheck` passed.
* The first production build reached the optimized compilation stage, then found a `WebsiteOrbStartupReadiness` TypeScript index-signature mismatch in the new warmup ref. The result is normalized at the API boundary now; the build is being rerun.
* Playwright's browser acceptance is host-blocked: no system Chromium is installed, and the installed Playwright release will not download Chromium for Ubuntu 26.04. No browser pass will be claimed until a compatible browser is available.
* The corrected source build passed (only pre-existing `AutonomousOrb`/LiDAR lint warnings remain). `npm run typecheck` and all 20 frontend Jest tests passed.
* The active local service's `POST /api/orb/startup-readiness` returned `WARMING`: Kokoro / `am_michael` synthesis works; local LLM and Faster Whisper are unreachable; Site World readiness is false; governance fails because its image lacks `/app/artifacts/inculcation.md`.
* The active local service's `POST /api/orb/website-text` returns HTTP 500 for the same missing foundational-standard file. Docker logs supply the traceback. Source repair: `Dockerfile` now copies `artifacts/` to `/app/artifacts`; the running reviewed container was not rebuilt or restarted.
* The live API returns a six-record, root-only owner-approved map with `POINTER_RECOVERY_REQUIRED` (`stable_pointer_floor_not_met`). It covers the suite logo, voice-orientation text, Preflight, and Dashboard only; map provenance fields are null. Marketplace, Diagnostics, Dock Station, Download, and Reports have no resolvable PlotRecord.
* The final production source build passed; the new landing startup warning is gone. Existing `AutonomousOrb`/LiDAR lint warnings remain unchanged.
* Pointer inspection confirms the public mount fetches `/api/orb/pointer-map`, but the returned map is not a fresh crawler artifact: `backend/main.py` merges the manual `ORB_WEAVER_SHOWCASE_POINTERS` overrides into any stored map. The current response is therefore manually authored owner-approved showcase data, not a current full Orb Weaver crawl map.
* Current runtime resolution is same-route only (`findPointerRecordForIntent` and `findPointerRecordById` reject another `page_route`). It uses a scoped semantic locator and text/tag identity check, plus final live verification before motion and Ping; content-fingerprint, accessibility-role/name, and localized visual recovery are not runtime fallback tiers. Cross-page travel, clicking, and action execution are not implemented by this mount.
* The existing target-validation suite protects the working semantic path: 8 tests cover identity match, stale/mismatched locator rejection, policy rejection, competing selector identity resolution, and scoped-locator containment. The full frontend suite is 20/20 passing.
* Aligned `AutonomousOrb`'s backend-TTS recovery script with the canonical Landing splash copy, so a genuine prerecorded-audio failure uses the same existing Kokoro route and does not change Weaver's startup message. TypeScript and `git diff --check` pass after this alignment.
* The isolated source frontend serves the checked-in intro asset at `/orb/voice/weaver-showroom-intro-am-michael.wav` with HTTP 200 / `audio/wav` (1,114,844 bytes). This confirms the source server can load the intended prerecorded voice asset; audible playback/caption sequencing still requires a compatible browser acceptance environment.
* All seven requested visitor-style text questions were sent to the active local `/api/orb/website-text` endpoint with TTS disabled. Each returned HTTP 500 / `Internal Server Error`, caused by the same missing `/app/artifacts/inculcation.md` image file. Therefore none can be counted as an answer, guide, Point/Ping, travel, navigation, or action pass.
* Next: deployment of the source Dockerfile repair and restoration of the required local LLM/STT/site-world services are needed before a full browser acceptance can pass. No reviewed service was restarted, rebuilt, committed, pushed, or deployed.

---

## 2026-07-30 — Website ORB CCO Runtime Trace and Site Learning Loop

### Commercial stance

* The Website ORB is ready to sell as a controlled, white-glove pilot installation.
* It is not ready for broad self-serve SaaS sales.
* Do not promise no-click microphone activation, complete live GPT/Claude adapter switching, unsupervised self-install, or automatic self-promotion into trusted Site World.

### Implemented

* Renamed the standalone Context Crystal work into **Context & Correspondence Orchestrator (CCO)**.
* New path: `Orb_Assistant/context_correspondence_orchestrator/`.
* Public names: `ContextCorrespondenceOrchestrator`, `OrchestrationMetadata`, `CCOConfig`.
* Added live Website ORB `cco_trace` output through `backend/app/orb/cco_runtime.py`.
* Added site-scoped Website ORB learning loop in `backend/app/orb/site_learning.py`.
* Runtime answer states now include `known`, `resolved`, `clarification_required`, and `unknown`.
* Unknown answers write to the site-specific Stump Ledger.
* Verified posteriori cases can be reused through the deterministic `resolved` path.
* Downloadable ORB packs now include clean-slate `website_orb_learning/` templates.
* Dock Station now controls ORB behavior, job description, must-follow/must-not rules, greeting, voice posture, and LLM provider metadata.
* Added documentation: `docs/WEBSITE_ORB_COMMERCIAL_READINESS.md`.
* Added handoff: `docs/handoffs/HANDOFF_2026-07-30_WEBSITE_ORB_CCO_LEARNING.md`.

### Verification

* Backend focused suite passed: `12 passed`.
* Frontend `npm run typecheck` passed.
* CCO package `compileall` passed.
* CCO `demo_smoke_test.py` passed.
* Live backend probe returned `cco_trace.schema = orb_weaver.cco_runtime_trace.v1` and a real `learning_record_id`.

### Current local dev ports

* Backend API: `http://127.0.0.1:16600`
* Frontend UI: `http://127.0.0.1:16610`
* Dock Station: `http://127.0.0.1:16610/orbs/11/dock`

### Next work

1. Build owner dashboard review for Stump Ledger entries.
2. Add owner-approved promotion into Site A Priori records.
3. Wire live OpenAI/Claude/OpenAI-compatible adapters behind server-side secret handling.
4. Add production observability for answer states, CCO traces, unknown frequency, and voice latency.
5. Create a controlled-pilot sales page for Founding Website ORBS Installation.

---

## 2026-07-19 — Owner-Verified Pointer Authority Milestone

### Implemented

* Added per-target owner authority decisions for Pointer Recovery jobs. Decisions are owner-scoped, signed, persisted beside the canonical pointer map, and included in lifecycle review evidence.
* `OWNER_VERIFIED` pointers become `VERIFIED` and may point only after live DOM verification; approval explicitly grants neither click nor navigation authority.
* Owner rejection blocks pointing. A later rescan retains owner authority only when the full target identity is unchanged; missing or changed identities are preserved as inactive `DEPRECATED` audit records.
* Added route-scoped deterministic semantic intent resolution with paraphrase concepts and ambiguity rejection. Uncertain matches remain voice-only.
* Added owner pointer review controls showing route, locator, fingerprint, permissions, and a live inspection link.
* Expanded crawler extraction to include meaningful CTA links outside navigation and to use their `href` as the semantic locator. Navigation links are not duplicated as CTAs.

### Verification

* Owner-approved Map Crawl job 2 / crawl 27 captured `/` and `/investor`.
* Site Scan job 3 completed from that crawl. ORB Scan job 4 produced 147 records and correctly required Pointer Recovery.
* Pointer Recovery job 5 rendered both routes at desktop and mobile sizes. After correcting an overly broad short-label match and deterministically reconciling the original capture, 22 records were recoverable and 125 remained unresolved for review.
* Owner approval promoted `target_598ed88cc1a1`, “Join the Founding Beta →”, to `OWNER_VERIFIED` / `VERIFIED`. Its policy permits pointing after live verification and explicitly denies click and navigation.
* Three natural paraphrases resolve the owner-approved target on `/`; the same intent resolves no pointer on `/investor`. Owner authority rejects the similarly named recovered CTA as a competing semantic candidate.
* Live acceptance against the active campaign page found three global selector matches but exactly one inside `article:nth-of-type(2)`. The scoped target survived reload, scrolled into view, moved the ORB 365 px, and received the ping with zero clicks, zero navigation, and zero ORB console errors.
* Backend: 31 passed. Frontend: 8 passed; TypeScript no-emit passed; optimized production build passed.
* Loader smoke: 35 checks passed, 8 bootstrap reports, 0 console errors.

### Remaining lifecycle work

* Pointer Recovery job 5 remains `REVIEW_REQUIRED`: 21 additional recovered records still need per-target authority decisions and 125 unresolved records remain in the critical visual-review queue. This does not reduce the completed authority or acceptance of `target_598ed88cc1a1`.
* Do not promote unresolved or recovered records from runtime evidence alone. Continue with stronger intent coverage only through owner-authorized records, then rendered acquisition hardening.

## 2026-07-15 — Canonical Root Vault and Website Voice Lifecycle Repair

### Repository checkpoint

* Active development state was committed and pushed to `main` as `8802fb8` before storage consolidation began.
* Orb Weaver remains in active development and is not in release preparation.
* Development PDFs, reference records, runtime notes, scan records, and architecture documents remain intentional project material.

### Voice repair verified in development

* The root-mounted Website ORB remains `frontend/src/landing/AutonomousOrb.tsx`.
* The movement effect previously owned voice cleanup and aborted `/api/orb/website-voice` whenever `voiceState` changed.
* Voice cancellation was removed from movement-effect cleanup and placed in an unmount-only effect.
* Frontend production compilation passed.
* Frontend development server on `http://localhost:16511` compiled successfully.
* Website voice returned a spoken response on the development port. Some latency remains but the aborted-request regression is repaired.
* Docker and the public site were intentionally not rebuilt from this development change.

### Current Website ORB defects

* Weaver can enter listening, thinking, and speaking states again on the development port.
* A request to open the Circus page did not perform a verified browser navigation action.
* Weaver produced an unsupported generic description of the Circus page instead of answering only from the compiled Site World.
* The fresh Orb Weaver self-crawl and pointer map need to be loaded from canonical client storage and injected into Weaver.
* The Circus page is rejected product content and must be removed from routes, navigation, compiled Site World, and pointer data.

### Canonical storage doctrine

* The repository-root `vault_system/` is the only storage authority for Orb Weaver and the standing standard for future repositories.
* Subsystems may own source code, but they may not maintain independent databases, caches, client records, scans, crawls, Site Worlds, pointer maps, reports, posteriori memory, indexes, manifests, logs, or runtime state.
* Canonical client records live under `vault_system/clients/<domain>/`.
* Canonical SQLite databases live under `vault_system/databases/`.
* Canonical learned memory lives under `vault_system/posteriori/`.
* Canonical generated speech lives under `vault_system/runtime/tts_cache/`.
* Canonical browser-review output lives under `vault_system/runtime/browser_reviews/`.

### Storage consolidation implemented on branch

* Added `backend/app/core/storage.py` as the path authority.
* Added `ORB_WEAVER_VAULT_ROOT` and normalized legacy Windows paths so Linux cannot create folders such as `backend/R:\R_Drive_Substrate/...`.
* Updated Docker to mount only `./vault_system:/app/vault_system` for Orb Weaver storage.
* Updated database, TTS-cache, browser-review, and legacy substrate settings to resolve through the root vault.
* Promoted the real `VaultManager` to `vault_system/manager.py`.
* Removed the duplicate `Orb_Assistant/vault_system` compatibility packages;
  ORB components import the one repository-root vault directly.
* Moved the tracked a-priori seed to `vault_system/apriori/apriori_core.json` and removed duplicate tracked copies.
* Added `scripts/migrate_to_canonical_vault.py` with dry-run, apply, and finalize modes.
* Migration preserves conflicting records under `vault_system/backups/migration_conflicts/`, hash-verifies copies, writes a manifest, and installs compatibility symlinks only after verified finalization.
* Docker build context excludes live client records, databases, posteriori memory, reports, indexes, manifests, caches, and backups.

### Migration sources covered

* `backend/data/orb_weaver.db`
* `backend/data/orb_weaver_check.db`
* `backend/data/tts_cache`
* `data/tts_cache`
* `Orb_Assistant/audio_cache`
* `substrate/clients`
* malformed `backend/R:\R_Drive_Substrate/.../clients` trees
* `Orb_Assistant/vault_system/posteriori`
* `Orb_Assistant/src/vault_system/posteriori`
* `backend/report_compiler`
* root `reports`
* root and backend browser-review folders

### Required before activating the new paths

1. Review the consolidation branch diff.
2. Merge the branch as one storage commit.
3. Pull the merged commit into the WSL workspace.
4. Keep the working development frontend available until the backend migration window.
5. Stop Orb Weaver backend/Docker writers before applying or finalizing data migration.
6. Run the migration dry-run, then apply, verify, and finalize.
7. Start an isolated backend against the canonical vault and verify database, voice cache, client Site World, and pointer-map access.
8. Rebuild Docker only after isolated verification passes.

---

## 2026-07-11 — Fluid Weaver Movement, Active Pointer Guidance, Warm LLM, Dual OCR

### Doctrine confirmed

* Weaver never parks, sleeps, docks, or remains in the upper-right or any other corner.
* Weaver does not run away from the cursor.
* Movement should feel ancient, deliberate, fluid, embodied, and aware of the site it inhabits.
* Weaver remains visible and clickable/tappable while moving.

### Implemented locally

* Removed cursor-proximity avoidance from the active `AutonomousOrb` runtime.
* Replaced fast full-screen random jumps with nearby fluid drift:
  * inspection travel: 3–5 seconds,
  * transition pause: 0.12–0.48 seconds,
  * varied short/medium travel distance on every direction change,
  * local travel radius capped near 240 pixels,
  * slow easing with no forced corner destination.
* Wired the existing verified DOM target resolver into active `AutonomousOrb`.
* Active ORB now loads the compiled pointer map, matches same-route visitor intent, validates the live element, scrolls smoothly, re-validates, travels slowly, and only then displays a browser ping bloom.
* Added a development-only `orbPointerDemo` query parameter that exercises the real intent-match, verification, travel, beam, and ping sequence.
* Pointer presentation now uses the existing spinning light as the origin: the beam brightens toward the verified target, a small star-light ping fires on the target, and the beam fades. Weaver's body does not brighten.
* Local dev now requests the canonical `orbweaver.spruked.com` pointer map instead of looking for a `127.0.0.1` map.
* Missing pointer maps now return HTTP 404 instead of an erroneous HTTP 500.
* Added non-blocking Ollama startup warmup using the configured model and `LOCAL_LLM_KEEP_ALIVE`.
* Compacted and reordered the Weaver envelope so the local model prioritizes identity/tool policy over anonymous memory.
* Added an explicit memory architecture to the Weaver envelope connecting compiled site-world/SKG knowledge, authenticated bounded user memory, and a-priori/posteriori cognitive vaults. Runtime learning remains advisory and cannot override permissions or authoritative pointer records.
* Added explicit WSL website OCR and Windows app OCR capability reporting.
* Set WSL `TESSDATA_PREFIX` automatically when the installed English language data is present.
* Added `tools/check_weaver_runtime.sh` for repeatable dev backend, Ollama, WSL Tesseract, Windows Tesseract, and optional recognition-fixture checks.

### Verification completed

* Cleared a stale React Refresh bundle that referenced `playPulse` before initialization by cleanly restarting only the isolated `16610` frontend; fresh webpack compilation reports no issues.
* Backend Python compilation passed.
* Frontend TypeScript no-emit check passed.
* Optimized frontend build passed with existing/new hook dependency warnings only.
* Backend focused ORB tests: 2 passed.
* Pointer resolver tests: 2 passed—verified identity accepted and mismatched identity refused.
* Canonical pointer map: 858 records across 31 routes.
* Canonical pointer map has 858 unique target IDs and zero duplicates; current planner outcome is `pointer_plot_map=ready`, `runtime_pointer_resolver=ready`, and no repair self-scan required.
* Uncached warm local-LLM response improved from about 28 seconds to about 5.1 seconds in the sampled escalation question.
* Ollama warm status reports ready for `qwen2.5:1.5b` with 30-minute keep-alive.
* WSL Tesseract 5.5.2 and Windows Tesseract 5.5.0 both recognized the generated OCR fixture after correcting WSL tessdata discovery.
* Isolated dev remains on `16600/16610`; reviewed services remain on `16500/16510`.

### Remaining focused checks

1. Perform a human visual pass in a real browser for movement feel, clickability during travel, smooth target travel, and ping placement. Host Playwright still has no browser executable installed.
2. Tune movement timing by observation if Weaver still feels too active; do not restore cursor avoidance or any corner parking.
3. Add localized OCR fallback to pointer resolution only when semantic/content/accessibility resolution fails; never OCR-scan the full site during live guidance.

### Reviewed-site crawl diagnosis

* The reviewed backend on `16500` remained operational; it did not stop.
* Live crawl job 12 completed 23/23 pages with zero transport errors.
* The crawl-quality failure was SPA shell capture: 21 repeated page signatures, zero pointer records, and zero internal links in that crawl.
* This is the rendered-browser capture defect, not a backend outage. No live service was restarted.

### Files changed in this work

* `frontend/src/landing/AutonomousOrb.tsx`
* `frontend/src/landing/Landing.css`
* `frontend/src/services/api.ts`
* `frontend/src/orb/targetValidation.test.ts`
* `backend/main.py`
* `tools/check_weaver_runtime.sh`
* `docs/DEV_LOG.md`

---

## 2026-07-10 — Isolated Development Environment and Weaver Guiderails

### Authoritative product doctrine

* The public Website ORB is named **Weaver**.
* Weaver is a voice-first website host, consultant, guide, and explainer—not a chatbot or Desktop CALI.
* O.R.B.S. means **Origin of Reasoning Bilateral Substrate**.
* Weaver must know the compiled site-world, use only verified tools, and route directional guidance through verified pointer targets.
* Current movement doctrine has no forced parking, sleep location, corner docking, or chat-bubble parking.
* Weaver must remain visible, clickable/tappable, freely moving, and available without getting stuck.
* Pointer guidance should include a browser ping light at the verified target.

### Reviewed/persistent site protection

* Existing reviewed Docker frontend: `http://127.0.0.1:16510`
* Existing reviewed Docker backend: `http://127.0.0.1:16500`
* Do not stop, restart, rebuild, or replace these services without explicit approval.
* Do not commit, push, rebuild production images, or deploy without explicit approval.

### Isolated development instance

* Frontend dev: `http://127.0.0.1:16610`
* Backend dev: `http://127.0.0.1:16600`
* Frontend command, run from `frontend/`:
  `PORT=16610 HOST=127.0.0.1 REACT_APP_API_URL=http://127.0.0.1:16600 BROWSER=none npm start`
* Backend command, run from repository root:
  `LOCAL_LLM_URL=http://127.0.0.1:11434/api/generate LOCAL_LLM_MODEL=qwen2.5:1.5b LOCAL_LLM_NUM_CTX=4096 LOCAL_LLM_NUM_PREDICT=64 .venv/bin/uvicorn main:app --app-dir backend --host 127.0.0.1 --port 16600`
* These processes were running when this entry was written, but their status must be checked when a new session starts.

### Live request path confirmed

* Root-mounted frontend ORB: `frontend/src/landing/AutonomousOrb.tsx`
* Mounted from: `frontend/src/index.tsx`
* Voice route: `POST /api/orb/website-voice`
* Text route: `POST /api/orb/website-text`
* `WebsiteFloatingOrb.tsx` is not the root-mounted public ORB.

### Implemented locally

* Added a centralized Website Weaver operational envelope in `backend/main.py`.
* Envelope contains Weaver identity, job, current page, approved site intelligence, public capabilities, pointer policy, navigation confirmation, escalation policy, and prohibitions.
* Added a public capability registry covering website text, website voice, public Preflight, marketplace guidance, verified pointer guidance, and human escalation status.
* Human escalation is explicitly unavailable until a real public handoff endpoint exists.
* Updated [`planning/Orb_Weaver_feature_board_v2.md`](planning/Orb_Weaver_feature_board_v2.md) with O.R.B.S. architecture and current no-parking/no-sleep movement doctrine.

### Verification completed

* `backend/main.py` compiles successfully.
* Focused ORB memory/request tests: 2 passed.
* Frontend development build compiled with one existing React hook dependency warning in `AutonomousOrb.tsx`.
* Dev frontend and backend returned HTTP 200.
* Cached Website Weaver context responses work.
* Guiderail envelope and six-capability registry assemble correctly.
* Reviewed Docker services on ports `16500/16510` remained untouched.

### Open issues / next steps

1. Uncached local-LLM requests currently time out or fall back when given the full context envelope. Ollama itself responds; profile and reduce the envelope/runtime latency without weakening doctrine.
2. The prior five-minute upper-right sleep test is retired because it conflicts with the authoritative no-sleep/no-parking movement doctrine.
3. Verify smooth idle movement, interaction, pointer ping, and wake/engagement behavior with a real browser. Host Playwright currently has no installed browser executable.
4. Address the existing `AutonomousOrb.tsx` exhaustive-dependencies warning carefully.
5. Do not build a new Docker image until the uncached LLM path and focused browser tests pass.

### Working-tree caution

The repository already contained many modified and untracked files before the guiderail work. Preserve unrelated user changes and inspect overlapping diffs before editing.

---

## 2026-09-13 — Dev Landing Content Behind Weaver

* Scope: restore the real landing-page content behind Weaver in the isolated frontend only (`127.0.0.1:16667`). No production/live service, Docker configuration, deployment, commit, or push was touched.
* The dev landing composition is now the real page content plus Weaver layered above it. The existing speaker/audio control remains with Weaver.
* Verification: fresh desktop and mobile captures from `16667` show the landing hero visible behind a single Weaver; the frontend returned HTTP 200.
* Fresh-session repair: restored a short, transparent intro/splash animation around Weaver without reintroducing a page cover. The durable startup handoff now survives the event-subscription race.
* Autoplay repair: blocked autoplay now holds the fresh-session intro at the existing Weaver speaker control; it does not complete the opening or start the tour until the visitor gives that control a gesture.
* Account-session repair: `/` remains the Weaver landing surface for an authenticated current-session account, so the account still receives the intro. After the intro, the mounted host emits `landing_tour_skipped_authenticated`; unsigned visitors begin Target One. Customer tokens use `sessionStorage` only and the legacy persistent token is removed on load.
* Account-session verification on the documented runtime (`127.0.0.1:16666` → `127.0.0.1:16667`): a fresh signed-in session showed the real landing hero and emitted `INTRO_AUDIO_REQUESTED`; the signed-in completed-intro handoff emitted `landing_tour_skipped_authenticated` without `target_one_tour_controller_initialized`; the signed-out handoff emitted `target_one_tour_controller_initialized` and `tour_converse_started`. A new browser context contained neither the session token nor a seeded legacy local-storage token. Both dev endpoints returned HTTP 200.
* Login-handoff correction: a successful existing-account `/login` now routes to `/` by default, preserving Weaver's intro before the authenticated tour-skip branch. Explicit internal `?next=` routes remain honored; external values fall back to `/`. Focused `AuthPage.test.ts` coverage passed (3 tests).
* Keep this entry current for the remainder of the active Codex session. Do not expand this task beyond the landing-content restoration without new direction.

---

## 2026-09-14 — A.I.M.S. session-memory integration foundation

* Added a narrow A.I.M.S. adapter to the existing Website ORB text cognition
  path. It retains the full active visit in process-local session memory while
  sending Qwen only a relevance-selected slice for each turn.
* A.I.M.S. is advisory context only. Site World/Vault/SKG evidence, governed
  capabilities, Pointer behavior, movement, and Stage Governor authority were
  not changed.
* Responses, observed governed actions/results, and weak delivery
  `OutcomeSignal`s are recorded. Delivery alone cannot reinforce retrieval;
  later verified visitor/action evidence is the explicit reinforcement path.
* Recognized visitors can retrieve explicit prior outcome packages through a
  pseudonymous local key. Raw transcripts and active-session events are not
  persisted as durable account memory.
* GraphQLite 0.8.0 is installed as the optional derived-SKG accelerator; the
  bridge prefers it and falls back to the Python derived backend if unavailable.
* Validation: A.I.M.S. suite 20 passed, including GraphQLite replay/query;
  Website ORB bridge tests 2 passed; backend compilation and whitespace checks
  passed. Docker and public runtime were not rebuilt or restarted in this pass.

## 2026-09-14 — Canonical Nine-of-Clubs registry and contract verification

* Read the owner-supplied 50-question bank and inspected the existing journey
  stages, semantic enums, chapter/stop contracts, destination scope checks, and
  all three authored engagement questions before extending the Governor.
* Preserved the canonical source in `docs/architecture/NINE_OF_CLUBS_CANONICAL_SOURCE.md`.
  Formalized 50 selectable records with 150 semantic branches, candidate action
  mappings, dimension/stage eligibility, confidence targets, ranking weights,
  lexical slots, generation constraints, and deterministic fallback text.
* Question dimensions are separate from existing journey stages. Scan and
  configuration candidates require explicit consent; demonstration candidates
  require live verification. Candidates do not authorize execution.
* Moved the three existing two-choice questions into compatibility registry
  records without changing their IDs, wording, meaning, or route mappings.
  None is an exact three-choice-bank equivalent; related records are documented
  explicitly instead of collapsing different topologies into an alias.
* Added provider-neutral compile/classify contracts, strict branch and lexical
  checks, bounded regeneration and fallback, and selection/candidate checks in
  the existing Governor module. Covered dimensions collapse; unavailable
  candidate actions, exhausted budgets, interruptions, pending interactions,
  ambiguity, and stale question/stage/chapter/stop scopes fail closed.
* Validation: 40 tests passed across seven suites (source-bank fidelity,
  compiler/classifier rejection and fallback, selection, existing Governor,
  interaction, concept evaluator, and journey persistence). Frontend
  `npm run typecheck` passed. Provider tests use doubles; no live-model or
  browser-navigation claim is made by these results.
* The live curriculum consumes the preserved compatibility records. New bank
  scheduling, AIMS evidence/confidence updates, concrete provider adapters,
  lexical scan inputs, and single-use action execution remain runtime wiring
  work. Existing scopes lack a nonce/movement epoch; candidate evaluation is
  not an execution authorization. See `docs/architecture/NINE_OF_CLUBS_REGISTRY.md`.
* No Docker build, service restart, deployment, commit, or push occurred in
  this registry pass. Existing unrelated worktree changes were preserved.

## 2026-09-14 — Agency Envelope implementation (in progress)

* Scope follows the owner-supplied Agency Envelope specification. Extended the
  existing Governor with coherent Candidate Moves, six optional legal vectors,
  environment intersection, revision checks, explicit consequence tiers, and
  single-use issuance/consumption. The registry and journey stages remain intact.
* Connected the configured inference gateway through choose/compile/classify
  contracts. Model output selects an ID; it cannot replace the Governor's move.
* Added an agency callback to the existing tour scheduler and connected it to
  the mounted Weaver, generated voice, semantic scan records, live Pointer
  verification, and existing navigation. Added transcription-only handling for
  agency voice turns to avoid a redundant answer-generation request.
* Agency observations and inferred classifications use existing AIMS session
  evidence with explicit source labels. Browser outcomes remain browser-reported
  evidence and do not acquire server-verified status or materially reinforce
  memory merely because execution was requested.
* Clarified the operational scaling contract: site discovery is approximately
  `O(P + E)`, while candidate decision cost is `O(k)` where `k <= Kmax`; the
  active inference payload is bounded by working-state budget `B`, independent
  of accumulated Vault history. The candidate count is capped before cognition
  request construction. `Kmax`, B, and evidence caps are configurable in both
  backend and frontend runtime configuration.
* Froze the trust boundary in code and architecture: site/DOM content is
  evidence rather than authority, and model output is a candidate-ID proposal
  rather than execution authority. Execution still requires candidate validity,
  current revision, permission, policy, and live environment checks. Candidate
  schema now rejects raw selectors/coordinates and invalid enum types; a route
  also requires live target evidence.
* Added focused regression coverage for bounded Kmax/B handling, checked-out
  scan labels without permission/policy authority, expired target evidence, and
  malformed candidate identities. Validation passed: 56 frontend tests across
  nine focused suites, 12 backend Agency/A.I.M.S. tests, and frontend TypeScript
  typecheck. These are deterministic/provider-doubled checks, not a live-model
  acceptance claim. No Docker build, service restart, deployment, commit, or
  push occurred in this pass.
* Read-only availability check on 2026-09-16 found no listener on dev frontend
  `16667`, backend `16666`, or configured inference gateway `16520`. No runtime
  was restarted under this pass, so live end-to-end acceptance remains pending
  restoration of the normal development lane.
* Restarted the project normal development runtime on 2026-09-16 at owner
  request. Backend `http://127.0.0.1:16666/openapi.json` and frontend
  `http://127.0.0.1:16667` both returned HTTP 200; the frontend compiled
  successfully. Backend startup still reports unavailable local inference
  gateway `16520`, so model-backed Agency acceptance remains separately pending.
* Follow-up gateway inspection found the inference gateway running and recent
  `/api/generate` requests returning HTTP 200. Its current log has no timing
  fields, so it proves request reachability but does not yet attribute observed
  tour latency between generation, TTS, and frontend sequencing. No movement,
  Pointer/LiDAR, or Governor changes were made for this inspection.
* Timing ledger inspection provides a partial latency attribution: recent
  llama.cpp generations took 8.8–19.1 seconds for roughly 959–1,162 prompt
  tokens, while one request encountered llama.cpp HTTP 400 and then completed
  through Ollama fallback in 14.0 seconds. This explains material portions of
  the observed pause, but not a full minute by itself; TTS and continuation
  sequencing still need correlated timing before changing behavior. `llama.log`
  currently contains no additional diagnostic entries. No runtime behavior was
  changed during this inspection.
* Product-status correction: the landing splash/intro remains a required
  Website ORB experience. It is not a parked or removed feature. Its intended
  acceptance chain is visible splash/intro over the real landing page -> same
  mounted Weaver -> concurrent inference/A.I.M.S./TTS warmup -> clean governed
  tour handoff, with no duplicate ORB, idle gap, or excursion replay. This
  corrects implementation-history wording only; no startup behavior changed in
  this entry.
* Surgical hands-free conversation repair: removed click-to-talk and
  click-again-to-talk doctrine from landing copy, startup text, and
  `PRESENCE_AND_CONTROL`. The normal contract is now: speak naturally -> pause
  -> Weaver listens hands-free -> responds -> rearms, while visitor control
  remains an outcome rather than a taught click workflow. The existing optional
  runtime click/interrupt implementation was not changed.
* `PRESENCE_AND_CONTROL` now requires hands-free natural speech and visitor
  control proof; click-only or partial natural-speech excerpts cannot complete
  the stop. Removed prerecorded intro variants that contained obsolete
  question/answer chatbot wording; the remaining Kokoro intro uses the same
  hands-free contract. Added a controller regression proving
  `stop-how-to-talk` completes once and hands the next interaction to governed
  Agency selection rather than re-conversing the stop. Focused validation:
  frontend evaluator/runtime suites 10/10 passing, backend tour-evaluation
  suite 18/18 passing, and frontend TypeScript typecheck passing. No Pointer,
  movement, Governor, A.I.M.S., or Agency Envelope behavior changed.
* Added `docs/architecture/ORB_WEAVER_SALES_JOURNEY_CONTRACT.md` to reconcile
  the public commercial objective with the existing Governor/Agency/A.I.M.S./
  Site World/Pointer boundaries before another implementation pass. Direct
  source review confirms the current mismatch: the public curriculum retains
  technical `mustUnderstand` stops and Agency discovery eligibility filters
  canonical Nine-of-Clubs actions to `EXPLAIN`, although the registry contains
  verified `DEMONSTRATE` actions. The contract records this as future rewiring,
  not an implementation change; no runtime code changed in this reconciliation
  pass.
* Completed the requested read-only Track A audit in
  `docs/architecture/TRACK_A_GAP_AUDIT.md`. It traces startup through the
  public curriculum/controller, Agency candidate construction, Pointer-backed
  demonstrations/excursions, Preflight/onboarding, and commercial authority.
  It identifies the smallest coherent boundary: sales-state policy, public
  objectives, semantic-answer candidate bindings, showroom route policy, and a
  current-commercial adapter—while retaining Governor/Agency safety, A.I.M.S.,
  Site World, Pointer/LiDAR, excursion return, and lifecycle state. It also
  confirms old `$488.88 Basic Visitor ORB` material is present in compiled
  Site World/pointer artifacts and can enter Website ORB context through an
  active manufactured vault; the audit does not claim the checked-in template
  is active for the dev domain. It is therefore a conditional retrieval risk
  until commercial speech is source-isolated. No code,
  test, Docker, deployment, or data change occurred in the audit pass.
* Track A Task 1 implemented the approved public sales-state cutover only.
  `WebsiteJourneyStateV2` now carries `salesPhase` inside—not instead of—the
  existing outer lifecycle, with the complete explicit phase vocabulary
  `ORIENT -> DISCOVER -> DEMONSTRATE -> PERSONALIZE -> VALUE -> OFFER ->
  COMMERCIAL -> CLOSE`. A fresh journey begins in `LANDING_TOUR/ORIENT`; an
  older V2 record without the new field safely normalizes to `ORIENT` without
  discarding its stored lifecycle or position facts.
* The fresh public path now bypasses legacy technical controller/evaluator
  coverage: Agency performs one authorized `ORIENT` explanation from verified
  context, persists `DISCOVER` only after successful speech, then constructs a
  bounded, canonical Nine-of-Clubs question set. The orientation is an
  objective passed to live cognition, not a fixed sales script. The intro is
  reduced to a neutral welcome so it does not teach backstage mechanics before
  that governed orientation.
* Task 1 did not alter Governor legality, Agency authorization/revalidation,
  Nine-of-Clubs registry/compiler, Pointer/LiDAR, excursions, A.I.M.S.,
  hands-free runtime, Preflight, authentication, movement, Site World,
  commercial catalog/pricing, checkout, or legacy curriculum data. In
  particular, it did not widen demonstration eligibility or routing.
* Focused frontend evidence for Task 1: the journey-store, Agency-runtime,
  and Governor suites passed 22/22 tests; the new Agency test proves
  `ORIENT -> DISCOVER`, no completed technical concepts, no legacy stop
  advance, a live-cognition orientation objective rather than a fixed dialogue
  string, and a legal `NOC_*` pending question. Frontend `tsc --noEmit` also
  passed. No Docker rebuild, service restart, deployment, commit, or push was
  performed in this pass.
* Dev startup handoff repair: the explicit `?orbStartupReset=1` diagnostic
  path previously cleared only splash/first-encounter markers. It left the
  saved Website Journey in place, so a previous pending question, active
  destination, interruption, or paused state could make `runLandingTour`
  correctly refuse a supposedly fresh run. `AutonomousOrb` now boots and
  persists `createInitialJourneyState()` when that explicit dev-only query is
  present, and skips the normal migration read for that one boot. Normal
  session resume remains unchanged. Frontend TypeScript typecheck passed; no
  Docker rebuild, service restart, deployment, commit, or push was performed.
* Live dev handoff diagnosis after the splash completed without ORIENT: backend
  `16666` logs proved the startup did reach Agency candidate selection and the
  ORIENT `website-text` request, but that request returned HTTP 503. The exact
  blocker was `_first_visitor_act_response` retaining obsolete ORIENT lexical
  requirements for `speak/talk/voice` plus `pause/finish/thought`. This
  contradicted Track A Task 1, which makes ORIENT an outcome-focused product
  objective rather than interaction training. The stale lexical gate is now
  removed; generic-help rejection, live cognition, TTS availability, Agency
  authorization, and all later tour systems remain unchanged. New focused
  backend regression test passed (1/1). The running `16666` Uvicorn process is
  non-reloading and therefore still needs its normal dev-runtime reload before
  browser acceptance can observe this source change; no restart was performed
  under the Task 1 boundary.
* Task 1 refinement (2026-09-16): removed a second stale instruction in the
  actual backend generation prompt, which still mandated speech/turn-taking
  training even after the output validator was corrected. ORIENT now asks
  for concise product outcomes in natural wording; no new keyword coverage
  requirement or canned speech was introduced. The provider-boundary test
  exercises prompt construction and delivery together and confirms that an
  outcome-oriented response succeeds on its first generation. Negative tests
  retain rejection of empty/fallback cognition, generic help questions, and
  missing synthesized audio.
* Tightened the existing sales adapter: duplicate startup calls cannot reset
  the mode of a running turn; cancelled speech cannot advance the phase;
  lifecycle, route, position, interruptions and pending interactions are
  checked before recording ORIENT completion. DISCOVER is admitted only after
  the persisted phase reaches DISCOVER. Completed orientation wording joins
  the existing recent-statement window so the next question has that context.
  Governor/authorization and excursion implementations remain unchanged.
* Evidence correction to the preceding diagnosis: an access-log HTTP 503 alone
  does not identify which backend rejection occurred, and the previously
  inspected URL also contained the malformed value
  `orbDevFullTour=1orbDevFullTour=1`. The stale validator and prompt are proven
  code defects; those logs do not prove they explain every reported browser
  stop. This refinement therefore makes no live end-to-end success claim.
  Validation: 34/34 frontend tests across Agency runtime, authorization,
  excursions and journey persistence; 6/6 backend ORIENT tests; frontend
  TypeScript typecheck and `git diff --check` passed. No restart,
  Docker build, deployment, commit or push was performed.

## 2026-09-24 — Capability evidence, reports, and development runtime handoff

* Added an evidence-backed capability ledger sourced from `Orb Weaver — Master Capability List.html`. The ledger contains 22 categories and 161 atomic capabilities and is exposed in both the Crawl/Scan Capabilities tab and the Reports Complete Data Inventory tab.
* Corrected crawl completion semantics. A crawl with `status=completed` is now still reported as `BLOCKED`, `FAILED`, or `PARTIAL` when required evidence is missing. `orb_ready` is reserved for completed stage evidence with pointer verification/recovery and runtime guidance complete.
* Added bounded Playwright render diagnostics for console errors, uncaught page errors, failed requests, failed responses, mount/root text, and rendered HTML size. Renderers remain bounded and do not wait on audio, WebSockets, or site-owned tour timers.
* Added explicit authentication-boundary evidence for protected/admin routes that return a login wall. The crawler does not claim authenticated dashboard or workspace coverage without an owner-authorized session.
* Added capability coverage to the persisted client crawl pack and `website_orb_context`, so Site World consumers receive the same evidence ledger as Reports.
* Added the review packet [`docs/reference/ORB_CAPABILITY_STATUS.md`](reference/ORB_CAPABILITY_STATUS.md), including the complete capability inventory, current Crawl #4 status, remaining implementation/wiring list, and template-clone audit.
* The template validator passed with 31 routes and 858 pointer records. The template contains the compiler, validator, Site World, pointer map, runtime language, Vault/TPC material, deployment source, loader, and tests; customer packages still require fresh crawl compilation and Live Test before download/deployment.
* Restarted the isolated development runtime on backend `127.0.0.1:16666` and frontend `127.0.0.1:16667`. Both returned HTTP 200; frontend compilation completed with existing non-blocking hook warnings and no TypeScript errors. Docker was not rebuilt.
* Validation for this packet: frontend TypeScript typecheck passed; Python compilation passed; focused crawler/pointer suite passed 16/16; `git diff --check` passed; template package validation passed.
