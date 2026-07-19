# Orb Weaver Development Log

Purpose: preserve implementation context, decisions, verification results, and next steps between development sessions.

Update this file after meaningful code, configuration, runtime, testing, or doctrine changes. Keep entries concise and newest-first. Never record credentials or secrets.

---

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
