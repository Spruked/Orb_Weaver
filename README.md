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
- Saves preflight output into the configured client intelligence substrate.

### SEO Audit Engine

- Scores overall, SEO, performance, accessibility, content, technical, mobile, and security categories.
- Groups issues into critical items, warnings, and opportunities.
- Produces recommendations, affected URL lists, report exports, and client-pack audit snapshots.

### Customer Workspace and Checkout

- Customer signup/login with bearer-token sessions.
- Per-customer project ownership.
- Account, cart, checkout order, admin customer, project, crawl, audit, GA4, report, and legal pages.
- Service catalog includes Starter Audit, Growth Audit, and Premium Intelligence Pack.

## Architecture

```text
Orb_Weaver/
  backend/
    app/
      crawler/          # Async website crawler engine
      audit/            # SEO scoring and issue detection
      analytics/        # GA4 API integration
      models/           # SQLAlchemy database models
      core/             # Configuration and settings
    main.py             # FastAPI application entry
    requirements.txt
  Preflight Scanner/
    preflight_site_scan.py
    orbs_preflight.py
    ssi_fastapi.py
    setup_orb.sh
  frontend/
    public/             # favicon, logo, robots.txt, sitemap.xml
    scripts/            # Playwright smoke tests
    src/
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
python -m compileall backend/main.py backend/app "Preflight Scanner/preflight_site_scan.py"
```

Frontend build:

```bash
cd frontend
REACT_APP_API_URL=http://127.0.0.1:16500 npm run build
```

Playwright preflight smoke test:

```bash
cd frontend
npm run smoke:preflight
```

## Root Docker Image

The repo has a root Dockerfile for WSL/tunnel use. Build from the repository root:

```bash
docker build -t orb-weaver:latest .
```

Run the combined container:

```bash
docker run --rm \
  -p 16500:16500 \
  -p 16510:16510 \
  -v "$PWD/.docker-data:/app/backend/data" \
  -v "$PWD/.docker-substrate:/app/substrate" \
  --env-file .env \
  orb-weaver:latest
```

Container ports:

```text
Backend API: 16500
Frontend UI: 16510
```

The root image copies `backend/`, `frontend/build`, and `Preflight Scanner/` into one container. The backend runs from `/app/backend`, so the copied scanner resolves at `/app/Preflight Scanner`.

## API Endpoints

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
DATABASE_URL=sqlite:///./data/orb_weaver.db
ORB_WEAVER_SUBSTRATE_ROOT=./orb_weaver_substrate
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

Preflight, crawl, and audit jobs preserve local client intelligence under `ORB_WEAVER_SUBSTRATE_ROOT`.

Expected artifacts include:

- `current/latest_preflight.json`
- `current/latest_crawl.json`
- `current/latest_audit.json`
- `website_orb_context/site_preflight_report.json`
- `website_orb_context/latest_context.json`
- `history/`
- `recommendations/`
- `reports/`
- `local_index/client_index.sqlite`

## Premium Intelligence Pack

The Premium Intelligence Pack is in the service catalog and checkout flow. It currently creates a cart item and checkout order. The intelligence artifacts are produced when preflight, crawl, and audit jobs run and are preserved into the client pack substrate.

Automatic post-payment entitlement and fulfillment are not yet wired.

## Documentation

- `docs/DEPLOYMENT_ORB_WEAVER_SPRUKED.md`
- `docs/PACK_CONTRACT_V0_1.md`
- `docs/INTELLIGENCE_PRESERVATION.md`
- `docs/ORB_WEAVER_INTELLIGENCE_GRAPH_SPEC.md`
- `docs/ORB_WEAVER_FAILURE_INVENTORY.md`

## License

Proprietary. All rights reserved.
