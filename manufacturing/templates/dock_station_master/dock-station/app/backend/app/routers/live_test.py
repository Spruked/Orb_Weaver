"""Live Test — real-time ORB testing environment"""
import uuid
import random
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from app.models import LiveTestSession, LiveTestControl, ProfileState
from app.services.profile_service import profile_service
from app.services.stage_governor import stage_governor
from app.core.security import decode_token

router = APIRouter(prefix="/live-test", tags=["Live Test"])

# In-memory session store (production: Redis)
_sessions: Dict[str, dict] = {}

class VisitorSpeechRequest(BaseModel):
    text: str

def get_current_owner(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

def _create_session(profile_id: str) -> dict:
    session = {
        "session_id": str(uuid.uuid4()),
        "profile_id": profile_id,
        "url": "http://localhost:3000",
        "route": "/",
        "status": "idle",
        "started_at": datetime.utcnow().isoformat(),
        "microphone_allowed": False,
        "speaker_active": False,
        "muted": False,
        "mobile_simulation": False,
        "current_stage": "preflight",
        "detected_intent": None,
        "confidence": 0.0,
        "latency_ms": 0,
        "active_lane": "universal",
        "pointer_target": None,
        "transcript": [],
        "allowed_actions": ["greet", "introduce", "site_world", "pointer_plot"],
        "tool_calls": [],
        "events": [{"event": "session_created", "at": datetime.utcnow().isoformat()}],
    }
    _sessions[session["session_id"]] = session
    return session

@router.post("/{profile_id}/start")
async def start_session(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Draft testing by default — use draft if available, never auto-publish
    session = _create_session(profile_id)
    session["status"] = "listening"
    session["microphone_allowed"] = True
    session["speaker_active"] = True
    session["active_lane"] = p.intelligence.active_lane

    # Seed initial greeting
    session["transcript"].append({
        "speaker": "weaver",
        "text": p.speech.greeting_text,
        "timestamp": datetime.utcnow().isoformat(),
        "stage": "preflight",
        "latency_ms": 340,
    })

    return session

@router.post("/{session_id}/control")
async def control_session(session_id: str, control: LiveTestControl, owner=Depends(get_current_owner)):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if control.action == "stop":
        session["status"] = "idle"
        session["speaker_active"] = False
        session["microphone_allowed"] = False
        session["events"].append({"event": "stopped", "at": datetime.utcnow().isoformat()})

    elif control.action == "mute":
        session["muted"] = True
        session["speaker_active"] = False

    elif control.action == "unmute":
        session["muted"] = False
        session["speaker_active"] = True

    elif control.action == "reset":
        profile_id = session["profile_id"]
        _sessions.pop(session_id, None)
        return _create_session(profile_id)

    elif control.action == "reload_site_world":
        session["events"].append({"event": "site_world_reloaded", "at": datetime.utcnow().isoformat()})
        session["current_stage"] = "crawl"
        session["allowed_actions"] = ["site_world", "page_capsule", "ask_question", "clarify"]

    elif control.action == "set_route":
        if control.route:
            session["route"] = control.route
            session["events"].append({"event": "route_changed", "route": control.route, "at": datetime.utcnow().isoformat()})

    return session

@router.post("/{session_id}/speak")
async def visitor_speak(session_id: str, req: VisitorSpeechRequest, owner=Depends(get_current_owner)):
    """Simulate visitor speech input — triggers full pipeline."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    profile = profile_service.get_profile(session["profile_id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Record visitor input
    session["transcript"].append({
        "speaker": "visitor",
        "text": req.text,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Simulate pipeline
    session["status"] = "thinking"
    session["latency_ms"] = random.randint(200, 1200)

    # Simulate intent detection
    intents = ["pricing_inquiry", "feature_question", "support_request", "general_chat"]
    session["detected_intent"] = random.choice(intents)
    session["confidence"] = round(random.uniform(0.6, 0.95), 2)

    # Stage progression
    stages = ["preflight", "crawl", "assessment", "presentation", "closure"]
    current_idx = stages.index(session["current_stage"]) if session["current_stage"] in stages else 0
    if current_idx < len(stages) - 1 and random.random() > 0.3:
        session["current_stage"] = stages[current_idx + 1]

    # Update allowed actions based on stage
    stage_tools = stage_governor.get_stage_tools(session["current_stage"], profile.tools)
    session["allowed_actions"] = [t["tool"].id for t in stage_tools if t["available"]]

    # Simulate tool call
    if random.random() > 0.5 and session["allowed_actions"]:
        tool_id = random.choice(session["allowed_actions"])
        session["tool_calls"].append({
            "tool": tool_id,
            "status": "requested",
            "requires_confirmation": True,
            "timestamp": datetime.utcnow().isoformat(),
        })

    # Simulate pointer target
    targets = [
        {"id": "hero-cta", "selector": "#hero .cta-button", "x": 120, "y": 340},
        {"id": "pricing-card", "selector": "#pricing .card", "x": 400, "y": 500},
        {"id": "nav-contact", "selector": "nav a[href='/contact']", "x": 600, "y": 60},
    ]
    session["pointer_target"] = random.choice(targets)

    # Weaver response
    responses = {
        "pricing_inquiry": "Our packages start at $49 for 5GB. Would you like me to walk you through the tiers?",
        "feature_question": "I can show you exactly how that works. Let me pull up the relevant section.",
        "support_request": "I'll connect you with support. First, let me gather a few details.",
        "general_chat": "I'm here to help. What would you like to explore?",
    }

    session["status"] = "speaking"
    session["transcript"].append({
        "speaker": "weaver",
        "text": responses.get(session["detected_intent"], "I understand. Let me help with that."),
        "timestamp": datetime.utcnow().isoformat(),
        "stage": session["current_stage"],
        "latency_ms": session["latency_ms"],
        "intent": session["detected_intent"],
        "confidence": session["confidence"],
    })

    session["events"].append({
        "event": "turn_complete",
        "latency_ms": session["latency_ms"],
        "stage": session["current_stage"],
        "at": datetime.utcnow().isoformat(),
    })

    # Return to listening
    session["status"] = "listening"

    return session

@router.get("/{session_id}")
async def get_session(session_id: str, owner=Depends(get_current_owner)):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.get("/{session_id}/stream")
async def stream_session(session_id: str, owner=Depends(get_current_owner)):
    """SSE-style polling endpoint for live updates."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session": session,
        "timestamp": datetime.utcnow().isoformat(),
    }
