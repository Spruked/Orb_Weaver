# Orb Weaver Failure Inventory

Date: 2026-06-05
Workspace: `C:\dev\Desktop\Orb_Weaver`

## Command Checks

### 1. `git status --short`

Initial normal `git status --short` timed out once. Retried with optional locks disabled.

```text
 M backend/app/crawler/engine.py
 M backend/main.py
 M frontend/src/App.tsx
 M frontend/src/components/Layout.tsx
 M frontend/src/index.css
 M frontend/src/pages/Account.tsx
 M frontend/src/pages/AuditReport.tsx
 M frontend/src/pages/CrawlJob.tsx
 M frontend/src/pages/Dashboard.tsx
 M frontend/src/pages/Projects.tsx
 M frontend/src/pages/ReportCompiler.tsx
 M frontend/src/services/api.ts
?? frontend/public/orbweaverlogo.png
?? frontend/src/pages/CrawlJobs.tsx
?? reports/c-drive-space-recovery-report.md
```

### 2. `git diff --stat`

Initial normal `git diff --stat` timed out once. Retried with optional locks disabled.

```text
 backend/app/crawler/engine.py         | 118 +++-
 backend/main.py                       | 977 +++-------------------------------
 frontend/src/App.tsx                  |   5 +-
 frontend/src/components/Layout.tsx    |  32 +-
 frontend/src/index.css                |  24 +
 frontend/src/pages/Account.tsx        |  26 +-
 frontend/src/pages/AuditReport.tsx    |  59 +-
 frontend/src/pages/CrawlJob.tsx       | 155 +++++-
 frontend/src/pages/Dashboard.tsx      | 164 +++++-
 frontend/src/pages/Projects.tsx       | 105 +++-
 frontend/src/pages/ReportCompiler.tsx | 101 +++-
 frontend/src/services/api.ts          |  76 ++-
 12 files changed, 829 insertions(+), 1013 deletions(-)
```

### 3. Backend Compile Check

Command:

```powershell
cd backend
..\.venv312\Scripts\python.exe -m py_compile main.py app\crawler\engine.py app\audit\engine.py app\analytics\ga4.py app\models\database.py app\core\config.py
```

Result: PASS.

### 4. Frontend Build Check

Command:

```powershell
cd frontend
npm.cmd run build
```

Result: PASS.

Build output:

```text
Compiled successfully.
main.82db66f1.js
main.5c523103.css
```

### 5. Backend OpenAPI Route List

Server was running at `http://127.0.0.1:16500`.

Routes from `GET /openapi.json`:

```text
/
/api/audit-reports/{audit_id}
/api/audit-reports/{audit_id}/export/csv
/api/audit-reports/{audit_id}/export/pdf
/api/auth/login
/api/auth/logout
/api/auth/me
/api/auth/signup
/api/combined/{project_id}/dashboard
/api/crawl-jobs
/api/crawl-jobs/{job_id}
/api/crawl-jobs/{job_id}/audit
/api/crawl-jobs/{job_id}/export/csv
/api/crawl-jobs/{job_id}/pages
/api/ga4/connect
/api/ga4/{property_id}/devices
/api/ga4/{property_id}/overview
/api/ga4/{property_id}/search-queries
/api/ga4/{property_id}/top-pages
/api/projects
/api/projects/{project_id}
/api/projects/{project_id}/crawl
/api/projects/{project_id}/reaudit
/api/projects/{project_id}/recrawl
/api/projects/{project_id}/report-compiler
/api/projects/{project_id}/report-files/{filename}
```

### 6. Frontend API Route Usage

Source: `frontend/src/services/api.ts`

```text
api.signup() -> POST /api/auth/signup
api.login() -> POST /api/auth/login
api.me() -> GET /api/auth/me
api.logout() -> POST /api/auth/logout
api.listProjects() -> GET /api/projects
api.createProject() -> POST /api/projects
api.deleteProject() -> DELETE /api/projects/{id}
api.startCrawl() -> POST /api/projects/{projectId}/crawl
api.recrawlProject() -> POST /api/projects/{projectId}/recrawl
api.reauditProject() -> POST /api/projects/{projectId}/reaudit
api.getCrawlJob() -> GET /api/crawl-jobs/{jobId}
api.listCrawlJobs() -> GET /api/crawl-jobs
api.getCrawlPages() -> GET /api/crawl-jobs/{jobId}/pages?limit=200
api.runAudit() -> POST /api/crawl-jobs/{jobId}/audit
api.getAuditReport() -> GET /api/audit-reports/{auditId}
api.getReportCompiler() -> GET /api/projects/{projectId}/report-compiler
api.getCombinedDashboard() -> GET /api/combined/{projectId}/dashboard
api.getGA4Overview() -> GET /api/ga4/{propertyId}/overview?days={days}
downloads.crawlCsv() -> GET /api/crawl-jobs/{jobId}/export/csv
downloads.auditCsv() -> GET /api/audit-reports/{auditId}/export/csv
downloads.auditPdf() -> GET /api/audit-reports/{auditId}/export/pdf
downloads.reportFile() -> GET /api/projects/{projectId}/report-files/{filename}?disposition=attachment
openFiles.auditPdf() -> GET /api/audit-reports/{auditId}/export/pdf?disposition=inline
openFiles.reportFile() -> GET /api/projects/{projectId}/report-files/{filename}?disposition=inline
```

