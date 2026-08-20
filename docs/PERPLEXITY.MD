# Orb Weaver: Corpus and Deterministic Recompile Architecture

**Status:** Architecture refinement — no code, design only
**Date:** 2026-08-14
**Context:** Extends the GPT/Claude brainstorm Rounds 1-3 on pointer authority, scan-scope semantics, and plane discipline

---

## The Problem This Solves

Today, `preserve_client_crawl_intelligence()` builds derived artifacts directly from whichever crawl just finished. A one-page freshness check can replace a five-page Site World, lexical index, knowledge chunks, retrieval index, route classification, and pointer map — because every derived artifact is treated as mutable state written by the crawl completion path.

This is the same bug class that caused the pointer authority incident: a routine operation silently discards knowledge it didn't know it needed to protect, because the write boundary is "whatever this crawl produced," not "what the system actually knows."

The fix: separate what a crawl observed from what the system knows, and make every derived artifact a deterministic projection of preserved sources.

---

## Architecture Overview

```
CRAWL SNAPSHOT (immutable, per-crawl)
    ↓ scope-aware merge
CURRENT SITE CORPUS (latest-per-route, the only crawl-mutable state)
    ↓
    ├────────────────────────┐
    │                        │
AUTHORITY LEDGER          CONFIGURATION
(append-only events)     (risk profiles, policies)
    │                        │
    └────────┬───────────────┘
             ↓
DETERMINISTIC COMPILER
             ↓
COMPILED ORB WORLD + DERIVED ARTIFACTS (disposable, rebuildable)
             ↓
LIVE RUNTIME RESOLUTION (ephemeral, per-interaction)
             ↓
WEBSITE ORB
```

**Three mutation boundaries only:**
1. Corpus — updated by scope-aware crawl merge
2. Authority ledger — updated by owner/system decisions only
3. Runtime resolution — ephemeral live DOM state, never persists back

Everything else is a derived view, disposable and deterministically rebuildable.

---

## 1. Current Site Corpus

### What It Is

The corpus is the system's latest-known observation of every route on the site. It is the single source of observational truth. A crawl writes to the corpus and nothing else. Derived artifacts are never written by crawls.

### Route Identity Envelope

The corpus key is not merely a normalized path. It is a **route identity envelope** — enough context to prevent false merges:

```
route_identity:
    tenant_id:          which customer site
    canonical_host:     e.g., "example.com" (after redirect normalization)
    normalized_path:    e.g., "/pricing" (human-readable route key)
    query_policy:       how query params are treated
                        IGNORE  — /pricing?ref=email == /pricing
                        VARIANT — /products?category=tools is a distinct entry
                        KEYED   — /products?page=2 is a distinct entry
    render_context:     SERVER | CLIENT_SPA
    auth_context:       PUBLIC | AUTHENTICATED (for routes that differ by login state)
    locale_variant:     e.g., "en", "es" (for multi-locale sites)
    final_url:          actual URL after redirects (for provenance)
```

The `normalized_path` is the human-readable route key. The full envelope is the corpus identity. This prevents `/pricing` (public) from collapsing into `/account` (authenticated), or `/products?page=2` from collapsing into `/products?page=1`.

For a solo-maintained system, most of these fields will be `PUBLIC`, `SERVER`, and `IGNORE`/`VARIANT` most of the time. The envelope exists so that when you do encounter an authenticated route or an SPA, the corpus doesn't silently merge observations that represent different things.

### Corpus Entry Structure

