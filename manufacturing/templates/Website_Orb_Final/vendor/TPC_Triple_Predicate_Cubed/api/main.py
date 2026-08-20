import sys
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).resolve().parents[1]
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from Integration import TPCSystem
except ImportError as e:
    print(f"Failed to import TPCSystem: {e}")
    sys.exit(1)

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, Optional
import time
import io
from results_vault import save_query_result, save_test_run
import tempfile
import numpy as np

app = FastAPI(title="TPC API", version="1.0.0")

_CORS_ORIGINS = [
    f"http://localhost:{p}" for p in range(5173, 5200)
] + [
    f"http://127.0.0.1:{p}" for p in range(5173, 5200)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Singletons ──────────────────────────────────────────────────────────────

_tpc: Optional[TPCSystem] = None
_whisper_model = None
_kokoro_pipeline = None

_COCHLEAR_DIR = parent_dir / "cochlear_processor_3.0"


def _default_substrate_root() -> Path:
    if os.name == "nt":
        return Path(r"R:\tpc_substrate")
    return Path("/mnt/r/tpc_substrate")


_SUBSTRATE_ROOT = Path(os.getenv("TPC_SUBSTRATE_ROOT", str(_default_substrate_root())))
_LOG = logging.getLogger("tpc.substrate")


def _substrate_paths() -> Dict[str, Path]:
    return {
        "root": _SUBSTRATE_ROOT,
        "pending": _SUBSTRATE_ROOT / "pending",
        "suspended": _SUBSTRATE_ROOT / "suspended",
        "quarantine": _SUBSTRATE_ROOT / "quarantine",
        "a_posteriori": _SUBSTRATE_ROOT / "vault" / "a_posteriori",
        "handoffs": _SUBSTRATE_ROOT / "orb_handoffs",
        "logs": _SUBSTRATE_ROOT / "logs",
        "snapshots": _SUBSTRATE_ROOT / "snapshots",
        "manifests": _SUBSTRATE_ROOT / "manifests",
    }


def _ensure_substrate_layout() -> None:
    for path in _substrate_paths().values():
        path.mkdir(parents=True, exist_ok=True)


def _setup_substrate_logging() -> None:
    if _LOG.handlers:
        return
    _ensure_substrate_layout()
    log_file = _substrate_paths()["logs"] / "tpc_governance.log"
    handler = RotatingFileHandler(str(log_file), maxBytes=100 * 1024 * 1024, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _LOG.setLevel(logging.INFO)
    _LOG.addHandler(handler)
    _LOG.propagate = False


def get_tpc() -> TPCSystem:
    if _tpc is None:
        raise HTTPException(status_code=503, detail="TPC system not ready")
    return _tpc


def _load_whisper():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    try:
        import whisper
        _whisper_model = whisper.load_model("base")
        print("Whisper model loaded (base)")
        return _whisper_model
    except ImportError:
        raise HTTPException(503, "openai-whisper not installed — run: pip install openai-whisper")


def _load_kokoro():
    global _kokoro_pipeline
    if _kokoro_pipeline is not None:
        return _kokoro_pipeline
    try:
        from kokoro import KPipeline
        _kokoro_pipeline = KPipeline(lang_code="a")   # American English
        print("Kokoro TTS pipeline loaded")
        return _kokoro_pipeline
    except ImportError:
        raise HTTPException(503, "kokoro not installed — run: pip install kokoro soundfile")


# ── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    global _tpc
    try:
        _setup_substrate_logging()
        _tpc = TPCSystem()
        _tpc.initialize()
        print("TPC system initialized successfully")
    except Exception as e:
        print(f"Failed to initialize TPC system: {e}")
        _tpc = None


# ── Request models ────────────────────────────────────────────────────────────

class ReasonRequest(BaseModel):
    text: str
    input_type: str = "text"


class SpeakRequest(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 1.0


class GovernRequest(BaseModel):
    text: str
    source: str = "swarm"
    artifact_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


# ── Basic routes ──────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "TPC API is running"}

@app.get("/test")
def test():
    return {"status": "test endpoint working"}

@app.get("/health")
def health():
    tpc = get_tpc()
    return {"status": "ok", "queries_processed": tpc.query_count}


@app.post("/reason")
def reason(req: ReasonRequest) -> Dict[str, Any]:
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")
    t0 = time.perf_counter()
    result = get_tpc().process(req.text.strip(), input_type=req.input_type)
    result["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    try:
        save_query_result({**result, "_input_text": req.text.strip()})
    except Exception:
        pass  # vault I/O must never fail a reasoning response
    return result


@app.post("/govern")
def govern(req: GovernRequest) -> Dict[str, Any]:
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text must not be empty")

    _ensure_substrate_layout()
    artifact_id = req.artifact_id or f"claim_{uuid4().hex[:12]}"
    timestamp = datetime.now(timezone.utc).isoformat()

    pending_envelope = {
        "artifact_id": artifact_id,
        "source": req.source,
        "status": "pending",
        "created_at": timestamp,
        "text": text,
        "metadata": req.metadata,
    }
    pending_path = _write_substrate_json("pending", artifact_id, pending_envelope)

    t0 = time.perf_counter()
    result = get_tpc().process(text, input_type="text")
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    verdict = _resolve_verdict(result)
    target_bucket = {
        "ADMIT": "a_posteriori",
        "SUSPEND": "suspended",
        "REJECT": "quarantine",
    }[verdict]

    routed_envelope = {
        "artifact_id": artifact_id,
        "source": req.source,
        "status": verdict,
        "created_at": timestamp,
        "governed_at": datetime.now(timezone.utc).isoformat(),
        "text": text,
        "metadata": req.metadata,
        "tpc": result,
        "latency_ms": latency_ms,
    }
    routed_path = _write_substrate_json(target_bucket, artifact_id, routed_envelope)
    handoff_path = _write_substrate_json("handoffs", artifact_id, routed_envelope)

    _LOG.info(
        "artifact_id=%s source=%s verdict=%s target=%s latency_ms=%.2f",
        artifact_id,
        req.source,
        verdict,
        target_bucket,
        latency_ms,
    )

    return {
        "artifact_id": artifact_id,
        "verdict": verdict,
        "target_bucket": target_bucket,
        "pending_path": str(pending_path),
        "routed_path": str(routed_path),
        "orb_handoff_path": str(handoff_path),
        "latency_ms": latency_ms,
        "confidence": result.get("confidence"),
        "query_id": result.get("query_id"),
    }


@app.get("/run-tests")
def run_tests() -> Dict[str, Any]:
    from tests.demo_test import run_all_tests
    results = run_all_tests()
    # Normalise list → dict for vault persistence and consistent schema
    results_dict = {
        r.get("name", str(i)): {**r, "status": "PASS" if r.get("passed") else "FAIL"}
        for i, r in enumerate(results)
    }
    try:
        save_test_run(results_dict)
    except Exception:
        pass  # vault I/O must never fail a test response
    return {"test_results": results_dict}


# ── Audio routes ───────────────────────────────────────────────────────────────

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Transcribe uploaded audio using Whisper, then refine with
    Cochlear 3.0 perceptual correction.

    Accepts: WAV / MP3 / M4A / OGG / FLAC
    Returns: { transcript, cochlear, duration_ms }
    """
    t0 = time.perf_counter()
    whisper_model = _load_whisper()

    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # 1. Whisper STT
        raw = whisper_model.transcribe(tmp_path)
        raw_transcript: str = raw["text"].strip()

        # 2. Cochlear 3.0 perceptual correction (optional; degrades gracefully)
        try:
            cochlear_report = _run_cochlear_correction(tmp_path, raw_transcript)
        except Exception as exc:
            raise HTTPException(503, f"Cochlear correction unavailable: {exc}")
        corrected = cochlear_report.get("corrected_transcript", raw_transcript)

        return {
            "transcript": corrected,
            "cochlear": cochlear_report,
            "duration_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    finally:
        _safe_unlink(tmp_path)


@app.post("/reason-audio")
async def reason_audio(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Full voice-to-reasoning pipeline:
      Whisper STT → Cochlear 3.0 correction → TPC tribunal → result dict
    """
    t0 = time.perf_counter()
    whisper_model = _load_whisper()
    tpc = get_tpc()

    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # 1. Whisper STT
        raw = whisper_model.transcribe(tmp_path)
        raw_transcript: str = raw["text"].strip()

        # 2. Cochlear 3.0 perceptual correction
        try:
            cochlear_report = _run_cochlear_correction(tmp_path, raw_transcript)
        except Exception as exc:
            raise HTTPException(503, f"Cochlear correction unavailable: {exc}")
        corrected = cochlear_report.get("corrected_transcript", raw_transcript)

        if not corrected:
            raise HTTPException(422, "Transcription produced empty text")

        # 3. TPC reasoning pipeline
        result = tpc.process(corrected, input_type="text")
        result["transcript"] = corrected
        result["cochlear"] = cochlear_report
        result["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        return result
    finally:
        _safe_unlink(tmp_path)


@app.post("/speak")
def speak(req: SpeakRequest) -> StreamingResponse:
    """
    Convert text to speech via Kokoro TTS.
    Returns: audio/wav stream
    """
    if not req.text.strip():
        raise HTTPException(422, "text must not be empty")

    pipeline = _load_kokoro()

    try:
        import soundfile as sf
    except ImportError:
        raise HTTPException(503, "soundfile not installed — run: pip install soundfile")

    chunks = []
    sample_rate = 24000
    for _gs, _ps, audio in pipeline(req.text.strip(), voice=req.voice, speed=req.speed):
        if audio is not None and len(audio) > 0:
            chunks.append(np.asarray(audio, dtype=np.float32))

    if not chunks:
        raise HTTPException(500, "Kokoro TTS produced no audio")

    combined = np.concatenate(chunks)
    buf = io.BytesIO()
    sf.write(buf, combined, sample_rate, format="WAV")
    buf.seek(0)
    return StreamingResponse(buf, media_type="audio/wav",
                             headers={"Content-Disposition": "inline; filename=tpc_response.wav"})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_cochlear_correction(audio_path: str, raw_transcript: str) -> Dict[str, Any]:
    """
    Route audio through Cochlear Processor 3.0 for perceptual correction.
    Returns a report dict. Gracefully degrades if cochlear deps missing.
    """
    cochlear_dir_str = str(_COCHLEAR_DIR)
    if cochlear_dir_str not in sys.path:
        sys.path.insert(0, cochlear_dir_str)

    from cochlear_processor_v3 import CochlearProcessorV3  # noqa: PLC0415
    proc = CochlearProcessorV3(skg_path=str(_COCHLEAR_DIR / "hearing_skg.json"))
    trace = proc.process_audio_human_like(
        audio_path, context={"topic": "tpc_reasoning", "text": raw_transcript}
    )
    final_transcript = trace.get("final_transcript", raw_transcript)
    perc_report = trace.get("perceptual_report", {})
    return {
        "available": True,
        "raw_transcript": raw_transcript,
        "corrected_transcript": final_transcript,
        "corrections_made": len(trace.get("corrections", [])),
        "perceptual_confidence": round(float(perc_report.get("confidence_factor", 1.0)), 4),
    }


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def _resolve_verdict(result: Dict[str, Any]) -> str:
    if result.get("error"):
        return "SUSPEND"

    invariants = result.get("invariants", {})
    escalation = result.get("escalation", {})
    if invariants.get("passed") is False or escalation.get("triggered") is True:
        return "SUSPEND"

    conclusion = (
        result.get("synthesis", {}).get("final_conclusion")
        or ""
    ).upper()
    if "REJECT" in conclusion:
        return "REJECT"
    if "SUSPEND" in conclusion:
        return "SUSPEND"
    return "ADMIT"


def _write_substrate_json(bucket: str, artifact_id: str, payload: Dict[str, Any]) -> Path:
    base = _substrate_paths()[bucket]
    path = base / f"{artifact_id}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=True)
    return path
