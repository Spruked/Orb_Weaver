# Orb Weaver Documentation Authority

## Purpose

This file prevents historical snapshots, future-product designs, and current
operations from being treated as interchangeable implementation instructions.
When documents conflict, the newest applicable item in the following order
governs: release evidence, canonical doctrine/contracts, current operations,
then history or future design.

## Current release authority

- `planning/Orb_Weaver_Web_Weaver_90_Day_Launch_Command_Sheet_RELEASE_EVIDENCE_REVISION_2026-09-11.docx`
  and its PDF counterpart govern the fixed Day-90 schedule and gate approval.
- `DEV_LOG.md` records dated implementation and verification evidence. It does
  not approve a release by itself.
- An RC passes a gate only when current, reproducible evidence exists for that
  identified RC. Historical/component proof is progress evidence, not release
  approval.

## Authority classes

| Class | Use | Current documents |
| --- | --- | --- |
| Canonical doctrine | Rules the code and product must obey | `ORB_WEAVER_V1_TRANSACTIONAL_DOCTRINE.md`, `ORBS_STAGE_GOVERNOR_CONTRACTS.md`, `INTELLIGENCE_PRESERVATION.md`, Corpus/Recompile architecture |
| Current operations | How the repository runs today | `operations/DEVELOPMENT_RUNTIME.md`, `DEPLOYMENT_ORB_WEAVER_SPRUKED.md`, `TOOLS_WIRING.md`, `DEV_LOG.md` |
| Contracts | Storage and package interfaces | `PACK_CONTRACT_V0_1.md` and `vault_system/schemas/` |
| Acceptance and evidence | What must be demonstrated | the launch command sheet and `TARGET_ONE_LANDING_TOUR.md` |
| History or future | Valuable context; never current execution instruction | dated checkpoints, prior gold masters, legacy prompts, tree snapshots, Desktop/productization material |

## Historical and future material

The following remain retained for provenance but are not current implementation
authority: `IMPLEMENTATION_CHECKPOINT_2026-07-20.md`,
`WEBSITE_ORB_COMMERCIAL_READINESS.md`,
`WEBSITE_ORB_GOLD_MASTER_MIGRATION_SOURCE.md`, `PERPLEXITY.MD`,
`journey_002.md`, reference tree dumps, and Desktop/Dock strategy material.

`STANDARD_WEBSITE_ORB_REBUILD_PROMPT.md` is quarantined pending regeneration
from a rewritten current Website ORB blueprint. Do not feed it to an agent as
an implementation prompt.

Historical documents must retain their dates and original claims. Do not edit
them to imply current proof. Their links and physical archive locations may be
updated in a dedicated migration after all incoming references are mapped.

## Current runtime facts

- Isolated development: backend `16666`, frontend `16667`.
- Reviewed Docker/public runtime: backend `16500`, frontend `16510`.
- Persistent intelligence and governed runtime records live only under the
  canonical repository-root `vault_system/`.
- Disposable local development state belongs outside the tracked worktree.

