"""
TPC Website ORB - FastAPI Backend
Main application entry point.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import uvicorn
import asyncio
import json
import time

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from Orb_Assistant.tpc_website_orb.tpc_core.pipeline.tpc_pipeline import get_tpc_pipeline, PipelineResult
from Orb_Assistant.tpc_website_orb.engines.phonatory_output_bridge.phonatory_bridge import get_phonatory_bridge


# Global state
pipeline = None
phonatory = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global pipeline, phonatory
    print("[TPC Website ORB] Initializing...")
    pipeline = get_tpc_pipeline()
    phonatory = get_phonatory_bridge()
    print("[TPC Website ORB] Ready")
    yield
    print("[TPC Website ORB] Shutting down...")


app = FastAPI(
    title="TPC Website ORB",
    description="Triple Predicate Cubed - Website ORB Assistant Backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:18020",
        "http://localhost:18020",
        "http://localhost:1420",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REST ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return {
        "name": "TPC Website ORB",
        "version": "1.0.0",
        "status": "active",
        "pipeline_ready": pipeline is not None
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "pipeline_stats": pipeline.get_stats() if pipeline else {},
        "phonatory_stats": phonatory.get_stats() if phonatory else {}
    }


@app.post("/api/v1/reason")
async def reason(request: dict):
    """
    Run TPC reasoning on input.

    Request body:
    {
        "input": "text or audio path",
        "input_type": "text" | "audio",
        "session_id": "optional"
    }
    """
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    input_data = request.get("input", "")
    input_type = request.get("input_type", "text")
    session_id = request.get("session_id")

    if not input_data:
        raise HTTPException(status_code=400, detail="Input required")

    result = await pipeline.process(input_data, input_type, session_id)

    return {
        "status": result.status.value,
        "output": result.output_text,
        "confidence": result.confidence,
        "philosopher_verdicts": result.philosopher_verdicts,
        "coherence": result.coherence_reading,
        "vault_retrieval": result.vault_retrieval,
        "ecm": result.ecm_output,
        "drift": result.drift_report,
        "processing_time_ms": result.processing_time_ms,
        "glyph_signature": result.glyph_signature,
        "depth_trace": result.depth_trace
    }


@app.post("/api/v1/speak")
async def speak(request: dict):
    """
    Convert text to speech.

    Request body:
    {
        "text": "text to speak",
        "voice": "optional voice id",
        "engine": "kokoro" | "qwen" | "auto"
    }
    """
    if not phonatory:
        raise HTTPException(status_code=503, detail="Phonatory bridge not initialized")

    text = request.get("text", "")
    voice = request.get("voice")
    engine = request.get("engine", "auto")

    if not text:
        raise HTTPException(status_code=400, detail="Text required")

    result = phonatory.speak(text, voice, engine)
    return result


@app.get("/api/v1/stats")
async def stats():
    """Get system statistics."""
    return {
        "pipeline": pipeline.get_stats() if pipeline else {},
        "phonatory": phonatory.get_stats() if phonatory else {},
        "timestamp": time.time()
    }


@app.get("/api/v1/voices")
async def voices():
    """List available TTS voices."""
    from Orb_Assistant.tpc_website_orb.engines.kokoro_engine.adapter import get_kokoro_adapter
    kokoro = get_kokoro_adapter()
    return {
        "kokoro": kokoro.list_voices(),
        "qwen": ["default"]
    }


@app.get("/api/v1/drift")
async def drift_report():
    """Get drift ping report."""
    from Orb_Assistant.tpc_website_orb.tpc_core.drift_ping.drift_ping import get_drift_ping_chain
    drift = get_drift_ping_chain()
    return drift.get_drift_report()


# ============================================================
# WEBSOCKET — Real-time Pipeline Streaming
# ============================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


@app.websocket("/ws/pipeline")
async def pipeline_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()

            action = data.get("action")

            if action == "reason":
                input_data = data.get("input", "")
                input_type = data.get("input_type", "text")

                # Stream pipeline stages
                await websocket.send_json({
                    "stage": "stt_gateway",
                    "status": "processing",
                    "message": "Normalizing input..."
                })

                result = await pipeline.process(input_data, input_type)

                await websocket.send_json({
                    "stage": "complete",
                    "status": result.status.value,
                    "output": result.output_text,
                    "confidence": result.confidence,
                    "depth_trace": result.depth_trace,
                    "processing_time_ms": result.processing_time_ms
                })

            elif action == "ping":
                await websocket.send_json({"pong": True, "timestamp": time.time()})

            elif action == "stats":
                await websocket.send_json({
                    "pipeline": pipeline.get_stats(),
                    "phonatory": phonatory.get_stats()
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        manager.disconnect(websocket)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
