"""Conversations panel — read-only view over event log"""
import json
import os
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Header
from app.models import ConversationSession
from app.core.config import settings
from app.core.security import decode_token

router = APIRouter(prefix="/conversations", tags=["Conversations"])

def get_current_owner(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

def _load_conversations() -> List[dict]:
    path = settings.CONVERSATIONS_PATH
    if not os.path.exists(path):
        return _seed_conversations()
    with open(path, "r") as f:
        return json.load(f)

def _seed_conversations() -> List[dict]:
    from datetime import datetime, timedelta
    seeds = [
        {
            "session_id": "sess-001",
            "profile_id": "seed",
            "started_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "ended_at": (datetime.utcnow() - timedelta(hours=1, minutes=45)).isoformat(),
            "transcript": [
                {"speaker": "weaver", "text": "Hello. I'm Weaver. How can I help you today?", "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat()},
                {"speaker": "visitor", "text": "I'm looking for pricing information.", "timestamp": (datetime.utcnow() - timedelta(hours=1, minutes=59)).isoformat()},
                {"speaker": "weaver", "text": "I'll pull that up for you. Our packages start at $49 for 5GB.", "timestamp": (datetime.utcnow() - timedelta(hours=1, minutes=58)).isoformat()},
            ],
            "outcome": "package_presented",
            "stage_transitions": ["preflight", "crawl", "assessment", "presentation"],
            "actions_requested": 2,
            "actions_approved": 1,
            "actions_verified": 1,
        },
        {
            "session_id": "sess-002",
            "profile_id": "seed",
            "started_at": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
            "ended_at": (datetime.utcnow() - timedelta(hours=4, minutes=50)).isoformat(),
            "transcript": [
                {"speaker": "weaver", "text": "Hello. I'm Weaver. How can I help you today?", "timestamp": (datetime.utcnow() - timedelta(hours=5)).isoformat()},
                {"speaker": "visitor", "text": "What is this?", "timestamp": (datetime.utcnow() - timedelta(hours=4, minutes=59)).isoformat()},
                {"speaker": "weaver", "text": "This is the ORB platform — we help you organize knowledge into sellable assets.", "timestamp": (datetime.utcnow() - timedelta(hours=4, minutes=58)).isoformat()},
                {"speaker": "visitor", "text": "Not interested.", "timestamp": (datetime.utcnow() - timedelta(hours=4, minutes=55)).isoformat()},
            ],
            "outcome": "abandoned",
            "stage_transitions": ["preflight", "crawl"],
            "actions_requested": 0,
            "actions_approved": 0,
            "actions_verified": 0,
        },
    ]
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    with open(settings.CONVERSATIONS_PATH, "w") as f:
        json.dump(seeds, f, indent=2, default=str)
    return seeds

@router.get("", response_model=List[ConversationSession])
async def list_conversations(profile_id: str = None, owner=Depends(get_current_owner)):
    data = _load_conversations()
    if profile_id:
        data = [d for d in data if d.get("profile_id") == profile_id]
    return [ConversationSession(**d) for d in data]

@router.get("/{session_id}", response_model=ConversationSession)
async def get_conversation(session_id: str, owner=Depends(get_current_owner)):
    data = _load_conversations()
    sess = next((d for d in data if d["session_id"] == session_id), None)
    if not sess:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationSession(**sess)
