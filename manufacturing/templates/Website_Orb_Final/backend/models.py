from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    message: str = Field(..., min_length=1)
    route: str = "/"
    want_pointer: bool = True


class AnswerResponse(BaseModel):
    answer: str
    route: str
    intent: str
    action_class: str
    pointer_targets: List[Dict[str, Any]]
    requires_confirmation: bool
    source: str = "tpc_website_runtime"
    tpc_trace: Dict[str, Any] = Field(default_factory=dict)


class RouteContextResponse(BaseModel):
    route: str
    matched_route: str
    record: Dict[str, Any]
    source: str = "resident_skg_lookup"


class DockActionRequest(BaseModel):
    action: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    route: Optional[str] = None
