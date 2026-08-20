from __future__ import annotations

from fastapi import FastAPI

from .config import POINTER_MAP_PATH, RUNTIME_LANGUAGE_PATH, SITE_WORLD_PATH, TOOL_CACHE_PATH
from .cognition.answer_engine import answer_from_world
from .cognition.tpc_runtime import tpc_runtime
from .dock_adapter.dockstation_adapter import DockStationAdapter
from .models import AnswerRequest, AnswerResponse, DockActionRequest, RouteContextResponse
from .pointer.pointer_index import route_pointer_targets
from .runtime.route_lookup import lookup_route
from .runtime.site_world import SiteWorld


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


@app.post("/orb/dock/action")
def dock_action(payload: DockActionRequest) -> dict:
    return DOCK.call(payload.action, payload.arguments)
