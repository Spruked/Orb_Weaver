# Orb Weaver: Corpus and Deterministic Recompile Architecture (v3 — Round 4 Converged)

**Status:** DRAFT — pending final convergence
**Date:** 2026-08-14
**Context:** Incorporates GPT Round 4 review (20 points), Claude Rounds 1-3, and code-verified analysis of the actual Orb Weaver repository

---

## Core Doctrine

The pointer problem was a symptom of a missing state-ownership doctrine across Orb Weaver. The solution is not more confidence thresholds. It is making it structurally clear what is evidence, what is a decision, what is learned truth, and what is merely a rebuildable representation.

---

## Orb Weaver State Taxonomy

All persistent data in Orb Weaver falls into exactly four categories:

### 1. Evidence — "What was actually observed?"
Crawl snapshots, route observations, runtime candidate corrections, audit measurements, tool observations. Has lifecycle, retention, and provenance. Precious — cannot be regenerated.

### 2. Decisions — "What has been verified/authorized?"
Owner authority, owner configuration, owner corrections, permissions, approved terminology, deployment decisions. Has lifecycle, retention, and provenance. Precious — cannot be regenerated.

### 3. Learned Verified State — "What has been confirmed through use?"
Confirmed outcomes, successful fixes, persistent ORB memory, proven relationships. Precious — accumulated through real operation, not rebuildable from first principles.

### 4. Derived Views — "What representation did Orb Weaver compile?"
Site World, retrieval indexes, pointer runtime map, quality summaries, readiness, recommendations, compiled ORB World. Always rebuildable from Evidence + Decisions + Learned State + Configuration.

**The rule:** Evidence, Decisions, and Learned Verified State are precious. Derived intelligence is rebuildable. A narrow observation may update what it observed. It may never erase knowledge, authority, or learned state outside the scope it was capable of observing. And derived artifacts are never state — they are always views compiled from the things that are.

---

## Architecture Overview

```
                    WEBSITE
                       ↓
               IMMUTABLE OBSERVATION
                       ↓
              SCOPE / COVERAGE CONTRACT
                       ↓
                CURRENT SITE CORPUS
                       ↓
       ┌───────────────┼────────────────┐
       ↓               ↓                ↓
   EVIDENCE       AUTHORITY         CONFIG/POLICY
   history         ledger
       └───────────────┼────────────────┘
                       ↓
              DETERMINISTIC COMPILER
                       ↓
                COMPILED ORB WORLD
                       ↓
                RETRIEVAL WORKING SET
                       ↓
                 WEBSITE ORB
                       ↓
               LIVE DOM VERIFICATION
                       ↓
                 GUIDED ACTION

Runtime feeds candidate evidence back upward:
    LIVE RECOVERY
          ↓
    candidate correction (persistent evidence inbox)
          ↓
    evidence/promotion pipeline
          ↓
    future corpus observation
```

The runtime can persist candidate evidence but never directly mutate canonical observation or authority. This preserves the existing promotion doctrine where `saveCandidateCorrection()` records divergent findings for later evaluation without letting one visitor session rewrite canonical truth.

---

## Three Mutation Boundaries (Revised)

1. **Corpus** — updated by scope-aware crawl merge only
2. **Authority ledger** — updated by owner/system decisions only
3. **Runtime** — ephemeral live DOM state, but may emit persistent candidate corrections to an evidence inbox

Everything else is a derived view, disposable and deterministically rebuildable.

**Critical revision from v2:** Runtime is not forbidden from persisting. It is forbidden from persisting canonical state. The distinction:

```
LIVE RUNTIME STATE
ephemeral (per-session)

        ↓ may emit

RUNTIME OBSERVATION EVENTS / CANDIDATE CORRECTIONS
persistent evidence inbox (survives session)

        ↓ never directly promotes

CORPUS RECONCILIATION / PROMOTION
separate process evaluates repeated evidence

        ↓ may eventually update

CORPUS (through the sanctioned merge path)
```

This preserves Orb Weaver's existing `CandidateCorrection` architecture where runtime writes correction records but never directly changes the authoritative `PlotRecord`.

---

## 1. Current Site Corpus

### Route Identity Envelope (Simplified)

