from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant|tool)$")
    content: Any
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str = "orb-auto"
    messages: List[ChatMessage]
    temperature: float = Field(default=0.35, ge=0.0, le=2.0)
    max_tokens: int = Field(default=128, ge=1, le=4096)
    stream: bool = False
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    stop: Optional[Any] = None
    seed: Optional[int] = None
    orb_route: Optional[str] = None


class OllamaGenerateRequest(BaseModel):
    model: str = "orb-auto"
    prompt: str = Field(default="", max_length=50000)
    system: Optional[str] = Field(default=None, max_length=20000)
    stream: bool = False
    keep_alive: Optional[Any] = None
    options: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class GenerationResult:
    text: str
    provider: str
    model: str
    latency_ms: float
    raw: Dict[str, Any] = field(default_factory=dict)
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    finish_reason: str = "stop"


@dataclass
class ProviderHealth:
    name: str
    enabled: bool
    ready: bool
    model: str
    base_url: str
    checked_at: float
    latency_ms: Optional[float] = None
    error: Optional[str] = None