```
CORPUS ENTRY (per route_identity)
├── route_identity:        (as above)
├── observation:
│   ├── source_crawl_id:   which crawl produced this observation
│   ├── observed_at:       timestamp
│   ├── http_status:       response status
│   ├── final_url:         after redirects
│   ├── title:             page title
│   ├── meta_description:  page meta
│   ├── content_hash:      hash of extracted text content
│   ├── structure_hash:    hash of DOM structure (element types, hierarchy, key attributes — NOT text)
│   └── extracted:
│       ├── text_content:      main body text
│       ├── heading_hierarchy: H1 → H2 → H3 structure
│       ├── links:             [{href, text, type: internal|external|anchor}]
│       ├── forms:             [{action, method, fields: [{name, type, label}]}]
│       ├── images:            [{src, alt, context}]
│       └── scripts:           [{src, type, async}]
├── pointer_candidates:
│   └── [{candidate_id, selector, element_type, text_label,
│         action_type, identity_hash, position_context, source_crawl_id}]
├── route_relationships:
│   ├── parent_routes:    which routes link here
│   ├── child_routes:     routes this page links to
│   └── nav_level:        where in site structure (root, section, subpage)
└── provenance:
    ├── first_observed:    when route was first discovered
    ├── last_observed:     when this observation was made
    ├── observation_count: how many times observed
    └── change_events:     [{timestamp, structure_changed: bool, content_changed: bool,
                             targets_added: [], targets_removed: []}]
```

### Target Identity Hash

Authority attaches to **target identity hashes**, not page-level structure hashes. A target identity hash is computed from:

```
target_identity_hash = hash(
    element_type,       # button, link, form, heading, etc.
    accessible_name,    # aria-label, visible text, or computed label
    role,               # ARIA role or implicit semantic role
    selector_context,   # stable ancestor path (not full DOM path)
    route_context       # which route this target lives on
)
```

This is deliberately **not** a full DOM selector hash. A button labeled "Buy Now" in the main content area of `/pricing` has a stable identity even if the surrounding DOM restructures, as long as those five properties hold. This means:

- Page structure changes → trigger **revalidation** of targets on that route
- Target identity unchanged → authority **still applies** (even if DOM around it changed)
- Target identity changed → authority is **STALE** for that specific target
- Route disappeared → authority is **STALE** for all targets on that route

Page-level `structure_hash` is a **revalidation trigger**, not an automatic staleness marker. This is important: if a page adds a new section but the "Contact Us" button keeps the same identity, the owner's approval of that button should survive without requiring re-review.

---

## 2. Coverage Certificate

Every crawl snapshot carries a **coverage certificate** — a structured record of what the crawl was actually capable of observing. This is the discriminator that prevents partial-scan amnesia.

```
coverage_certificate:
    declared_scope:    FULL_SITE | ROUTE_SET | TARGETED_RECOVERY | PREFLIGHT
    routes_observed:   [list of route identities actually visited and successfully rendered]
    routes_attempted:  [routes that were tried but failed — 404, timeout, render error]
    routes_skipped:    [routes known to exist but not in this crawl's scope]
    
    completion_status: COMPLETED_NORMAL | TRUNCATED_MAX_PAGES | TRUNCATED_MAX_DEPTH |
                        TRUNCATED_TIMEOUT | TRUNCATED_ERROR | PARTIAL
    
    frontier_exhausted: bool    # did the link/sitemap frontier actually run to completion?
    max_pages_hit:      bool
    max_depth_hit:      bool
    robots_blocked:     [routes blocked by robots.txt]
    
    redirects:          [{from, to, permanent}]
    not_found:          [routes that returned 404]
    
    scope_routes:       [for ROUTE_SET, the explicit list of routes this crawl intended to cover]
```

### How Coverage Determines Merge Behavior

```
For each route in the corpus:
    Is this route in the crawl's routes_observed?
        YES → REPLACE corpus entry with new observation
    
    Is this route in routes_attempted (failed)?
        YES → Mark corpus entry as OBSERVATION_FAILED (preserve previous observation)
              Do NOT delete or replace
    
    Is this route in routes_skipped or not mentioned?
        PRESERVE unchanged
        (Absence is not evidence — the crawl didn't look here)
    
    Special: FULL_SITE + completion_status == COMPLETED_NORMAL + frontier_exhausted == true
        Routes in corpus but NOT in routes_observed and NOT in routes_attempted
        → These routes may have been genuinely removed from the site
        → Mark as DEPRECATED (preserved with deprecated status, not deleted)
        → Authority decisions for deprecated routes become STALE
    
    FULL_SITE + TRUNCATED_* (any truncation):
        Treat as ROUTE_SET — unobserved routes are PRESERVED
        (The crawl intended full coverage but couldn't prove it)
```

