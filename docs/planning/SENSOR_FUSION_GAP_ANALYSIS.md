# Orb Weaver — Sensor-Fusion Mapping Gap Analysis (first pass)

Status: DRAFT. Evidence is grep-level static inspection of the repo on 2026-10-10,
plus the pops.spruked.com crawl artifact. Nothing here was executed. "Missing"
means "no code found by search", not "proven absent". Verify each row before acting.

Goal: Orb Weaver as a sensor-fusion site mapper, where no single representation of
a page (DOM, a11y tree, geometry, pixels) is trusted alone, and a target becomes
canonical only when independent signals converge.

## Coverage matrix (benchmark signals)

States: IMPL+TESTED / IMPL-UNVERIFIED / PARTIAL / MISSING

| # | Signal / capability | State | Evidence found | Gap to top-end |
|---|---|---|---|---|
| 1 | Real browser rendering (Playwright) | IMPL-UNVERIFIED | `backend/app/crawler/render_page_snapshot.js`, `motion_runtime/server/pointer/pointer_recovery_capture.js` | Two separate capture paths; no shared single-session capture feeding every sensor |
| 2 | CDP DOM+layout snapshot (`DOMSnapshot.captureSnapshot`) | MISSING | 0 files match | One call returns DOM, computed styles, paint order, bounds together. Foundation for fusion |
| 3 | Accessibility tree (CDP `Accessibility.getFullAXTree` / aria snapshot) | MISSING | 0 files match | Role/name/state is the strongest "what is this control" signal and the best cross-check on DOM guesses |
| 4 | Geometry (bounding boxes, viewport, scroll) | PARTIAL | `getBoundingClientRect` in client pointer code; screenshot dimensions in capture JS | Client-runtime only for most; server mapper needs per-element rects stored in the map, per viewport (mobile/desktop) |
| 5 | Hit-testing / occlusion (`elementFromPoint`) | PARTIAL | `Lidar2DGuidanceMap.ts` lists `hit_test` method | Runtime side only; not a recorded crawl-time field |
| 6 | Playwright-style actionability (unique, visible, stable, receives events, enabled) | PARTIAL | `targetValidation.ts` | Not applied as a crawl-time verification gate on every mapped target |
| 7 | OCR / vision grounding | MISSING (wired) | `pointerResolution.ts:68,160` Tier 4 is a `TODO(integration)`; Tesseract appears only as naming (`tesseract_weave`) | Pixel evidence that DOM misses: canvas text, image-text buttons, shadow/iframe content, DOM-vs-pixels lies |
| 8 | Interaction verification (click, observe effect) | MISSING at crawl level | no server-side click-and-observe | Prove a target does what the map claims: URL change, DOM mutation, dialog open, request fired |
| 9 | Dynamic-state crawling (menus, modals, tabs, accordions, SPA routes, infinite scroll, forms) | MISSING / ad hoc | modal handling appears only in tests and runtime LiDAR | Systematic state-graph exploration with state fingerprinting and dedup; map states, not just URLs |
| 10 | Multi-viewport / device mapping | UNKNOWN | `avg_mobile_ux_score` exists in stats | Per-viewport maps; targets that exist only at some breakpoints |
| 11 | Confidence and convergence | PARTIAL | hard-coded confidence constants in `orbital_behavior_skg/index.ts`; pointer `stable_ratio`, `authority_reconciliation` in the crawl | Confidence is heuristic per method, not derived from agreement between independent sensors. No canonical-promotion rule across DOM+AX+geometry+OCR+interaction |
| 12 | Regression / drift detection | PARTIAL | `historical`, `trend_model` in crawl | Target-level drift (a button moved or renamed), not only page-level stats |

## What the pops.spruked.com artifact shows about current output quality

- `pointer_plot_map`: 1616 records, `route_locator_conflicts` list holds 200 entries,
  `capability_coverage` marks "Selective Pointer Authority" as `blocked` and
  "LiDAR / Pointer" as `requires_runtime_verification`. The system already knows
  its target layer is not converged.
- `commercial_catalog`: 12 entries, names such as "Action Desktop App How",
  "Service", "Presence System Enter Pops". No SKU, price or description. A
  structural extractor emitting text fragments as products is exactly what a
  second independent signal (AX roles, schema.org, visual layout) should reject.
- Routes `/admin`, `/cart`, `/account` are mapped alongside public pages.
  Route classification exists; it must gate downstream marketing/SEO outputs.

## Proposed canonicalization rule (for discussion)

A target is CANONICAL only if:
1. DOM and AX tree agree on role and accessible name,
2. geometry shows it visible, non-occluded (hit-test returns the element or a descendant) and stable across two frames,
3. where it has visible text, OCR of its rect matches the accessible name above a threshold,
4. an interaction probe (where safe) produces the recorded effect.

Otherwise it stays CANDIDATE with the list of disagreeing sensors recorded.
Confidence = f(number of independent agreeing sensors), never a hand-set constant.
Unsafe interactions (purchase, delete, submit, anything on an authenticated
or admin surface) are never probed without explicit owner authorization.

## Suggested build order (smallest step that changes the architecture first)

1. Single shared capture session that records CDP DOMSnapshot + AX tree + per-element rects + screenshot together, per viewport. (Rows 1-5, 10)
2. Fusion layer: join DOM node, AX node and rect into one record with per-sensor agreement flags. (Row 11)
3. Wire OCR on element rects as a verifier, not a discoverer. (Row 7)
4. Safe interaction probes + state fingerprinting for menus, tabs, modals. (Rows 8-9)
5. Target-level drift detection. (Row 12)
6. Benchmark harness: a fixed set of hard fixture sites (shadow DOM, iframes, canvas UI, SPA, overlays, cookie walls) with ground-truth maps, scored on precision/recall of targets. "Best in the world" needs a measurable claim; without a benchmark it is only a slogan.

## Out of scope / unknowns to check first

- Whether `render_page_snapshot.js` already captures more than found by grep.
- Whether the Tesseract weave in the crawl output does real OCR or is a naming stub.
- Competitor capability claims in the originating research were not independently verified here.
