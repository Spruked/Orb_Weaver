# ORB Diagnostic Bay — Real Engineering Plan
### FastAPI Bridge: Turning the Demo into a Genuine Product
**Status:** Planning. Nothing in this document is built yet.
**Dependency:** Diagnostic Bay HTML is complete. This is the backend it needs.

---

## What "Real" Means Here

Right now the Diagnostic Bay:
- Has a mock login gate (accepts anything)
- Runs scripted DOM sequences when the user scrolls
- Logs to an in-memory JS array that resets on page refresh
- Does not touch your MCP tools
- Does not persist anything

For it to be a real product used by real paying customers, it needs:
- Actual session authentication (login = a real account)
- A controlled bridge to a scoped subset of your MCP tools
- A persistent audit log with a real timestamp and a real user identifier
- A sandbox profile so a customer's session can only trigger safe, bounded actions
- Rate limiting and abuse protection before it faces the public internet

None of that is exotic engineering. It is four bounded problems solved in order.

---

## Architecture Overview

```
Browser (Diagnostic Bay HTML)
        │
        │  HTTPS
        ▼
FastAPI Bridge (NEW — this document)
        │
        ├── Auth layer         ← validates session token
        ├── Scope enforcer     ← maps user tier to allowed tools
        ├── MCP dispatcher     ← calls the actual tools on R: drive
        ├── Audit writer       ← persists every action to SQLite
        └── Result formatter   ← shapes tool output for the front end
        │
        ▼
MCP Server (existing — R: drive services)
        │
        ├── 23+ tools (existing)
        └── Sandbox profile (NEW — scoped-down tool list for demo use)
```

The browser never talks to the MCP server directly.
The bridge is the only thing that knows the MCP server exists.
The bridge enforces the scope boundary on every single request.

---

## Phase 1 — Auth Layer

**Goal:** replace the mock gate with a real session check.

### What to build

A simple account table and session token system. This does not need to be OAuth or
a full identity platform at this stage. A `users` table, a `sessions` table, and a
`POST /auth/login` endpoint that returns a signed JWT.

```python
# models — SQLite via SQLAlchemy (already in your stack likely)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)   # ulid
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    tier = Column(String, default="basic")  # basic | pro | enterprise
    created_at = Column(DateTime)
    active = Column(Boolean, default=True)

class Session(Base):
    __tablename__ = "sessions"
    token = Column(String, primary_key=True)  # signed JWT
    user_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime)
    expires_at = Column(DateTime)
    revoked = Column(Boolean, default=False)
```

```python
# endpoint

@router.post("/auth/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.active:
        raise HTTPException(status_code=403, detail="Account suspended")
    token = create_jwt(user.id, user.tier)
    return {"token": token, "tier": user.tier, "user_id": user.id}
```

### What changes in the HTML

The gate form POSTs to `/api/auth/login`. On success, it stores the JWT in
`sessionStorage` (not `localStorage` — session only, clears on tab close).
Every subsequent request to the bridge sends `Authorization: Bearer <token>`.

### Wiring point

Replace this comment in `diagnostic-bay.html`:
```javascript
// TODO: wire to real auth
document.getElementById('gate-btn').addEventListener('click', () => { ... })
```
With a real fetch to `/api/auth/login`.

---

## Phase 2 — Scope Enforcer

**Goal:** a customer's session can only trigger the tools appropriate to their account
tier. A demo-tier user cannot accidentally (or deliberately) trigger a destructive
MCP action.

### The scope table

```python
TOOL_SCOPES = {
    "demo": [
        "orb.fill_text",
        "orb.open_file_readonly",
        "orb.deploy_morb_diagnostic",
        "orb.research_topic",
    ],
    "basic": [
        "orb.fill_text",
        "orb.open_file_readonly",
        "orb.deploy_morb_diagnostic",
        "orb.research_topic",
        "orb.scan_site",
        "orb.summarize_document",
    ],
    "pro": [
        # all basic tools +
        "orb.write_file",
        "orb.send_draft",        # draft only, does not send without confirm
        "orb.schedule_task",
        "orb.query_records",
        "orb.deploy_morb_repair",
    ],
    "enterprise": [
        # all pro tools +
        "orb.swarm_deploy",
        "orb.mesh_coordinate",
        "orb.full_site_audit",
        "orb.integrate_crm",
        # ... up to all 23+ tools with full capability
    ],
}

def get_allowed_tools(tier: str) -> list[str]:
    return TOOL_SCOPES.get(tier, TOOL_SCOPES["demo"])

def enforce_scope(tool_name: str, tier: str) -> bool:
    return tool_name in get_allowed_tools(tier)
```

