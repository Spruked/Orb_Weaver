# Target One — Landing-page tour

Source status: Target One is built and aligned to the approved curriculum. Focused development-runtime debugging is in progress; Targets Two through Five are future work.

## Scope and sequence

Existing introduction → five-chapter landing tour → explicit visitor decision → stop.

Target One remains the complete Home / Landing Page walkthrough. Its internal five chapters are not separate presentation targets. The frozen later presentation spine is: Target One `/` → Target Two `/features` → Target Three `/lidar-guidance` → Target Four `/how-it-works` → Target Five `/preflight` → authentication → purchase/onboarding → a short post-purchase Marketplace introduction. Security, Desktop ORB, Campaign, Investor, Beta, and the pre-purchase Marketplace remain normal site pages outside the forced sequence. No cross-page presentation controller is part of the current Target One scope.

| Chapter / ID | Ordered stops | Required concept IDs |
| --- | --- | --- |
| Meet Weaver / `chapter-meet-weaver` | `stop-hero-meet` → `stop-how-to-talk` | `WEAVER_IDENTITY`; `PRESENCE_AND_CONTROL`, `VERIFIED_GUIDANCE` |
| Why Weaving Exists / `chapter-why-weaving` | `stop-crawl-vs-weave` → `stop-relationships` | `CRAWL_VS_WEAVE`; `RELATIONSHIP_MODEL` |
| Trust / `chapter-trust` | `stop-website-orb-outcome` → `stop-trust-security` | `WEBSITE_ORB_OUTCOME`; `TRUST_SECURITY_GOVERNANCE` |
| How Orb Weaver Builds Intelligence / `chapter-intelligence` | `stop-28-weave` → `stop-outcomes-status` | `TWENTY_EIGHT_WEAVE`, `UNIQUE_WEAVES`; `BUSINESS_OUTCOMES` |
| Preflight Decision / `chapter-preflight` | `stop-preflight-decision` | `PREFLIGHT_PURPOSE`, `PREFLIGHT_CHOICE` |

The terminal choices are **Run a Free Preflight Scan** and **Continue Exploring / Onboarding**. The first routes to `/preflight` only on an explicit visitor click; it does not execute or complete a scan. The second records deferral and leaves the visitor exploring the existing page. There is no automatic next chapter or onboarding execution.

Intermediate DOM beats are visual transitions, not additional instructional stops. Trust remains an independent chapter. Weaver remains male and speaks naturally: quote → interpret → connect. Strong branded copy may be quoted verbatim; conviction scales to evidence without fabricated results or mechanical page reading.

## Implementation ownership

- `frontend/src/types/tour.ts`: domain contracts and the canonical Preflight status type.
- `frontend/src/tour/curriculum.ts`: active five chapters, nine stops, twelve concept IDs, native selectors and grouped DOM source material.
- `frontend/src/tour/evaluator.ts`: conservative excerpt/keyword checks against the exact spoken output. These checks do not prove general semantic understanding; missed or ambiguous coverage remains pending.
- `frontend/src/tour/controller.ts`: deterministic sequence, bounded explanation attempts and terminal decision. Model suggestions do not grant progression authority.
- `frontend/src/state/tourControllerStore.ts`: V2 state, explicit V1 migration, compatibility position aliases and session persistence under `orbweaver-website-journey`. Visitor utterances remain in the existing conversation system.
- `frontend/src/landing/AutonomousOrb.tsx`: existing introduction handoff, cognition/TTS, live DOM evidence, Pointer/LiDAR, interruption/resume and decision controls.
- `backend/app/orb/tour_evaluation.py`, `backend/main.py`, `frontend/src/services/api.ts`: structured concept evidence on the existing Website ORB text/cognition path, with no separate evaluator model call.

V1 migration preserves known position and infers zero concept coverage, account creation or scan completion. Positions from the superseded four-chapter construction map to Target One positions; earlier concept IDs do not become Target One accomplishments. Unknown positions are not reset to the opening.

The controller accepts coverage only after speech playback completes. Missing DOM targets, failed pointer verification, malformed evidence and incomplete coverage preserve the current stop. Interruption cancels the active turn and retains position and accepted coverage.

## Source details

Native selectors use `#beat-1`, `#weaver-first-encounter`, `#beat-2`, `#beat-3`, `#beat-7`, `#beat-8`, `#beat-9`, `#weave-business-outcomes`, and `#beat-10`. Browser-tool `text=` and `:has-text()` syntax is not passed to native `querySelector`. Grouped DOM evidence supplies related content without adding stops. The hero opens without initiating a scroll.

The “Weave Assembly Status” display in LandingPage is static illustration, not live telemetry or evidence of a customer scan. Presentation guidance preserves that distinction.

## Boundaries and next handoff

Retain the existing voice, cognition, Pointer/LiDAR and migration infrastructure. Compatible account/production-stage fields and the existing derived gate helper are not permission to expand Target One. Full Preflight results/review, account creation, production scans and later onboarding chapters remain out of scope.

Focused development proof has confirmed live cognition, Kokoro playback, first-stop advancement, prompt interruption, saved-position resume, and the corrected `watch_weaver_guide` Pointer/LiDAR target. Target One construction remains the immediate job. A physical visitor microphone turn and the complete nine-stop run remain final acceptance work; keep validation brief during construction.