The principle: **absence is evidence only when the coverage certificate proves the route was within scope and observable.** A truncated full-site crawl is treated as a route-set crawl for safety purposes.

---

## 3. Scope-Aware Merge

The merge operation takes an immutable crawl snapshot and updates the corpus. This is the **only** function that writes to the corpus.

### Merge Contract

```
Input:  crawl_snapshot (immutable, with coverage_certificate)
        current_corpus (mutable)
Output: updated_corpus
        change_set (list of what changed, for the compiler)

Rules:
1. Only routes in routes_observed may update the corpus
2. Routes not observed are preserved unchanged
3. DEPRECATED marking requires FULL_SITE + COMPLETED_NORMAL + frontier_exhausted
4. Each updated route records a change_event in provenance
5. The change_set notes: routes_added, routes_updated, routes_deprecated,
   targets_added, targets_removed, identity_hashes_changed
6. The merge is idempotent: merging the same snapshot twice produces the same result
7. The merge is atomic: either all updates apply or none do
```

### What This Replaces

The current `preserve_client_crawl_intelligence()` function, which builds a payload from the current crawl's `stored_pages` and writes derived artifacts directly. That function is split into:

1. `merge_crawl_into_corpus(crawl_snapshot, corpus)` → scope-aware merge, produces change_set
2. `recompile_derived_artifacts(corpus, authority_ledger, config, change_set)` → deterministic compile

The crawl completion path becomes: crawl → snapshot → merge into corpus → trigger recompile. The crawl never touches derived artifacts directly.

### What This Replaces in Pointer Authority

The current `merge_canonical_pointer_authority()` function becomes unnecessary in its current form. Authority is no longer merged — it is **composed at compile time**. The compiler reads the authority ledger and the corpus together and produces the effective authority state. No separate merge function for authority during crawl completion.

---

## 4. Authority Ledger

### Event-Sourced Decisions

The authority ledger is an append-only event log. Decisions are never mutated. Applicability is derived at compile time.

```
AUTHORITY EVENT:
    timestamp:        when the decision was made
    event_type:       OWNER_APPROVED | OWNER_REJECTED | SYSTEM_AUTO_APPROVED |
                      SYSTEM_AUTO_REJECTED | IDENTITY_CHANGED | AUTHORITY_REVOKED
    target_identity:  the identity_hash this decision applies to
    route_identity:   which route this target was on when decided
    decided_by:       owner | system | automated_rule
    prior_state:      what the effective authority was before this event
    evidence_ref:     link to the observation that supported this decision
    notes:            optional human notes
```

### Why Event-Sourced

- **Decisions are permanent.** "Owner approved identity H123 at T1" never disappears, even if the target later changes.
- **The projection is disposable.** If the current authority state gets corrupted, replay the event log.
- **Full audit trail for free.** Every decision has provenance: who, when, what was the prior state.
- **"Authority is monotonic unless identity changes" becomes a property of the event log**, not something each function independently maintains.

### Authority Projection at Compile Time

The compiler reads the event log and produces the current effective authority state:

```
For each target in the corpus's pointer_candidates:
    events = authority_ledger.events_for(target.identity_hash)
    
    If no events exist:
        authority_state = UNREVIEWED
    
    If OWNER_APPROVED exists:
        Does target.identity_hash still match the current corpus observation?
            YES → authority_state = OWNER_VERIFIED
            NO  → authority_state = STALE (flag for reconciliation)
    
    If OWNER_REJECTED exists (and no subsequent OWNER_APPROVED):
        Does target.identity_hash still match?
            YES → authority_state = OWNER_REJECTED
            NO  → authority_state = STALE_REJECTED (no longer applicable)
    
    If IDENTITY_CHANGED event exists:
        The old authority decision is STALE
        The new identity is UNREVIEWED (unless a new decision was made)
```