### 7. Frontend Routes Compared To Backend Routes

Result: route shapes are present in OpenAPI for the frontend API calls.

Notes:

- The comparison script initially reported mismatches because frontend route params were normalized to `{param}` while backend uses `{project_id}`, `{job_id}`, `{audit_id}`, and `{filename}`.
- No missing backend route shape was found for current `frontend/src/services/api.ts`.
- There is no frontend `api.getProject()` helper, even though backend has `GET /api/projects/{project_id}`. The project detail workflow was tested directly by HTTP.

## Workflow Inventory

### login/signup signup

- Component: `frontend/src/pages/AuthPage.tsx`
- Frontend API call: `api.signup()`
- Backend route: `POST /api/auth/signup`
- Expected result: customer token returned
- Actual result: PASS. Token and customer returned.
- Console/HTTP error: none
- Likely responsible file: `frontend/src/pages/AuthPage.tsx`, `backend/main.py`

### login/signup login

- Component: `frontend/src/pages/AuthPage.tsx`
- Frontend API call: `api.login()`
- Backend route: `POST /api/auth/login`
- Expected result: login token returned
- Actual result: PASS. Token and customer returned.
- Console/HTTP error: none
- Likely responsible file: `frontend/src/pages/AuthPage.tsx`, `backend/main.py`

### account page

- Component: `frontend/src/pages/Account.tsx`
- Frontend API call: `api.me()`
- Backend route: `GET /api/auth/me`
- Expected result: full customer/business fields returned
- Actual result: PASS. Returned `id`, `email`, `business_name`, `contact_name`, `phone`, `status`, `created_at`, `updated_at`, `last_login_at`.
- Console/HTTP error: none
- Likely responsible file: `frontend/src/pages/Account.tsx`, `frontend/src/services/api.ts`, `backend/main.py`

### create folder/project

- Component: `frontend/src/pages/Projects.tsx`
- Frontend API call: `api.createProject()`
- Backend route: `POST /api/projects`
- Expected result: project/folder returned
- Actual result: PASS. Project returned.
- Console/HTTP error: none
- Likely responsible file: `frontend/src/pages/Projects.tsx`, `frontend/src/services/api.ts`, `backend/main.py`

### project list

- Component: `frontend/src/pages/Projects.tsx`
- Frontend API call: `api.listProjects()`
- Backend route: `GET /api/projects`
- Expected result: customer projects returned
- Actual result: PASS. Project list returned.
- Console/HTTP error: none
- Likely responsible file: `frontend/src/pages/Projects.tsx`, `backend/main.py`

### project detail

- Component: no dedicated current page/helper
- Frontend API call: no `api.getProject()` helper in `frontend/src/services/api.ts`
- Backend route: `GET /api/projects/{project_id}`
- Expected result: project detail returned if called
- Actual result: PASS by direct HTTP call.
- Console/HTTP error: none
- Likely responsible file: `backend/main.py`; optional frontend gap in `frontend/src/services/api.ts`

### start crawl

- Component: `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Projects.tsx`
- Frontend API call: `api.startCrawl()`
- Backend route: `POST /api/projects/{project_id}/crawl`
- Expected result: pending crawl job returned
- Actual result: PASS. Pending crawl job returned.
- Console/HTTP error: none
- Likely responsible file: `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Projects.tsx`, `backend/main.py`

### crawl jobs list

- Component: `frontend/src/pages/CrawlJobs.tsx`
- Frontend API call: `api.listCrawlJobs()`
- Backend route: `GET /api/crawl-jobs`
- Expected result: crawl jobs returned
- Actual result: PASS. Crawl jobs returned, including `project_name` and `project_domain`.
- Console/HTTP error: none
- Likely responsible file: `frontend/src/pages/CrawlJobs.tsx`, `backend/main.py`

### crawl job detail