```
route_identity:
    site_id:              tenant/customer identity
    canonical_host:       e.g., "example.com"
    normalized_route:     e.g., "/pricing" (human-readable route key)
    variant:
        query_signature:  DEFAULT | specific query pattern
        auth_context:     DEFAULT | AUTHENTICATED
        locale:           DEFAULT | "en" | "es"
        render_context:   DEFAULT | CLIENT_SPA
```

Most routes get `variant = DEFAULT`. Only when Orb Weaver discovers meaningful variation does it materialize a separate variant entry. This prevents the common path from becoming cumbersome while retaining the ability to distinguish `/account` (public) from `/account` (authenticated), or `/en/pricing` from `/es/pricing`.

### Corpus Entry Structure (Revised)

```
CORPUS ENTRY (per route_identity)
├── route_identity:        (as above)
├── observation:
│   ├── source_crawl_id
│   ├── observed_at
│   ├── http_status
│   ├── final_url
│   ├── title, meta_description
│   ├── content_hash
│   ├── structure_hash
│   └── extracted: text_content, heading_hierarchy, links, forms, images, scripts
├── pointer_candidates: [{candidate_id, selector, element_type, text_label,
│         action_type, identity_hash, position_context, source_crawl_id}]
├── route_relationships: parent_routes, child_routes, nav_level
├── observation_lifecycle:       ← REVISED
│   ├── latest_attempt:          what the most recent crawl saw (may be broken)
│   ├── latest_accepted_observation: last good observation (may differ from latest_attempt)
│   ├── first_observed
│   ├── observation_count
│   └── change_events: [{timestamp, structure_changed, content_changed,
│         targets_added, targets_removed, identity_hashes_changed}]
└── route_disappearance_state:   ← NEW
    ACTIVE | SUSPECTED_MISSING | CONFIRMED_GONE | DEPRECATED
```

### Latest-Good Observation (Revision #6)

The corpus preserves the latest accepted observation separately from the latest attempt. If today's crawl of `/pricing` returns HTTP 500 with a broken DOM, the corpus does not replace yesterday's good observation with broken garbage.

```
/pricing crawl today → HTTP 500
    → latest_attempt = {status: 500, observed_at: today, observation: broken}
    → latest_accepted_observation = {status: 200, observed_at: yesterday, observation: good}
    → ORB can say: "Latest successful knowledge is from yesterday; today's refresh failed."
```

Acceptance criteria for promoting `latest_attempt` to `latest_accepted_observation`:
- HTTP 200
- Valid HTML rendered (not an error page)
- Content hash differs from error-page signatures
- Pointer candidates extracted successfully

### Route Disappearance States (Revision #11)

Routes don't immediately go ACTIVE → DEPRECATED. The transition is gradual:

```
ACTIVE
    ↓ single 404/timeout
SUSPECTED_MISSING
    ↓ confirmed 404/410 in complete recheck with coverage certificate
CONFIRMED_GONE
    ↓ next compile cycle
DEPRECATED (preserved in corpus with deprecated status, not deleted)
```

A route that times out once does not disappear from Site World. Only confirmed absence (verified through recheck with sufficient coverage) leads to deprecation.

### Target Identity Hash

Already exists in the codebase as `_pointer_identity_hash()` (pointer_recovery.py:482). Hashes:
- target_id, page_route, meaning, semantic_locator, content_fingerprint, structural_context, allowed_actions

No change needed. This is already the correct identity mechanism.

---

## 2. Observation/Change Timeline (Separate from Authority)

### Revision #3: IDENTITY_CHANGED is an observation fact, not an authority decision

The authority ledger should not contain identity-change events. Those are observations. Instead, two separate timelines:

**Observation/Change Timeline** (owned by the corpus/observation plane):
```
TARGET_ADDED          — new target discovered in observation
TARGET_REMOVED        — target no longer present in observation
TARGET_IDENTITY_CHANGED — target's identity hash changed between observations
ROUTE_ADDED           — new route discovered
ROUTE_DEPRECATED      — route confirmed gone
CONTENT_CHANGED       — content hash changed, structure hash unchanged
STRUCTURE_CHANGED     — structure hash changed
```

