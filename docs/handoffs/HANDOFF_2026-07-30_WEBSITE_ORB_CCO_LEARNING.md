# Handoff: Website ORB CCO Runtime + Site Learning Loop

Date: 2026-07-30

## Resume Prompt

Use this if the session is reloaded:

> Continue from `/home/bryan/projects/Orb_Weaver`. Read `README.md`, `docs/WEBSITE_ORB_COMMERCIAL_READINESS.md`, and `docs/handoffs/HANDOFF_2026-07-30_WEBSITE_ORB_CCO_LEARNING.md` first. Preserve existing user changes. The Website ORB is sellable only as a controlled white-glove pilot, not broad self-serve SaaS. Next work should focus on owner Stump Ledger review/promotion, production adapters, or release hardening.

## Current Commercial Answer

The ORB is ready to sell as a controlled pilot installation.

It is not ready for broad self-serve sales yet.

Use this truthful offer language:

> We install a site-specific Website ORB that guides visitors, answers from verified site knowledge, records unanswered questions, and improves through owner-approved learning.

Do not promise:

- fully autonomous no-click browser microphone activation;
- complete live GPT/Claude adapter switching;
- unsupervised customer self-install;
- automatic self-promotion of runtime answers into trusted Site World;
- unstumpable behavior.

## Current Persistent Dev App

As of this handoff, the intended local dev ports are:

```text
Backend API: http://127.0.0.1:16600
Frontend UI: http://127.0.0.1:16610
Dock Station: http://127.0.0.1:16610/orbs/11/dock
```

The most recent backend process was started with:

```bash
PYTHONPATH=/home/bryan/projects/Orb_Weaver/backend \
/home/bryan/projects/Orb_Weaver/.venv/bin/python -m uvicorn main:app \
  --host 0.0.0.0 --port 16600
```

The frontend dev server remained live on `16610` with:

```bash
PORT=16610 HOST=0.0.0.0 BROWSER=none \
REACT_APP_API_URL=http://127.0.0.1:16600 npm start
```

If these are no longer running, restart them rather than using the reviewed `16500/16510` pair unless the user asks.

## Work Completed

### Dock Station behavior and model policy

Files:

```text
frontend/src/pages/OrbDockStation.tsx
frontend/src/services/api.ts
backend/app/orb_dock.py
backend/main.py
```

Added owner-editable ORB behavior policy:

- tone;
- response style;
- startup greeting;
- auto listening;
- voice-only;
- mute/sleep defaults;
- greeting script;
- job description;
- persona notes;
- must-follow rules;
- must-not rules;
- prohibited tone.

Expanded LLM provider policy:

- runtime default;
- local Ollama;
- OpenAI API;
- Claude API;
- OpenAI-compatible API.

Important boundary: OpenAI/Claude are policy metadata only at this point. Live adapter execution is not finished. API key values must remain server-side, referenced by env var names such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

### Site-scoped Website ORB learning loop

Files:

```text
backend/app/orb/site_learning.py
backend/main.py
backend/app/pack_generator/generator.py
backend/tests/test_orb_site_learning.py
backend/tests/test_pack_single_vault.py
```

Added site-scoped learning-vault records under:

```text
vault_system/clients/<domain>/website_orb_learning/
```

Runtime answer states:

```text
known
resolved
clarification_required
unknown
```

Unknown answers are now governed outcomes and enter the site-specific Stump Ledger.

Verified posteriori cases can be reused through deterministic `resolved` path via `verified_cases.json`.

Raw visitor conversations are not stored as reusable knowledge. The interaction recorder sanitizes emails, phone numbers, SSN-like values, and card-like values.

### Clean-slate downloadable ORB template

Every generated `.orbpack` now includes:

```text
website_orb_learning/learning-loop-template.json
website_orb_learning/posteriori/interactions.jsonl
website_orb_learning/stump_ledger/stump-ledger.json
website_orb_learning/promotion_queue/promotion-queue.json
website_orb_learning/verified_cases.json
website_orb_learning/apriori-promotion-template.json
```

This is site-specific and empty at package generation. It is not shared learning.

### CCO rename

Old local folder:

```text
Orb_Assistant/Context_Coresspondance_Orchestration
```

New folder:

