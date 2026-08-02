"""Intelligence & Models panel — full model selector"""
import random
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Header
from app.models import IntelligenceConfig, ModelLane, ModelConfig, ProfileUpdate, ModelTestResult
from app.services.profile_service import profile_service
from app.services.health_monitor import health_monitor
from app.core.security import decode_token

router = APIRouter(prefix="/intelligence", tags=["Intelligence & Models"])

def get_current_owner(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

@router.get("/{profile_id}", response_model=IntelligenceConfig)
async def get_intelligence(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.intelligence

@router.patch("/{profile_id}", response_model=IntelligenceConfig)
async def update_intelligence(profile_id: str, config: IntelligenceConfig, owner=Depends(get_current_owner)):
    p = profile_service.update_profile(profile_id, ProfileUpdate(intelligence=config))
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.intelligence

@router.get("/{profile_id}/lanes")
async def get_lanes(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"lanes": p.intelligence.lanes, "active": p.intelligence.active_lane}

@router.patch("/{profile_id}/lanes/{lane_name}")
async def update_lane(profile_id: str, lane_name: str, config: ModelConfig, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    lanes = []
    for lane in p.intelligence.lanes:
        if lane.name == lane_name:
            lanes.append(lane.model_copy(update={"config": config}))
        else:
            lanes.append(lane)

    updated = p.intelligence.model_copy(update={"lanes": lanes})
    profile_service.update_profile(profile_id, ProfileUpdate(intelligence=updated))
    return {"lane": lane_name, "updated": True}

@router.post("/{profile_id}/lanes/{lane_name}/activate")
async def activate_lane(profile_id: str, lane_name: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    lane = next((l for l in p.intelligence.lanes if l.name == lane_name), None)
    if not lane:
        raise HTTPException(status_code=404, detail="Lane not found")

    updated = p.intelligence.model_copy(update={"active_lane": lane_name})
    profile_service.update_profile(profile_id, ProfileUpdate(intelligence=updated))
    return {"active_lane": lane_name, "provider": lane.config.provider, "model": lane.config.model_id}

@router.post("/{profile_id}/lanes/{lane_name}/test")
async def test_lane_connection(profile_id: str, lane_name: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    lane = next((l for l in p.intelligence.lanes if l.name == lane_name), None)
    if not lane:
        raise HTTPException(status_code=404, detail="Lane not found")

    # Simulated connection test
    ttf = random.randint(80, 450)
    total = ttf + random.randint(200, 800)

    return ModelTestResult(
        lane_name=lane_name,
        passed=lane.config.healthy,
        latency_ms=total,
        ttf_ms=ttf,
        sample_output="Connection established. Model responsive." if lane.config.healthy else "Connection failed.",
        error=None if lane.config.healthy else "Endpoint unreachable",
    )

@router.post("/{profile_id}/lanes/{lane_name}/test-response")
async def test_lane_response(profile_id: str, lane_name: str, prompt: str = "Say hello briefly.", owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    lane = next((l for l in p.intelligence.lanes if l.name == lane_name), None)
    if not lane:
        raise HTTPException(status_code=404, detail="Lane not found")

    ttf = random.randint(80, 450)
    total = ttf + random.randint(300, 1200)

    sample_outputs = {
        "llama.cpp": "Hello! I'm ready to assist you with your questions.",
        "Aphrodite": "Greetings. I am operational and awaiting your inquiry.",
        "Ollama": "Hey there! What can I help you with today?",
        "TensorRT-LLM": "Hello. System online. Awaiting input.",
        "predicate-logic": "PASS",
    }

    return ModelTestResult(
        lane_name=lane_name,
        passed=lane.config.healthy,
        latency_ms=total,
        ttf_ms=ttf,
        sample_output=sample_outputs.get(lane.config.provider, "Response received."),
        error=None if lane.config.healthy else "Endpoint unreachable",
    )

@router.post("/{profile_id}/restore-recommended")
async def restore_recommended(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Reset to seed configuration
    from app.services.profile_service import ProfileService
    seed = ProfileService()._create_seed_profile()
    updated = p.intelligence.model_copy(update={
        "lanes": seed.intelligence.lanes,
        "active_lane": "universal",
        "fallback_enabled": True,
        "deterministic_fallback": True,
    })
    profile_service.update_profile(profile_id, ProfileUpdate(intelligence=updated))
    return {"restored": True, "active_lane": "universal"}

@router.get("/health/gateway")
async def gateway_health(owner=Depends(get_current_owner)):
    return health_monitor.get_gateway_report()
