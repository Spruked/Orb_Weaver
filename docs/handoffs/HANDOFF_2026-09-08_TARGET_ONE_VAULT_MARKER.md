# Handoff — Target One and Manufactured Vault Marker

Date: 2026-09-08  
Marker: `d9e4387` on `checkpoint/target-one-working-2026-09-07`

## What is complete

Target One’s active public runtime is `frontend/src/landing/AutonomousOrb.tsx`.
The dynamic Preflight presentation uses the same physical-truth pointer path as
the landing tour:

```text
persisted Preflight fact
→ rendered report card
→ report-scoped data-orb-target locator
→ current live DOM rectangle
→ existing LiDAR/runtime verification
→ final live recheck
→ authorized movement / Point / Ping
```

The locator is not authority. Crawl candidates remain evidence only; only
current live verification authorizes guidance. Browser evidence has shown a
valid report-card path through `website-text`, `llamacpp-tour`, Kokoro, and a
fresh Point/Ping; resize/reflow reacquisition; and target-loss blocking with no
stale Point/Ping.

The same global Weaver now survives the approved Preflight → onboarding route
handoff. The Preflight offer records an `ONBOARDING` continuation in session
storage and performs a React route transition. On `/signup`, the existing
mounted runtime refreshes its spatial state, resolves the live Full name field
through a route-local `data-orb-target` locator, injects only ephemeral
geometry into the existing LiDAR channel, and must pass the ordinary live
validation plus final arrival/Ping rechecks. It never adds a second ORB or
mutates the crawl Pointer Map. The Playwright proof
`frontend/scripts/orb-onboarding-continuity-e2e-proof.js` passed the real form
handoff and back/forward no-duplicate case.

MORB visual travel offers direct, swirl, and dart-orbit patterns. These are
visual waypoints only; final Pointer/Ping authority remains the existing fresh
live target recheck.

The manufactured Website ORB single-Vault repair is also complete for **new
packages**. The assembler now:

- injects payload once, under `<package>/runtime/vault_system/`;
- strips the copied `Orb_Vault_System/orb_vault_skg/vaults/` data tree;
- strips inactive vendor TPC API/results/vaults/tooling persistence surfaces;
- passes explicit canonical A Priori and A Posteriori paths to SKG;
- writes SKG ledger and glyph provenance under the same package Vault; and
- fails closed if `ORB_WEAVER_VAULT_ROOT` is missing, external, legacy,
  vendor, parent-escaped, or symlinked.

The repair does not migrate or delete legacy/template source trees. Those
remain subject to their own inventory and lifecycle audit.

The live `experience.tour` delivery boundary and the separate manufactured
Website ORB delivery boundary are now repaired at the **automated-test** tier.
Neither may deliver visitor speech or invoke TTS unless its final governance
trace is `approved`, TPC is `passed`, and Doctrine validation is true. A
withheld delivery records a minimal canonical-Vault audit event; it does not
persist unnecessary visitor speech.

## 2026-09-09 Preflight presentation repair

The live public Preflight page now uses a time-synchronized caption surface
for Weaver’s generated Kokoro narration. Captions take their progress from the
actual media clock (or decoded-audio clock for speaker boost), never from a
separate typewriter timer. Until playback reaches a natural phrase boundary,
no narration is exposed. Pause, interruption, playback error, and turn
replacement stop progression immediately; no unspoken future text is retained.

The caption is rendered through a page-level portal, outside the moving ORB’s
transformed DOM tree. Its routine presentation is capped at four readable
lines and has a stable, high interaction layer so it neither changes the
Preflight-card layout nor becomes unclickable beneath a card. On completion it
collapses to an accessible control; the complete transcript is revealed only
by an explicit visitor action and can be minimized.

The final `experience.tour` visitor-delivery path additionally sanitizes
private orchestration language such as tour stops, controller/curriculum
references, and internal route/state terminology. The sanitizer does not
globally suppress ordinary uses of “stop”; empty post-sanitization output fails
closed before speech delivery.

The landing tour control also no longer renders the internal `stop.purpose`
field. It uses concise visitor-facing guidance instead, keeping authoring
instructions out of the visible page panel.

Verification added:

```text
CI=true npm test -- --watch=false --runInBand src/orb/speechCaptions.test.ts
PYTHONPATH=backend .venv/bin/pytest -q backend/tests/test_orb_loader_runtime.py \
  -k 'visitor_speech_sanitizer or clean_spoken_output'
node frontend/scripts/preflight-caption-e2e-proof.js
CAPTION_INTERRUPT=1 node frontend/scripts/preflight-caption-e2e-proof.js
```

