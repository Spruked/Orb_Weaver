# ORB Dock Station v2.0.0

Owner-facing configuration surface for ORB profiles.

## Architecture

```
WEBSITE OWNER
      ↓
ORB DOCK STATION UI  (React + Electron)
      ↓ authenticated owner API
ORB WEAVER AUTHORITY  (FastAPI)
├── Draft profile
├── Published profile
├── Version history
├── Stage Governor
└── ...
      ↓ read-only published runtime contract
WEBSITE ORB
```

## Quick Start

```bash
./install.sh

# Terminal 1 — Backend
cd backend && source venv/bin/activate && uvicorn app.main:app --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Login: `owner@orb.system` / `orb-owner-2026`

## Panels

- **Overview** — Profile picker, diff, publish/restore
- **Behavior & Personality** — Sliders, doctrine flags, stage directives
- **Speech & Listening** — Interruption, timing, greeting, tone check
- **Intelligence & Models** — Gateway lanes, provider health
- **Tools & Permissions** — Catalog with Stage Governor scoping
- **Appearance & Motion** — Skin, speed doctrine, clumsy motion
- **Conversations** — Transcript viewer
- **Statistics** — Pipeline latency, action governance, visitor metrics
- **Diagnostics** — Health reports, pointer recovery

## Key Design Rules

1. **Selecting a tool does not authorize it** — Stage Governor still validates every action
2. **Publish is explicit and confirmed** — never a side effect
3. **Orb Assistant reads published config read-only** — no local authority
4. **Draft → Published lifecycle** — versioned, reversible

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /auth/login` | Owner authentication |
| `GET /profiles` | List all profiles |
| `GET /profiles/{id}` | Get profile |
| `PATCH /profiles/{id}` | Update draft profile |
| `POST /profiles/{id}/publish` | Publish profile |
| `POST /profiles/{id}/restore/{version}` | Restore version |
| `GET /profiles/{id}/diff` | Draft vs published diff |
| `GET /speech/{id}` | Speech settings |
| `GET /behavior/{id}/personality` | Personality blend |
| `GET /intelligence/{id}` | Model lanes |
| `GET /tools/{id}` | Tool catalog |
| `GET /appearance/{id}` | Appearance config |
| `GET /conversations` | Conversation log |
| `GET /statistics` | Statistics snapshots |
| `GET /diagnostics/health` | System health |
| `POST /diagnostics/pointer/recovery` | Run pointer recovery |
