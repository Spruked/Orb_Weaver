from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
import httpx

from .config import POINTER_MAP_PATH, RUNTIME_LANGUAGE_PATH, SITE_WORLD_PATH, TOOL_CACHE_PATH
from .cognition.answer_engine import answer_from_world
from .cognition.tpc_runtime import tpc_runtime
from .dock_adapter.dockstation_adapter import DockStationAdapter
from .models import AnswerRequest, AnswerResponse, DockActionRequest, RouteContextResponse
from .pointer.pointer_index import route_pointer_targets
from .runtime.route_lookup import lookup_route
from .runtime.site_world import SiteWorld
from .voice_runtime import VOICE_CACHE, speak, transcribe


app = FastAPI(title="Website ORB Runtime", version="0.1.0")
WORLD = SiteWorld.load(SITE_WORLD_PATH, POINTER_MAP_PATH, RUNTIME_LANGUAGE_PATH, TOOL_CACHE_PATH)
DOCK = DockStationAdapter()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "world": WORLD.stats(), "dock": DOCK.status(), "cognition": tpc_runtime.status()}


@app.get("/orb/tpc-status")
def tpc_status() -> dict:
    return tpc_runtime.status()


@app.get("/orb/site-world")
def site_world() -> dict:
    return {
        "identity": WORLD.site_world.get("identity"),
        "stats": WORLD.stats(),
        "route_aliases": WORLD.route_aliases,
    }


@app.get("/orb/route-context", response_model=RouteContextResponse)
def route_context(route: str = "/") -> RouteContextResponse:
    matched_route, record = lookup_route(WORLD, route)
    return RouteContextResponse(route=route, matched_route=matched_route, record=record)


@app.get("/orb/pointer-map")
def pointer_map(route: str = "/", limit: int = 20) -> dict:
    matched_route, _record = lookup_route(WORLD, route)
    return {
        "route": route,
        "matched_route": matched_route,
        "records": route_pointer_targets(WORLD, matched_route, limit=limit),
    }


@app.post("/orb/answer-text", response_model=AnswerResponse)
def answer_text(payload: AnswerRequest) -> AnswerResponse:
    matched_route, route_record = lookup_route(WORLD, payload.route)
    targets = route_pointer_targets(WORLD, matched_route, payload.message, limit=5) if payload.want_pointer else []
    result = answer_from_world(payload.message, matched_route, route_record, WORLD.runtime_language, targets)
    return AnswerResponse(**result)


@app.post("/orb/website-voice")
async def website_voice(audio: UploadFile = File(...), route: str = "/") -> dict:
    content = await audio.read()
    if not content:
        raise HTTPException(status_code=400, detail="No audio was received")
    try:
        transcript = await transcribe(audio.filename or "website-orb.webm", audio.content_type or "application/octet-stream", content)
        answer = answer_text(AnswerRequest(message=transcript, route=route, want_pointer=True))
        tts = await speak(answer.answer)
        return {"transcript": transcript, "spoken_output": answer.answer, **answer.model_dump(), **tts}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Voice provider failed: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/orb/audio/{audio_id}")
def voice_audio(audio_id: str):
    candidate = (VOICE_CACHE / audio_id).resolve()
    if candidate.parent != VOICE_CACHE.resolve() or not candidate.is_file() or candidate.suffix != ".wav":
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(candidate, media_type="audio/wav", headers={"Cache-Control": "no-store"})


@app.post("/orb/dock/action")
def dock_action(payload: DockActionRequest) -> dict:
    return DOCK.call(payload.action, payload.arguments)