- Component: `frontend/src/pages/CrawlJob.tsx`
- Frontend API call: `api.getCrawlJob()`, `api.getCrawlPages()`
- Backend route: `GET /api/crawl-jobs/{job_id}`, `GET /api/crawl-jobs/{job_id}/pages`
- Expected result: crawl detail and page list returned
- Actual result: FAIL.
- Console/HTTP error: `500 Internal Server Error`
- Isolated HTTP result:

```text
GET /api/crawl-jobs/22 -> 500 Internal Server Error
GET /api/crawl-jobs/22/pages?limit=200 -> 500 Internal Server Error
```

- TestClient traceback:

```text
NameError: name '_owned_crawl_job' is not defined. Did you mean: 'run_crawl_job'?
backend/main.py line 1464 in get_crawl_job
```

- Likely responsible file: `backend/main.py`
- Root cause: helper functions `_owned_crawl_job()` and `_owned_audit_report()` are referenced but missing from the repaired `backend/main.py`.

### recrawl

- Component: `frontend/src/pages/CrawlJobs.tsx`, `frontend/src/pages/Projects.tsx`
- Frontend API call: `api.recrawlProject()`
- Backend route: `POST /api/projects/{project_id}/recrawl`
- Expected result: new pending crawl job returned
- Actual result: PASS. New pending crawl job returned.
- Console/HTTP error: none
- Likely responsible file: `frontend/src/pages/CrawlJobs.tsx`, `frontend/src/pages/Projects.tsx`, `backend/main.py`

### audit start

- Component: `frontend/src/pages/CrawlJob.tsx`, `frontend/src/pages/CrawlJobs.tsx`
- Frontend API call: `api.runAudit()`
- Backend route: `POST /api/crawl-jobs/{job_id}/audit`
- Expected result: audit id returned after completed crawl
- Actual result: FAIL / not runnable in this workflow pass because crawl detail polling failed first.
- Console/HTTP error: upstream `GET /api/crawl-jobs/{job_id}` returns `500`.
- Likely responsible file: `backend/main.py`, `backend/app/crawler/engine.py`
- Additional risk: `backend/main.py` also references missing `_owned_audit_report()` for audit report/export routes.

### audit report

- Component: `frontend/src/pages/AuditReport.tsx`
- Frontend API call: `api.getAuditReport()`
- Backend route: `GET /api/audit-reports/{audit_id}`
- Expected result: audit report returned
- Actual result: FAIL / not run because audit start was unavailable.
- Console/HTTP error: no audit id available; audit start blocked by crawl detail failure.
- Likely responsible file: `frontend/src/pages/AuditReport.tsx`, `backend/main.py`
- Additional risk: `GET /api/audit-reports/{audit_id}` uses missing `_owned_audit_report()`.

### report compiler

- Component: `frontend/src/pages/ReportCompiler.tsx`
- Frontend API call: `api.getReportCompiler()`
- Backend route: `GET /api/projects/{project_id}/report-compiler`
- Expected result: report compiler payload returned
- Actual result: PASS. Payload returned.
- Observed payload had no completed crawl/audit and no files:

```text
latest_crawl: null
latest_audit: null
files: []
```

- Console/HTTP error: none
- Likely responsible file: `frontend/src/pages/ReportCompiler.tsx`, `backend/main.py`

### report file open/download

- Component: `frontend/src/pages/ReportCompiler.tsx`
- Frontend API call: `openFiles.reportFile()`, `downloads.reportFile()`
- Backend route: `GET /api/projects/{project_id}/report-files/{filename}`
- Expected result: report file content returned
- Actual result: FAIL in workflow context.
- Console/HTTP error: no file request made because report compiler returned `files: []`.
- Likely responsible file: `backend/main.py` report compiler/write paths
- Root cause: no completed crawl/audit generated report files because crawl detail/audit flow is blocked by missing ownership helpers.

## Current Highest Priority Failures

### Failure 1: Crawl detail route crashes

- Exact page/component: `frontend/src/pages/CrawlJob.tsx`
- Exact frontend API call: `api.getCrawlJob(jobId)`
- Exact backend route: `GET /api/crawl-jobs/{job_id}`
- Expected result: crawl job JSON
- Actual result: `500 Internal Server Error`
- Console/HTTP error: backend `NameError`
- File likely responsible: `backend/main.py`
- Required repair: restore `_owned_crawl_job(job_id, customer, db)`.

### Failure 2: Crawl pages route crashes

- Exact page/component: `frontend/src/pages/CrawlJob.tsx`
- Exact frontend API call: `api.getCrawlPages(jobId)`
- Exact backend route: `GET /api/crawl-jobs/{job_id}/pages`
- Expected result: `{ total, pages }`
- Actual result: `500 Internal Server Error`
- Console/HTTP error: same missing `_owned_crawl_job()`
- File likely responsible: `backend/main.py`
- Required repair: restore `_owned_crawl_job(job_id, customer, db)`.

