"""
Context & Correspondence Orchestrator - FastAPI Server
Production API with /v1/compress and /v1/context/run
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn

from ..models import (
    CompressRequest, CompressResponse,
    ContextRunRequest, ContextRunResponse,
    CanaryTestRequest, CanaryTestResponse
)
from ..core.engine import ContextCorrespondenceOrchestrator
from ..core.store import HandleStore
from ..core.canary import CanaryTester
from ..core.llm_abstraction import get_llm
from ..config import config


app = FastAPI(
    title="Context & Correspondence Orchestrator API",
    description="Governed ORBS context, retrieval, correspondence, and articulation orchestration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
store = HandleStore()
llm = get_llm(config.LLM_PROVIDER)
engine = ContextCorrespondenceOrchestrator(store=store, llm=llm)
canary = CanaryTester(engine=engine, llm=llm)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "store_stats": store.stats()
    }


@app.post("/v1/compress", response_model=CompressResponse)
async def compress(request: CompressRequest):
    """
    Compile source material into a task-aware CCO working context package.
    Returns a handle for later retrieval.
    """
    try:
        response = engine.compress(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/context/run", response_model=ContextRunResponse)
async def context_run(request: ContextRunRequest):
    """
    Run a task against a stored CCO working context package.
    """
    try:
        response = engine.run(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/canary/test", response_model=CanaryTestResponse)
async def canary_test(request: CanaryTestRequest):
    """
    Run canary tests to detect scope leakage and factual loss.
    """
    try:
        response = canary.run_tests(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/v1/context/{handle}")
async def delete_context(handle: str):
    """Delete a CCO context handle."""
    success = store.delete(handle)
    if not success:
        raise HTTPException(status_code=404, detail="Handle not found")
    return {"deleted": True, "handle": handle}


@app.get("/v1/context/{handle}/stats")
async def context_stats(handle: str):
    """Get statistics for a CCO context handle."""
    metadata = store.get(handle)
    if not metadata:
        raise HTTPException(status_code=404, detail="Handle not found")

    return {
        "handle": metadata.handle,
        "strategy": metadata.strategy,
        "original_tokens": metadata.original_tokens,
        "crystal_tokens": metadata.crystal_tokens,
        "compression_ratio": round(metadata.original_tokens / max(metadata.crystal_tokens, 1), 1),
        "task": metadata.task,
        "created_at": metadata.created_at.isoformat(),
        "last_accessed": metadata.last_accessed.isoformat(),
        "access_count": metadata.access_count,
        "ttl_seconds": metadata.ttl_seconds
    }


@app.post("/v1/admin/cleanup")
async def cleanup_expired():
    """Remove expired context handles."""
    removed = store.cleanup_expired()
    return {"removed": removed}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        workers=config.API_WORKERS
    )