**Authority Ledger** (owned by the owner/governance plane):
```
OWNER_APPROVED        — owner explicitly approved a target identity
OWNER_REJECTED        — owner explicitly rejected a target identity
AUTHORITY_REVOKED     — owner revoked a previously granted approval
POLICY_AUTHORIZED     — system policy permitted an action (not owner-approved)
POLICY_DENIED         — system policy blocked an action
```

### Why POLICY_AUTHORIZED instead of SYSTEM_AUTO_APPROVED (Revision #4)

The source of authority matters. A future owner looking at a diagnostic should distinguish instantly:
- "I approved this." (OWNER_VERIFIED)
- "Orb Weaver permitted this under informational-target policy v3." (POLICY_AUTHORIZED)

This distinction becomes critical once review becomes scalable and machine-authorized targets coexist with owner-verified ones.

---

## 3. Three-Dimensional Target Representation (Revision #5)

### Evidence State (category)
```
DISCOVERED      — seen once, never verified
OBSERVED        — seen in at least one successful crawl
REOBSERVED      — same identity confirmed across multiple crawls
MACHINE_STABLE  — stable across multiple renders/viewports/crawls
CONFLICT        — duplicate semantic targets detected
STALE           — identity no longer matches latest observation
DEPRECATED      — route or target confirmed gone
```

### Evidence Confidence (strength within category)
```
0.00 – 1.00
```

Two OBSERVED targets may have radically different evidence:
- Target A: seen once, confidence 0.62
- Target B: seen four times, same identity, multiple viewport classes, confidence 0.97

The state tells us the category. Confidence tells us evidence strength within that category. Neither directly grants an action.

### Authority State (permission)
```
UNREVIEWED
POLICY_AUTHORIZED
OWNER_VERIFIED
OWNER_REJECTED
REVOKED
STALE            — decision exists but identity no longer matches current observation
```

---

## 4. Action-Specific Authority Envelope (Revision #6)

### The Capability Ladder

```
KNOW → DESCRIBE → GUIDE → POINT → SCROLL → NAVIGATE → CLICK → FILL → SUBMIT
```

Consequence increases moving right. Each target has an effective capability envelope computed from evidence state + authority state + target risk class + policy version.

### Examples

**Pricing heading (INFORMATIONAL risk):**
```
KNOW: yes     DESCRIBE: yes    GUIDE: yes
POINT: yes    SCROLL: yes      NAVIGATE: n/a
CLICK: no     FILL: no         SUBMIT: no
```

**Checkout button (TRANSACTIONAL risk):**
```
KNOW: yes     DESCRIBE: yes    GUIDE: yes
POINT: yes    SCROLL: yes      NAVIGATE: maybe
CLICK: confirmation required   FILL: n/a
SUBMIT: no
```

**Delete-account control (DESTRUCTIVE risk):**
```
KNOW: yes     DESCRIBE: yes    GUIDE: maybe
POINT: maybe  CLICK: no automatic authority
SUBMIT: explicit confirmation/handoff required
```

### Target Risk Classifier (Revision #7)

A small deterministic risk classifier for action targets:

```
INFORMATIONAL      — headings, paragraphs, sections, FAQ answers
NAVIGATIONAL       — nav links, breadcrumbs, menu items
TRANSACTIONAL      — checkout, add-to-cart, signup
AUTHENTICATION     — login, logout, password reset
PERSONAL_DATA      — profile fields, address forms
FINANCIAL          — payment fields, billing
DESTRUCTIVE        — delete account, cancel subscription, remove data
EXTERNAL_HANDOFF   — links to external sites, phone numbers, email
```

Policy maps risk class + evidence state + authority state → effective action envelope. This replaces dozens of hand-built `runtime_policy` dictionaries scattered through the code with a single deterministic classifier that owners can customize without rewriting pointer logic.

**Owner policy example:**
```
INFORMATIONAL + MACHINE_STABLE → POLICY_AUTHORIZED for KNOW through POINT
TRANSACTIONAL + any → CLICK always requires confirmation
DESTRUCTIVE + any → no automatic authority, explicit handoff required
```

---

## 5. Coverage Certificate (Revised)

### Revision: Coverage basis field (Point #10)