### Failure 3: Audit routes are at risk / blocked

- Exact page/component: `frontend/src/pages/CrawlJob.tsx`, `frontend/src/pages/CrawlJobs.tsx`, `frontend/src/pages/AuditReport.tsx`
- Exact frontend API calls: `api.runAudit(jobId)`, `api.getAuditReport(auditId)`, audit export helpers
- Exact backend routes:
  - `POST /api/crawl-jobs/{job_id}/audit`
  - `GET /api/audit-reports/{audit_id}`
  - `GET /api/audit-reports/{audit_id}/export/csv`
  - `GET /api/audit-reports/{audit_id}/export/pdf`
- Expected result: audit starts and reports load/export
- Actual result: audit start not reached because crawl detail polling fails
- Console/HTTP error: upstream crawl detail `500`
- File likely responsible: `backend/main.py`
- Required repair: restore `_owned_crawl_job()` and `_owned_audit_report(audit_id, customer, db)`.

## Summary

The app compiles and the frontend builds. Auth, account, project creation, project listing, start crawl, crawl jobs list, recrawl, and report compiler route all respond through direct API workflow tests.

The current blocking backend regression is missing ownership helper functions in `backend/main.py`:

```text
_owned_crawl_job
_owned_audit_report
```

These missing helpers cause the crawl detail page and pages API to return `500`, which blocks audit/report completion and report file generation.

## Repair Pass - 2026-06-05

### Code Repairs Applied

- `backend/main.py`
  - Restored `_owned_crawl_job(job_id, customer, db)`.
  - Restored `_owned_audit_report(audit_id, customer, db)`.
  - Hardened `_owned_project(project_id, customer, db)` so bad IDs return `404` instead of uncaught `ValueError`.
  - Added `folder_title` to `_serialize_project()` so create/list/detail project responses identify the actual report compiler folder.

### Verification Commands

Backend compile:

```powershell
cd backend
..\.venv312\Scripts\python.exe -m py_compile main.py app\crawler\engine.py app\audit\engine.py app\analytics\ga4.py app\models\database.py app\core\config.py
```

Result: PASS.

Frontend build:

```powershell
cd frontend
npm.cmd run build
```

Result: PASS.

Runtime:

```text
API: http://127.0.0.1:16500/ -> {"name":"Orb Weaver - Website ORB Intelligence Engine","version":"1.0.0","status":"operational"}
UI:  http://127.0.0.1:16510/ -> HTTP 200
```

### Workflow Retest Results

Smoke customer: `orb.repair.final.20260605064834@example.test`

Project: `16`, domain `www.iana.org`, folder `16_repair_final_20260605064834`

```text
login/signup: PASS
  signup HTTP 200, customer 17
  login HTTP 200, token issued

account page: PASS
  GET /api/auth/me HTTP 200
  business=Orb Repair Final 20260605064834
  contact=Repair Operator
  phone=555-0100

create folder/project: PASS
  POST /api/projects HTTP 200
  project=16
  domain=www.iana.org
  folder=16_repair_final_20260605064834

project list: PASS
  GET /api/projects HTTP 200
  count=1

project detail: PASS
  GET /api/projects/{id} HTTP 200
  domain=www.iana.org
  folder=16_repair_final_20260605064834

start crawl: PASS
  POST /api/projects/{id}/crawl HTTP 200
  job=26
  status=pending
  project=www.iana.org

crawl jobs list: PASS
  GET /api/crawl-jobs HTTP 200
  count=1

crawl job detail: PASS
  GET /api/crawl-jobs/{id} HTTP 200
  status=completed
  pages=2
  project=www.iana.org

crawl job detail pages: PASS
  GET /api/crawl-jobs/{id}/pages HTTP 200
  total=2

recrawl: PASS
  POST /api/projects/{id}/recrawl HTTP 200
  job=27
  status=pending
  project=www.iana.org
  follow-up DB status=completed
  follow-up DB pages=1

audit start: PASS
  POST /api/crawl-jobs/{id}/audit HTTP 200
  audit=6
  status=started

audit report: PASS
  GET /api/audit-reports/{id} HTTP 200
  project=www.iana.org
  DB overall_score=95.4
  DB warnings=5
  DB opportunities=1

report compiler: PASS
  GET /api/projects/{id}/report-compiler HTTP 200
  files=4

report file open/download: PASS
  inline HTTP 200
  attachment HTTP 200
  file=latest_report.json
```

### Updated Status

The original highest-priority backend regression is repaired. Crawl detail, crawl pages, audit start, audit report, report compiler, and report file open/download all pass direct workflow tests against the live local API.
