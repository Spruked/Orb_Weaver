# Orb Weaver Guided Presentation — Targets 1–5 Scaffold

Status: **architecture scaffold only**. This file is intentionally not wired into the live Target One runtime.

## Non-negotiable scope boundary

The current five-chapter landing-page walkthrough remains **Target One only**. Do not refactor Target One into a multi-page controller while Target One is still being completed and validated.

The later presentation controller will own page-to-page transitions after Target One is proven end to end.

## Canonical presentation sequence

1. **Target One — Home / Landing** (`/`)
2. **Target Two — Features** (`/features`)
3. **Target Three — LiDAR Guidance** (`/lidar-guidance`)
4. **Target Four — How It Works** (`/how-it-works`)
5. **Target Five — Preflight** (`/preflight`)
6. **Authentication handoff — Login or Create Account** (`/login` or `/signup`)
7. **Purchase / customer onboarding**
8. **Short post-purchase Marketplace introduction**

Pages intentionally omitted from the required pre-Preflight guided route:
- Security
- Desktop ORB
- Campaign
- Investor
- Beta
- Marketplace before purchase

Those pages may remain normally accessible. Weaver simply does not require them in the first guided presentation.

---

# Target One — Home / Landing

Route: `/`

Implementation state: **current active build target**.

The authoritative implementation remains in the existing landing-tour curriculum and controller. The current five chapters and nine stops are not redefined here.

Target One responsibilities:
- introduce Weaver;
- establish natural conversation and visitor control;
- explain crawl vs. weave and the relationship model;
- communicate Website ORB outcome and trust;
- explain 28-Weave at the current landing-page level;
- explain Preflight as the later first website-specific step;
- demonstrate verified Pointer/LiDAR behavior where the live target is actually available;
- preserve controller authority over progression;
- require exact concept evidence before advancement;
- support Pause and Continue without losing position.

Target One completion does **not** auto-run Preflight. Once the later presentation controller is introduced, Target One completion becomes the handoff to Target Two.

Acceptance gate before Targets Two–Five are wired:
- clean frontend compile;
- splash/startup handoff succeeds;
- all Target One chapters/stops complete in order;
- live target verification remains mandatory;
- no Ping without verified target;
- cognition returns usable concept evidence;
- live TTS plays;
- controller records required concepts before advancing;
- Pause settles promptly;
- Continue resumes the exact saved position;
- no cross-page presentation code is required to make Target One pass.

---

# Target Two — Features

Route: `/features`

Purpose: move from the landing-page value proposition into the concrete Website ORB capability set.

Controller objectives:
- confirm the `/features` route is loaded before beginning;
- verify each target against the live DOM before guidance;
- explain capabilities from the actual page and verified Site World material rather than generic marketing copy;
- distinguish existing/live capabilities from future or optional offerings;
- connect features to visitor service and owner outcomes;
- avoid repeating the entire Target One narrative.

Proposed internal stop groups for later implementation:

1. `features-overview`
   - establish what the feature page is showing;
   - identify the primary Website ORB capability groups.

2. `features-site-intelligence`
   - verified website knowledge;
   - page/content/relationship awareness;
   - navigation and customer-service context.

3. `features-live-assistance`
   - natural conversation;
   - guidance;
   - owner-reportable operational/customer-service value where supported by actual page/source evidence.

4. `features-transition-to-lidar`
   - explain that the next target demonstrates guidance rather than merely describing it;
   - prepare a controller-owned handoff to `/lidar-guidance`.

Target Two completion condition:
- required Target Two concepts verified;
- route remains `/features` until completion;
- presentation controller authorizes the transition to Target Three;
- no LLM-generated route choice.

---

# Target Three — LiDAR Guidance

Route: `/lidar-guidance`

Purpose: demonstrate the verified guidance system as an observable capability.

This target must preserve the current Pointer/LiDAR doctrine:
- discovery is not verification;
- target lookup is not live geometry proof;
- Point/Ping occurs only after the destination is verified live;
- target loss cancels/recoveries rather than fabricating success;
- the controller owns movement sequence and completion;
- the LLM may explain what is happening but cannot declare target verification.

Proposed internal stop groups for later implementation:

1. `lidar-what-it-is`
   - explain why ordinary “click here” guidance is insufficient;
   - introduce verified live-target guidance.

2. `lidar-acquire-target`
   - resolve a real target on the page;
   - verify its selector/semantic locator/live geometry.

3. `lidar-point-and-ping`
   - move Weaver using the existing production Pointer/LiDAR path;
   - Point;
   - Ping only after verification;
   - explain the proof in natural language.

4. `lidar-recovery`
   - if a target is lost, recover or stop cleanly;
   - never substitute a guessed position.

5. `lidar-transition-to-how-it-works`
   - after successful verified demonstration, prepare the transition to `/how-it-works`.

Target Three completion condition:
- at least one real live target has been successfully verified and demonstrated through the production Pointer/LiDAR path;
- no synthetic/mock geometry is accepted as completion evidence;
- presentation controller authorizes Target Four.

---

# Target Four — How It Works

Route: `/how-it-works`

Purpose: explain the operational process after the visitor has already seen the product and the guidance capability.

This stage should answer “what happens to my website?” without becoming a deep technical dump.