The real public-form browser runs returned
`PREFLIGHT_CAPTION_E2E_PROOF_OK` and
`PREFLIGHT_CAPTION_INTERRUPT_E2E_PROOF_OK`. The positive trace includes the
actual report-card locator → live LiDAR verification → final live-refresh
Point/Ping → `website-text` → `llamacpp-tour` → Kokoro → caption events chain.
The interruption trace proves an in-progress caption does not become a full
transcript.

## Verification performed

```text
PYTHONPATH=.:backend .venv/bin/pytest -q \
  backend/tests/test_website_orb_manufacturer.py \
  backend/tests/test_canonical_storage.py \
  backend/tests/test_tour_evaluation.py
# 25 passed

.venv/bin/python -m compileall -q \
  backend/app/manufacturing/dock_station_builder.py \
  manufacturing/templates/Website_Orb_Final/backend

git diff --check
```

The manufactured-package test creates a temporary ORB, verifies one runtime
Vault, runs deterministic cognition, records posteriori/ledger/provenance,
restarts, and rejects all prohibited storage-root variants.

Post-repair governance verification (automated, not browser evidence):

```text
PYTHONPATH=.:backend .venv/bin/pytest -q \
  backend/tests/test_website_orb_manufacturer.py::test_manufacturer_builds_complete_delivery_ready_package
# 1 passed

PYTHONPATH=backend .venv/bin/pytest -q \
  backend/tests/test_orb_loader_runtime.py::test_tour_delivery_requires_final_approved_governance \
  backend/tests/test_orb_loader_runtime.py::test_tour_delivery_invokes_tts_only_after_final_governance_approval \
  backend/tests/test_website_orb_governance.py \
  backend/tests/test_tour_evaluation.py
# 22 passed
```

The live regression injects each final `pending`, `rejected`, and `errored`
state and proves HTTP 409, no TTS call, and a `TTS_WITHHELD` Vault event. Its
approved companion proves TTS is invoked only after final approval. The
manufactured-package test builds a temporary ORB, proves an approved answer
trace, then injects a pending voice response and proves HTTP 409, no `speak`
call, and a canonical `tts_withheld` audit record.

## Do not disturb

- Do not rebuild Docker during this isolated development packet.
- Do not stop or retune the established Windows llama.cpp service.
- Keep frontend `16667`, dev API `19667`, and inference gateway `19620` as the
  isolated lane; leave reviewed `16510`/`16500` untouched.
- Do not weaken pointer identity checks, let LiDAR telemetry become action
  authority, or add a parallel geometry cache.
- Do not use `chmod -R 777` to fix the development Preflight write failure.

## Known open defects / unproven runtime work

- The live and manufactured hard delivery boundaries are source and automated
  test proven, but not yet proven in one real browser Preflight request with
  live llama.cpp, Kokoro, and a persisted withholding event.
- The new delivery sanitizer blocks known status-stop/controller language in
  final visitor speech. Broader factual-elevation review remains open.
- Tour controls use visitor-facing copy rather than `stop.purpose`; no known
  curriculum/authoring-field rendering remains in that panel.
- The Outcomes source material permits a small model to elevate intended
  benefits into unsupported accomplished results.
- Dynamic Preflight geometry authority is proven, but the timing of cognition
  relative to glide has not been conclusively measured.
- The manufactured template remains a separate runtime, now with its own
  finalized delivery trace and package-level negative/positive proof. It still
  needs commercial-environment runtime acceptance before shipment.

## Preserved Phase-A pre-repair failure

Source-level test added: `backend/tests/test_orb_loader_runtime.py::test_tour_delivery_requires_final_approved_governance`.

```text
PYTHONPATH=backend .venv/bin/pytest -q \
  backend/tests/test_orb_loader_runtime.py::test_tour_delivery_requires_final_approved_governance

3 failed
pending: HTTP 200; mocked TTS invoked with unapproved articulation
rejected: HTTP 200; mocked TTS invoked with unapproved articulation
errored: HTTP 200; mocked TTS invoked with unapproved articulation
```

This is the required pre-repair Phase-A evidence. The test now passes against
the repaired boundary; the initial failure remains preserved as proof that the
test exercised the actual bypass. The first attempted run was invalid evidence
because its test harness inherited an external TTS cache path; the harness was
bound to its temporary canonical Vault before the preserved run above.

