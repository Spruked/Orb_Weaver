# Track A Sales-Journey Gap Audit

Date: 2026-09-16. Scope: read-only comparison of the live Website ORB path to [Track A Canonical Sales-Journey Contract v1](ORB_WEAVER_SALES_JOURNEY_CONTRACT.md). No runtime behavior, test, Docker, deployment, or data was changed.

## Live path traced

Fresh `/` loads `LandingPage`, begins startup readiness warmup and intro, then releases the mounted `AutonomousOrb` into `runLandingTour`. The controller verifies a curriculum DOM stop, performs a stop-mapped demonstration, asks `website-text` to satisfy every required concept, and retries twice before refusing progression. Once a stop completes, Agency constructs bounded candidates, selects a model-proposed ID, revalidates it, and can speak, ask a registry question, guide to a verified target, or navigate through an excursion contract. Preflight/onboarding remain separate lifecycle paths.

## Retain

| Mechanism | Exact evidence | Contract fit |
| --- | --- | --- |
| Startup intro and same mounted Weaver | `frontend/src/landing/LandingPage.tsx:60-125`, `AutonomousOrb.tsx:1892-1941` | Correct Orient substrate; concise sales orientation must replace only its public objective. |
| Governor route/state authority | `frontend/src/tour/governor.ts:1-115,170-295` | Retain all scoped legality, revision, candidate validation, and single-use authorization. |
| Agency execution safety and excursion return | `frontend/src/tour/agencyRuntime.ts:200-300` | Retain revalidation, Pointer proof, observation, and return/resume mechanics. |
| Nine-of-Clubs canonical actions | `frontend/src/tour/discovery/registry.ts:13-47`; `patterns.json` contains `DEMONSTRATE` and `REVIEW_COMMERCIAL_FIT` | Retain discovery semantics and candidate-action data. |
| A.I.M.S. evidence/outcome role | `backend/app/orb/agency_cognition.py` | Retain as backstage context/outcome memory; it is not the stage director. |
| Approved commercial catalog authority | `backend/app/orbs_governor.py:200-206,402-408,539-570` | Retain as the source of current approved public product/price data. |

## Rewire

| Contract gap | Exact responsible code/state transition | Smallest coherent change |
| --- | --- | --- |
| No public sales-state policy | `TourJourneyStage` has only `LANDING_TOUR`, `PREFLIGHT`, `ONBOARDING`, `PRODUCTION_SCAN` in `frontend/src/state/tourControllerStore.ts:3-7`. | Layer ORIENT through CLOSE policy over existing lifecycle state; do not replace lifecycle stages. |
| Linear technical curriculum controls tour | `LANDING_TOUR_CHAPTERS` in `frontend/src/tour/curriculum.ts`; controller loop `controller.ts:37-120`. Chapters include technical 28-Weave and pointer concepts. | Replace mandatory public technical stops with concise ORIENT then governed sales objectives; preserve an explicitly requested technical route separately. |
| Coverage evidence can block progression | `controller.ts:44-63` retries a stop twice, then throws when required concepts remain; `AutonomousOrb.tsx:1980-2024` explicitly asks for curriculum concepts/excerpts. | Remove technical-concept coverage as the public progression gate; use sales-state completion and governed interaction evidence instead. |
| Demonstration actions filtered from discovery eligibility | `agencyRuntime.ts:79-82` admits only `candidateAction.kind === 'EXPLAIN'`, while registry supports `DEMONSTRATE`. | Build approved discovery action availability from current semantic answer, sales state, live target proof, and policy—not only EXPLAIN. |
| Generic demonstrations are unconnected to visitor need | `agencyRuntime.ts:111-132` creates candidates from every verified current-route pointer; semantic question answers only update confidence at `85-89`. | Bind demonstration candidates to the classified Nine-of-Clubs answer and selected sales objective before bounded ranking. |
| Public candidate families lack value/offer/commercial moves | Current bindings are explain/question/demo/navigation at `agencyRuntime.ts:101-132`; environment permits only `OBSERVE` and `NAVIGATE` at `77`. | Add PERSONALIZE, ESTABLISH_VALUE, MATCH_OFFER, COMMERCIAL, and CLOSE bindings only where existing current authority makes them legal. Do not expose PREPARE/COMMIT without their real executors. |
| Showroom routing is legacy-branch limited | `legalTourNavigationRoutes` in `governor.ts:38-42` returns routes from three legacy landing branches; navigation then requires that list at `agencyRuntime.ts:124-132`. | Extend route policy from current sales stage/answer to legal showroom resources, preserving Governor ownership and live route/target checks. |
| Preflight is terminal technical curriculum | `curriculum.ts:218-268` forces a final Preflight decision chapter. | Make Preflight one governed CLOSE option when justified, not the compulsory conclusion of every visitor tour. |

## Retire or disconnect after replacement is live

Do not delete the Governor, Agency, Pointer/LiDAR, A.I.M.S., Nine-of-Clubs, or marketplace governor. Disconnect the mandatory technical chapter traversal and coverage-driven repetition from the primary public path after sales objectives replace it. Preserve that material only for an explicitly requested technical education route.

## Stale-data cleanup and reachability

Historical `Basic Visitor ORB` and `$488.88` data exists in `manufacturing/templates/Website_Orb_Final/compiled_orb/latest_context.json`, `site_world.json`, and `pointer_plot_map.json`. `backend/main.py:8128-8147` loads a delivery-ready manufactured vault's `payload/site_world.json` over fresh crawl context, and `8212-8242` passes a compact Site World slice into tour articulation. This is a code-path reachability risk: an active manufactured vault containing that data can influence public tour context unless commercial speech is explicitly isolated from it. This audit does **not** prove that the checked-in template itself is the active vault for `orbweaver.spruked.com`; `_fresh_runtime_website_context` normally selects the configured/latest completed database crawl at `4671-4716`.

The separate authoritative current source exists in `orbs_governor.py` and filters marketplace products to active, public, approved Website ORBs. The public Agency runtime does not currently bind/query that source for commercial moves. Therefore stale artifacts should remain provenance-only, and a future commercial adapter must source price/name/scope exclusively from the approved catalog before any public COMMERCIAL/CLOSE speech or action.

No deletion is justified in this audit: first block historical commercial facts from current commercial retrieval, then test the authoritative replacement.

## Proposed Track A change boundary

One coherent implementation pass may change only public sales-state policy, public curriculum/objectives, semantic-answer-to-candidate bindings, legal showroom-resource policy, and a read-only current-commercial adapter. It must retain Governor safety, Agency authorization, A.I.M.S., Site World, Pointer/LiDAR, existing excursion return, and lifecycle stages. Track B A.I.M.S. hardening remains separate.

## Acceptance tests for that future pass

1. Fresh visitor: intro -> concise ORIENT -> one relevant Nine-of-Clubs question, without technical coverage lecture.
2. Conversion/navigation/support answer produces bounded legal candidates including a verified relevant demonstration when available.
3. Demonstration revalidates Pointer/live target, returns/resumes, then connects outcome to stated visitor need.
4. Follow-up question narrows sales fit without replaying a linear technical chapter.
5. Commercial response reads only active/public/approved catalog data; injected `$488.88 Basic Visitor ORB` Site World data cannot appear as a current offer.
6. Preflight, purchase, and onboarding appear only when their existing Governor conditions and confirmations permit them.
7. Existing stale-revision, token, target-disappearance, route-away/back, and session-memory tests continue to pass.
