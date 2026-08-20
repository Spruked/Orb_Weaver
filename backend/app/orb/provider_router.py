from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx


def _join_url(base: str, suffix: str) -> str:
    clean = (base or "").strip().rstrip("/")
    return clean if clean.endswith(suffix) else f"{clean}{suffix}"


def _credential(configuration: Dict[str, Any]) -> Optional[str]:
    variable = str(configuration.get("api_key_env") or "").strip()
    return os.environ.get(variable) if variable else None


def _extract_openai(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if choices:
        return str((choices[0].get("message") or {}).get("content") or choices[0].get("text") or "").strip()
    return str(payload.get("output_text") or "").strip()


def _extract_anthropic(payload: Dict[str, Any]) -> str:
    return "\n".join(
        str(block.get("text") or "")
        for block in payload.get("content") or []
        if block.get("type") == "text"
    ).strip()


def _extract_google(payload: Dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    return "\n".join(
        str(part.get("text") or "")
        for part in (candidates[0].get("content") or {}).get("parts") or []
    ).strip()


async def invoke_provider(
    configuration: Dict[str, Any],
    *,
    prompt: str,
    system_instruction: str,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    provider = str(configuration.get("provider") or "runtime_default")
    model = str(configuration.get("model") or "").strip()
    timeout = min(120.0, max(5.0, float(configuration.get("timeout_seconds") or 45.0)))
    result: Dict[str, Any] = {"success": False, "provider": provider, "model": model, "text": None, "error": None}
    if provider == "runtime_default":
        return {**result, "error": "provider_not_requested"}
    if not model:
        return {**result, "error": "provider_model_missing"}

    api_key = _credential(configuration)
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=timeout)
    try:
        if provider == "anthropic_api":
            if not api_key:
                return {**result, "error": "provider_credential_missing"}
            base = str(configuration.get("base_url") or "https://api.anthropic.com/v1")
            response = await http.post(
                _join_url(base, "/messages"),
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                json={"model": model, "system": system_instruction, "max_tokens": 220, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            text = _extract_anthropic(response.json())
        elif provider == "google_api":
            if not api_key:
                return {**result, "error": "provider_credential_missing"}
            base = str(configuration.get("base_url") or "https://generativelanguage.googleapis.com/v1beta")
            response = await http.post(
                f"{_join_url(base, f'/models/{model}:generateContent')}?key={api_key}",
                json={
                    "systemInstruction": {"parts": [{"text": system_instruction}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.35, "maxOutputTokens": 220},
                },
            )
            response.raise_for_status()
            text = _extract_google(response.json())
        else:
            if provider == "openai_api":
                base = str(configuration.get("base_url") or "https://api.openai.com/v1")
                if not api_key:
                    return {**result, "error": "provider_credential_missing"}
            elif provider in {"openai_compatible", "local_openai_compatible"}:
                base = str(configuration.get("base_url") or "").strip()
                if not base:
                    return {**result, "error": "provider_endpoint_missing"}
            else:
                return {**result, "error": "provider_unsupported"}
            response = await http.post(
                _join_url(base, "/chat/completions"),
                headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
                json={
                    "model": model,
                    "messages": [{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}],
                    "temperature": 0.35,
                    "max_tokens": 220,
                    "stream": False,
                },
            )
            response.raise_for_status()
            text = _extract_openai(response.json())
        if not text:
            return {**result, "error": "provider_empty_response"}
        return {**result, "success": True, "text": text}
    except httpx.HTTPStatusError as exc:
        return {**result, "error": f"provider_request_failed:http_{exc.response.status_code}"}
    except httpx.HTTPError as exc:
        return {**result, "error": f"provider_request_failed:{exc.__class__.__name__}"}
    except ValueError:
        return {**result, "error": "provider_request_failed:invalid_response"}
    finally:
        if owns_client:
            await http.aclose()
