# Orb Weaver capability status — review packet

This is the complete capability inventory for the current repository review. The canonical source is [`Orb Weaver — Master Capability List.html`](../../Orb%20Weaver%20%E2%80%94%20Master%20Capability%20List.html). The inventory contains 22 categories and 161 atomic capabilities.

Status language is evidence-based:

- **Verified** — current repository code and persisted crawl evidence support the capability.
- **Partial** — code or extraction exists, but the complete evidence contract is not satisfied.
- **Blocked** — a prerequisite stage or recovery action is preventing the capability from becoming authoritative.
- **Runtime verification required** — crawler evidence cannot fabricate live DOM geometry or interaction truth.
- **Runtime capability not crawl-verified** — the capability belongs to the manufactured runtime/product layer and requires Live Test evidence.

## Current Crawl #4 rollup

The existing Crawl #4 artifact contains 34 fetched pages, 833 extracted pointer targets, 86 guidance-eligible candidates, 317 uncertain targets, and 67 route/locator conflicts. It reached login walls on protected routes. JavaScript rendering completed 30 of 32 required renders. Pointer verification and runtime guidance are blocked until live verification and recovery run.

The resulting capability ledger is **partial**: 2 verified categories, 7 partial, 2 blocked, 1 requiring runtime verification, and 10 runtime-only categories not crawl-verified. These counts are mutually exclusive and reconcile with all 22 category headers.

## Complete capability inventory

### 1. Discovery & Crawl Intelligence — partial

Domain/subdomain discovery; sitemap discovery & parsing; robots.txt; route discovery (sitemap-listed, discovered outside sitemap, unresolved); internal/external link inventory; redirect & redirect-chain detection; broken-link detection; HTTP status collection; canonical URL collection; duplicate/query-string/trailing-slash route variants; orphan-page detection; authenticated/protected route scanning where permitted; route depth & ownership; application-route discovery; API-route inventory; public endpoint mapping; capability endpoint discovery; incremental rescan; targeted (page/route/workflow) rescan; full-site rescan; scan timestamping, versioning, provenance, confidence tracking; scan-result validation, deduplication, normalization, indexing, and persistence; scan audit logging.

### 2. Rendering & Live DOM Intelligence — blocked

Per-route render success/failure with cause; hydration errors; client-routing failures; missing chunks; console errors, uncaught exceptions, network failures; DOM element inventory; DOM-anchor collection; visible-label collection; data-attribute collection; visible/hidden/disabled/interactive state; duplicated or unstable/generated selectors; parent-child and region relationships; bounding geometry and viewport status.

### 3. Content & Semantic Intelligence — verified from crawl evidence

Content extraction and classification; page-title and meta-description collection; page-purpose classification; page-type classification; headings/sections/content blocks; products, services, prices, features, FAQs, policies, contact/business/location/hours information; terms/privacy/legal-page discovery; documentation and downloadable-file discovery; document metadata; image discovery and alt-text collection; video/audio discovery and media metadata; JSON-LD, Schema.org, Open Graph; social links; search-engine metadata; site-search discovery and behavior mapping; terminology, synonyms, aliases, visitor-language mapping; intent-to-page/section/control/workflow mapping; contradiction detection; semantic completeness scoring.

### 4. Design Intelligence — partial

Visual hierarchy; layout/grid analysis; spacing rhythm; typography system and font roles; color system and contrast; brand consistency, brand-name collection, logo and brand-asset discovery, imagery style; component and section-pattern classification; page-template classification; CTA prominence and trust-element placement; responsive/breakpoint behavior; mobile versus desktop comparison; animation/motion inventory; design-token extraction; visual-signature generation.

### 5. Commerce & Catalog Intelligence — partial

Product/SKU/variant discovery; product-name, description, and feature collection; pricing collection and pricing dictionary; availability; specifications and options; category structure; product/service relationships; catalog generation; inventory-change tracking with structural-diff escalation. Crawl #4 produced zero catalog entries, so zero is reported as incomplete evidence rather than proof that no catalog exists.

### 6. Interface & Workflow Intelligence — partial

Navigation-menu discovery; buttons, links, CTAs, forms, inputs, submit/search controls; modals, dialogs, accordions, tabs, dropdowns, carousels, pagination, and menu controls; login/signup/account/cart/checkout/contact/download/media controls; authentication, signup, login, contact, purchase, cart, checkout, and lead-generation funnel mapping; multi-step workflow mapping; required-field and validation-rule detection; error/success/confirmation-state collection; navigation/click/scroll/form action mapping; route-transition and action-result mapping; conversion-path mapping; broken/abandoned-path detection.

### 7. LiDAR / Pointer Intelligence — runtime verification required

Bounding boxes, screen geometry, viewport position, scroll containers, and scroll-target mapping; fixed/sticky elements, overlays, z-order/occlusion; responsive layout and breakpoint geometry changes; pointer-target extraction; pointer-anchor, pointer-manifest, and pointer plot-map generation; target aliases; target-to-route/section/control mapping.

### 8. Selective Pointer Authority — blocked pending verification/recovery

Semantic-reference versus live-guidance distinction; guidance eligibility gating; confidence gating before a live Ping; target-loss recovery; no-false-Ping enforcement; candidate correction and promotion path.

### 9. Tesseract Weave — partial

OCR and intelligence extraction from images, PDFs, Office documents, and other non-DOM sources, feeding the same content, semantic, and catalog pipelines as live-page extraction.

### 10. Site World / SKG Compilation — verified for current crawl artifacts