`frontier_exhausted = true` is necessary but not sufficient to prove a route disappeared. A route can be orphaned (no longer linked from navigation) without being deleted.

```
coverage_certificate:
    declared_scope:    FULL_SITE | ROUTE_SET | TARGETED_RECOVERY | PREFLIGHT
    routes_observed:   [list of route identities actually visited and rendered]
    routes_attempted: [routes tried but failed — 404, timeout, render error]
    routes_skipped:    [routes known to exist but not in scope]
    
    completion_status: COMPLETED_NORMAL | TRUNCATED_MAX_PAGES | TRUNCATED_MAX_DEPTH |
                        TRUNCATED_TIMEOUT | TRUNCATED_ERROR | PARTIAL
    
    frontier_exhausted: bool
    max_pages_hit:      bool
    max_depth_hit:      bool
    robots_blocked:     [routes blocked by robots.txt]
    
    redirects:          [{from, to, permanent}]
    not_found:          [routes that returned 404/410]
    
    scope_routes:       [for ROUTE_SET, the explicit list intended to cover]
    
    coverage_basis:     ← NEW (Revision #10)
        seed_routes_checked:              [routes from owner seeds that were visited]
        sitemap_routes_checked:           [routes from sitemap that were visited]
        discovered_link_routes_checked:  [routes found via link discovery that were visited]
        previously_known_routes_rechecked: [routes from corpus that were explicitly rechecked]
```

### How Coverage Basis Prevents Orphan-Route Amnesia

```
Scenario: /pricing was previously known. New crawl starts at /.
Navigation no longer links to /pricing. Frontier exhausts successfully.

Without coverage_basis:
    /pricing not in routes_observed
    frontier_exhausted = true
    → /pricing marked DEPRECATED (wrong — it might be orphaned, not deleted)

With coverage_basis:
    previously_known_routes_rechecked does NOT include /pricing
    (the crawler didn't explicitly recheck it)
    → /pricing remains ACTIVE (preserved from corpus)
    → Flagged for explicit recheck in next crawl
```

For a FULL_SITE crawl to justify deprecating a previously known route, the coverage certificate should show that route was in `previously_known_routes_rechecked` and returned 404/410.

---

## 6. Authority Ledger (Event-Sourced)

### What Lives in the Authority Ledger

Only explicit decisions by owners or system policy:

```
AUTHORITY EVENT:
    timestamp
    event_type:       OWNER_APPROVED | OWNER_REJECTED | AUTHORITY_REVOKED |
                      POLICY_AUTHORIZED | POLICY_DENIED
    target_identity:  identity_hash this decision applies to
    route_identity:   which route this target was on when decided
    decided_by:       owner | system_policy
    policy_version:   which policy rule authorized this (for POLICY_* events)
    prior_state:      effective authority before this event
    evidence_ref:     link to observation that supported this decision
    notes:            optional human notes
```

### What Does NOT Live in the Authority Ledger

- Identity changes (TARGET_IDENTITY_CHANGED) — these are observation facts, live in the observation timeline
- Route additions/removals — observation facts
- Content/structure changes — observation facts

### Authority Projection at Compile Time

The compiler reads the event log and produces the current effective authority state:

```
For each target in the corpus's pointer_candidates:
    events = authority_ledger.events_for(target.identity_hash)
    
    No events → authority_state = UNREVIEWED
    
    OWNER_APPROVED exists, identity_hash matches current observation:
        → OWNER_VERIFIED
    
    OWNER_REJECTED exists, identity_hash matches:
        → OWNER_REJECTED
    
    Decision exists but identity_hash doesn't match current observation:
        → STALE (flag for reconciliation)
    
    POLICY_AUTHORIZED exists for this risk class:
        → POLICY_AUTHORIZED (computed from policy + risk class, not per-target)
```

### Already Exists in the Codebase

`pointer_authority.json` at `website_orb_context/pointer_authority.json` is already an append-only decisions log with `signature_hash`, `reviewer`, and `identity_hash`. The format is correct; only the consumer (`merge_canonical_pointer_authority()`) needs to change to read from it.

---

## 7. Deterministic Compiler

### Inputs

