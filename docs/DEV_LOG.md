# Orb Weaver Development Log

Purpose: preserve implementation context, decisions, verification results, and next steps between development sessions.

Update this file after meaningful code, configuration, runtime, testing, or doctrine changes. Keep entries concise and newest-first. Never record credentials or secrets.

---

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
