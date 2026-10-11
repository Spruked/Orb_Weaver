# Web-TAMP Compliance Audit — Orb Weaver + Website_Orb_Final template

Date: 2026-10-10. Method: static structural inspection (file sizes, function maps,
grep for stores and call sites, architecture docs, one real crawl artifact for
pops.spruked.com). No code was executed or changed. Line numbers refer to the repo
as of this date. Scores are judgment calls against the locked architecture
(0 = no resemblance, 10 = compliant), not measurements.

Locked architecture under test: Task Layer / Harvest layer / World Model (single
source of truth) / Planner / ORB as brain.

## Headline

The system is a capable, well-evidenced **pipeline**, not a Web-TAMP system.
The three layers do not exist as separable things. They are fused inside
`backend/main.py` (13,809 lines, 129 routes). The conceptual pieces are present
(a graph, stage tracking, fail-closed approvals, a diff engine) but each is an
isolated island. Migration is feasible without a rewrite if the order below is
followed, because most harvest code is already file-in/file-out.

## Compliance by component

| Component | Score | One-line reason |
|---|---|---|
| `backend/main.py` orchestration | 1/10 | Task, plan, harvest dispatch, state writes and HTTP API in one file |
| `app/crawler/engine.py` (harvest) | 4/10 | Clean-ish fetch/parse, but owns traversal decisions and interpretation |
| Storage / world state | 3/10 | Four overlapping stores, heavy duplication, no single authority |
| Task layer | 0/10 | Does not exist |
| Planner | 1/10 | Only `_planned_tool_calls`, a static rule list, not a planner |
| Approval / governance | 5/10 | Strong fail-closed pieces, but scattered across five places |
| `app/dandy` pack | 6/10 | Isolated module, non-blocking, fail-closed approval; wired through main.py |
| `orbs_governor.py` | 6/10 for its job | Good snapshot/allowed_actions/idempotency pattern, but it governs the sales/onboarding state machine, not harvest |
| `motion_runtime` | 4/10 | Mixes crawl-time capture with visitor-time actuation under one name |
| Template `Website_Orb_Final` | 5/10 | Disciplined single-vault consumer; not a brain; duplicates pointer code |

## Findings

### BLOCKING

**B1. The monolith fuses every layer.**
`backend/main.py` holds crawl job orchestration (`run_crawl_job` 7843,
`preserve_client_crawl_intelligence` 6428), pack building, pointer authority
decisions (12152), lifecycle (8221), audit (8792), marketplace, TTS and 129 HTTP
routes. `backend/app/routers/` and `backend/app/api/` exist and contain 0 lines,
so an intended split was never done. Nothing can be moved to a clean boundary
until the orchestration is extracted.

**B2. There is no Task Layer.**
No goal objects, decomposition, success criteria or coverage targets exist as
data. Goals appear only as crawl config (`max_pages`, `max_depth`, `tier`).
Coverage is *reported after the fact* (`capability_coverage`,
`scan_assembly_status`) instead of *driving* what to do next.

**B3. The "planner" is not a planner.**
`_planned_tool_calls` (main.py:7160) returns a fixed list with `if` rules over a
finished crawl's `pointer_summary` and is embedded in reports. It plans
*runtime tools for the visitor ORB*, not harvest primitives, and it runs after
harvest. `run_crawl_job` is a hard-coded sequence of 26 stages
(`scan_stage_execution`); it does not replan on failure, cost or value of
information. The stage list is a good seed for a task/plan trace, nothing more.

**B4. World Model is not the single source of truth.**
State lives in at least four places:
1. SQL database: `Project`, `CrawlJob`, `CrawledPage`, `ReviewItem`, `OrbToolCache`, build-order and entitlement tables.
2. Per-client JSON files under `vault_system/clients/<domain>/`: written by 46 `_write_json` call sites in main.py: `latest`, `history`, `crawl_<id>`, pointer maps, `website_orb_context`, dandy packs, claims, recommendations, mail/CRM stubs.
3. Template `compiled_orb/*.json` (`site_world`, `pointer_plot_map`, `tool_cache`).
4. In-memory resident runtime in the template.

The same facts are duplicated: `knowledge_graph` (524 nodes / 1363 edges),
`authority_flow`, `competitor_gap`, `capability_coverage` and `page_knowledge`
appear in both the crawl blob and `website_orb_context`. A graph exists, but it
is a derived artifact, not the authority.

**B5. No registered harvest primitives.**
There is no primitive interface (name, preconditions, effects, cost, risk,
idempotency). Harvest capability is: one aiohttp crawler class, a separate Node
render script, a separate Node pointer-capture script, lifecycle jobs and audit
jobs, each invoked ad hoc from main.py. The planner cannot enumerate or choose
among them because they are not registered anywhere.

**B6. Doctrine conflict: "ORB owns approval authority" vs. the existing locked rules.**
`docs/ORBS_STAGE_GOVERNOR_CONTRACTS.md` says its contracts "do not grant the
ORB, frontend, or a language model transition authority"; the Dandy rule is that
neither system grants itself the other's authority; `AGENTS.md` makes the
embodied ORB a website host. Web-TAMP as written has the ORB enforce approval.
These cannot all be literally true. This needs an explicit amendment (see
Decisions) *before* code moves, or the migration will bake in a contradiction.

### IMPORTANT