| Input | Category | Owner | Mutability |
|-------|----------|-------|-----------|
| Current Site Corpus | Evidence | Crawl merge | Updated on scoped crawl |
| Authority Ledger | Decisions | Owner/system | Append-only |
| Configuration | Decisions | Owner settings | Editable by owner |
| Policy Version | Decisions | System | Versioned |
| Learned Verified State | Learned | Promotion pipeline | Accumulated over time |

### Outputs (All Derived Views — Category 4)

| Artifact | What It Contains |
|----------|-----------------|
| Site World | Route graph, page summaries, entity relationships |
| Pointer Observation Map | Current pointer candidates from corpus |
| Route Classification | Route types: landing, product, contact, etc. |
| Knowledge Chunks | Page content chunked for retrieval |
| Retrieval Index | Semantic retrieval surface |
| Quality Summary | Coverage, freshness, health metrics |
| Readiness Matrix | Per-capability readiness |
| Compiled ORB World | Composite view consumed by the ORB runtime |

### Content-Addressed Generations (Point #14)

```
corpus_version = sha256(canonical corpus state)
authority_version = sha256(authority events through latest)
config_version = sha256(owner configuration)
policy_version = sha256(policy rules)
compiler_version = semver of compiler code

compiled_world_version = hash(
    corpus_version,
    authority_version,
    config_version,
    compiler_version,
    policy_version
)
```

The runtime can cheaply answer: "Am I running the world that corresponds to current sources?"

Dock Station deployment manifests can reference exact versions:
```
Customer ORB generated from:
    Corpus: C123    Authority: A44
    Policy: P7      Compiler: 1.4.0
```

Deployment is reproducible.

### Compiled-From Manifest (Revised)

```
compiled_from:
    corpus_version
    authority_version
    config_version
    compiler_version
    schema_version
    policy_version          ← NEW (Point #13)
    change_set_ref
    compiled_at
    routes_included
```

`policy_version` is needed because effective permissions can change even if neither the page nor owner decision changed. Example: policy v2 allows machine-stable nav to POINT; policy v3 allows POINT + SCROLL. Same corpus, same authority, different effective ORB World.

### Incremental vs. Full Compile (Points #15, #16)

Two compilation modes permanently:

**Full compiler** — the reference implementation. Rebuilds everything from scratch. Always kept, never deprecated. Used for recovery, debugging, and correctness verification.

**Incremental compiler** — optimized for speed. Rebuilds only affected routes. Used for normal operation.

**Correctness oracle:** During development, `incremental_result_hash == full_result_hash` for the same source state. This becomes one of Orb Weaver's strongest regression tests. If incremental and full disagree, the incremental logic has a bug.

---

## 8. Runtime Layer (Revised)

### Effective Permission Computation

```
EVIDENCE (from corpus):
    "Does this target exist in our latest accepted observation?"
    
AUTHORITY (from ledger projection):
    "Has the owner/system authorized actions for this target?"
    
LIVE (from runtime DOM):
    "Is this target physically present in the live interface right now?"

EFFECTIVE CAPABILITY = EVIDENCE ✓ AND AUTHORITY ✓ AND LIVE ✓
```

Each capability in the envelope (KNOW, DESCRIBE, GUIDE, POINT, SCROLL, NAVIGATE, CLICK, FILL, SUBMIT) is computed independently from the intersection of these three truths.

### Runtime Evidence Feedback (Revision #2)

```
LIVE RECOVERY (runtime finds divergent target)
    ↓
saveCandidateCorrection() — persists to evidence inbox
    ↓
CandidateCorrection record survives session
    ↓
Promotion pipeline evaluates repeated evidence
    ↓
If promoted: corpus observation updated through sanctioned merge path
    ↓
Next compile cycle includes corrected observation
```

The runtime never directly mutates canonical observation or authority. But it does persist candidate evidence for later evaluation. This is one of the smarter parts of the existing architecture and is preserved.

---

## 9. Multi-Tenant Isolation (Point #9)

Physical per-client corpora, not a shared corpus:

```
vault_system/
  clients/
    customer_A/
      corpus/           ← per-client corpus
      evidence/         ← per-client evidence inbox
    customer_B/
      corpus/
      evidence/
```

