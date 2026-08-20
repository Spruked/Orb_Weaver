# Orb Weaver Functional Readiness Checkpoint
Date: 2026-08-14
Status: GPT-5.6 Sol allocation expired during controlled owner-path verification.

## DO NOT START OVER

This checkpoint continues the existing FULL ORB WEAVER FUNCTIONAL READINESS REPAIR.

Do not:
- reset
- stash
- clean
- pull over the worktree
- switch branches
- Dockerize
- deploy
- push
- redesign
- rerun the entire forensic audit from the beginning
- allow a new defect to replace the active task

Preserve all current local modifications and unrelated local files.

---

## Current Objective

Prove every user-visible Orb Weaver capability through the real owner workflow:

input
→ executor
→ computation
→ persisted artifact
→ validation
→ truthful status
→ downstream consumer
→ functional proof

No stage may report COMPLETE merely because data exists or a counter is nonzero.

---

## Runtime

Known working source services at last checkpoint:

- frontend: 127.0.0.1:16777
- backend: 127.0.0.1:16776
- Kokoro: 8880
- Whisper: 9000
- Ollama/Qwen: 11434

Alternative inference endpoints observed unavailable from WSL:
- 11435
- 8009
- 40343

Classify those as BLOCKED_BY_RUNTIME unless separately repaired/proven.

Docker and public deployment were intentionally untouched.

---

## Major Repairs Already Completed

- corrected source frontend/backend pairing: 16777 → 16776
- orphaned crawl reconciliation
- lightweight crawl-history serialization
- Account page separated from heavyweight combined-dashboard/GA4 path
- removed multiple silent page/result truncations
- broadened dynamic JavaScript rendering detection
- implemented actual robots.txt enforcement
- added persisted scan-stage execution evidence
- removed inferred/fake assembly completion states
- persisted lexical artifacts
- persisted knowledge chunks
- persisted retrieval artifacts
- persisted route classification
- persisted source validation/provenance evidence
- pointer readiness no longer inferred from record counts
- pointer verification/recovery/runtime-guidance status tied to persisted execution evidence
- orb_ready requires appropriate guidance evidence
- recovery evidence propagates back into source crawl, Website ORB context, and client pack
- public bootstrap cannot advertise readiness solely because a pointer map exists
- audit affected URLs and various lifecycle/pointer listings no longer silently truncate
- browser speech/TTS fallback search found no prohibited browser fallback
- lifecycle cancellation/status bug repaired so cancellation checking does not db.refresh(job) and erase uncommitted stage progress
- deterministic Site World route resolver added ahead of free-form generation
- spoken-output Markdown normalization added
- unknown correspondence can no longer release invented route facts as verified answers
- rejected/inactive pointer records remain in provenance but are excluded from active guidance quality denominator

---

## Static Verification Already Proven

At points during this repair:

- Python compilation: PASS
- frontend TypeScript typecheck: PASS
- focused backend suite: 29 PASS
- complete backend suite: 42 PASS
- loader smoke checks: 35 PASS
- 8 bootstrap reports
- zero loader console errors
- preflight smoke exited cleanly
- Playwright Chromium available and executable

Do not rerun all of these simply to rediscover state.
Rerun appropriate regression tests only after relevant new edits.

---

## Controlled Owner-Path Runtime Evidence

### MAP_CRAWL

Controlled owner-path project:
- project 18
- initial lifecycle job 8

Evidence:
- 5 pages persisted
- 8 URLs discovered
- heartbeat advanced
- lifecycle correctly stopped at REVIEW_REQUIRED
- signed-review gate worked

Observed display defect:
- final phase remained `preserving_map_evidence`
  instead of `awaiting_map_approval`

This was parked for later repair rather than interrupting the dependency chain.

### SITE_SCAN

Real SITE_SCAN exposed a critical status bug:

`ensure_lifecycle_not_cancelled()` used `db.refresh(job)` after the stage had
updated phase/progress but before commit.

This reverted pending execution-state fields and made the UI show:
`initializing_evidence / 0 of 0`

even though the artifact/result existed.

This was repaired using an independent committed cancellation-state check.

Regression tests were added.

### ORB_SCAN

Real ORB_SCAN job 11:

- 546 pointer targets
- manifest persisted
- status correctly reported POINTER_RECOVERY_REQUIRED
- automatically queued one recovery job
- five routes involved

Recovery job 12:

- 20 real browser renders
- two viewports
- two render passes per route
- 200 screenshots
- 220 promoted stable targets
- 326 unresolved targets
- two critical owner-review sets
- signed manifest

The system correctly REFUSED readiness.

Source crawl showed:
- verification COMPLETE
- recovery COMPLETE
- runtime guidance BLOCKED

The unresolved count propagated into Website ORB context.

This is correct evidence behavior.

---

## Website ORB Downstream Consumption

The generated Site World contained the correct route mapping:

`Configuring Vite` → `/config`

The 1.5B model originally invented `/guide/config` and emitted Markdown.

The CCO trace correctly considered the answer unknown, but the response-release
gate allowed it through.

