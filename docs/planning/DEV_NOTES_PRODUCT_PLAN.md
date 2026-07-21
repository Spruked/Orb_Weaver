# Orb Weaver Final Product Plan — Development Notes

Source: `Orb Weaver final product plan.docx` (updated 2026-07-18)

## Working doctrine

The product lifecycle is: Discovery → Understanding → Embodiment → Verification → Human Approval → Preflight → Deployment → Sentinel Monitoring → Versioned Update/Rebuild → Historical Audit Chain.

Work is prioritized from the document's P0/P1 board. Existing user changes in the worktree must remain intact.

## Baseline found before implementation

- The backend has one `CrawlJob` type and one `AuditReport` type; Map, Site, ORB, Full Audit, and Sentinel are not yet distinct lifecycle jobs.
- Project Preflight exists, but it is a website scan and is not gated by unresolved review items.
- Crawls already collect semantic analysis, rendered SPA DOM where Chromium is available, link graphs, entity analysis, pointer records, and client history JSON.
- Pointer records contain a numeric confidence value but not the required confidence class, evidence history, or explicit runtime policy.
- Client preservation exists under `vault_system/clients/<domain>`, but does not yet produce the required per-run directory layout, complete checksums, database snapshots, or previous-manifest hash chain.
- Failures are stored as a plain error string in crawl config rather than structured `failure_diagnostics.json` records.
- The Projects UI exposes Crawl, Re-crawl, Audit, Preflight, and Reports, but not the product-plan lifecycle controls.

## Implementation checklist

### In progress

- [x] Add durable lifecycle job identities and a stage-specific API surface for Map Crawl, Site Scan, ORB Scan, and Full Audit.
- [x] Integrate per-run evidence roots, manifests, checksums, SQLite snapshots, structured diagnostics, and previous-manifest hash chaining for implemented lifecycle stages.
- [x] Add pointer confidence classes and enforce runtime behavior policy in the browser validator.
- [x] Add independent Full Audit verification, structured URL/pointer reconciliation, and signed human-review decisions.
- [x] Expose separate lifecycle controls and truthful count/phase progress in the Projects UI for implemented stages.
- [ ] Integrate lifecycle Preflight with hard blocking checks, then Sentinel orchestration.

### Remaining P1/P2 work

- [ ] Sentinel light/standard/deep live drift scanning and proposed change sets.
- [ ] Route/action safety classification enforced at interaction time.
- [ ] Versioned deployed Site World, Pointer Map, and Knowledge Index with atomic swap/rollback.
- [ ] Retention automation with export-before-prune.
- [ ] Pricing/package definitions and optional hosted Sentinel policy.
- [ ] PDF reports for every stage and complete evidence-package export.

## Verification log