Proposed internal stop groups for later implementation:

1. `how-it-works-input`
   - website enters through Preflight / site URL and customer intent;
   - explain that the system starts from the real site rather than a generic template.

2. `how-it-works-discovery`
   - crawl/scan discovers pages, routes, content and site structure;
   - distinguish discovery from the richer weave.

3. `how-it-works-weave`
   - explain that relationships, knowledge, journeys, Pointer intelligence and other required structures are assembled into a site-specific ORB;
   - use the page’s actual language and supported architecture.

4. `how-it-works-operation`
   - explain the resulting Website ORB as customer-service / hospitality / concierge intelligence for that site;
   - explain continuous learning/owner visibility only to the extent supported by the page and actual architecture.

5. `how-it-works-transition-to-preflight`
   - make Preflight the natural next action: “now let’s look at your site”;
   - prepare controller-owned navigation to `/preflight`.

Target Four completion condition:
- visitor has been given a coherent site-to-ORB process explanation;
- no fabricated scan results or completion claims;
- presentation controller authorizes Target Five.

---

# Target Five — Preflight

Route: `/preflight`

Purpose: transition from product education to the visitor’s own website.

Target Five is the first point where the guided presentation becomes website-specific.

Proposed internal stop groups for later implementation:

1. `preflight-purpose`
   - explain what Preflight checks and why it comes before the full weave;
   - keep the free/first-step positioning consistent with the actual product.

2. `preflight-input`
   - obtain/confirm the visitor’s website URL and required preflight inputs;
   - do not silently invent customer data.

3. `preflight-run`
   - initiate Preflight only after the visitor explicitly chooses to run it;
   - preserve the real scan path;
   - no synthetic result fallback.

4. `preflight-review`
   - review actual returned results;
   - distinguish summary access from paid detailed data where applicable;
   - explain available next options and estimated Web Weaver/Website ORB paths only from real configured product data.

5. `preflight-auth-handoff`
   - existing customer: `/login`;
   - new customer: `/signup`;
   - authentication choice belongs to the visitor;
   - preserve project/preflight continuity across the handoff.

Target Five completion condition:
- visitor has either completed/reviewed Preflight or explicitly deferred according to the production product rules;
- visitor chooses Login or Create Account;
- no automatic account creation;
- presentation state needed for the next authorized customer step is persisted.

---

# Authentication and purchase handoff

This is downstream of Target Five and is not a numbered presentation target unless implementation later requires one.

Required behavior:
- Login and Create Account are explicit user choices;
- preserve the relevant Preflight/project context across authentication;
- after authentication, continue into the real purchase/onboarding path;
- do not route directly to Marketplace as a substitute for purchase/onboarding;
- do not expose checkout/payment data to conversational context beyond what is technically required.

---

# Post-purchase Marketplace introduction

Marketplace introduction happens **after purchase**, not during the required pre-Preflight tour.

Purpose:
- briefly show the customer that skins, add-ons, specialized ORBS or future marketplace offerings exist;
- orient, do not derail onboarding;
- keep the introduction short;
- customer can enter Marketplace intentionally or continue with their purchased Website ORB setup.

This is not an automatic purchase or upsell action.

---

# Future presentation-controller contract

The later cross-page controller should own the deterministic sequence:

```text
TARGET_ONE_COMPLETE
  -> navigate /features
  -> verify route and first Target Two stop

TARGET_TWO_COMPLETE
  -> navigate /lidar-guidance
  -> verify route and first Target Three stop

TARGET_THREE_COMPLETE
  -> navigate /how-it-works
  -> verify route and first Target Four stop

TARGET_FOUR_COMPLETE
  -> navigate /preflight
  -> verify route and first Target Five stop

TARGET_FIVE_COMPLETE
  -> explicit /login or /signup choice
  -> purchase/onboarding
  -> short Marketplace introduction after purchase
```

Rules:
- **Controller owns sequence. LLM owns conversation.**
- LLM may not mark a target complete, select a route, choose an auth path, start Preflight, or purchase anything.
- Route transitions must be observed/verified before the next target begins.
- Each target owns its internal stop/concept curriculum.
- Page-to-page presentation state must survive normal navigation and Pause/Continue.
- No parallel presentation architecture.
- Reuse the current Website ORB cognition, TTS, Site World and Pointer/LiDAR runtime.
- No second tour LLM.
- No mock/synthetic evidence accepted for production acceptance.

---

# Codex implementation order after Target One is accepted

1. Read this scaffold and the proven Target One controller/curriculum implementation.
2. Do not rewrite Target One.
3. Inspect the real `/features` page and derive Target Two stops from its live DOM/content.
4. Implement and validate Target Two only.
5. Then inspect `/lidar-guidance` and implement Target Three using the existing Pointer/LiDAR path.
6. Then inspect `/how-it-works` and implement Target Four.
7. Then implement Target Five against the actual Preflight runtime and auth handoff.
8. Add the cross-page presentation controller only after the target-local controllers are individually proven, unless a minimal shared state layer is technically required earlier.
9. Add the short post-purchase Marketplace introduction last.

At every stage: test the next exact operation after the last visibly successful operation. Do not broaden diagnosis without evidence.