```text
Orb_Assistant/context_correspondence_orchestrator
```

Inner Python package:

```text
Orb_Assistant/context_correspondence_orchestrator/context_correspondence_orchestrator
```

Public names:

```python
ContextCorrespondenceOrchestrator
OrchestrationMetadata
CCOConfig
```

Compatibility fields such as `crystal_tokens` and `crystal_data` remain intentionally to avoid breaking storage/API consumers.

### CCO active in live Website ORB path

Files:

```text
backend/app/orb/cco_runtime.py
backend/main.py
backend/tests/test_orb_loader_runtime.py
```

Website ORB text and voice responses now include:

```text
cco_trace
```

Trace schema:

```text
orb_weaver.cco_runtime_trace.v1
```

The trace includes:

- site ID;
- domain;
- target URL;
- route;
- task profile;
- selected strategy;
- token budget;
- evidence package hash;
- original/context token counts;
- retrieved fact IDs;
- source namespaces;
- correspondence result;
- answer state;
- articulation source;
- posteriori write-back status;
- learning record ID.

The accepted runtime flow is now:

```text
visitor request
-> task profile
-> site-scoped retrieval
-> compact evidence package
-> correspondence evaluation
-> justified answer state
-> articulation
-> posteriori outcome recording
```

## Verification Completed

Backend focused suite:

```bash
/home/bryan/projects/Orb_Weaver/.venv/bin/python -m pytest \
  backend/tests/test_orb_loader_runtime.py \
  backend/tests/test_orb_site_learning.py \
  backend/tests/test_pack_single_vault.py \
  backend/tests/test_orb_dock.py -q
```

Result:

```text
12 passed
```

Frontend:

```bash
cd frontend
npm run typecheck
```

Result: passed.

CCO package checks:

```bash
/home/bryan/projects/Orb_Weaver/.venv/bin/python -m compileall \
  Orb_Assistant/context_correspondence_orchestrator
```

and:

```bash
cd Orb_Assistant/context_correspondence_orchestrator
/home/bryan/projects/Orb_Weaver/.venv/bin/python demo_smoke_test.py
```

Both passed.

Live backend probe after restart returned a real `cco_trace` and `learning_record_id`.

## Important Dirty Worktree Note

The repo is intentionally dirty. Do not revert unrelated files.

Known current modified/untracked areas include:

```text
.vscode/settings.json
backend/app/core/config.py
backend/app/orb_dock.py
backend/app/pack_generator/generator.py
backend/main.py
backend/app/orb/cco_runtime.py
backend/app/orb/site_learning.py
backend/tests/test_orb_loader_runtime.py
backend/tests/test_orb_site_learning.py
backend/tests/test_pack_single_vault.py
frontend/src/landing/AutonomousOrb.tsx
frontend/src/landing/Landing.css
frontend/src/pages/OrbDockStation.tsx
frontend/src/services/api.ts
Orb_Assistant/context_correspondence_orchestrator/
docs/WEBSITE_ORB_COMMERCIAL_READINESS.md
docs/handoffs/HANDOFF_2026-07-30_WEBSITE_ORB_CCO_LEARNING.md
```

Also present as user/generated untracked files:

```text
docs/Orb_Weaver_Intro_Greetings.pdf
frontend/src/assets/ORBexamplesskins.jpg
```

## Next Best Work

1. Build owner dashboard review for Stump Ledger entries.
2. Add promotion endpoint/actions that convert owner-approved answers into verified Site A Priori entries.
3. Wire live OpenAI/Claude/OpenAI-compatible adapters behind server-side secret handling.
4. Add observability: answer-state counts, CCO trace counts, unknown-question frequency, TTS/STT latency, and provider failure rates.
5. Harden customer ORB package install/release/rollback.
6. Add a sales-facing Founding Website ORBS Installation page with controlled-pilot promise boundaries.

## Safety Notes

- Do not claim this is broad self-serve ready.
- Do not claim browser voice permission can be bypassed.
- Do not put API secrets into frontend config.
- Do not promote posteriori records into trusted Site World without owner approval or a defined low-risk promotion gate.
- Do not treat old `WebsiteFloatingOrb.tsx` as the active landing ORB unless browser initiator evidence proves it is mounted.
