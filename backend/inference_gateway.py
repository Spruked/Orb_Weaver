from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.inference_gateway import GatewayConfig, build_gateway
from app.inference_gateway.contracts import ChatCompletionRequest, OllamaGenerateRequest
from app.inference_gateway.providers import ProviderError


config = GatewayConfig.from_env()
gateway = build_gateway(config)

app = FastAPI(
    title="ORB Inference Gateway",
    description=(
        "One stable ORB inference boundary routing universal llama.cpp, "
        "Aphrodite scale, TensorRT-LLM acceleration, and Ollama fallback lanes."
    ),
    version="1.0.0",
)


@app.on_event("startup")
async def warm_provider_registry() -> None:
    # Prime provider discovery without delaying Orb Weaver's backend startup.
    asyncio.create_task(gateway.status(force=True))


def require_gateway_key(
    authorization: Optional[str] = Header(default=None),
    x_orb_inference_key: Optional[str] = Header(default=None),
) -> None:
    if not config.api_key:
        return
    bearer = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization[7:].strip()
    if bearer != config.api_key and x_orb_inference_key != config.api_key:
        raise HTTPException(status_code=401, detail="invalid ORB inference key")


def _messages_from_generate(request: OllamaGenerateRequest) -> list[Dict[str, Any]]:
    messages: list[Dict[str, Any]] = []
    if request.system:
        messages.append({"role": "system", "content": request.system})
    messages.append({"role": "user", "content": request.prompt})
    return messages


@app.get("/health/live")
async def live() -> Dict[str, Any]:
    return {"status": "live", "service": "orb-inference-gateway"}


@app.get("/health/ready")
async def ready(_: None = Depends(require_gateway_key)) -> JSONResponse:
    status = await gateway.status(force=True)
    return JSONResponse(status_code=200 if status["ready"] else 503, content=status)


@app.get("/api/providers")
async def providers(_: None = Depends(require_gateway_key)) -> Dict[str, Any]:
    return await gateway.status(force=True)


@app.get("/v1/models")
async def models(_: None = Depends(require_gateway_key)) -> Dict[str, Any]:
    status = await gateway.status(force=False)
    data = []
    for name, provider in status["providers"].items():
        if provider.get("ready"):
            data.append(
                {
                    "id": provider.get("model") or name,
                    "object": "model",
                    "owned_by": f"orb-weaver/{name}",
                    "orb_provider": name,
                }
            )
    return {"object": "list", "data": data}


@app.post("/api/generate")
async def ollama_generate(
    payload: OllamaGenerateRequest,
    x_orb_lane: Optional[str] = Header(default=None),
    _: None = Depends(require_gateway_key),
) -> Dict[str, Any]:
    if payload.stream:
        raise HTTPException(
            status_code=400,
            detail="Ollama compatibility is non-streaming; use /v1/chat/completions for streaming",
        )
    options = payload.options or {}
    try:
        result = await gateway.generate(
            _messages_from_generate(payload),
            lane=x_orb_lane,
            temperature=float(options.get("temperature", 0.35)),
            max_tokens=int(options.get("num_predict", 128)),
            top_p=options.get("top_p"),
            stop=options.get("stop"),
            seed=options.get("seed"),
            request_model=payload.model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    prompt_tokens = result.prompt_tokens or 0
    completion_tokens = result.completion_tokens or 0
    return {
        "model": result.model,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "response": result.text,
        "done": True,
        "done_reason": result.finish_reason,
        "context": [],
        "total_duration": int(result.latency_ms * 1_000_000),
        "load_duration": 0,
        "prompt_eval_count": prompt_tokens,
        "eval_count": completion_tokens,
        "orb_runtime": {
            "provider": result.provider,
            "lane": x_orb_lane or config.default_lane,
            "latency_ms": result.latency_ms,
        },
    }


@app.post("/v1/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    request: Request,
    x_orb_lane: Optional[str] = Header(default=None),
    _: None = Depends(require_gateway_key),
):
    lane = payload.orb_route or x_orb_lane
    messages = [message.model_dump(exclude_none=True) for message in payload.messages]
    if payload.stream:
        stream = gateway.stream_chat(
            messages,
            lane=lane,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            top_p=payload.top_p,
            stop=payload.stop,
            seed=payload.seed,
            request_model=payload.model,
        )
        return StreamingResponse(stream, media_type="text/event-stream")

    try:
        result = await gateway.generate(
            messages,
            lane=lane,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            top_p=payload.top_p,
            stop=payload.stop,
            seed=payload.seed,
            request_model=payload.model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    prompt_tokens = result.prompt_tokens or 0
    completion_tokens = result.completion_tokens or 0
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": result.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result.text},
                "finish_reason": result.finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "orb_runtime": {
            "provider": result.provider,
            "lane": lane or config.default_lane,
            "latency_ms": result.latency_ms,
            "request_host": request.client.host if request.client else None,
        },
    }