The projection is computed, never stored. If the corpus changes, the projection changes on next recompile. No authority merge function needed.

---

## 5. Deterministic Compiler

### Inputs

| Input | Owner | Mutability |
|-------|-------|-----------|
| Current Site Corpus | Crawl merge | Updated on scoped crawl |
| Authority Ledger | Owner/system decisions | Append-only |
| Configuration | Owner settings | Editable by owner |
| Change Set | Corpus merge output | Transient |

### Outputs (All Derived, All Disposable)

| Artifact | What It Contains |
|----------|-----------------|
| Site World | Route graph, page summaries, entity relationships, compiled knowledge |
| Lexical Index | Search terms mapped to routes and targets |
| Knowledge Chunks | Page content chunked for retrieval |
| Retrieval Index | Semantic retrieval surface for the ORB |
| Pointer Observation Map | Current pointer candidates from corpus (replaces pointer_plot_map.json) |
| Route Classification | Route types: landing, product, contact, form, etc. |
| Source Validation | Verified sources and provenance chain |
| Quality Summary | Coverage metrics, freshness, health indicators |
| Readiness Matrix | Per-capability readiness (knowledge, guidance, pointing, action, voice, tool, deployment) |
| Compiled ORB World | Composite view consumed by the ORB runtime |

### Compilation Modes

**Full Recompile:** Rebuild everything from scratch. Used after significant changes, as recovery, or on first compile. Inputs: full corpus + full authority ledger + config.

**Incremental Recompile:** Rebuild only artifacts affected by changed routes. Inputs: full corpus + full authority ledger + config + change_set.

```
Incremental logic:

changed_routes = change_set.routes_updated + change_set.routes_added
deprecated_routes = change_set.routes_deprecated
identity_changes = change_set.identity_hashes_changed

For each changed_route:
    Rebuild knowledge chunks for that route
    Update lexical index (remove old terms for this route, add new)
    Update retrieval index for this route
    Rebuild pointer candidates for this route
    Update route relationships (if links changed)
    Recompile authority applicability for this route's targets

For each deprecated_route:
    Remove from lexical index
    Remove from retrieval index
    Mark pointer candidates as DEPRECATED
    Mark authority decisions as STALE (identity no longer exists)

After per-route updates:
    Rebuild aggregate artifacts:
        - Route graph (from updated route relationships)
        - Quality summary (recompute coverage/freshness)
        - Readiness matrix (recompute per-capability)
    Compile ORB World (composite view)
```

The aggregate rebuild touches everything but is cheap — it's reassembling from per-route compiled results, not re-extracting from raw pages.

### Determinism Guarantee

Same inputs always produce identical outputs. This means:
- Running the compiler twice is a valid correctness check
- A corrupted derived artifact can be verified by recompilation
- Debugging is possible: "does the ORB World match a fresh compile from the same corpus + authority?"

### Compiled-From Manifest

Every derived artifact carries a manifest:

```
compiled_from:
    corpus_version:        hash of current corpus state
    authority_version:     hash of authority ledger through latest event
    compiler_version:      compiler code version
    change_set_ref:        which change_set triggered this compile (if incremental)
    compiled_at:           timestamp
    routes_included:       [list of route identities in this compile]
```

This gives deterministic rebuild proof. If a published ORB World looks wrong, you can check whether its `compiled_from` manifest matches the current corpus + authority versions. If they don't match, recompile. If they do match, the problem is in the compiler logic or the source data, not in a stale cache.

---

## 6. Runtime Layer (Live Resolution)

The compiled ORB World is what the ORB runtime consumes, but it is not the final truth for physical actions. At runtime:

