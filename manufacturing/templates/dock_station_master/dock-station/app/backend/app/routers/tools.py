"""Tools & Permissions panel"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List
from app.models import ToolEntry, ProfileUpdate
from app.services.profile_service import profile_service
from app.services.stage_governor import stage_governor
from app.core.security import decode_token

router = APIRouter(prefix="/tools", tags=["Tools & Permissions"])

def get_current_owner(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

@router.get("/{profile_id}", response_model=List[ToolEntry])
async def get_tools(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.tools

@router.patch("/{profile_id}", response_model=List[ToolEntry])
async def update_tools(profile_id: str, tools: List[ToolEntry], owner=Depends(get_current_owner)):
    p = profile_service.update_profile(profile_id, ProfileUpdate(tools=tools))
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.tools

@router.get("/{profile_id}/stage/{stage}")
async def get_stage_tools(profile_id: str, stage: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return stage_governor.get_stage_tools(stage, p.tools)
