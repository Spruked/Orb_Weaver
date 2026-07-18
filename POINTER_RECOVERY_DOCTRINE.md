# Pointer Recovery Doctrine

## Operation boundary

A Pointer Recovery Pass is not a recrawl. It preserves and reuses the compiled Site World, source crawl, and baseline Pointer Map. It asks only why individual pointer identities could not be verified.

```text
Public Crawl
  -> Site World
  -> Pointer Extraction
  -> Confidence Analysis
  -> Pointer Recovery Pass when required
  -> Visual/Human Review for unresolved records
  -> Preflight
```

Only one automatic recovery attempt is allowed per ORB Scan. A second automatic loop is prohibited.

## Automatic gate

Recovery is required when any condition is true:

- stable ratio is below 70%;
- uncertain ratio exceeds 25%;
- fewer than 10 pointers are stable;
- duplicate/conflict count exceeds 3.

The gate is reported as `POINTER_RECOVERY_REQUIRED`. Website knowledge and speech remain available. Pointer actions remain limited to `VERIFIED` and `STABLE` records whose live DOM identity matches. Deployment Preflight does not pass.

## Evidence pass

The focused Chromium pass:

- visits only selected routes from the baseline map;
- uses independent desktop and mobile contexts;
- performs two clean renders per route and viewport;
- waits for hydration/network idle, fonts, animations, and layout stabilization;
- walks long pages in viewport-sized scroll segments and preserves screenshots;
- observes only visible, actionable or guideable elements;
- excludes hidden, inert, decorative, framework-generated, and duplicate candidates;
- favors durable IDs, hrefs, accessible names, roles, and DOM ancestry;
- reconciles candidate identity and locator stability without rebuilding Site World.

The campaign configuration targets `/` and `/investor` explicitly.

## Finding taxonomy and subreasons

Recovery preserves the shared finding taxonomy:

- `CONFIRMED`: durable pointer identity is consistent across renders;
- `DYNAMIC`: pointer identity is stable while content changes;
- `TRANSIENT`: pointer availability depends on a responsive or temporary state;
- `CONFLICT`: multiple semantic targets cannot be uniquely reconciled;
- `UNVERIFIED`: the pass cannot prove a safe pointer identity.

Technical explanations remain subreasons, including:

- `layout_not_stable`
- `selector_not_durable`
- `element_not_visible`
- `duplicate_semantic_target`
- `scroll_section_unresolved`
- `cross_route_mismatch`
- `responsive_variant`
- `decorative_only`

Dynamic content is not treated as structural instability. A price or viewer count may change while its durable pointer remains valid.

## Pointer health

Pointer records carry an operational health state:

```text
NEW -> VERIFIED -> RECOVERED -> OWNER_VERIFIED
                              -> DEPRECATED -> REMOVED
```

The current implementation creates `NEW`, `VERIFIED`, and `RECOVERED` states. Owner verification will promote reviewed records to `OWNER_VERIFIED`. Sentinel will own transitions to `DEPRECATED` and `REMOVED` when deployed identities drift or disappear.

## Separate reporting

The Projects interface contains a dedicated **Pointer Plot Map** report. It reports these independently:

1. Initial Pointer Extraction: total, initially safe count, stable ratio, and recovery trigger.
2. Pointer Recovery Pass: lifecycle status, attempt 1/1, routes, renders, promoted count, unresolved count, finding classes, and reason counts.

Unresolved records create a critical visual-review item. The pass never silently retries.

## Campaign validation — 2026-07-18

Campaign crawl job `#24` is a legacy crawl, not a lifecycle-evaluated ORB Scan. Its initial map contains 137 extracted pointers: 1 safe `STABLE` record and 136 `UNCERTAIN` records. It is therefore `POINTER_RECOVERY_REQUIRED`; zero duplicate IDs and a nonzero record count do not constitute pointer readiness.

The non-publishing proof pass against `campaign.orbweaver.spruked.com` produced:

- 8 independent renders;
- 104 viewport segments;
- 270 visible/actionable candidate observations;
- 28 pointers promoted;
- 109 pointers retained for visual review;
- finding result: 27 `CONFIRMED`, 1 `DYNAMIC`, 5 `TRANSIENT`, 73 `CONFLICT`, and 31 `UNVERIFIED`;
- pointer health: 28 `RECOVERED`, 109 `NEW` records awaiting visual review.

The proof recovery is non-canonical. The canonical customer map was not overwritten because legacy job `#24` has no lifecycle evidence chain. A new lifecycle ORB Scan is still required; it will create and report its automatic Pointer Recovery Pass through the lifecycle system.

## Packaging direction

- Standard: initial scan, one Pointer Recovery Pass, Preflight.
- Professional: Standard plus owner visual verification and human-review assistance.
- Enterprise: advanced verification, ongoing owner review, and multi-site packages.
