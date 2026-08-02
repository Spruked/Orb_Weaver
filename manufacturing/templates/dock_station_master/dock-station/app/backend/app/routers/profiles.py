"""Profile management — CRUD, publish, restore, diff"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Header
from app.models import (
    OrbProfile, ProfileCreate, ProfileUpdate, PublishRequest,
    ProfileVersion, ProfileState
)
from app.services.profile_service import profile_service
from app.core.security import decode_token

router = APIRouter(prefix="/profiles", tags=["Profiles"])

def get_current_owner(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

@router.get("", response_model=List[OrbProfile])
async def list_profiles(owner=Depends(get_current_owner)):
    return profile_service.list_profiles()

@router.post("", response_model=OrbProfile)
async def create_profile(req: ProfileCreate, owner=Depends(get_current_owner)):
    return profile_service.create_profile(req)

@router.get("/{profile_id}", response_model=OrbProfile)
async def get_profile(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p

@router.patch("/{profile_id}", response_model=OrbProfile)
async def update_profile(profile_id: str, req: ProfileUpdate, owner=Depends(get_current_owner)):
    p = profile_service.update_profile(profile_id, req)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p

@router.post("/{profile_id}/publish", response_model=OrbProfile)
async def publish_profile(profile_id: str, req: PublishRequest, owner=Depends(get_current_owner)):
    p = profile_service.publish_profile(profile_id, req.change_summary, owner.get("email", "owner"))
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p

@router.post("/{profile_id}/restore/{version}", response_model=OrbProfile)
async def restore_version(profile_id: str, version: int, owner=Depends(get_current_owner)):
    p = profile_service.restore_version(profile_id, version)
    if not p:
        raise HTTPException(status_code=404, detail="Version not found")
    return p

@router.get("/{profile_id}/versions", response_model=List[ProfileVersion])
async def get_versions(profile_id: str, owner=Depends(get_current_owner)):
    return profile_service.get_versions(profile_id)

@router.get("/{profile_id}/diff")
async def diff_profile(profile_id: str, owner=Depends(get_current_owner)):
    return profile_service.diff_profile(profile_id)
