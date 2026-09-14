# Agency Envelope handoff — 2026-09-14

This file is the current handoff for the in-progress Website ORB Agency Envelope work on branch `development/startup-account-session-16667`.

Historical development-log entries that say `127.0.0.1:16520` is unavailable describe earlier observations. They are not the current service state.

## Current service boundary

Development remains isolated to:

- frontend: `127.0.0.1:16667`
- backend: `127.0.0.1:16666`
- inference gateway expected by the backend: `127.0.0.1:16520`

The current inference gateway has been re-established for the development session and verified through:

- `GET /health/live` -> live
- `GET /health/ready` -> `ready: true`
- `llamacpp` provider -> ready, Qwen 2.5 1.5B Instruct Q4_K_M through the existing host llama.cpp service on port 8080
- `ollama` provider -> ready after restoring container-to-host reachability

Aphrodite and TensorRT adapters remain architectural provider lanes but are not installed/running on this non-NVIDIA development host. Their absence is not an Agency acceptance blocker.

The present `16520` and Ollama host/container reachability repairs use temporary relays and therefore are development-session infrastructure, not the permanent deployment design. Do not rebuild Docker merely to replace those relays while the current Agency work is being accepted.

## Checkpoint lineage

Owner checkpoints:

- `50bdd49` — Agency Envelope cognition work
- `8e98031` — Agency dependencies, A.I.M.S. memory, discovery registry

Continuation commits add:

- bounded browser-session Agency cache;
- governed cross-page excursion return/resume;
- excursion/cache focused tests;
- consistent backend UTF-8 byte budget `B` and payload/evidence byte telemetry;
- canonical Nine-of-Clubs Agency/scaling/trust-boundary documentation.

## Implemented authority model

The LLM receives only a bounded set of Governor/environment assembled coherent candidate moves. It returns a supplied `candidate_id`; it does not construct executable routes, targets, permissions, coordinates, or action objects.

Execution authority remains:

`Candidate Validity ∩ State Revision ∩ Permission ∩ Policy ∩ Live Environment`

The Governor:

- bounds candidate count with configurable `Kmax`;
- binds candidates to `bounded_set_revision`;
- re-reads live state before authorization and consumption;
- rejects stale model replies;
- rejects unknown/forged candidate IDs;
- issues single-use authorization nonces;
- rejects replay and cross-envelope use;
- invalidates on position, route, DOM/target, permission, visitor, evidence, and execution events;
- independently enforces OBSERVE/NAVIGATE/PREPARE/COMMIT consequence tiers.

Site content and A.I.M.S. memory are evidence, never authority. Model output is proposal/preference, never execution authority.

## Bounded cognition contract

`Kmax` bounds candidate count. Selection is described as `O(k)`, where `k <= Kmax`, not `O(1)`.

`B` is the configurable UTF-8 byte limit for the complete active cognition prompt. The frontend bounds its working payload before sending; the backend independently measures raw JSON payload bytes and the final prompt bytes before inference.

A.I.M.S. evidence retrieval has separate item and byte limits. Current telemetry includes:

- candidate count;
- `Kmax`;
- raw payload bytes;
- final prompt bytes;
- selected evidence item count;
- selected evidence bytes;
- context/evidence budgets.

Historical Vault/evidence growth may be `O(N)` while the active inference payload remains bounded by `B`.

## Short-term cache and return/resume contract

The browser now owns a bounded session-only Agency continuity cache separate from durable A.I.M.S. evidence. It is derived state and cannot authorize actions.

It preserves irreducible continuity across route/React remounts:

- visitor context;
- active bounded-set/candidate metadata;
- recent A.I.M.S. evidence IDs;
- a bounded excursion stack.

Recomputable confidence, coverage, permissions, live targets, and DOM state are re-derived from canonical journey/environment state instead of trusted from cache.

Every governed cross-page navigation now creates a return/resume contract before leaving the origin. The contract records:

- excursion ID;
- selected candidate and bounded-set revision;
- purpose;
- exact origin stage/chapter/stop/route;
- governed destination route/semantic destination;
- expected verified destination work.

Nested cross-page navigation is suppressed while an excursion is active. Arrival is revalidated against current route and journey state. Destination work runs through a fresh Agency Envelope. After verified destination work, the contract is consumed before returning to the governed origin and `activeDestinationRoute` is cleared.

This specifically addresses the prior failure mode where Weaver reached the LiDAR page and then lost the cognitive return path.

## Current unfinished acceptance work

Do not start a new feature before this pass is accepted.

Run and resolve, in this order:

1. backend Agency cognition tests, including UTF-8 byte budget regression;
2. backend A.I.M.S. bridge tests;
3. frontend Agency/Governor/cache/excursion runtime tests;
4. frontend TypeScript no-emit check;
5. live `16667 -> 16666 -> 16520` Agency candidate-selection call;
6. live cross-page tour proof using the actual mounted ORB:
   - explain;
   - Nine-of-Clubs question;
   - visitor answer;
   - semantic classification;
   - Governor candidate selection;
   - governed route to LiDAR page;
   - live Pointer/LiDAR destination action;
   - A.I.M.S. evidence observation;
   - automatic return to the saved origin;
   - continuation from the preserved tour position without intro replay.

Acceptance must also prove stale revision, replay, invalid target, and unavailable-cognition paths continue to fail closed.

## Do not regress

- voice-first Website ORB; no conventional chat panel or text-entry assistant;
- same mounted ORB through intro/tour/navigation;
- no fallback speech may advance governed coverage;
- Stage Governor remains authority;
- site scan / DOM / A.I.M.S. data remain evidence rather than authority;
- no persistent account authentication across browser sessions;
- no Docker rebuild, production deploy, or push to a production branch unless explicitly directed by the owner.