```
ORB World says: target_123 on /pricing has may_point: true
    ↓
Live DOM check: does an element matching target_123's identity exist right now?
    ↓
YES → POINT is allowed
NO  → target is LIVE_STALE
      POINT is not allowed
      Trigger runtime recovery (re-observe, attempt re-acquire)
      If recovery fails → escalate, do not Ping
```

Live resolution is **ephemeral**. It never writes back to the corpus or authority ledger. It only affects the current interaction. The runtime can cache live resolution results within a session but must not persist them as canonical state.

### Effective Permission Computation

The ORB's effective permission for any action is the intersection of three independent truths:

```
OBSERVATION (from corpus):
    "Does this target exist in our latest observed site knowledge?"
    
AUTHORITY (from ledger projection):
    "Has the owner/system permitted this action for this target?"
    
LIVE (from runtime DOM):
    "Is this target physically present in the live interface right now?"

EFFECTIVE PERMISSION = OBSERVATION ✓ AND AUTHORITY ✓ AND LIVE ✓
```

No single signal substitutes for the other two. This is the principle that prevents the ORB from pointing at something it's not authorized for, or acting on something that no longer exists.

---

## 7. Provenance and Audit Chain

Full traceability from ORB action back to source observation:

```
"Why did the ORB point at this target?"
    ↓
Runtime action log: pointed at target_123, live-verified, timestamp T5
    ↓
ORB World version at T5: compiled_from manifest → corpus_version V12, authority_version A7
    ↓
Corpus V12: route /pricing, observation from crawl 50, structure_hash H789
    ↓
Authority A7: OWNER_APPROVED event for identity_hash H123, timestamp T1, decided_by: owner
    ↓
Crawl 50: snapshot with coverage certificate, observed /pricing at T0
```

Every link in the chain is recoverable. If any link is missing, the action should not have been permitted.

---

## 8. Failure Modes and Recovery

| Failure | Impact | Recovery |
|---------|--------|----------|
| Corpus corruption | Observations lost | Re-merge from crawl snapshots (snapshots are immutable, stored separately) |
| Authority ledger corruption | Decisions lost | Replay from event log backup, or restore from backup |
| Derived artifact corruption | Site World, index, pointer map damaged | Recompile from corpus + authority (trivial, deterministic) |
| Partial recompile failure | Some derived artifacts stale | Re-run (idempotent, deterministic — safe to retry) |
| Bad crawl data | One route's observation is wrong | Only affects that route. Recompile produces bad artifacts for that route only. Re-crawl the route to fix. |
| Concurrent crawl attempts | Two crawls finish near-simultaneously | Serialize corpus merges. Each produces its own snapshot. Merge sequentially. Second merge may produce additional changes. |
| Compiler bug | Derived artifacts are wrong | Fix compiler, recompile. Source data (corpus + authority) is unaffected. |
| Runtime live check fails | Target not found in live DOM | ORB does not point. Triggers recovery or escalation. No persistent state change. |

The critical property: **only two things are truly precious — the corpus (observations) and the authority ledger (decisions). Everything else is rebuildable.**

---

## 9. Migration Path

Designed for a solo maintainer. Each phase delivers a safety property before moving to the next.

### Phase 1: Corpus as Read Projection (Lowest Risk)

- Build the corpus as a **read-only projection** over existing `stored_pages`
- The corpus is initially "latest stored_pages per route across all crawls"
- Don't change any publication paths yet
- Build the projection, verify it matches current derived artifacts
- **Safety property proven:** the corpus accurately represents current site knowledge

### Phase 2: Route Publication Through Corpus

- Change `preserve_client_crawl_intelligence()` to:
  1. Merge crawl observations into the corpus (scope-aware, with coverage certificate)
  2. Trigger recompile from corpus for affected routes only
- Derived artifacts are now produced by the compiler, not directly by the crawl
- **Safety property proven:** a one-page crawl cannot shrink the current world
- Do not rebuild every artifact system at once — move artifact production behind the compiler **one class at a time**:
  - First: pointer observation map (directly addresses the current bug class)
  - Then: lexical index, knowledge chunks
  - Then: retrieval index, route classification
  - Then: Site World, readiness matrix, compiled ORB World

