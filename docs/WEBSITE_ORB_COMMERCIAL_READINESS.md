# Website ORB Commercial Readiness

Date: 2026-07-30

## Current Sellability

The Website ORB is ready to sell as a controlled, white-glove pilot installation.
It is not ready for broad self-serve SaaS sales.

The truthful offer is:

> We install a site-specific Website ORB that guides visitors, answers from verified site knowledge, records unanswered questions, and improves through owner-approved learning.

## What Is Sellable Now

- Live Website ORB runtime exists.
- Dock Station exists for owner policy controls.
- Owner can configure ORB behavior, greeting posture, voice defaults, job description, must-follow rules, must-not rules, and LLM provider metadata.
- Local Ollama model selection is supported.
- OpenAI, Claude, and OpenAI-compatible providers can be selected as policy metadata with server-side environment variable references.
- Website ORB answers are classified as `known`, `resolved`, `clarification_required`, or `unknown`.
- Site-specific posteriori interaction records are written into the canonical Vault.
- Unknown answers enter the site-specific Stump Ledger.
- Verified posteriori cases can be reused through a deterministic `resolved` path.
- CCO is active in the Website ORB answer path and returns an auditable `cco_trace`.
- Downloadable ORB packs include a clean-slate `website_orb_learning/` template.

## What Must Not Be Promised Yet

- Fully autonomous no-click microphone startup. Browsers still enforce microphone/audio permission rules.
- Fully wired GPT/Claude live runtime adapters. The Dock can configure provider policy, but the live adapter path is not complete.
- Self-serve customer onboarding without supervised installation.
- Owner dashboard promotion workflow for Stump Ledger review.
- Production-grade monitoring, billing, support, rollback, and release automation.
- Broad claims that the ORB is unstumpable or self-learning without governance.

## Core Runtime Doctrine

The Website ORB does not learn by believing its own answers.

It learns by:

1. preserving site-grounded interactions;
2. measuring answer state and outcome;
3. identifying knowledge gaps;
4. placing unresolved questions into owner review;
5. promoting only verified resolutions into authoritative Site World.

The loop is:

```text
visitor query
-> task profile
-> site-scoped retrieval
-> compact evidence package
-> correspondence evaluation
-> justified answer state
-> articulation
-> posteriori outcome recording
-> Stump Ledger or verified-case reuse
-> owner-approved promotion
```

## CCO Runtime Trace

CCO means **Context & Correspondence Orchestrator**.

The active package path is:

```text
Orb_Assistant/context_correspondence_orchestrator/
```

The CCO public names are:

```python
ContextCorrespondenceOrchestrator
OrchestrationMetadata
CCOConfig
```

The live Website ORB response includes:

```json
{
  "cco_trace": {
    "schema": "orb_weaver.cco_runtime_trace.v1",
    "short_name": "CCO",
    "site_id": "...",
    "domain": "...",
    "task_profile": {},
    "selected_strategy": "vault_compile",
    "token_budget": 1200,
    "evidence_package": {
      "package_hash": "...",
      "original_tokens": 0,
      "context_tokens": 0,
      "retrieved_fact_ids": []
    },
    "correspondence_result": {
      "status": "supported|gap_detected",
      "answer_state": "known|resolved|clarification_required|unknown",
      "requires_owner_review": false
    },
    "articulation": {
      "llm_source": "..."
    },
    "write_back": {
      "posteriori_recorded": true,
      "learning_record_id": "...",
      "promotion_directly_allowed": false
    }
  }
}
```

Compatibility fields such as `crystal_tokens` and `crystal_data` remain inside the CCO package for existing storage/API stability. They are not the architectural name.

## Site-Scoped Learning Vault

Each Website ORB uses only its own site namespace:

```text
vault_system/clients/<domain>/website_orb_learning/
  learning-loop-template.json
  posteriori/interactions.jsonl
  stump_ledger/stump-ledger.json
  promotion_queue/promotion-queue.json
  verified_cases.json
  apriori-promotion-template.json
```

No cross-customer learning and no shared visitor data are allowed.

## Clean-Slate ORB Pack Template

Every future downloadable `.orbpack` includes the same site-scoped learning template. This is generated from:

```text
backend/app/pack_generator/generator.py
backend/app/orb/site_learning.py
```

The pack template does not contain customer-shared knowledge. It provides empty governed files for the site being installed.

## Current Local Dev Ports

Current persistent local development ports used during the July 30 work:

```text
Backend API: http://127.0.0.1:16600
Frontend UI: http://127.0.0.1:16610
Dock Station: http://127.0.0.1:16610/orbs/11/dock
```

These ports were intentionally isolated from the reviewed `16500/16510` pair.

## Verification Commands

The last focused verification passed with:

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

Frontend typecheck also passed:

```bash
cd frontend
npm run typecheck
```

## Next Commercial Milestones

1. Add owner dashboard review for Stump Ledger entries.
2. Add promotion actions that convert owner-approved answers into verified Site A Priori records.
3. Wire live OpenAI/Claude/OpenAI-compatible runtime adapters behind server-side secret handling.
4. Add production observability for CCO trace, TTS/STT latency, answer state distribution, and unknown-question frequency.
5. Add a release/rollback process for customer ORB installations.
6. Create a sales-facing “Founding Website ORBS Installation” offer page with careful promise boundaries.
