# Orb Weaver - Website ORB Intelligence Engine

Orb Weaver is a local-first website intelligence platform with authenticated customer workspaces, website crawling, preflight scanning, ORB-readable semantic scoring, report generation, checkout records, client intelligence packs, and Cloudflare Tunnel deployment support.

## Features

### Website ORB Crawler Engine

- Async crawling with configurable page limits, crawl depth, delay, sitemap discovery, and context seed URLs.
- On-page SEO analysis for titles, meta descriptions, headings, canonicals, links, images, and indexability.
- Technical SEO checks for SSL, robots.txt, sitemap.xml, schema markup, redirects, and broken links.
- Semantic and entity analysis for ORB-readable website context.
- Crawl history and client-pack preservation for later assistant use.

### Preflight Scanner

- Runs install/readiness reconnaissance before or alongside full crawling.
- Detects sitemap, robots, CMS signals, auth pages, contact forms, products, checkout, booking, blog, PDFs, third-party scripts, and custom behavior flags.
- Exposes dashboard controls on the main dashboard and per-project Client Folder cards.
- Saves preflight output into the canonical client vault.

### SEO Audit Engine

- Scores overall, SEO, performance, accessibility, content, technical, mobile, and security categories.
- Groups issues into critical items, warnings, and opportunities.
- Produces recommendations, affected URL lists, report exports, and client-pack audit snapshots.

### Customer Workspace and Checkout

- Customer signup/login with bearer-token sessions.
- Per-customer project ownership.
- Account, cart, checkout order, admin customer, project, crawl, audit, GA4, report, and legal pages.
- Service catalog includes Starter Audit, Growth Audit, and Premium Intelligence Pack.

### Website ORB Voice Runtime

- The live public Website ORB voice runtime is `frontend/src/landing/AutonomousOrb.tsx`.
- One click starts microphone capture; end-of-speech detection submits automatically through `POST /api/orb/website-voice`.
- The backend performs Faster Whisper STT, ORB cognition, protected identity answer selection, local LLM answers for ordinary questions, local TTS/cache, and WAV delivery.
- Browser `SpeechRecognition` and browser `speechSynthesis` are not the canonical public ORB voice path.
- Gold-master replication details live in `docs/ORB_VOICE_RUNTIME_REPLICATION_REPORT.md`.
- Pointer/runtime intent details live in `docs/ORB_POINTER_RUNTIME_MODEL.md`.

### Universal ORB Loader and Factory Identity

- `frontend/public/orb-loader.js` is the universal external-script adapter; `frontend/src/adapters/react-component.tsx` is the native React/TypeScript adapter. Both use the shared `frontend/src/orb-client/` core.
- Every installation starts with immutable `orb_factory_default_v1` (**O.R.B.S. Factory Default**) using the tuxedo asset at `/orb-skins/tuxorb.png`.
- Factory Default is the permanent fallback. A failed custom asset and an explicit owner rollback both restore it immediately.
- Skin selection is an appearance-only PATCH operation: it does not rebuild Site World or Pointer Map, restart the runtime, or disconnect the WebSocket.
- The repository and local container image can include these files without implying that the public `orbweaver.spruked.com` loader has been deployed.

### Pointer Quality Gate

- Pointer extraction count and duplicate-ID checks are not deployment approval. Confidence quality must also pass the Pointer Recovery doctrine.
- Campaign legacy crawl job `#24` extracted 137 pointers: 1 is safe and 136 are uncertain, so its truthful status is `POINTER_RECOVERY_REQUIRED`, not passed.
- A non-canonical proof recovery produced 8 renders, 104 viewport segments, 28 recovered pointers, and 109 unresolved pointers. It did not overwrite the canonical map because job `#24` has no lifecycle evidence chain.
- A lifecycle ORB Scan is still required before campaign pointer readiness or deployment can be approved.

### ORB Product Boundary

- Orb Weaver's own demo ORB is the showcase/development ORB. It may use Desktop MCP, OCR, browser review, and visual audit tools to prove the ceiling of the ecosystem.
- Installed customer Website ORBs are website-native packages: target map, compiled intent cache, voice assets, approved website context, and deployment files.
- Pointer guidance is core to every ORB. Every Website ORB gets a Pointer Plot Map, runtime pointer resolution, and verified visual guidance; tiers change coverage, density, maintenance, branding, and adaptation.
- Basic customer ORBs do not inherit Desktop MCP tools from the Orb Weaver demo.
- Advanced customer deployments can receive explicit tool adapters only when the customer, tier, environment, and confirmation policy justify them.
- The Desktop ORB and DockStation remain the primary home for the deeper MCP tool system.

## Canonical Storage Authority

The repository-root `vault_system/` is the only storage authority.