Site_id/tenant identity still embedded inside records for provenance. Physical isolation gives us:
- Simpler backups
- Simpler deletion/export
- Much lower cross-customer leakage risk
- Easier Dock Station packaging
- Cleaner customer-specific compilation
- Easier debugging

This follows Orb Weaver's existing customer-owned Vault isolation doctrine.

---

## 10. CCO Alignment (Point #19)

The four-category state taxonomy gives CCO cleaner inputs:

```
EVIDENCE: What was actually observed?
DECISIONS: What has been verified/authorized?
DERIVED WORLD: What representation did Orb Weaver compile?
LIVE REALITY: What exists now?
```

Correspondence can ask:
- Does representation still correspond to evidence?
- Does runtime correspond to compiled expectation?
- Does action authority correspond to decision provenance?

This is exactly where CCO becomes useful rather than expensive overhead. It can remain off the hot path most of the time, invoked when correspondence is questioned.

---

## Migration: Two Tracks (Revision #7)

### CURRENT REPAIR TRACK (do first, prove the product)

The current runtime has an actual functional defect: 10 verified pointers + 77 rejected/unresolved → `recovery_required` → all guidance blocked. We do not need the full corpus architecture to fix that.

```
1. Finish Fix 3
   - Set pointer_health = "OWNER_REJECTED" in reject_owner_pointer()
   - Add OWNER_REJECTED to retention logic in merge_canonical_pointer_authority()
   - Or: redirect merge to read from pointer_authority.json (closes Fix 3 naturally)

2. Regression-prove Fixes 1–3
   - Create known approvals + rejections
   - Run ordinary crawl
   - Prove both survived correctly
   - Prove rejected targets remain excluded from active quality calculations

3. Split map health from target guidance authority
   - quality.recovery_required remains diagnostic/ops signal
   - guidance_ready computed from "does at least one target have may_point: true"
   - One verified target is enough to permit truthful pointing to that target

4. Prove target-level API/runtime readiness
   - Show a specific verified target emitted as guidance-eligible
   - While unrelated unresolved records remain

5. Visible Chromium proof
   - Question → Site World → target → live DOM → scroll/reacquire → geometry → ORB movement → Point/Ping
```

### HARDENING TRACK (after product is proven)

```
6. Read-only corpus projection
   - Build corpus as projection over existing stored_pages / latest_crawl.json
   - Verify it accurately represents current site knowledge
   - No behavior change yet

7. Define scan scope + coverage certificate
   - Formalize existing crawler state (max_pages_hit, queue_exhausted) into structured record
   - Add coverage_basis with previously_known_routes_rechecked
   - Add coverage certificate to crawl snapshot
   - Safety property: every published artifact carries proof of what the crawl was capable of observing

8. Make corpus the scope-aware observation writer
   - Extend scoped.py to all scopes (including full with incomplete coverage)
   - Corpus merge uses coverage certificate to determine what to replace
   - Preserve latest-good observation separately from latest attempt
   - Route disappearance goes through ACTIVE → SUSPECTED_MISSING → CONFIRMED_GONE → DEPRECATED
   - Safety property: a one-page crawl cannot shrink the current world

9. Move derived artifacts behind deterministic compilation
   - Refactor preserve_client_crawl_intelligence() to compile from corpus + authority
   - Pointer map published per-route, not wholesale
   - Website context merged per-route
   - One artifact class at a time: pointer map first, then context
   - Safety property: derived artifacts are always rebuildable from preserved sources

10. Move authority to durable event ledger / projection
    - Redirect merge_canonical_pointer_authority() to read from pointer_authority.json
    - Separate observation/change timeline from authority ledger
    - Authority projection at compile time, not at merge time
    - Safety property: authority decisions are monotonic; identity changes are observations

11. Remove legacy direct-write paths
    - Once all derived artifacts are compiler-produced, remove direct writes
    - Three mutation boundaries enforced structurally
    - Full compiler kept as reference implementation
    - Incremental-vs-full compile oracle as regression test
```

