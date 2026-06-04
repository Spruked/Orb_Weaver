# Orb Weaver Spruked Subdomain Deployment

## Hostname

Use:

```text
orb-weaver.spruked.com
```

Do not use `Orb_Weaver.spruked.com`. Public DNS hostnames are case-insensitive and should not use underscores.

## Runtime Boundary

- Website/navigation surface: Spruked.com adds a navigation tab to `https://orb-weaver.spruked.com`.
- Orb Weaver frontend: serves the React build.
- Orb Weaver backend: serves `/api/*` on the same host.
- Customer records, sessions, projects, crawls, and audits stay in the Orb Weaver backend database.

## Reverse Proxy Shape

Point the subdomain to the host running Orb Weaver, then proxy:

```nginx
server {
    server_name orb-weaver.spruked.com;

    location /api/ {
        proxy_pass http://127.0.0.1:16500/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root C:/dev/Desktop/Orb_Weaver/frontend/build;
        try_files $uri /index.html;
    }
}
```

## Local Production Commands

```powershell
cd C:\dev\Desktop\Orb_Weaver
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm.cmd install
npm.cmd run build
cd ..\backend
..\.venv312\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 16500
```

## Spruked.com Navigation Tab

Add a top-level navigation item on the main Spruked.com website:

```text
Orb Weaver -> https://orb-weaver.spruked.com
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
