"""Speech & Listening panel"""
from fastapi import APIRouter, HTTPException, Depends, Header
from app.models import SpeechSettings, TryItLiveResult
from app.services.profile_service import profile_service
from app.core.security import decode_token

router = APIRouter(prefix="/speech", tags=["Speech & Listening"])

def get_current_owner(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

@router.get("/{profile_id}", response_model=SpeechSettings)
async def get_speech(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.speech

@router.patch("/{profile_id}", response_model=SpeechSettings)
async def update_speech(profile_id: str, settings: SpeechSettings, owner=Depends(get_current_owner)):
    from app.models import ProfileUpdate
    p = profile_service.update_profile(profile_id, ProfileUpdate(speech=settings))
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.speech

@router.post("/{profile_id}/test-greeting", response_model=TryItLiveResult)
async def test_greeting(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Simulated test
    return TryItLiveResult(
        test_type="greeting",
        passed=True,
        notes=f"Greeting delivered: '{p.speech.greeting_text[:50]}...'",
        latency_ms=340,
        tone_flags=[],
    )

@router.post("/{profile_id}/test-tone", response_model=TryItLiveResult)
async def test_tone(profile_id: str, owner=Depends(get_current_owner)):
    p = profile_service.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Simulated tone check
    flags = []
    if p.personality.conviction > 0.9:
        flags.append("potentially_overbearing")
    if p.personality.warmth < 0.3:
        flags.append("sounds_flat")

    return TryItLiveResult(
        test_type="tone_check",
        passed=len(flags) == 0,
        notes="Tone analysis complete." if not flags else f"Flags: {', '.join(flags)}",
        tone_flags=flags,
    )
