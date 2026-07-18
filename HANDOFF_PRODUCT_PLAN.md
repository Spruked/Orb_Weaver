# Orb Weaver Product Plan — Reload Handoff

Use this handoff after reloading Codex:

> Continue implementing `/home/bryan/projects/Orb_Weaver/Orb Weaver final product plan.docx`. Read `/home/bryan/projects/Orb_Weaver/HANDOFF_PRODUCT_PLAN.md` and `/home/bryan/projects/Orb_Weaver/DEV_NOTES_PRODUCT_PLAN.md` first. Preserve all existing user changes. Resume from the unfinished lifecycle integration and verify the partial changes before adding more work.

## User request

Use `Orb Weaver final product plan.docx` as the source of truth, complete as much of its implementation-priority list as possible, and keep durable development notes in case work is interrupted.

## Product-plan priorities

1. P0: Separate Map Crawl, Site Scan, ORB Scan, Preflight, Full Audit, and Sentinel job identities, APIs, storage, reports, and UI controls.
2. P0: Preserve every generated database/dataset with manifests, checksums, provenance, versions, and structured diagnostics.
3. P0: Full Audit baseline + independent verification + reconciliation classifications.
4. P0: Hard review gate before Preflight/deployment.
5. P0: Pointer confidence evidence and enforced runtime policy.
6. P1: Sentinel, route safety, versioned deployment, hash-chain verification, and failure-diagnostics UI.

## Work completed before interruption

### Durable notes

- Added `DEV_NOTES_PRODUCT_PLAN.md` with the plan doctrine, baseline audit, implementation checklist, remaining work, and resume guidance.

### Pointer confidence foundation

- Modified `backend/app/orb/pointer_plot.py`.
- New pointer records now include:
  - `confidence_class`: `VERIFIED`, `STABLE`, `UNCERTAIN`, or `BLOCKED`
  - `runtime_policy` including `may_point`, verification, and confirmation rules
  - `confidence_evidence` fields required by the plan
  - locator method, source revision, and verification timestamp
- Added `pointer_runtime_policy()` and `_locator_method()`.
- Runtime/UI enforcement is not yet wired into `frontend/src/orb/targetValidation.ts`.

### Lifecycle database foundation

- Modified `backend/app/models/database.py`.
- Added `LifecycleJob` with job type, lifecycle status/phase, truthful progress, config/result, evidence root, and manifest-chain fields.
- Added `ReviewItem` with severity, decision, reviewer, notes, timestamps, and signature hash.
- Added relationships from `Project` to lifecycle jobs and from lifecycle jobs to review items.
- New tables should be created by the existing `Base.metadata.create_all()` path, but this has not yet been tested.

### Evidence preservation and hash-chain foundation

- Added `backend/app/lifecycle/__init__.py`.
- Added `backend/app/lifecycle/evidence.py` with:
  - required per-run directory layout
  - atomic JSON artifact writes
  - structured failure diagnostics
  - consistent SQLite backup snapshots plus schema metadata
  - checksums and evidence-root hash
  - previous-run manifest chain fields
  - manifest verification
- Imported these helpers and the new models into `backend/main.py`, but lifecycle routes/orchestration have not yet been added.
- The evidence module has not yet been tested. Check `_sqlite_path()` carefully with both absolute and relative SQLite URLs.

### Crawl provenance foundation

- Modified `backend/app/crawler/engine.py`.
- Added discovery provenance tracking for owner seeds, sitemaps, and internal links.
- Internal links now identify header, footer, navigation, form-action, or body discovery zones.
- Provenance is copied into page semantic analysis and crawl stats.
- These changes have not yet been compiled or tested.

## Important pre-existing worktree state

The repository was already dirty. Do not discard or overwrite unrelated user work. Before this product-plan task, `git status --short` included modified/deleted/untracked files across the frontend, Docker setup, runtime data, and Orb Assistant. The earlier task also modified `deploy/nginx/orb-weaver.conf` to return `404` for missing `/static/` assets; that change was tested but not deployed.

## Exact resume point

1. Run syntax/unit checks immediately because the latest backend changes were interrupted before verification:

   ```bash
   python3 -m compileall backend/app backend/main.py
   pytest -q backend/tests
   npm test -- --watchAll=false
   npm run build
   ```

   Run frontend commands from `/home/bryan/projects/Orb_Weaver/frontend`.

2. Fix any syntax/type/test problems without reverting unrelated changes.

3. Add backend lifecycle serialization, ownership checks, and APIs:
   - `GET /api/projects/{project_id}/lifecycle-jobs`
   - `POST /api/projects/{project_id}/lifecycle-jobs/{job_type}`
   - `GET /api/lifecycle-jobs/{job_id}`
   - review decision endpoints
   - evidence manifest/verification endpoints

4. Add lifecycle orchestration:
   - Map Crawl may wrap the existing crawler but must have its own `LifecycleJob` and evidence root.
   - Site Scan and ORB Scan must consume an approved map/crawl rather than silently invent routes.
   - Full Audit must create independent baseline and verification passes, reconcile URL/content/pointer datasets, and classify results as `CONFIRMED`, `TRANSIENT`, `DYNAMIC`, `CONFLICT`, `UNVERIFIED`, or `PASSED`.
   - Create `ReviewItem` rows for critical conflicts and set `REVIEW_REQUIRED`.
   - Block Preflight when critical review items, pointer conflicts, unapproved stateful tools, invalid Site World schemas, or conflict thresholds remain.

5. Integrate evidence finalization into each lifecycle run. Persist database snapshots, normalized datasets, scan contract, structured diagnostics, checksums, manifest, previous-run link, and software versions.

6. Enforce pointer policy in `frontend/src/orb/targetValidation.ts`: `UNCERTAIN` and `BLOCKED` pointers must never point. Add tests.

7. Add lifecycle types/methods to `frontend/src/services/api.ts` and separate stage controls/statuses to `frontend/src/pages/Projects.tsx`. Progress must use actual phase/count data, not a fake fixed-width bar.

8. Update `DEV_NOTES_PRODUCT_PLAN.md` after every completed vertical slice.

## Current plan status

- Read/extract product plan: completed.
- Map current implementation and prioritize: substantially completed.
- Implement and verify priority items: in progress; foundations exist, integration and verification remain.
- Durable development notes: created and must continue to be updated.

## Safety and scope reminders

- Do not rebuild/restart/deploy Docker services unless needed for verification and clearly within the task.
- Do not delete existing runtime evidence or user files.
- Use `apply_patch` for edits.
- The new code is partial and unverified; do not describe it as complete until tests pass and routes/UI are integrated.
