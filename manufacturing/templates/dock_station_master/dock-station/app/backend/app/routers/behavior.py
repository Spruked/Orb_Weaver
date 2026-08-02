"""Behavior & Personality panel"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List
from app.models import PersonalityBlend, StageDirective, ProfileUpdate
from app.services.profile_service import profile_service
from app.core.security import decode_token

router = APIRouter(prefix="/behavior", tags=["Behavior & Personality"])

def get_current_owner(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

@router.get("/{profile_id}/personality", response_model=PersonalityBlend)
async def get_personality(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.personality

@router.patch("/{profile_id}/personality", response_model=PersonalityBlend)
async def update_personality(profile_id: str, personality: PersonalityBlend, owner=Depends(get_current_owner)):
    p = profile_service.update_profile(profile_id, ProfileUpdate(personality=personality))
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.personality

@router.get("/{profile_id}/directives", response_model=List[StageDirective])
async def get_directives(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.stage_directives

@router.patch("/{profile_id}/directives", response_model=List[StageDirective])
async def update_directives(profile_id: str, directives: List[StageDirective], owner=Depends(get_current_owner)):
    p = profile_service.update_profile(profile_id, ProfileUpdate(stage_directives=directives))
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.stage_directives

@router.get("/{profile_id}/prohibited-patterns")
async def get_prohibited_patterns(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"patterns": p.prohibited_patterns}

@router.patch("/{profile_id}/prohibited-patterns")
async def update_prohibited_patterns(profile_id: str, patterns: List[str], owner=Depends(get_current_owner)):
    p = profile_service.update_profile(profile_id, ProfileUpdate(prohibited_patterns=patterns))
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"patterns": p.prohibited_patterns}