```text
vault_system/
  apriori/                 # canonical seed truths
  posteriori/              # learned deterministic memory
  cognition/               # TPC and reasoning-worker histories
  clients/<domain>/        # scans, crawls, Site Worlds, pointer maps and reports
  databases/               # SQLite application databases
  reports/                 # generated suite reports
  indexes/                 # semantic/global indexes
  manifests/               # scan, pack and migration manifests
  schemas/                 # vault data schemas
  runtime/
    tts_cache/             # generated speech audio
    browser_reviews/       # browser verification output
    state/                 # runtime state
    logs/                  # runtime logs
  backups/migration_conflicts/
```

Component folders such as `backend/`, `Orb_Assistant/`, and legacy `substrate/` paths may contain source code or compatibility links, but they must not own independent data stores.

## Architecture

```text
Orb_Weaver/
  backend/
    app/
      crawler/          # Async website crawler engine
      audit/            # SEO scoring and issue detection
      analytics/        # GA4 API integration
      models/           # SQLAlchemy database models
      core/             # Configuration and canonical storage authority
    main.py             # FastAPI application entry
    requirements.txt
  vault_system/         # single persistent/runtime storage authority
  Preflight Scanner/
    preflight_site_scan.py
    orbs_preflight.py
    ssi_fastapi.py
    setup_orb.sh
  frontend/
    public/             # favicon, logo, robots.txt, sitemap.xml
    scripts/            # Playwright smoke tests
    src/
      landing/          # live AutonomousOrb voice runtime and landing app
      components/
      pages/
      services/
  deploy/cloudflared/   # Cloudflare Tunnel config
  docs/                 # deployment, pack contract, intelligence specs
```

## Quick Start from WSL

```bash
git clone https://github.com/Spruked/Orb_Weaver.git
cd Orb_Weaver
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
cp .env.example .env
```

Run the backend:

```bash
cd backend
../.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 16500
```

Run the frontend in another terminal:

```bash
cd frontend
npm install
REACT_APP_API_URL=http://127.0.0.1:16500 npm run build
npx serve -s build -l 16510
```

Local URLs:

```text
Backend API: http://127.0.0.1:16500
Frontend UI: http://127.0.0.1:16510
```

## Windows Local Commands

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv312\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 16500
```

```powershell
cd frontend
$env:REACT_APP_API_URL = "http://127.0.0.1:16500"
npm install
npm run build
npx serve -s build -l 16510
```

## Validation

Backend compile:

```bash
python -m compileall backend/main.py backend/app "Preflight Scanner/preflight_site_scan.py" vault_system scripts/migrate_to_canonical_vault.py
```

Frontend build:

```bash
cd frontend
REACT_APP_API_URL=http://127.0.0.1:16500 npm run build
```

Universal loader and Factory lifecycle:

```bash
cd frontend
npm run verify:factory-skin
npm run smoke:orb-loader
```

Playwright preflight smoke test:

```bash
cd frontend
npm run smoke:preflight
```

Vault migration dry run:

```bash
python3 scripts/migrate_to_canonical_vault.py
```

Stop Orb Weaver writers before applying or finalizing migration:

```bash
python3 scripts/migrate_to_canonical_vault.py --apply
python3 scripts/migrate_to_canonical_vault.py --finalize
```

## Root Docker Image

The repo has a root Dockerfile for WSL/tunnel use. Build from the repository root:

```bash
docker build -t orb-weaver:latest .
```

Run the combined container with one storage mount:

```bash
docker run --rm \
  -p 16500:16500 \
  -p 16510:16510 \
  -v "$PWD/vault_system:/app/vault_system" \
  --env-file .env \
  orb-weaver:latest
```

Container ports:

```text
Backend API: 16500
Frontend UI: 16510
```

The root image compiles the React frontend during Docker build, copies the resulting `/app/frontend/build` into the final image, and serves it with nginx. Running `npm run build` in the workspace does not update the public container by itself; use `docker compose up -d --build orb-weaver` only after development verification and confirm the served main bundle hash before public browser tests.

Static frontend: `http://127.0.0.1:16510`

Backend API: `http://127.0.0.1:16500`

Public tunnel routing is documented in `deploy/cloudflared/orbweaver.spruked.com.yml`.

## API Endpoints

### Website ORB Voice

- `POST /api/orb/website-voice` - Upload recorded audio for STT, answer selection, TTS/cache, and one spoken response
- `POST /api/orb/website-text` - Submit an existing transcript through the same answer/TTS path, with optional project cache lookup for authenticated Orb Weaver showcase usage
- `POST /api/orb/tts` - Generate/cache TTS for text
- `GET /api/orb/tts/{audio_id}` - Retrieve cached WAV/audio
- `GET /api/orb/capabilities` - Current ORB voice/tool capability report, including the demo-vs-customer product boundary

### Auth and Customer