Repair:
- deterministic Site World route resolver added before free-form generation
- spoken-output normalizer removes Markdown formatting
- unknown correspondence cannot release an unverified route as fact

Repeated authenticated Website ORB request then returned:

`You'll find Configuring Vite at /config.`

Evidence:
- source: site-world-route
- answer state: known
- supported CCO correspondence
- exact persisted route fact used
- pointer match remained guidance_eligible: false
- no unsafe pointer lock queued

This downstream route-resolution path is PROVEN for this controlled case.

---

## Large Pointer Review Finding

The five-page Vite documentation weave produced:

- 546 total pointer candidates
- 249 buttons
- 161 repeated navigation targets

Tracing showed this was not simply a hard-cap defect.

The map is comprehensive and intentionally records headings, sections,
links, qualifying prose targets, and controls.

The unresolved issue is OWNER REVIEW ERGONOMICS / AUTHORITY SCALABILITY.

Hundreds of pointer decisions cannot reasonably be required from a human owner.

Do NOT solve this by:
- deleting legitimate map evidence
- rubber-stamping machine approvals
- weakening verification
- granting automatic navigation/click authority

The full five-page run remains preserved as large-site evidence.

---

## Bounded One-Route Continuation Run

A second one-route controlled weave was started to complete downstream
lifecycle testing without pretending the 546-record map had been human-reviewed.

Recovery result before authority decisions:

- 12 independently recovered targets
- 75 unresolved targets
- two recovered locator identities were duplicated

Planned conservative authority policy for the TEST RUN:

- retain one semantically correct target from each duplicated recovered identity
- approve only unique durable recovered identities
- reject duplicate identities
- reject unresolved targets
- never grant click authority
- never grant navigation authority
- rejected records remain in provenance

Expected approval set:
- approximately 10 unique recovered targets

A script was applying signed authority decisions through lifecycle job 16 when
the GPT-5.6 Sol allocation expired.

Each decision atomically republishes authority and refreshes evidence checksums,
so this process was relatively slow.

LAST OBSERVED STATE:
The signed review process was still progressing and a polling command was
waiting for the authority process to finish and then fetch lifecycle job 16.

THIS IS THE EXACT RUNTIME CONTINUATION POINT.

---

## Critical Unproven Capability

VISIBLE WEBSITE ORB POINTER/GUIDANCE EXECUTION IS NOT PROVEN.

The owner has never observed the Website ORB successfully:

- point to a real target
- move to a target
- scroll to requested information
- navigate to the desired page
- visually guide from one page/section to another

Do not classify runtime pointer guidance as IMPLEMENTED_AND_PROVEN until
observable end-to-end browser behavior has actually been demonstrated.

Existing pointer records, recovery artifacts, confidence classes, manifests,
and successful backend tests are NOT sufficient proof of visible guidance.

This was deliberately not introduced as a new task during the previous run
because doing so would have interrupted the active lifecycle work.

---

## Other Remaining / Parked Issues

- large-site owner pointer-review ergonomics/scalability
- MAP_CRAWL final display phase should become `awaiting_map_approval`
- complete the one-route lifecycle after signed pointer authority processing
- determine resulting readiness/guidance state
- continue remaining downstream lifecycle stages
- visible pointer/navigation/scroll/movement execution remains unproven
- independently rerun frontend production build and verify a fresh build/index.html
  because an earlier parallel build did not leave a fresh artifact and therefore
  was correctly NOT counted as proven
- complete final capability matrix and classify every remaining capability
- public deployment/API routing remains separate from source-runtime proof

---

## Capability Status Vocabulary

Use only:

- IMPLEMENTED_AND_PROVEN
- IMPLEMENTED_BUT_FAILING
- PARTIALLY_IMPLEMENTED
- WIRED_BUT_NOT_EXECUTED
- UI_ONLY
- DERIVED_PLACEHOLDER
- NOT_IMPLEMENTED
- BLOCKED_BY_RUNTIME
- DEAD_CODE

Never use optimistic language in place of one of these evidence states.

---

## Exact Next Action

DO NOT restart the audit.

1. Verify whether the lifecycle-job-16 signed authority decision process completed.
2. Read lifecycle job 16 and its review items/results.
3. Do not reapply decisions blindly if they already completed.
4. Verify the resulting canonical pointer map, active denominator, review state,
   manifest/checksum state, and runtime-guidance eligibility.
5. Continue the SAME controlled one-route lifecycle from that exact state.
6. Repair only defects encountered in that active dependency chain.
7. Finish remaining owner-path lifecycle stages.
8. Then independently run and verify the fresh production frontend build.
9. Preserve the large-site 546-target run as separate scalability evidence.
10. Do not claim visible pointer guidance works until physically demonstrated.

---

## Backup Artifacts Outside Repo

Created before further work:

../ORB_WEAVER_TRACKED_BACKUP_20260814_FINAL.patch
../ORB_WEAVER_UNTRACKED_BACKUP_20260814_FINAL.tar.gz
../ORB_WEAVER_STATUS_20260814_FINAL.txt

These are emergency recovery artifacts.
Do not overwrite them casually.

