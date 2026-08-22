from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from .config import GatewayConfig
from .contracts import GenerationResult, ProviderHealth
from .providers import BaseProvider, OllamaProvider, OpenAICompatibleProvider, ProviderError
from .telemetry import VaultTelemetry


LANE_PRIORITY: Dict[str, Tuple[str, ...]] = {
    "universal": ("llamacpp", "aphrodite", "tensorrt", "ollama"),
    "scale": ("aphrodite", "tensorrt", "llamacpp", "ollama"),
    "accelerated": ("tensorrt", "llamacpp", "aphrodite", "ollama"),
    "fallback": ("ollama", "llamacpp", "aphrodite", "tensorrt"),
}


class InferenceGateway:
    def __init__(
        self,
        config: GatewayConfig,
        providers: Dict[str, BaseProvider],
        telemetry: Optional[VaultTelemetry] = None,
    ) -> None:
        self.config = config
        self.providers = providers
        self.telemetry = telemetry or VaultTelemetry(config.telemetry_path)
        self._health_cache: Dict[str, ProviderHealth] = {}
        self._health_locks: Dict[str, asyncio.Lock] = {name: asyncio.Lock() for name in providers}
        self._active_lock = asyncio.Lock()
        self._active_requests = 0
        self._totals: Dict[str, Dict[str, int]] = {
            name: {"success": 0, "failure": 0} for name in providers
        }

    @property
    def active_requests(self) -> int:
        return self._active_requests

    def _normalize_lane(self, requested: Optional[str]) -> str:
        lane = (requested or self.config.default_lane or "universal").strip().lower()
        if lane == "auto":
            return "scale" if self._active_requests >= self.config.scale_threshold else "universal"
        return lane if lane in LANE_PRIORITY else "universal"

    def provider_order(self, lane: Optional[str]) -> List[str]:
        normalized = self._normalize_lane(lane)
        preferred = list(LANE_PRIORITY[normalized])
        configured = list(self.config.provider_order)
        ordered: List[str] = []
        for name in preferred + configured:
            if name in self.providers and name not in ordered:
                ordered.append(name)
        return ordered

    @asynccontextmanager
    async def _request_slot(self):
        async with self._active_lock:
            self._active_requests += 1
            active = self._active_requests
        try:
            yield active
        finally:
            async with self._active_lock:
                self._active_requests = max(0, self._active_requests - 1)

    async def provider_health(self, name: str, force: bool = False) -> ProviderHealth:
        provider = self.providers[name]
        cached = self._health_cache.get(name)
        if (
            not force
            and cached is not None
            and time.time() - cached.checked_at <= self.config.health_ttl_seconds
        ):
            return cached
        async with self._health_locks[name]:
            cached = self._health_cache.get(name)
            if (
                not force
                and cached is not None
                and time.time() - cached.checked_at <= self.config.health_ttl_seconds
            ):
                return cached
            health = await provider.health()
            self._health_cache[name] = health
            return health

    async def status(self, force: bool = False) -> Dict[str, Any]:
        health_items = await asyncio.gather(
            *(self.provider_health(name, force=force) for name in self.providers),
            return_exceptions=True,
        )
        providers: Dict[str, Dict[str, Any]] = {}
        ready = False
        for name, item in zip(self.providers, health_items):
            if isinstance(item, Exception):
                providers[name] = {
                    "name": name,
                    "enabled": self.providers[name].enabled,
                    "ready": False,
                    "error": str(item)[:300],
                }
                continue
            providers[name] = asdict(item)
            ready = ready or item.ready
        return {
            "ready": ready,
            "default_lane": self.config.default_lane,
            "active_requests": self._active_requests,
            "scale_threshold": self.config.scale_threshold,
            "provider_order": list(self.config.provider_order),
            "providers": providers,
            "totals": self._totals,
        }

    def _validate_messages(self, messages: List[Dict[str, Any]]) -> None:
        char_count = 0
        for message in messages:
            content = message.get("content")
            char_count += len(content) if isinstance(content, str) else len(str(content))
        if char_count > self.config.max_prompt_chars:
            raise ValueError(
                f"prompt exceeds ORB_INFERENCE_MAX_PROMPT_CHARS ({self.config.max_prompt_chars})"
            )

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        *,
        lane: Optional[str],
        temperature: float,
        max_tokens: int,
        top_p: Optional[float] = None,
        stop: Any = None,
        seed: Optional[int] = None,
        request_model: Optional[str] = None,
    ) -> GenerationResult:
        self._validate_messages(messages)
        normalized_lane = self._normalize_lane(lane)
        errors: List[str] = []
        ordered_names = [
            name for name in self.provider_order(normalized_lane) if self.providers[name].enabled
        ]
        health_results = await asyncio.gather(
            *(self.provider_health(name) for name in ordered_names),
            return_exceptions=True,
        )
        ready_names = [
            name
            for name, health in zip(ordered_names, health_results)
            if isinstance(health, ProviderHealth) and health.ready
        ]

        async with self._request_slot() as active:
            for name in ready_names:
                provider = self.providers[name]
                model_override = request_model if self.config.allow_model_override else None
                started = time.perf_counter()
                try:
                    result = await provider.complete(
                        messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        stop=stop,
                        seed=seed,
                        request_model=model_override,
                    )
                    self._totals[name]["success"] += 1
                    await self.telemetry.record(
                        {
                            "event": "inference_completed",
                            "request_id": uuid.uuid4().hex,
                            "lane": normalized_lane,
                            "provider": result.provider,
                            "model": result.model,
                            "latency_ms": result.latency_ms,
                            "active_requests": active,
                            "prompt_characters": sum(len(str(m.get("content", ""))) for m in messages),
                            "output_characters": len(result.text),
                            "prompt_tokens": result.prompt_tokens,
                            "completion_tokens": result.completion_tokens,
                        }
                    )
                    return result
                except Exception as exc:
                    self._totals[name]["failure"] += 1
                    errors.append(f"{name}: {str(exc)[:240]}")
                    await self.telemetry.record(
                        {
                            "event": "inference_provider_failed",
                            "lane": normalized_lane,
                            "provider": name,
                            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                            "active_requests": active,
                            "error": str(exc)[:500],
                        }
                    )

        if not ready_names:
            for name, health in zip(ordered_names, health_results):
                if isinstance(health, Exception):
                    errors.append(f"{name}: {str(health)[:160]}")
                elif not health.ready:
                    errors.append(f"{name}: {health.error or 'not ready'}")
        raise ProviderError("all configured inference providers failed: " + " | ".join(errors))

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        lane: Optional[str],
        temperature: float,
        max_tokens: int,
        top_p: Optional[float] = None,
        stop: Any = None,
        seed: Optional[int] = None,
        request_model: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        self._validate_messages(messages)
        normalized_lane = self._normalize_lane(lane)
        selected: Optional[BaseProvider] = None
        for name in self.provider_order(normalized_lane):
            provider = self.providers[name]
            if not provider.enabled:
                continue
            health = await self.provider_health(name)
            if health.ready:
                selected = provider
                break
        if selected is None:
            raise ProviderError("no healthy provider is available for streaming")

        model_override = request_model if self.config.allow_model_override else None
        async with self._request_slot() as active:
            started = time.perf_counter()
            try:
                async for chunk in selected.stream_chat(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    stop=stop,
                    seed=seed,
                    request_model=model_override,
                ):
                    yield chunk
                self._totals[selected.name]["success"] += 1
                await self.telemetry.record(
                    {
                        "event": "inference_stream_completed",
                        "lane": normalized_lane,
                        "provider": selected.name,
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                        "active_requests": active,
                    }
                )
            except Exception as exc:
                self._totals[selected.name]["failure"] += 1
                await self.telemetry.record(
                    {
                        "event": "inference_stream_failed",
                        "lane": normalized_lane,
                        "provider": selected.name,
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                        "active_requests": active,
                        "error": str(exc)[:500],
                    }
                )
                raise


def build_gateway(config: GatewayConfig) -> InferenceGateway:
    providers: Dict[str, BaseProvider] = {}
    for name, provider_config in config.providers.items():
        if provider_config.kind == "ollama":
            providers[name] = OllamaProvider(provider_config)
        else:
            providers[name] = OpenAICompatibleProvider(provider_config)
    return InferenceGateway(config=config, providers=providers)
