# Nine-of-Clubs canonical registry

The owner-supplied [source bank](NINE_OF_CLUBS_CANONICAL_SOURCE.md) defines 50
selectable patterns and 150 semantic choices. Source numbers identify patterns;
they never prescribe traversal order. The executable source is
`frontend/src/tour/discovery/patterns.json`, schema version 1.

## Existing architecture and compatibility

The Website Tour Governor remains `frontend/src/tour/governor.ts`. Its stages
are `LANDING_TOUR`, `PREFLIGHT`, `ONBOARDING`, and `PRODUCTION_SCAN`; the new nine
dimensions describe missing information within those stages. They do not
replace stages, chapters, stops, or the separate backend ORBS purchase journey.

All 50 records are initially eligible only during `LANDING_TOUR`. Broader stage
eligibility requires an explicit registry policy change. Ranking requires a
positive acquisition budget, an unanswered/uncovered dimension, satisfied
prerequisites, and current available candidate bindings for every presented
branch. An interrupted/deferred journey, an outstanding question, or ongoing
destination guidance blocks acquisition. Sufficient dimension confidence
removes further questions in that dimension. There is no forced question count.

| Decision dimension | Source patterns |
| --- | --- |
| GOAL_DISCOVERY | 1, 19 |
| VISITOR_STATE_DISCOVERY | 4, 6, 13, 14, 37, 39 |
| FRICTION_DISCOVERY | 2, 18, 24, 25, 27, 28 |
| PRIORITY_SELECTION | 3, 5, 7, 8, 12, 16, 36, 40 |
| CONSTRAINT_DISCOVERY | 9, 17, 21, 22, 23, 35, 45 |
| CAPABILITY_SELECTION | 11, 15, 20, 26, 29, 30, 31, 32, 33, 34, 38, 41, 42 |
| PROOF_SELECTION | 10, 43, 44, 48, 49 |
| COMMERCIAL_FIT_DISCOVERY | 46, 47 |
| COMMITMENT_NEXT_STEP | 50 |

The existing three two-choice questions are retained in
`discovery/legacyQuestions.ts`, which the existing curriculum now imports.
Their IDs, text, options, keywords, semantic enums, and Governor route maps are
unchanged. Related canonical patterns are recorded in
`LEGACY_PATTERN_RECONCILIATION`, but are deliberately not treated as aliases:

| Existing question | Related bank entries | Why it remains distinct |
| --- | --- | --- |
| discovery-or-guidance | 1, 31 | Discovery versus guidance is not guidance/conversion/support or answer/guide/verify. |
| understanding-or-helping | 11, 41 | Understanding versus assistance has two meanings, not the bank's three. |
| discovery-or-conversion | 2 | The bank adds an availability branch absent from the current question. |

## Record and action contract

Each record carries its source number, dimension, intent, ordered choices,
explicit per-choice candidate action, required lexical slots, legal stages,
dimension prerequisites, confidence target, information-gain/convergence
weights, generation constraints, fallback stem, and complete fallback rendering.
The semantic codes are preserved exactly as supplied. A semantic output is
scoped to its pattern; repeated labels such as `GUIDANCE` do not imply identical
question intent.

Candidate actions describe explanation, demonstration, commercial-fit review,
site-scan request, configuration request, or implementation review. A request
is not an execution grant. Demonstrations require live verification; scan and
configuration candidates require explicit consent. Ownership options describe
preferences, never a claim that a product or pricing plan is available.

`resolveDiscoveryCandidate` checks the current pending question and the existing
`TourDestinationAuthorizationScope` stage/chapter/stop binding, then rechecks
current candidate availability. It returns no route and performs no action.
`resolveDiscoveryInterpretation` additionally rejects weak, ambiguous, or
unsupported classifications. The host must still obtain and consume a real
execution authorization from its existing action path.

Confidence targets and ranking weights are deterministic policy values, not
measured conversion claims. Commercial-fit patterns require goal, friction,
capability, and proof coverage; commitment additionally requires commercial-fit
coverage. The host supplies evidence-derived confidence and the acquisition
budget. Neither is an LLM-selected policy field.

## Wording and interpretation boundaries

`compiler.ts` accepts a provider-neutral adapter with `compile_question()` and
`classify_response()`. Provider output is treated as unknown data. Structured
validators reject extra fields, unknown/missing/reordered/duplicate branches,
action injection, and labels outside approved lexical alternatives. Final speech
is assembled from the canonical question frame and validated choice labels;
arbitrary model prose cannot insert an unvalidated fourth branch or yes/no exit.

The only parameterized source noun currently needed is `{host}`, replacing the
product term ORB. Lexical slots and optional per-category aliases require source
references from the host's reviewed lexical site model. They are not free-form
provider instructions. Missing vocabulary blocks compilation rather than being
invented. Compilers may choose grounded label alternatives but cannot rewrite
the canonical frame freely in this first implementation.