### Every bridge endpoint runs this check first

```python
async def dispatch_tool(
    tool_name: str,
    params: dict,
    user: User = Depends(get_current_user)
):
    if not enforce_scope(tool_name, user.tier):
        audit_log(user.id, tool_name, params, result="SCOPE_DENIED")
        raise HTTPException(status_code=403, detail=f"Tool {tool_name} not available on {user.tier} tier")
    # proceed to dispatch
```

---

## Phase 3 — MCP Dispatcher

**Goal:** the bridge calls your actual R: drive MCP tools and returns real results
to the front end.

### Connecting to your existing MCP server

Your MCP server already exists on the R: drive. The bridge needs a client
that speaks to it. Two options depending on your MCP server's transport:

**Option A — HTTP transport (if your MCP server exposes endpoints)**
```python
import httpx

MCP_BASE_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8020")
MCP_API_KEY  = os.getenv("MCP_API_KEY")   # internal auth between bridge and MCP

async def call_mcp_tool(tool_name: str, params: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{MCP_BASE_URL}/tools/{tool_name}",
            json={"params": params},
            headers={"X-Internal-Key": MCP_API_KEY},
        )
        response.raise_for_status()
        return response.json()
```

**Option B — stdio transport (if your MCP server runs as a subprocess)**
```python
import asyncio, json

async def call_mcp_tool_stdio(tool_name: str, params: dict) -> dict:
    # MCP stdio protocol: send a JSON-RPC call, read the response
    proc = await asyncio.create_subprocess_exec(
        "python", "R:/services/mcp_server.py",   # your actual path
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    request = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": params}
    }) + "\n"
    stdout, _ = await proc.communicate(input=request.encode())
    return json.loads(stdout)
```

### Which option to use

If your MCP server already has FastAPI or HTTP routes: Option A.
If it's the stdio-based MCP reference implementation: Option B.
We resolve this when you tell me how the 23+ tools are currently exposed.

### Sandbox profile for demo use

Before any customer session touches your real tools, you need a demo profile
that returns representative results without touching real data:

```python
DEMO_RESPONSES = {
    "orb.fill_text": lambda params: {
        "field": params.get("target"),
        "written": params.get("content"),
        "status": "ok",
        "chars": len(params.get("content", ""))
    },
    "orb.open_file_readonly": lambda params: {
        "filename": params.get("path"),
        "lines": [
            f"target: {params.get('path', 'unknown')}",
            f"status: opened by ORB session",
            f"scope: demo-readable",
            "note: real file content returned on production tier"
        ],
        "status": "ok"
    },
    # ... one for each demo-tier tool
}

async def dispatch_with_sandbox_fallback(tool_name, params, tier):
    if tier == "demo" and tool_name in DEMO_RESPONSES:
        return DEMO_RESPONSES[tool_name](params)
    return await call_mcp_tool(tool_name, params)
```

---

## Phase 4 — Persistent Audit Log

**Goal:** every action taken in every session is written to disk, timestamped,
user-identified, and retrievable. This is what you show an enterprise buyer when
they ask "prove it did what you said it did."

### Schema

```python
class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(String, primary_key=True)       # ulid
    session_id = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"))
    tool_name = Column(String, nullable=False)
    params_json = Column(Text)                  # JSON blob — no PII in params at demo tier
    result_status = Column(String)              # ok | error | scope_denied
    result_summary = Column(Text)
    duration_ms = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_hash = Column(String)                    # hashed, not raw IP
```

### Every dispatch writes to this table