**Why this ordering (Revision #1):** Coverage semantics are not an enhancement to the corpus. They are part of the corpus write contract. The corpus cannot safely merge without knowing scope. So scope/coverage (Step 7) comes before corpus-owned publication (Step 8).

**Why repair first (Revision #7):** We should not postpone proving the defining Website ORB behavior for a large migration. The current guidance-gate defect is fixable without the corpus architecture. Prove the product works. Then harden the architecture.

---

## What Does NOT Need to Change (Code-Verified)

- **`pointer_authority.json` format** — already append-only with signature hashes
- **`_pointer_identity_hash()`** — already computes the correct identity
- **`website_orb_bootstrap()`** — reads the right files; once those files are scope-aware, bootstrap is fine
- **`scoped.py` merge logic** — already correct for non-full scopes; needs extension to full
- **Crawler engine coverage tracking** — already tracks max_pages, depth, frontier; needs formalization
- **Evidence system** (`lifecycle/evidence.py`) — already immutable with atomic writes
- **Vault storage layout** — already well-organized per-client
- **CandidateCorrection architecture** — already separates runtime evidence from canonical truth

---

## Fix 3 Verification (From Code)

Current `merge_canonical_pointer_authority()` (pointer_recovery.py:411):
```python
previous_owner = {
    str(record.get("target_id")): record
    for record in previous_map.get("records") or []
    if record.get("pointer_health") == "OWNER_VERIFIED"
}
```

Only preserves `OWNER_VERIFIED`. `reject_owner_pointer()` (line 346) sets `confidence_class = "BLOCKED"` but does NOT set `pointer_health = "OWNER_REJECTED"`.

**Fix 3 options:**
- Quick: Add `record["pointer_health"] = "OWNER_REJECTED"` to `reject_owner_pointer()` and add `OWNER_REJECTED` to the merge retention check
- Better: Redirect merge to read from `pointer_authority.json` (already records both approvals and rejections with identity hashes). This makes Fix 3 a natural consequence of reading from the authority ledger rather than a separate patch. This is Step 10 of the hardening track, but the quick fix can land first.

---

## System Properties Locked

1. A narrow observation may update what it observed. It may never erase evidence, decisions, or learned state outside the scope it was capable of observing.

2. Derived artifacts are never state. They are always views compiled from preserved sources.

3. Authority decisions are monotonic. An ordinary crawl cannot transform OWNER_VERIFIED into NEW, or lose OWNER_REJECTED. Only an identity change makes a decision STALE, and identity changes are observations, not authority events.

4. Effective capability requires three independent truths to agree: evidence, authority, and live verification. Each capability in the action envelope is computed independently.

5. Absence is evidence only when the coverage certificate proves the route was within scope, observable, and explicitly rechecked.

6. Runtime may persist candidate evidence but never directly mutate canonical observation or authority.

7. The corpus preserves latest-good observation separately from latest attempt.

8. Route disappearance is gradual: ACTIVE → SUSPECTED_MISSING → CONFIRMED_GONE → DEPRECATED.

9. The full compiler is never deprecated. It is the reference implementation and recovery mechanism.

10. Evidence, Decisions, and Learned Verified State are precious. Derived intelligence is rebuildable.

---

## Open Questions

1. **Should `full` scope crawls with incomplete coverage automatically fall back to scope-aware merge?** Automatic fallback is safer but changes existing behavior. Consider a flag for Phase 8 with automatic fallback as default in Phase 11.

2. **Should the authority projection happen in the merge function or a separate compile step?** Given Claude's "plane discipline without plane bureaucracy" principle, keep it in the merge function but redirect it to read from the authority ledger.

3. **Should the risk classifier be configurable per-customer?** Default risk classifications should be system-wide. Customer overrides (e.g., "treat our checkout as DESTRUCTIVE, not TRANSACTIONAL") should be possible through configuration without rewriting pointer logic.

4. **Should CandidateCorrection promotion be automatic or require owner approval?** Automatic promotion is faster but risks accepting a transient DOM state as canonical. Owner approval is safer but adds review burden. Consider: automatic promotion after N consistent corrections across M sessions, with owner notification.

5. **How does the observation timeline relate to the existing `authority_history` field on pointer records?** The `authority_history` already tracks events per-target. The observation timeline would be a separate, broader record covering route-level and target-level observation events. Both should coexist — `authority_history` for decision provenance, observation timeline for evidence provenance.