Site knowledge graph construction; route/page/section/control/product/service/workflow capsule generation; current-page awareness; physical-navigation map; page-to-page, product-to-page, service-to-page, FAQ-to-page, and control-to-workflow relationships; capability mapping; allowed-action mapping; stage and stage-transition mapping; Stage Governor input generation.

### 11. Vault Intelligence — runtime capability not crawl-verified

A Priori verified knowledge versus A Posteriori learned, promotion-gated knowledge; structured catalog/pricing stores; interaction memory and verified outcomes; verified-site-state storage; semantic retrieval; self-pruning, merge/compress/weaken/retire logic.

### 12. TPC / Runtime Cognition — runtime capability not crawl-verified

Deterministic fast-path answers from Vault/catalog; LLM escalation only when required; intent recognition; contextual articulation; capability selection governed by the existing cognitive-engine/Doctrine architecture.

### 13. Voice & Visitor Guidance — runtime capability not crawl-verified

STT/TTS; browser playback; voice selection and fallback; listening/speaking state; interruption handling; low-latency response; guided focus, scroll/move/highlight; visitor-approved actions; MORB-assisted guidance; safe handoff and recovery when guidance fails.

### 14. ORB Personality & Physical Design — runtime capability not crawl-verified

Factory-default ORB; skins; opacity/motion doctrine; animation; behavior packs; voice packs; sound effects; idle, presence, and speech behavior; custom identity.

### 15. Manufacturing Pipeline — runtime capability not crawl-verified

Project → weave → Site World → catalog → pointer map → A Priori compile → owner policy → skin → voice → behavior → Vault → runtime assembly → release manifest; site-specific ORB knowledge, tool, pointer, navigation, and workflow configuration; articulation-context and capability-snapshot generation.

### 16. Dock Station — runtime capability not crawl-verified

Owner configuration for appearance, behavior, conversation review, intelligence, speech, tools, profiles, deployment, statistics, diagnostics, and Live Test entry.

### 17. Live Test & Release QA — runtime capability not crawl-verified

Site identity and domain binding; Site World binding; pointer integrity; voice; cognition; Vault isolation; policy compilation; skin fallback; secrets check; release validation.

### 18. Release & Deployment — runtime capability not crawl-verified

Downloadable ORB package; compiled-site-package, ORB deployment-data, ORB update-data, and website-intelligence-package generation; release versioning and manifest; universal loader script; install snippet; runtime endpoint binding; updates and rollback.

### 19. Marketplace — runtime capability not crawl-verified

Skins, voices, behavior packs, sound packs, enhancements, services, and upgrade packages.

### 20. Lifecycle & Self-Maintenance — partial

New, removed, and changed page/control/form/navigation/workflow detection; stale-content and stale-route detection; Site World and pointer-map refresh; learned-correction promotion; self-pruning.

### 21. Auditing & Reporting — partial

Crawl-report generation; endpoint-map generation; SEO; accessibility where measurable; technical health; performance metrics where instrumentable; security/trust signals; design audit; pointer, route, control, and workflow audit. This is explicitly not a penetration-testing tool.

### 22. Manufacturing Tiers & Web Weaver — runtime capability not crawl-verified

Basic, Enhanced, and Platinum manufacturing configurations with increasing intelligence, customization, and guidance depth; Web Weaver using the same intelligence stack to design/build a new site when no existing site is worth upgrading.

## Remaining implementation/wiring work

1. Complete the crawl orchestration contract: authenticated-session acquisition for protected dashboards/workspaces, route-depth/frontier completion, and rerun of the two failed JavaScript renders.
2. Persist and surface complete browser diagnostics, including hydration/client-route/chunk classification and per-route failure artifacts.
3. Run independent live DOM pointer verification, resolve 317 uncertain targets and 67 conflicts, and promote only verified targets into runtime guidance.
4. Complete LiDAR geometry verification for responsive layouts, overlays, sticky/fixed elements, scroll containers, ORB/caption footprint, and hard interactive-control exclusions.
5. Wire full workflow/action evidence: click, scroll, form, validation, modal, route-transition, success/error, and abandoned-path tests.
6. Complete Tesseract/OCR and document pipelines, then merge their evidence into Site World, Vault, catalog, and Reports.
7. Finish authenticated Site World/Vault/TPC/voice/live-guidance proof with customer-isolation and owner-policy evidence.
8. Connect manufacturing output to a generated package containing the current Site World, pointer map, catalog, Vault/SKG, runtime language, deployment data, update data, manifests, loader contract, and validation results.
9. Run Live Test and release QA before treating a package as downloadable/deployable/installable.

## Template clone audit

`manufacturing/templates/Website_Orb_Final` currently contains the runtime source, compiled Site World/pointer artifacts, backend/frontend package, Vault/TPC material, install documentation, compiler, validator, and tests. Its validator passes with 31 routes and 858 pointer records.

The template is structurally ready for compilation, but it is not a substitute for a fresh customer-specific build. Its compiled artifacts must be regenerated from the customer crawl after pointer verification, Site World compilation, policy compilation, and Live Test. Docker remains intentionally unchanged until that acceptance step.

## Live Test promotion mechanism

Live Test is a separate runtime evidence artifact, not an implied crawl stage. When it passes, it persists a `runtime_evidence` object on the crawl/package containing `status: COMPLETE`, the tested package/site identity, evidence artifact references, and an explicit `verified_categories` list. The capability ledger is then rebuilt with that object. Only categories explicitly listed by a completed Live Test can move from `runtime_capability_not_crawl_verified` to `verified`; a passing deployment gate alone does not promote categories.
