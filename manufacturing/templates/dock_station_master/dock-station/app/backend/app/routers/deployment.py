"""Deployment panel"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List
from app.models import DeploymentTarget, OrbChannel, ProfileUpdate
from app.services.profile_service import profile_service
from app.core.security import decode_token

router = APIRouter(prefix="/deployment", tags=["Deployment"])

def get_current_owner(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

@router.get("/{profile_id}", response_model=List[DeploymentTarget])
async def get_deployment(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.deployment

@router.patch("/{profile_id}", response_model=List[DeploymentTarget])
async def update_deployment(profile_id: str, targets: List[DeploymentTarget], owner=Depends(get_current_owner)):
    p = profile_service.update_profile(profile_id, ProfileUpdate(deployment=targets))
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.deployment

@router.get("/channels")
async def list_channels(owner=Depends(get_current_owner)):
    return [
        {"channel": OrbChannel.WEB, "description": "Website ORB — full pointer, motion, and visual capability.", "available": True},
        {"channel": OrbChannel.TELEPHONE, "description": "Telephone ORB — voice-only, no pointer/spatial claims.", "available": False, "future": True},
        {"channel": OrbChannel.SIP, "description": "SIP trunk ORB — enterprise voice integration.", "available": False, "future": True},
    ]