### Phase 3: Separate Authority as Event Log

- Migrate `pointer_authority.json` to the event-sourced ledger
- Import current decisions as the initial event set
- The compiler joins corpus + authority at compile time
- Authority is never directly written by crawl paths
- **Safety property proven:** a crawl cannot modify the authority ledger

### Phase 4: Remove Direct Artifact Writes

- Once all derived artifacts are produced by the compiler, remove the direct write paths from crawl completion
- The only writers are: corpus (crawl merge), authority ledger (owner decisions), runtime (live resolution cache)
- **Safety property proven:** the three-boundary architecture is enforced structurally, not by convention

### Phase 5: Scan Scope Semantics

- Formalize scope types: FULL_SITE, ROUTE_SET, TARGETED_RECOVERY, PREFLIGHT
- Implement coverage certificates
- PREFLIGHT scans discover but do not publish canonical state
- TARGETED_RECOVERY updates evidence for specific identities but does not rewrite Site World
- **Safety property proven:** narrow observations update only what they observed

---

## 10. System Properties Locked

These are the invariants the architecture enforces structurally:

1. **A narrow observation may update what it observed. It may never erase knowledge or authority outside the scope it was capable of observing.**

2. **Derived artifacts are never state. They are always views compiled from preserved sources.**

3. **Authority decisions are monotonic. An ordinary crawl cannot transform OWNER_VERIFIED into NEW, or OWNER_REJECTED into UNCERTAIN. Only an identity change makes a decision STALE, and staleness requires reconciliation — not forgetting.**

4. **Effective permission requires three independent truths to agree: observation, authority, and live verification. No single signal substitutes for the other two.**

5. **Absence is evidence only when the coverage certificate proves the route was within scope and observable.**

6. **The corpus and authority ledger are the only precious state. Everything else is recoverable through deterministic recompilation.**

---

## 11. Relationship to Existing Orb Weaver Doctrine

This architecture directly supports the ORBS Foundational Architecture Standard's compilation requirement (Section 13):

- **Persistent portion** (Core Four baseline, professional identity, doctrine) → lives in configuration, immutable across compiles
- **Deployment-specific portion** (Site World index, route graph, products, policies, terminology) → produced by the compiler from corpus + authority
- **Turn-specific portion** (current page, route, visible controls, prior answers, pointer target state, live verification) → assembled at request time from the compiled ORB World + live runtime resolution

The turn-specific working set is assembled from the compiled ORB World, not from the full corpus. The ORB "knows the whole site" because it can deterministically retrieve from the compiled world, not because every token is loaded into every inference call. This keeps the hot voice path small and fast — the 1.5B local model handles articulation and ambiguity, while the heavy intelligence lives in the precompiled world.

---

## Open Questions for Next Round

1. **SPA route observation**: How does the corpus handle routes that are client-side rendered? The crawler already renders pages, but the corpus entry may need a `render_context: CLIENT_SPA` flag and potentially different staleness rules (DOM might be dynamic by design).

2. **Authenticated route variants**: Routes that differ by login state need separate corpus entries. How does the crawler authenticate, and how are auth-context variants managed without duplicating the entire corpus?

3. **Multi-tenant corpus isolation**: Each customer site has its own corpus. Is the corpus a per-tenant data structure, or is there a shared corpus with tenant_id in the route identity envelope? (The envelope suggests the latter, but the isolation properties of the former may be safer.)

4. **Corpus pruning policy**: Crawl snapshots are immutable and accumulate. What's the retention policy? Keep last N crawls? Keep all crawls that contributed to the current corpus state? Keep a change log instead of full snapshots?

5. **Compiler as service vs. inline**: Should the compiler run inline (blocking crawl completion) or as a separate async service? Inline is simpler for a solo maintainer. Async allows crawl completion to return faster but introduces a "compile pending" state.