## Resume in this order

### A. Live governance boundary — source and automated proof complete

1. The preserved negative regression test demonstrated that `pending`,
   `rejected`, and `errored` formerly reached TTS. The repaired authoritative
   sequence is:

   ```text
   facts/evidence → TPC truth evaluation → llama.cpp articulation
   → Doctrine V1 evaluation/sanitation → finalized governance trace → approval
   ```

2. Finalized `approved` is now the hard TTS delivery boundary. Missing,
   incomplete, pending, rejected, or errored evaluation fails closed and writes
   the minimal canonical-Vault diagnostic event. The negative and positive
   companion tests pass.

### B. Manufactured Website ORB boundary — package proof complete

3. The template is confirmed separate: it has no `experience.tour` controller.
   Its own answer engine now finalizes a delivery trace and its text/voice
   endpoints enforce it. A temporary manufactured package proves a pending
   voice response cannot invoke `speak` and writes `tts_withheld`; this is not
   commercial-environment acceptance.

### C. Prove the corrected live governance path

4. Run one real browser Preflight articulation under one correlation/report/
   request identity and capture:

   ```text
   authoritative Preflight fact → TPC evaluated → llamacpp-tour articulation
   → Doctrine V1 evaluated → finalized approved → Kokoro → visitor speech
   ```

5. If practical, force a controlled development TPC/Doctrine rejection and
   prove rejection produces no Kokoro request and no visitor delivery, while a
   canonical Vault withholding event records why.

### D. Measure Glide timing after the governance fix

6. In a separate post-governance browser pass, capture timestamps for guidance
   acquisition, glide start, cognition request and return, TTS preparation,
   final live refresh, Point/Ping, and speech. Change choreography only if
   evidence proves cognition starts after arrival; preserve the proven
   LiDAR/live-target authority.

### E. Repair the operational Preflight write failure

7. Fix ownership of the root-owned development client Preflight path so the
   `bryan`-owned dev API can write its existing canonical report location.
   Use the narrow owner/mode repair, determine which process created the
   root-owned path, and prove later report replacements retain correct owner.

### F. Repair known landing articulation defects

8. Constrain Outcomes speech to intended/capability language such as “designed
   to reduce” or “can help” unless authoritative measured evidence supports an
   accomplished claim.
9. Block the known private-orchestration phrase and related leakage with a
    narrow prompt/visitor-speech validation repair; do not build a broad regex
    paraphraser.
10. Replace public `stop.purpose` rendering with genuine visitor-facing copy;
    purpose, presentation guidance, controller terminology, and authoring
    instructions remain internal.
11. Recheck Why Weaving Exists, Trust, 28-Weave, Outcomes, and Preflight
    Decision for brevity, natural speech, no DOM recitation, no repeated
    identity, no private language, and no unsupported claims.

### G. Close Target One, then manufacturing follow-through

12. Run the complete nine-stop Target One journey: startup, real DOM travel,
    natural articulation, verified Pointer/LiDAR, Point/Ping, interruption,
    visitor question, preserved resume, mobile/user-activation gate,
    microphone/audio, explicit decision, real Preflight, dynamic explanation,
    and governance-approved speech.
13. Do not accept simple tour completion. Acceptance requires no internal
    authoring text, no private orchestration speech, no unsupported outcomes,
    no stale pointer action, and no unapproved speech.
14. Continue the repository-wide Vault audit without deletion until unique
    information is reconciled and an audit manifest exists.
15. Before commercial installer/productization acceptance, neutralize any
    remaining manufactured vendor TPC persistence capability. It must not
    become a second storage root, but it does not interrupt the immediate
    Target One governance repair.

### H. Documentation and save-point discipline

16. Update documentation only with evidence actually demonstrated. Identify
    proof tier explicitly: source inspection, automated/unit test,
    manufactured-package test, or live browser/runtime trace. A stronger
    claim may not be inferred from a weaker tier.
17. Commit and push only when authorized and when a phase reaches a real save
    point. Do not create a documentation-only checkpoint that represents an
    unfixed governance or delivery defect as complete.

See [the development log](../DEV_LOG.md), [Target One scope](../TARGET_ONE_LANDING_TOUR.md), [the Immutable Vault law](../../IMMUTABLE_VAULT_STORAGE_LAW.md), and [the repository tree](../../structure_tree.txt).
