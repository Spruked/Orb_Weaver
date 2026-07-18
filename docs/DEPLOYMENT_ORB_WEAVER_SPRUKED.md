# Orb Weaver Spruked Subdomain Deployment

## Hostname

Use:

```text
orbweaver.spruked.com
```

Do not use `Orb_Weaver.spruked.com`. Public DNS hostnames are case-insensitive and should not use underscores.

## Runtime Boundary

- Website/navigation surface: Spruked.com adds a navigation tab to `https://orbweaver.spruked.com`.
- Orb Weaver frontend: serves the React app on local port `16510`.
- Orb Weaver backend: serves `/api/*` on local port `16500`.
- Customer records, sessions, projects, crawls, and audits stay in the Orb Weaver backend database.

## Cloudflare Tunnel

Tunnel ID:

```text
911f1d54-b575-4c79-aeec-b62ee5b1050a
```

Point `orbweaver.spruked.com` to this tunnel and route local services by path:

```yaml
tunnel: 911f1d54-b575-4c79-aeec-b62ee5b1050a
credentials-file: C:\Users\bryan\.cloudflared\911f1d54-b575-4c79-aeec-b62ee5b1050a.json

ingress:
  - hostname: orbweaver.spruked.com
    path: /api/*
    service: http://localhost:16500
  - hostname: orbweaver.spruked.com
    path: /*
    service: http://localhost:16510
  - service: http_status:404
```

Cloudflare dashboard order:

```text
1. orbweaver.spruked.com /api/* -> http://localhost:16500
2. orbweaver.spruked.com *      -> http://localhost:16510
3. Catch-all                    -> http_status:404
```

Keep `/api/*` above `*`.

DNS route command:

```powershell
cloudflared tunnel route dns 911f1d54-b575-4c79-aeec-b62ee5b1050a orbweaver.spruked.com
```

Tunnel run command:

```powershell
cloudflared tunnel --config C:\dev\Desktop\Orb_Weaver\deploy\cloudflared\orbweaver.spruked.com.yml run 911f1d54-b575-4c79-aeec-b62ee5b1050a
```

## Local Dev Commands

### Windows

```powershell
cd C:\dev\Desktop\Orb_Weaver
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv312\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 16500
```

```powershell
cd C:\dev\Desktop\Orb_Weaver\frontend
$env:PORT = "16510"
$env:HOST = "127.0.0.1"
$env:BROWSER = "none"
$env:REACT_APP_API_URL = ""
npm.cmd start
```

### WSL Clone

```bash
git clone https://github.com/Spruked/Orb_Weaver.git
cd Orb_Weaver
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
cp .env.example .env
```

Backend:

```bash
cd backend
../.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 16500
```

Frontend:

```bash
cd frontend
npm install
REACT_APP_API_URL=http://127.0.0.1:16500 npm run build
npx serve -s build -l 16510
```

Validation:

```bash
python -m compileall backend/main.py backend/app "Preflight Scanner/preflight_site_scan.py"
python3 scripts/build_preflight_tool_cache.py --domain orbweaver.spruked.com --backend-url ""
cd frontend
npm run smoke:preflight
REACT_APP_API_URL=http://127.0.0.1:16500 npm run build
```

If `cloudflared` runs inside WSL, adapt the config credentials path to the WSL filesystem path for the tunnel JSON. Keep the ingress services on `http://localhost:16500` and `http://localhost:16510` when the backend and frontend are also running inside WSL.

### WSL Docker

Build the combined root image from the repo root:

```bash
docker build -t orb-weaver:latest .
```

Run it:

```bash
docker run --rm \
  -p 16500:16500 \
  -p 16510:16510 \
  -v "$PWD/.docker-data:/app/backend/data" \
  -v "$PWD/.docker-substrate:/app/substrate" \
  -v "$PWD/.runtime/rdrive_mcp_server:/app/rdrive_mcp_server:ro" \
  --env-file .env \
  orb-weaver:latest
```

The root Dockerfile builds the React frontend, runs the FastAPI backend on `16500`, serves the frontend on `16510` with nginx, and copies `Preflight Scanner/` into `/app/Preflight Scanner` for backend preflight imports.

Orb Weaver's own showcase ORB may use the repo-local Desktop MCP server slot at `.runtime/rdrive_mcp_server`. Basic customer Website ORB builds must not require this folder or the MCP relay.

### Self-Scan / Pointer Verification

Run a local self-scan so Orb Weaver scans its own public site and regenerates the pointer map:

```bash
python3 scripts/self_scan_orbweaver.py --url https://orbweaver.spruked.com --max-pages 50
python3 scripts/build_preflight_tool_cache.py --domain orbweaver.spruked.com --backend-url ""
```

Expected artifacts:

```text
substrate/clients/orbweaver.spruked.com/website_orb_context/pointer_plot_map.json
substrate/clients/orbweaver.spruked.com/website_orb_context/tool_cache.json
```

The pointer map must report nonzero `record_count`, no duplicate `target_id` values, scoped locator data, and acceptable confidence quality under `POINTER_RECOVERY_DOCTRINE.md`. Record count and duplicate checks alone are not a passed map. If the stable ratio, uncertainty ratio, absolute safe-pointer floor, or conflict threshold fails, report `POINTER_RECOVERY_REQUIRED`, allow only verified/stable live-matched guidance, and block deployment Preflight until recovery and required review complete.

## Spruked.com Navigation Tab

Add a top-level navigation item on the main Spruked.com website:

```text
Orb Weaver -> https://orbweaver.spruked.com
```

Keep this as a link to the Orb Weaver app. Do not merge Spruked.com website routing with the Orb Weaver engine backend.

## Customer Access

The app now supports:

- customer signup
- customer login
- bearer-token customer sessions
- Account tab
- per-customer project ownership
- protected crawl, audit, report, and export endpoints

## Protection Notes

- Use HTTPS before public customer signup.
- Keep `SECRET_KEY` unique per deployment.
- Keep the customer database backed up.
- Publish Terms, Privacy, and acceptable-use language before offering public website crawling access.
