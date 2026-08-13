from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from .config import ProviderConfig
from .contracts import GenerationResult, ProviderHealth


class ProviderError(RuntimeError):
    pass


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
        return "\n".join(parts)
    if content is None:
        return ""
    return str(content)


class BaseProvider(ABC):
    def __init__(self, config: ProviderConfig, client: Optional[httpx.AsyncClient] = None) -> None:
        self.config = config
        self._external_client = client
        self._discovered_model: Optional[str] = None

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(
            timeout=httpx.Timeout(
                self.config.timeout_seconds,
                connect=min(2.0, self.config.timeout_seconds),
            )
        )

    async def _close_if_owned(self, client: httpx.AsyncClient) -> None:
        if self._external_client is None:
            await client.aclose()

    async def resolved_model(self) -> str:
        if self.config.model.lower() != "auto":
            return self.config.model
        if self._discovered_model:
            return self._discovered_model
        models = await self.list_models()
        if not models:
            raise ProviderError(f"{self.name} returned no models")
        self._discovered_model = models[0]
        return self._discovered_model

    @abstractmethod
    async def list_models(self) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> ProviderHealth:
        raise NotImplementedError

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        top_p: Optional[float] = None,
        stop: Any = None,
        seed: Optional[int] = None,
        request_model: Optional[str] = None,
    ) -> GenerationResult:
        raise NotImplementedError

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        top_p: Optional[float] = None,
        stop: Any = None,
        seed: Optional[int] = None,
        request_model: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        result = await self.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
            seed=seed,
            request_model=request_model,
        )
        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": result.model,
            "choices": [{"index": 0, "delta": {"content": result.text}, "finish_reason": None}],
            "orb_runtime": {"provider": result.provider, "latency_ms": result.latency_ms},
        }
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8")
        done = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": result.model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": result.finish_reason}],
        }
        yield f"data: {json.dumps(done)}\n\n".encode("utf-8")
        yield b"data: [DONE]\n\n"