- `POST /api/auth/signup` - Create customer account
- `POST /api/auth/login` - Create customer session
- `GET /api/auth/me` - Current customer profile
- `POST /api/auth/logout` - End current session

### Projects

- `POST /api/projects` - Create project
- `GET /api/projects` - List customer projects
- `GET /api/projects/{id}` - Get project details
- `DELETE /api/projects/{id}` - Delete project

### Crawling

- `POST /api/projects/{id}/crawl` - Start crawl job
- `POST /api/projects/{id}/recrawl` - Re-run crawl with context seed URLs
- `GET /api/crawl-jobs` - List crawl jobs
- `GET /api/crawl-jobs/{id}` - Get crawl status
- `GET /api/crawl-jobs/{id}/pages` - Get crawled pages

### Preflight

- `GET /api/projects/{id}/preflight` - Get latest preflight report
- `POST /api/projects/{id}/preflight` - Run the copied Preflight Scanner for the project

### Auditing and Reports

- `POST /api/crawl-jobs/{id}/audit` - Run SEO audit
- `POST /api/projects/{id}/reaudit` - Re-run audit for latest crawl
- `GET /api/audit-reports/{id}` - Get audit report
- `GET /api/projects/{id}/report-compiler` - Report compiler payload
- `GET /api/projects/{id}/report-files/{filename}` - Retrieve report file

### Cart and Checkout

- `GET /api/products` - Service catalog
- `GET /api/cart` - Current customer cart
- `POST /api/cart/items` - Add/update cart item
- `DELETE /api/cart/items/{sku}` - Remove cart item
- `POST /api/cart/checkout` - Create Stripe or PayPal checkout order
- `GET /api/checkout/orders` - Customer checkout order history

### GA4 and Combined Dashboard

- `GET /api/ga4/{property_id}/overview` - Full traffic report
- `GET /api/combined/{project_id}/dashboard` - Unified dashboard data

## Configuration

Copy `.env.example` to `.env` and adjust deployment-specific values.

```env
DEBUG=false
SECRET_KEY=change-this-secret
ORB_WEAVER_VAULT_ROOT=../vault_system
ORB_WEAVER_SUBSTRATE_ROOT=../vault_system
DATABASE_URL=sqlite:///../vault_system/databases/orb_weaver.db
ORB_TTS_CACHE_DIR=../vault_system/runtime/tts_cache
CHROME_DEVTOOLS_OUTPUT_ROOT=../vault_system/runtime/browser_reviews
PUBLIC_BASE_URL=http://127.0.0.1:16510

GA4_PROPERTY_ID=
GA4_CREDENTIALS_PATH=

CRAWL_MAX_PAGES=1000
CRAWL_DELAY=1.0
CRAWL_TIMEOUT=30
CRAWL_MAX_DEPTH=5

STRIPE_SECRET_KEY=
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
```

## Cloudflare Tunnel

Tunnel config is staged at:

```text
deploy/cloudflared/orbweaver.spruked.com.yml
```

Path routing:

```text
orbweaver.spruked.com /api/* -> http://localhost:16500
orbweaver.spruked.com *      -> http://localhost:16510
```

Keep `/api/*` above `*`. For WSL, make sure the tunnel process can reach the same host and ports where the backend and frontend are listening.

## Client Intelligence Pack

Preflight, crawl, audit, Site World, pointer-map, and report jobs preserve local client intelligence under:

```text
vault_system/clients/<domain>/
```

Expected artifacts include:

- `current/latest_preflight.json`
- `current/latest_crawl.json`
- `current/latest_audit.json`
- `website_orb_context/site_preflight_report.json`
- `website_orb_context/latest_context.json`
- `website_orb_context/site_world.json`
- `website_orb_context/pointer_plot_map.json`
- `website_orb_context/pointer_manifest.json`
- `history/`
- `recommendations/`
- `reports/`
- `local_index/client_index.sqlite`

## Premium Intelligence Pack

The Premium Intelligence Pack is in the service catalog and checkout flow. It currently creates a cart item and checkout order. The intelligence artifacts are produced when preflight, crawl, and audit jobs run and are preserved into the canonical client vault.

Automatic post-payment entitlement and fulfillment are not yet wired.

## Documentation

- `docs/README.md` (central documentation index)
- `docs/DEPLOYMENT_ORB_WEAVER_SPRUKED.md`
- `docs/ORB_MARKETPLACE_ARCHITECTURE.md`
- `docs/ORB_WEAVER_V1_TRANSACTIONAL_DOCTRINE.md`
- `docs/PACK_CONTRACT_V0_1.md`
- `docs/INTELLIGENCE_PRESERVATION.md`
- `docs/ORB_WEAVER_INTELLIGENCE_GRAPH_SPEC.md`
- `docs/ORB_WEAVER_FAILURE_INVENTORY.md`
- `vault_system/README.md`

## License

Proprietary. All rights reserved.