```python
async def dispatch_and_audit(tool_name, params, user, session_id, ip):
    start = time.monotonic()
    result_status = "error"
    result_summary = ""

    try:
        result = await dispatch_with_sandbox_fallback(tool_name, params, user.tier)
        result_status = "ok"
        result_summary = result.get("status", "")
        return result
    except HTTPException as e:
        result_status = "scope_denied" if e.status_code == 403 else "error"
        result_summary = str(e.detail)
        raise
    finally:
        duration_ms = int((time.monotonic() - start) * 1000)
        db.add(AuditEvent(
            id=str(ulid.ULID()),
            session_id=session_id,
            user_id=user.id,
            tool_name=tool_name,
            params_json=json.dumps(sanitize_params(params)),
            result_status=result_status,
            result_summary=result_summary,
            duration_ms=duration_ms,
            ip_hash=hash_ip(ip),
        ))
        db.commit()
```

### Audit API endpoint (so the front end can fetch the real log)

```python
@router.get("/audit/session/{session_id}")
async def get_session_audit(
    session_id: str,
    user: User = Depends(get_current_user)
):
    events = db.query(AuditEvent)\
        .filter(AuditEvent.session_id == session_id)\
        .filter(AuditEvent.user_id == user.id)\
        .order_by(AuditEvent.timestamp)\
        .all()
    return {"events": [e.__dict__ for e in events]}
```

Replace the in-memory `auditEvents` array in the HTML with a fetch to this endpoint
every time a new action fires, then re-render the audit panel from the real response.

---

## Phase 5 — Rate Limiting and Abuse Protection

**Goal:** a customer (or an attacker) cannot hammer the MCP tools 10,000 times.

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Demo tier: 20 tool calls per session
# Basic tier: 100 tool calls per day
# Pro tier: 500 tool calls per day
# Enterprise: negotiated

@router.post("/tools/dispatch")
@limiter.limit("20/hour")
async def dispatch_endpoint(request: Request, ...):
    ...
```

Also add per-user tool call accounting in the audit table so you can enforce
daily limits by user tier, not just by IP.

---

## Build Order

Do these in sequence. Do not skip to Phase 3 without Phase 2 in place.

| Phase | What | Estimated effort |
|---|---|---|
| 1 | Auth layer (real login, JWT, session) | 1–2 days |
| 2 | Scope enforcer (tier → allowed tools) | half a day |
| 3A | MCP dispatcher — sandbox responses first | 1 day |
| 3B | MCP dispatcher — real tool wiring | depends on MCP transport, 1–3 days |
| 4 | Persistent audit log (SQLite + endpoint) | 1 day |
| 5 | Rate limiting + abuse protection | half a day |
| 6 | Wire HTML to real endpoints | 1 day |

**Total honest estimate: 6–10 focused days of engineering.**

Not a sprint. Not a quarter. A focused two weeks gets you from demo to real product.

---

## The One Decision That Blocks Phase 3

Before I can write the MCP dispatcher code, I need to know:

**How does your MCP server currently expose its tools — HTTP endpoints, or stdio?**

Everything else in this plan is already decided. That one question determines
which dispatcher code you actually run. Tell me that and Phase 3 becomes a
two-hour build, not a two-day one.

---

## Files This Plan Produces (when built)

```
bridge/
├── main.py                    ← FastAPI app, router registration
├── auth/
│   ├── models.py              ← User, Session tables
│   ├── router.py              ← /auth/login, /auth/logout, /auth/refresh
│   └── deps.py                ← get_current_user dependency
├── scope/
│   └── enforcer.py            ← TOOL_SCOPES, enforce_scope()
├── dispatch/
│   ├── mcp_client.py          ← HTTP or stdio transport
│   ├── sandbox.py             ← DEMO_RESPONSES
│   └── router.py              ← /tools/dispatch endpoint
├── audit/
│   ├── models.py              ← AuditEvent table
│   └── router.py              ← /audit/session/{id} endpoint
├── db.py                      ← SQLite engine + session factory
├── config.py                  ← env vars (MCP_SERVER_URL, JWT_SECRET, etc.)
└── requirements.txt
```

All of this lives alongside your existing FastAPI app — it is an additional
router group, not a new application. Include it in your existing `main.py`:

```python
from bridge.auth.router import router as auth_router
from bridge.dispatch.router import router as dispatch_router
from bridge.audit.router import router as audit_router

app.include_router(auth_router, prefix="/api")
app.include_router(dispatch_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
```

One command to start the whole thing. No new process.
