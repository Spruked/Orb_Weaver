"""ORB Dock Station — FastAPI backend v2.1"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.security import authenticate_owner, create_access_token
from app.models import OwnerLogin, TokenResponse

from app.routers import profiles, speech, behavior, intelligence, tools, appearance, deployment, conversations, statistics, diagnostics, try_it_live, live_test

@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version="2.1.0",
    description="Owner-facing configuration surface for ORB profiles. Draft → Publish lifecycle with Stage Governor enforcement, Live Test environment, Skin Editor, and Model Selector.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/auth/login", response_model=TokenResponse)
async def login(req: OwnerLogin):
    user = authenticate_owner(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user["email"], "role": user["role"], "name": user["name"]})
    return TokenResponse(access_token=token, owner=user)

@app.get("/auth/me")
async def me():
    return {"message": "Use Bearer token in Authorization header"}

app.include_router(profiles.router)
app.include_router(speech.router)
app.include_router(behavior.router)
app.include_router(intelligence.router)
app.include_router(tools.router)
app.include_router(appearance.router)
app.include_router(deployment.router)
app.include_router(conversations.router)
app.include_router(statistics.router)
app.include_router(diagnostics.router)
app.include_router(try_it_live.router)
app.include_router(live_test.router)

@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": "2.1.0"}

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "2.1.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/auth/login",
            "profiles": "/profiles",
            "speech": "/speech/{profile_id}",
            "behavior": "/behavior/{profile_id}",
            "intelligence": "/intelligence/{profile_id}",
            "tools": "/tools/{profile_id}",
            "appearance": "/appearance/{profile_id}",
            "live_test": "/live-test/{profile_id}/start",
            "deployment": "/deployment/{profile_id}",
            "conversations": "/conversations",
            "statistics": "/statistics",
            "diagnostics": "/diagnostics",
            "try_it_live": "/try-it-live/{profile_id}",
        }
    }