Two failed or invalid compilation attempts produce the exact deterministic
fallback. Each attempt has a timeout. Classification failure returns no
selection; multi-category interpretation may be retained as evidence but cannot
choose an action until ambiguity is resolved. Supporting excerpts must appear
in the actual visitor response. This is interpretation evidence, not promotion
to an authoritative visitor declaration or an execution permission.

## Agency Envelope and coherent candidate moves

The live tour runtime now constructs a bounded Agency Envelope from the current
verified environment. The six legal vectors describe the model's current
freedom, but the model never assembles an executable action by independently
mixing vector values. The Governor/environment first assembles complete,
coherent candidate moves; cognition may select only one supplied
`candidate_id`.

The legal set is an intersection of universal capability, site-scan evidence,
live DOM/target evidence, Governor policy, visitor permission, and applicable
security/business policy. Site content is evidence, never authority. A model
response is a proposal/preference, never execution authority.

Each candidate is bound to a `bounded_set_revision`. The Governor re-reads the
live environment before issuing and consuming authorization. Relevant position,
route, DOM/target, permission, visitor, evidence, or execution changes invalidate
the prior set. Single-use authorization nonces are consumed before action
execution; stale, forged, replayed, cross-envelope, or superseded grants fail
closed.

Consequence tier is independent of cognitive action. `OBSERVE`, `NAVIGATE`,
`PREPARE`, and `COMMIT` are separate permission classes. `COMMIT` always requires
explicit confirmation. A scanned checkout label or model-selected destination
cannot elevate permission.

## Bounded working state and scaling contract

`Kmax` is the configured upper bound on candidate count supplied to cognition.
Selection cost is described as `O(k)`, where `k <= Kmax`; it is not claimed to be
mathematically `O(1)`.

`B` is the configured UTF-8 byte budget for the complete active cognition
prompt. The browser bounds its serialized working set before sending it, and the
backend independently measures payload and final prompt bytes before inference.
A.I.M.S. retrieval is relevance-selected and separately bounded by evidence item
and byte budgets. Historical memory growth therefore does not imply unbounded
inference context.

Operationally:

- site discovery/indexing scales with the discovered site, approximately `O(P + E)` for pages and indexed affordances/evidence;
- active cognition context is `O(B)`;
- model candidate selection is `O(k)`, `k <= Kmax`;
- Vault/evidence storage grows with recorded history, approximately `O(N)`;
- inference payload remains bounded by `B` rather than total historical `N`.

Payload telemetry records candidate count, `Kmax`, payload bytes, prompt bytes,
selected evidence items/bytes, and their configured budgets. These are measured
operational bounds, not latency guarantees.

## Memory, evidence, and continuity boundaries

A.I.M.S. is an advisory evidence/memory layer. Its selected session context may
inform cognition, but it cannot create routes, targets, permissions, candidate
moves, or execution grants. Browser observations preserve provenance and are not
silently promoted to server-verified facts. Inference records are stored as
`INFERRED`, distinct from direct visitor declarations and verified results.

The mounted runtime also owns a bounded, browser-session-only Agency short-term
cache. It carries irreducible continuity across React/page remounts: visitor
context, recent evidence identifiers, active candidate/revision metadata, and a
small excursion stack. Recomputable confidence, coverage, permissions, and live
DOM facts remain derived from the canonical journey/environment rather than
being trusted from cache.

Cross-page governed navigation is treated as an excursion. Before navigation,
Weaver must persist a return/resume contract containing the candidate/revision,
purpose, exact origin stage/chapter/stop/route, and governed destination. The
runtime suppresses nested cross-page navigation while that excursion is active.
On the destination page it re-verifies arrival against the current journey and
live route, performs destination work through a fresh Agency Envelope, then
consumes the return contract before navigating back to the exact governed
origin. Cached return data alone never grants authority.

## Current runtime status and remaining acceptance work

Connected now:

- all 50 canonical patterns and 150 semantic choices;
- compatibility questions and existing route semantics;
- evidence-derived acquisition ranking and confidence suppression;
- provider-neutral question compilation and response classification;
- live Agency Envelope construction and bounded candidate selection;
- single-use authorization, stale-revision rejection, replay rejection, and
  live target/destination revalidation;
- bounded A.I.M.S. context and outcome/evidence recording;
- browser-session short-term continuity and governed cross-page return/resume.

Remaining work is acceptance/hardening rather than missing architectural
ownership: run the backend Agency/A.I.M.S. tests, frontend Agency/runtime/cache
suite, TypeScript typecheck, and the live `16667 -> 16666 -> 16520` cognition
path against the current dev services. Provider equivalence, voice playback,
real DOM target behavior, and end-to-end LiDAR excursion/return must be verified
live before this work is called production-ready.

No Docker rebuild or production deployment is implied by this architecture
work.

Candidate/inference scaling and the execution trust boundary are specified in
[Agency Envelope](AGENCY_ENVELOPE.md). That document is normative for Kmax/B,
site content as evidence, and model output as a non-authoritative proposal.