class OpenAICompatibleProvider(BaseProvider):
    async def list_models(self) -> List[str]:
        if not self.enabled:
            return []
        client = self._client()
        try:
            response = await client.get(f"{self.config.base_url}/models", headers=self._headers())
            response.raise_for_status()
            payload = response.json()
            items = payload.get("data", []) if isinstance(payload, dict) else []
            return [str(item.get("id")) for item in items if isinstance(item, dict) and item.get("id")]
        except Exception as exc:
            raise ProviderError(f"{self.name} model discovery failed: {exc}") from exc
        finally:
            await self._close_if_owned(client)

    async def health(self) -> ProviderHealth:
        started = time.perf_counter()
        checked_at = time.time()
        if not self.enabled:
            return ProviderHealth(
                name=self.name,
                enabled=False,
                ready=False,
                model=self.config.model,
                base_url=self.config.base_url,
                checked_at=checked_at,
                error="provider disabled",
            )
        try:
            model = await self.resolved_model()
            return ProviderHealth(
                name=self.name,
                enabled=True,
                ready=True,
                model=model,
                base_url=self.config.base_url,
                checked_at=checked_at,
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
        except Exception as exc:
            return ProviderHealth(
                name=self.name,
                enabled=True,
                ready=False,
                model=self.config.model,
                base_url=self.config.base_url,
                checked_at=checked_at,
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                error=str(exc)[:300],
            )

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        top_p: Optional[float] = None,
        stop: Any = None,
        seed: Optional[int] = None,
        request_model: Optional[str] = None,
    ) -> GenerationResult:
        model = request_model or await self.resolved_model()
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if top_p is not None:
            payload["top_p"] = top_p
        if stop is not None:
            payload["stop"] = stop
        if seed is not None:
            payload["seed"] = seed

        client = self._client()
        started = time.perf_counter()
        try:
            response = await client.post(
                f"{self.config.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            raw = response.json()
            choices = raw.get("choices") or []
            if not choices:
                raise ProviderError(f"{self.name} returned no choices")
            first = choices[0]
            message = first.get("message") or {}
            usage = raw.get("usage") or {}
            return GenerationResult(
                text=_content_to_text(message.get("content")).strip(),
                provider=self.name,
                model=str(raw.get("model") or model),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                raw=raw,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                finish_reason=str(first.get("finish_reason") or "stop"),
            )
        except Exception as exc:
            if isinstance(exc, ProviderError):
                raise
            raise ProviderError(f"{self.name} completion failed: {exc}") from exc
        finally:
            await self._close_if_owned(client)

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        top_p: Optional[float] = None,
        stop: Any = None,
        seed: Optional[int] = None,
        request_model: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        model = request_model or await self.resolved_model()
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if top_p is not None:
            payload["top_p"] = top_p
        if stop is not None:
            payload["stop"] = stop
        if seed is not None:
            payload["seed"] = seed

        client = self._client()
        try:
            async with client.stream(
                "POST",
                f"{self.config.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk
        except Exception as exc:
            raise ProviderError(f"{self.name} stream failed: {exc}") from exc
        finally:
            await self._close_if_owned(client)


class OllamaProvider(BaseProvider):
    async def list_models(self) -> List[str]:
        if not self.enabled:
            return []
        client = self._client()
        try:
            response = await client.get(f"{self.config.base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
            return [
                str(item.get("name"))
                for item in payload.get("models", [])
                if isinstance(item, dict) and item.get("name")
            ]
        except Exception as exc:
            raise ProviderError(f"ollama model discovery failed: {exc}") from exc
        finally:
            await self._close_if_owned(client)

    async def health(self) -> ProviderHealth:
        started = time.perf_counter()
        checked_at = time.time()
        if not self.enabled:
            return ProviderHealth(
                name=self.name,
                enabled=False,
                ready=False,
                model=self.config.model,
                base_url=self.config.base_url,
                checked_at=checked_at,
                error="provider disabled",
            )
        try:
            models = await self.list_models()
            model = self.config.model if self.config.model != "auto" else (models[0] if models else "")
            ready = bool(model and models and (model in models or any(m.startswith(model + ":") for m in models)))
            return ProviderHealth(
                name=self.name,
                enabled=True,
                ready=ready,
                model=model,
                base_url=self.config.base_url,
                checked_at=checked_at,
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                error=None if ready else "configured model not present",
            )
        except Exception as exc:
            return ProviderHealth(
                name=self.name,
                enabled=True,
                ready=False,
                model=self.config.model,
                base_url=self.config.base_url,
                checked_at=checked_at,
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                error=str(exc)[:300],
            )

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        top_p: Optional[float] = None,
        stop: Any = None,
        seed: Optional[int] = None,
        request_model: Optional[str] = None,
    ) -> GenerationResult:
        model = request_model or self.config.model
        system_parts: List[str] = []
        prompt_parts: List[str] = []
        for message in messages:
            role = str(message.get("role") or "user")
            text = _content_to_text(message.get("content"))
            if role == "system":
                system_parts.append(text)
            else:
                prompt_parts.append(f"{role.title()}: {text}")
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": "\n".join(prompt_parts),
            "system": "\n".join(system_parts) or None,
            "stream": False,
            "keep_alive": "30m",
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if top_p is not None:
            payload["options"]["top_p"] = top_p
        if stop is not None:
            payload["options"]["stop"] = stop
        if seed is not None:
            payload["options"]["seed"] = seed

        client = self._client()
        started = time.perf_counter()
        try:
            response = await client.post(f"{self.config.base_url}/api/generate", json=payload)
            response.raise_for_status()
            raw = response.json()
            return GenerationResult(
                text=str(raw.get("response") or "").strip(),
                provider=self.name,
                model=str(raw.get("model") or model),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                raw=raw,
                prompt_tokens=raw.get("prompt_eval_count"),
                completion_tokens=raw.get("eval_count"),
                finish_reason=str(raw.get("done_reason") or "stop"),
            )
        except Exception as exc:
            raise ProviderError(f"ollama completion failed: {exc}") from exc
        finally:
            await self._close_if_owned(client)
