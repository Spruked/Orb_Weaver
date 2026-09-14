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

Confidence targets and ranking weights are initial deterministic policy values,
not measured conversion claims. Commercial-fit patterns require goal, friction,
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

## Connected versus remaining runtime work

Connected: legacy curriculum consumes shared registry records; the existing
Governor owns canonical ranking and scoped candidate evaluation; canonical
compile/classify outputs have validated, provider-neutral boundaries.

The live controller still uses the three compatibility questions. It does not
yet schedule the new bank. Required follow-on runtime work includes wiring
evidence-derived confidence/budgets and currently legal candidate bindings into
selection, registering real cognition adapters, connecting the existing scanned
lexical model, and recording question/answer/demo provenance through AIMS.
Provider tests use deterministic doubles; they do not prove live Qwen/cloud
equivalence or voice/DOM behavior.

The present destination scope has question/stage/chapter/stop checks but no
single-use nonce or movement epoch. Full action grants, nonce consumption,
return-to-same-position replay rejection, and live Pointer confirmation must
be connected before candidate actions become executable. New selection helpers
do not claim to supply those guarantees. No startup, movement, purchase,
production service, or live deployment behavior is changed by this registry pass.