**I1. Harvest contains interpretation and traversal decisions.**
`engine.py:1045` recurses into links (`_crawl_page(link, depth+1)`), so frontier
and depth policy are decided inside the harvester. Line 676 classifies
"products" with a regex over words like `Plan|Pro|App|Service|System`, which is
exactly why the pops.spruked.com catalog contains junk such as "Service" and
"Presence System Enter Pops". It also calls a local LLM for entities (line 697).
Harvest should emit raw observations with provenance; classification belongs to
a derivation step that writes to the World Model.

**I2. Inverted dependency.**
`crawler/engine.py` imports from `motion_runtime.server.*` (tesseract weave,
pointer plot). The harvester depends on the "runtime".

**I3. "Motion" is overloaded.**
Web-TAMP's Harvest/Motion = world-changing primitives. In this repo
`motion_runtime` = visitor-facing pointer movement and spatial guidance, and
also contains crawl-time capture (`pointer_recovery_capture.js`). Rename or
split to avoid a permanent naming trap.

**I4. Approval is scattered.**
`ReviewItem` (DB), `owner_approval` in the Dandy pack JSON,
`decide_pointer_authority` (main.py:12152), `_governance_delivery_approved`
(4531), empty `approved_claims/` and `banned_claims/` directories,
`owner_seed_changes/`. No single Operational/Approval layer. Good patterns to
promote: Dandy's `build_approved_dandy_payload` (fails closed) and
`orbs_governor` (versioned snapshot, `allowed_actions`, idempotency keys).

**I5. Temporal layer is embryonic.**
Page-level `historical`/`trend_model` exist in the crawl. Target-level diffing
lives in the *template* (`runtime/field_maintenance.py`, 577 lines,
`FieldMaintenanceEngine`, own store). That is the right primitive in the wrong
place, with a private store.

**I6. Visual-spatial layer missing as data.**
Geometry, accessibility, hit-test and OCR evidence are not world-model fields
(see `SENSOR_FUSION_GAP_ANALYSIS.md`). The locked architecture requires this layer.

**I7. Template is a consumer, not a brain.**
`Website_Orb_Final` precompiles `site_world.json` and answers by dictionary
lookup. This is sound for a fast visitor runtime and its storage module
(`backend/storage.py`) already enforces the right principle (single canonical
vault, refuses to create a fallback store). But it has no Task layer or
Planner, and copies pointer code (`frontend/src/pointer/*`) that also lives in
`motion_runtime/client/pointer`, so drift is likely.

### CLEANUP

- `scan_stage_execution`, `assembly_status` and `capability_coverage` overlap; consolidate into one execution trace in the World Model.
- Duplicate pointer implementations (template vs `motion_runtime`).
- Two Playwright capture scripts to merge behind one primitive.
- Hard-coded confidence constants in `orbital_behavior_skg/index.ts`.
- Empty `routers/`, `api/` directories: either use or delete.

## What already fits (do not rewrite)

- Dandy pack: isolated, failure-isolated, fail-closed approval gate.
- `orbs_governor` snapshot/action/idempotency contract style.
- Template storage rule: one vault, no fallback store.
- `knowledge_graph` generation, `field_maintenance` diffing, `scan_stage_execution` stage ids: seeds for World Model, Temporal layer and plan trace.
- Provenance culture (source URLs, timestamps, schema ids) already common in artifacts.

## Decisions needed from the owner before migration

1. **Authority model.** Does the ORB *hold* the World Model and *propose* actions while Weaver's governor remains the only authority that approves/transitions? (Recommended: yes. Keeps existing locked contracts, and satisfies "enforces boundaries" via a governor the ORB cannot override.) Or does Web-TAMP formally supersede the stage-governor rule? That would be a contract amendment.
2. **Where the Planner runs.** Factory side (Orb Weaver, plans scans/builds) and/or inside the deployed Website ORB (plans visitor guidance)? The two have different task domains. Recommended: one Planner library, two task domains, same World Model schema.
3. **Naming.** Rename crawl-time `motion_runtime` parts to `harvest`; keep `motion_runtime` for visitor actuation.

## Suggested migration order (each step shippable, nothing big-bang)

0. Write contracts only: `Task`, `HarvestPrimitive`, `WorldModel` (layered), `Plan`/trace schemas, plus the authority amendment. No code moved.
1. **World Model facade.** One repository interface that reads/writes by layer, backed initially by the existing DB and files. Route all 46 `_write_json` sites and pack readers through it. No data migration yet; this stops the sprawl.
2. **Extract primitives.** Wrap crawl-fetch, render, pointer-capture, audit, diff as registered primitives with declared inputs/outputs/effects/risk. Move link recursion out of `engine.py` (it returns discovered URLs; the planner decides). Move product/entity classification out into a derivation step.
3. **Minimal Planner + Task layer** replacing the fixed `run_crawl_job` sequence and `_planned_tool_calls`. Start with one task domain, "map this site to coverage target X", with replanning on failure.
4. **Unify approval** into the World Model's Operational layer; Dandy and pointer authority read from it.
5. **Break up `main.py`** into routers on top of the stable boundaries (the empty `routers/` dir is the target).
6. **Visual-spatial and temporal layers**: the sensor-fusion primitives (CDP snapshot, AX tree, rects, OCR, interaction probes) land as new primitives plus a new layer, no core changes.
7. **Template**: consume a World Model export, delete the duplicated pointer code, move target diffing to the shared Temporal layer.

## Limits of this audit

Structural and grep-based. I did not read every function, run the tests, or
trace data flow end to end. Scores are subjective. Findings B4 and I4 should be
confirmed by enumerating every reader and writer of each store before step 1.
