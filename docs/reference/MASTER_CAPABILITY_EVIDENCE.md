# Master capability evidence contract

The Master Capability List is the source checklist for crawl, Site World, Website ORB, manufacturing, and reporting coverage. The crawler now parses that document into an evidence-backed capability ledger instead of treating the existence of an implementation as proof that a capability is operational.

## Evidence flow

`crawl orchestration → persisted page/stage evidence → capability coverage ledger → Scan capabilities tab + Reports data tab`

The ledger contains every category and atomic item from `Orb Weaver — Master Capability List.html`. Each category receives an explicit state:

- `verified`: the current crawl produced the required persisted evidence.
- `partial`: some evidence exists, but the required contract is incomplete.
- `blocked`: a prerequisite stage or recovery action prevents completion.
- `requires_runtime_verification`: crawler evidence is not allowed to fabricate live DOM geometry or interaction truth.
- `runtime_capability_not_crawl_verified`: the capability belongs to the runtime/product layer and must be proven by runtime QA, not inferred from a crawl.

`complete` is reserved for a ledger in which every category is verified. A database crawl with status `completed` is therefore not automatically an ORB-ready release.

## Current evidence rules

- JavaScript rendering uses a bounded Playwright snapshot with reduced motion, muted audio, blocked service workers, and no waiting on site-owned tour timers.
- Browser diagnostics capture console errors, uncaught page errors, failed requests, and failed HTTP responses per rendered page.
- Protected/admin routes are recorded as authentication boundaries when the crawler reaches a login wall. The crawler does not claim authenticated dashboard coverage without an owner-authorized authenticated session.
- Pointer mapping is extraction evidence only. Pointer verification, conflict recovery, live DOM geometry, and runtime guidance remain blocked until independently verified.
- LiDAR geometry is always `live_dom_only`; crawler output cannot authorize a fabricated coordinate.
- The commercial catalog is partial when extraction completes with zero entries; zero is not evidence that a site has no commercial data.

## User-facing locations

- Crawl/Scan → Capabilities: full category and atomic-item ledger.
- Reports → Complete data inventory: reportable systems, access state, capability ledger, and completion contract.
- Site World/client crawl pack: the persisted capability ledger is included with route, knowledge, pointer, and retrieval artifacts.

No Git push or Docker rebuild is part of this review. Deployment follows only after a fresh crawl and the focused validation suite confirm the evidence contract.
