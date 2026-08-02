"""Diagnostics panel"""
from typing import List
from fastapi import APIRouter, Depends, Header
from app.models import DiagnosticEntry, HealthStatus
from app.services.health_monitor import health_monitor
from app.core.security import decode_token

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])

def get_current_owner(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

@router.get("/health")
async def overall_health(owner=Depends(get_current_owner)):
    return health_monitor.get_overall_health()

@router.get("/pointer")
async def pointer_report(owner=Depends(get_current_owner)):
    return health_monitor.get_pointer_report()

@router.post("/pointer/recovery")
async def run_pointer_recovery(owner=Depends(get_current_owner)):
    return health_monitor.run_pointer_recovery()

@router.get("/gateway")
async def gateway_report(owner=Depends(get_current_owner)):
    return health_monitor.get_gateway_report()

@router.get("/issues", response_model=List[DiagnosticEntry])
async def list_issues(owner=Depends(get_current_owner)):
    issues = health_monitor.get_diagnostics()
    return [DiagnosticEntry(**i, detected_at=__import__('datetime').datetime.utcnow()) for i in issues]
