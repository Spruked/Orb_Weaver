"""Statistics panel"""
import json
import os
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Header
from app.models import StatisticsSnapshot
from app.core.config import settings
from app.core.security import decode_token

router = APIRouter(prefix="/statistics", tags=["Statistics"])

def get_current_owner(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

def _load_stats() -> List[dict]:
    path = settings.STATS_PATH
    if not os.path.exists(path):
        return _seed_stats()
    with open(path, "r") as f:
        return json.load(f)

def _seed_stats() -> List[dict]:
    now = datetime.utcnow()
    seeds = [
        {
            "profile_id": "seed",
            "period_start": (now - timedelta(days=7)).isoformat(),
            "period_end": now.isoformat(),
            "conversations_total": 142,
            "avg_time_to_first_word_ms": 420,
            "avg_speech_recognition_ms": 180,
            "avg_llm_response_ms": 850,
            "avg_tts_generation_ms": 290,
            "cache_hit_percent": 34.5,
            "interrupted_responses": 12,
            "failed_mic_permissions": 3,
            "pointer_success_rate": 0.91,
            "guided_journeys_completed": 38,
            "actions_requested": 89,
            "actions_approved": 67,
            "actions_verified": 61,
            "visitor_abandonment_stage": "assessment",
            "local_vs_api_cost_ratio": 1.0,
        },
        {
            "profile_id": "seed",
            "period_start": (now - timedelta(days=14)).isoformat(),
            "period_end": (now - timedelta(days=7)).isoformat(),
            "conversations_total": 98,
            "avg_time_to_first_word_ms": 510,
            "avg_speech_recognition_ms": 220,
            "avg_llm_response_ms": 920,
            "avg_tts_generation_ms": 310,
            "cache_hit_percent": 28.0,
            "interrupted_responses": 18,
            "failed_mic_permissions": 7,
            "pointer_success_rate": 0.85,
            "guided_journeys_completed": 22,
            "actions_requested": 54,
            "actions_approved": 41,
            "actions_verified": 38,
            "visitor_abandonment_stage": "presentation",
            "local_vs_api_cost_ratio": 1.0,
        },
    ]
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    with open(settings.STATS_PATH, "w") as f:
        json.dump(seeds, f, indent=2, default=str)
    return seeds

@router.get("", response_model=List[StatisticsSnapshot])
async def list_statistics(profile_id: str = None, owner=Depends(get_current_owner)):
    data = _load_stats()
    if profile_id:
        data = [d for d in data if d.get("profile_id") == profile_id]
    return [StatisticsSnapshot(**d) for d in data]

@router.get("/latest")
async def latest_statistics(profile_id: str = "seed", owner=Depends(get_current_owner)):
    data = _load_stats()
    filtered = [d for d in data if d.get("profile_id") == profile_id]
    if not filtered:
        return {}
    return StatisticsSnapshot(**filtered[-1])