- 2026-07-18: Extracted and reviewed the complete product plan.
- 2026-07-18: Confirmed current frontend production build uses root-relative CRA assets and added Nginx `/static/` 404 handling in prior work.
- 2026-07-18: Enforced pointer runtime policy in `targetValidation.ts`; `UNCERTAIN`, `BLOCKED`, and explicit `may_point: false` records halt safely before DOM resolution.
- 2026-07-18: Added authenticated lifecycle list/start/detail APIs; Map Crawl now wraps a real crawl and requires signed map approval before Site Scan, while ORB Scan consumes the completed Site Scan dataset.
- 2026-07-18: Added evidence manifest and verification endpoints, SQLite backup/schema preservation, checksum tamper detection, and previous-manifest chain validation.
- 2026-07-18: Added Full Audit independent verification crawl and URL/pointer reconciliation classifications (`CONFIRMED`, `TRANSIENT`, `DYNAMIC`, `CONFLICT`, `UNVERIFIED`, `PASSED`) with critical review items.
- 2026-07-18: Added lifecycle types/API methods and separate stage controls to Projects UI; progress bars are shown only from actual item counts.
- 2026-07-18: Built the universal shared ORB client, external-script adapter, React/TypeScript adapter, bootstrap/runtime/WebSocket contracts, Shadow DOM mount, SPA observer, clean teardown, visible failure state, and runtime pointer enforcement.
- 2026-07-18: Bound `orb-weaver-campaign` installations to the real campaign Site World from legacy crawl job #24: 137 pointers, with only the 1 `STABLE` target currently eligible to guide and 136 `UNCERTAIN` targets halted safely. Job #24 is not lifecycle-evaluated, so the map is `POINTER_RECOVERY_REQUIRED`, not passed.
- 2026-07-18: Initial loader checkpoint verification passed before Factory skin lifecycle expansion: backend 12/12, frontend 4/4, TypeScript no-emit check, optimized production build, and browser smoke 10/10 with 5 bootstrap reports and 0 console errors.
- 2026-07-18: Added the one-attempt Pointer Recovery Pass. Pointer quality now gates at 70% stable, 25% uncertain, a 10-stable-pointer absolute floor, and duplicate/conflict threshold 3. ORB speech stays ready while deployment remains blocked.
- 2026-07-18: Pointer Recovery reuses the baseline Site World and map; it performs two desktop and two mobile renders per route, scroll-segment capture, durable-identity reconciliation, shared finding taxonomy, uncertainty subreasons, and pointer-health tracking.
- 2026-07-18: Added a separate Pointer Plot Map UI report for initial extraction versus recovery results. Real campaign proof covered `/` and `/investor`: 8 renders, 104 segments, 270 candidates, 28 promoted, and 109 routed to visual review without publishing over the legacy map.
- 2026-07-18: Pointer recovery verification at checkpoint: backend 18/18, frontend 4/4, loader smoke 10/10, TypeScript no-emit and optimized production build passed. The lifecycle test proves one recovery job is queued automatically and cannot duplicate for the same ORB Scan. The 28-recovered/109-unresolved campaign proof remains non-canonical because it was derived from legacy job #24.
- 2026-07-18: Installed the exact owner-supplied O.R.B.S. artwork as immutable `orb_factory_default_v1`, the complete default identity every customer receives before any custom skin. Verified SHA-256 `8eb49c628211c7d077fb65f3591107f1489124ccbfa840dc0f2381157cd87e61`, 1492x1474, PNG RGBA 8-bit. Existing bow-tie `tuxorb.png` files remain non-substitutes.
- 2026-07-18: Factory lifecycle verification passed 25 browser checks with 8 bootstrap reports and 0 console errors: Factory-first mount, valid custom skin, failed-custom automatic fallback, explicit Factory rollback, offline/reconnect, SPA persistence, unchanged motion/runtime, no Site World or Pointer Map rebuild during skin PATCH, and no WebSocket disconnect. The loader and Factory asset are verified locally but not yet publicly deployed.
- 2026-07-18: The owner explicitly restored `tuxorb.png` as immutable `orb_factory_default_v1`, superseding the earlier large O.R.B.S. artwork decision. Factory-first mount, fallback, and rollback now consistently use the 512x512 tuxedo asset with SHA-256 `f447043b007e9aba07c0c67e3b5749751f8db327b21b09f1a763eca359e73ca5`.
- 2026-07-18: Installed the owner-supplied tuxedo brand family for banner, square, touch, compact, and favicon surfaces, with a hash-verified public asset registry in `frontend/public/orb-brand-assets.json`.
- 2026-07-18: Locked the commercial V1 target to trustworthy buyer-seller transaction guidance. Added `docs/ORB_WEAVER_V1_TRANSACTIONAL_DOCTRINE.md` covering the seven minimum workflows, participant states, runtime grounding, action/consent boundaries, handoff rules, acceptance criteria, measurement, and implementation order.
- 2026-07-19: Real CALI/Website ORB navigation test exposed a better class of failure: movement now works quickly, but route identity and verification must fail closed. Backend runtime route suggestions now verify against approved route hints or scanned authority-flow pages before exposing a navigable `suggested_route`; stale tool suggestions return an honest refusal instead of a destination. Frontend pointer validation now allows only `VERIFIED`/`STABLE` records with explicit `runtime_policy.may_point === true`; missing legacy confidence is blocked by default.
- 2026-07-19: Added a real public `/signup` route that opens the existing account form in create-account mode. Signup now creates a default `spruked.com` project for the customer, grants admin only under the existing first-customer/no-admin safety rule, and writes a pending CALI CRM import record under the canonical vault while attempting optional sync to `http://localhost:21010/`.
- 2026-07-19: Dialed the CALI CRM bridge. The live service copy under `/home/bryan/projects/spruked.com/Orb_Assistant` now honors `CALI_CRM_SUBSTRATE_ROOT`, migrates contact import metadata/link tables, and exposes admin-protected generic dataset import plus Orb Weaver customer-signup import endpoints. `spruked-cali-api.service` now reads the R-drive CRM substrate at `/mnt/c/mnt/r/R_Drive_Substrate/crm`; `spruked-cali-crm-frontend.service` serves the Spruked admin/CRM UI on `http://localhost:21010/` while preserving the existing `3001` Spruked site service. The old root CALI memory folder was first safety-copied to `/home/bryan/spruked.com/archive/CALI_SKG_DB_legacy_20260719T111341/`, then moved out of WSL root into `/home/bryan/spruked.com/archive/CALI_SKG_DB_root_moved_20260719T112905/`.
- 2026-07-19: Spruked `Orb_Assistant/electron_dock_adapter` was synced byte-for-byte from Orb Weaver's canonical `Orb_Assistant/electron_dock_adapter`; the prior smaller Spruked-specific adapter was archived under `Orb_Assistant/archive/electron_dock_adapter_spruked_before_orb_weaver_sync_20260719T113420/`. Spruked launch/package scripts now target `electron_dock_adapter` directly. Doctrine: Electron remains an optional dockstation adapter surface; CALI cognition and website voice stay owned by `cali_skg`, the website ORB API, and Kokoro.
- 2026-07-19: Removed remaining WSL-home clutter by moving the small legacy `/home/bryan/spruked.com` runtime/memory folder into the real website repo archive at `/home/bryan/projects/spruked.com/Orb_Assistant/archive/root_home_spruked_com_legacy_20260719T115451/`. The active website repo remains `/home/bryan/projects/spruked.com`; live CALI CRM continues through `http://localhost:21010/` and the R-drive substrate.
- 2026-07-19: Granted the owner ORB explicit admin/navigation awareness in docs and crawler policy. Authenticated Orb Weaver crawls now include configured admin route seeds such as `/admin`, tag admin-section pages in semantic analysis, and report admin seed/page counts in crawl stats. Public/free scans remain public-only. Spruked Orb Assistant docs record canonical tool access and pointer escalation folder authority.
- 2026-07-19: Enabled admin-section scanning from the Orb Weaver UI. Dashboard Start Audit and Projects Crawl/Re-Crawl now expose/send `include_admin_sections`, lifecycle Map Crawl carries the same flag, and Crawl Jobs re-crawls preserve it. The visible UI label is “Scan admin” / “Include admin section in owner scan.”
- 2026-07-19: Corrected audit classification for owner/admin scans. Admin routes such as `/admin` remain scanned and preserved for ORB/operator awareness, performance/accessibility/security context, and report summary, but are excluded from public SEO/content/canonical/schema/link-graph scoring so operator pages do not pollute public marketing recommendations.
- 2026-07-19: Generalized audit route classification into `public_content`, `admin`, `transactional`, `utility`, `system`, and `private`. Only `public_content` routes receive the full public SEO/semantic scoring suite. Cart mutation URLs such as `/cart?add=...`, checkout, admin, private account/dashboard, system files, and utility routes are scanned for ORB/runtime context but excluded from public scoring. Recomputed job #28 data validates a cleaner model: 14 public pages scored, 8 non-public routes excluded, and no `/admin` or `/cart` URLs leak into public SEO issue affected URLs.

## Resume point

Complete owner-enabled per-pointer visual verification so reviewed records can transition to `OWNER_VERIFIED`. Then implement the versioned participant-state and transaction-flow contracts plus the seven V1 buyer-seller demonstrations before expanding into broader agent behavior. Sentinel still follows with `DEPRECATED` and `REMOVED` health transitions. The Brand World and owner-controlled ORB Identity wizard remain specified in [`../handoffs/HANDOFF_BRAND_WORLD.md`](../handoffs/HANDOFF_BRAND_WORLD.md) after the pointer-recovery checkpoint.
