# Target One — Landing-page tour

Source status: Target One is built and aligned to the approved curriculum.
Targets Two through Five are future work. Target One has current component and
startup proof, but it is not Gate-1 acceptance-complete until its requirements
are reproduced as part of one identified release-candidate evidence bundle.

## Scope and sequence

Existing introduction → governed explanation/question loop → an eligible
visitor-responsive destination → verified guidance → further explanation.

The current implementation is a linear Home / Landing Page walkthrough, but
that is no longer sufficient acceptance. Target One now requires the governed,
visitor-responsive cross-page loop in
[Visitor Interaction Doctrine](architecture/VISITOR_INTERACTION_DOCTRINE.md):
Landing → Features/capability evidence → LiDAR/guidance → How It
Works/intelligence → Preflight in an answer-responsive order selected only
from the Stage Governor's eligible destination set. Security, Desktop ORB,
Campaign, Investor, Beta, and the pre-purchase Marketplace remain outside this
interaction contract.

| Chapter / ID | Ordered stops | Required concept IDs |
| --- | --- | --- |
| Meet Weaver / `chapter-meet-weaver` | `stop-hero-meet` → `stop-how-to-talk` | `WEAVER_IDENTITY`; `PRESENCE_AND_CONTROL`, `VERIFIED_GUIDANCE` |
| Why Weaving Exists / `chapter-why-weaving` | `stop-crawl-vs-weave` → `stop-relationships` | `CRAWL_VS_WEAVE`; `RELATIONSHIP_MODEL` |
| Trust / `chapter-trust` | `stop-website-orb-outcome` → `stop-trust-security` | `WEBSITE_ORB_OUTCOME`; `TRUST_SECURITY_GOVERNANCE` |
| How Orb Weaver Builds Intelligence / `chapter-intelligence` | `stop-28-weave` → `stop-outcomes-status` | `TWENTY_EIGHT_WEAVE`, `UNIQUE_WEAVES`; `BUSINESS_OUTCOMES` |
| Preflight Decision / `chapter-preflight` | `stop-preflight-decision` | `PREFLIGHT_PURPOSE`, `PREFLIGHT_CHOICE` |

The existing terminal choices are **Run a Free Preflight Scan** and **Continue
Exploring / Onboarding**. The first routes to `/preflight` only on an explicit
visitor action; it does not execute or complete a scan. They are not a model
for earlier interaction questions: guided questions must have multiple useful
governed outcomes rather than a generic yes/no continuation exit.

Intermediate DOM beats are visual transitions, not additional instructional stops. Trust remains an independent chapter. Weaver speaks naturally: quote → interpret → connect. Strong branded copy may be quoted verbatim; conviction scales to evidence without fabricated results or mechanical page reading. He introduces himself naturally only at the identity stop; later speech does not repeat an identity or gender label.

## Implementation ownership

- `frontend/src/types/tour.ts`: domain contracts and the canonical Preflight status type.
- `frontend/src/tour/curriculum.ts`: active five chapters, nine stops, twelve concept IDs, native selectors and grouped DOM source material.
- `frontend/src/tour/evaluator.ts`: conservative excerpt/keyword checks against the exact spoken output. These checks do not prove general semantic understanding; missed or ambiguous coverage remains pending.
- `frontend/src/tour/controller.ts`: deterministic sequence, bounded explanation attempts, finite authored engagement questions and terminal decision. Model suggestions do not grant progression authority.
- `frontend/src/tour/interaction.ts`: deterministic answer-to-semantic-category classification. An unclassified answer grants no destination.
- `frontend/src/tour/governor.ts`: the sole Website Tour Stage Governor for public interaction routes. It maps semantic answer categories to finite legal destinations for the current journey state; questions and models never contain route authority.
- `frontend/src/state/tourControllerStore.ts`: V2 state, explicit V1 migration, compatibility position aliases and session persistence under `orbweaver-website-journey`, including question, answer, route, and recent-context continuity.
- `frontend/src/landing/AutonomousOrb.tsx`: existing introduction handoff, cognition/TTS, live DOM evidence, Pointer/LiDAR, interruption/resume, decision controls, and bounded selected-route arrival continuation.
- `backend/app/orb/tour_evaluation.py`, `backend/main.py`, `frontend/src/services/api.ts`: structured concept evidence on the existing Website ORB text/cognition path, with no separate evaluator model call.

V1 migration preserves known position and infers zero concept coverage, account creation or scan completion. Positions from the superseded four-chapter construction map to Target One positions; earlier concept IDs do not become Target One accomplishments. Unknown positions are not reset to the opening.

The controller accepts coverage only after speech playback completes. Missing DOM targets, failed pointer verification, malformed evidence and incomplete coverage preserve the current stop. Interruption cancels the active turn and retains position and accepted coverage.

## Source details

Native selectors use `#beat-1`, `#weaver-first-encounter`, `#beat-2`, `#beat-3`, `#beat-7`, `#beat-8`, `#beat-9`, `#weave-business-outcomes`, and `#beat-10`. Browser-tool `text=` and `:has-text()` syntax is not passed to native `querySelector`. Grouped DOM evidence supplies related content without adding stops. The hero opens without initiating a scroll.

The “Weave Assembly Status” display in LandingPage is static illustration, not live telemetry or evidence of a customer scan. Presentation guidance preserves that distinction.

## Boundaries and next handoff

Retain the existing voice, cognition, Pointer/LiDAR and migration infrastructure. Compatible account/production-stage fields and the existing derived gate helper are not permission to expand Target One. Full Preflight results/review, account creation, production scans and later onboarding chapters remain out of scope.

Focused development proof has confirmed live cognition, Kokoro playback,
first-stop advancement, prompt interruption, saved-position resume, and the
corrected `watch_weaver_guide` Pointer/LiDAR target. The public Preflight
handoff binds rendered report cards to report-scoped `data-orb-target`
identities, uses the existing LiDAR/runtime verifier, rechecks at arrival, and
blocks Point/Ping on target loss. The governed delivery path now withholds
non-approved results from TTS and sanitizes visitor-facing delivery; those
earlier repair items are not current blockers.

The linear nine-stop implementation is not acceptance-complete. The
concept-evidence/progression boundary has been repaired: non-empty speech is
not coverage, and dynamic-tour fallback is non-advancing. The source lane now
has a bounded question/answer routing slice that separates semantic
classification from Stage-Governor route selection and preserves cross-page
context, but it has not yet proved the complete destination graph in a browser
with live cognition. Remaining release-candidate work includes: restoring and
proving live dynamic articulation with the required cognition service;
completing the eligible-destination graph and per-destination live
Pointer/DOM evidence; a real visitor microphone/STT turn; full pointer
positive/negative and target-loss evidence; timing capture; and current
same-RC deployment evidence. These requirements are part of Gate 1 and do not
authorize unbounded later-product expansion.
