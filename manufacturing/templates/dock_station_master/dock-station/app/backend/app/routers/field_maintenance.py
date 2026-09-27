"""Owner-authenticated proxy to the installed Website ORB maintenance lane."""

from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import decode_token


router = APIRouter(prefix="/field-maintenance", tags=["Field Site World Maintenance"])


def get_current_owner(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    payload = decode_token(authorization.split(" ", 1)[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


class MaintenanceRequest(BaseModel):
    observations: list[Dict[str, Any]] = Field(..., min_length=1, max_length=500)


class ReverificationRequest(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=240)
    targets: list[Dict[str, Any]] = Field(default_factory=list, max_length=200)


async def _orb_request(method: str, path: str, payload: Dict[str, Any] | None = None) -> Any:
    url = settings.WEBSITE_ORB_URL.rstrip("/") + path
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.request(method, url, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Installed Website ORB unavailable: {exc}") from exc
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


@router.get("/status")
async def status(owner=Depends(get_current_owner)):
    return await _orb_request("GET", "/orb/maintenance/status")


@router.post("/product-delta-scan")
async def product_delta_scan(request: MaintenanceRequest, owner=Depends(get_current_owner)):
    return await _orb_request("POST", "/orb/maintenance/product-delta-scan", request.model_dump())


@router.post("/affected-target-reverification")
async def affected_target_reverification(request: ReverificationRequest, owner=Depends(get_current_owner)):
    return await _orb_request("POST", "/orb/maintenance/affected-target-reverification", request.model_dump())


@router.post("/cycle")
async def cycle(request: MaintenanceRequest, owner=Depends(get_current_owner)):
    return await _orb_request("POST", "/orb/maintenance/cycle", request.model_dump())
