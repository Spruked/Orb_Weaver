from __future__ import annotations

import io
import os
import threading
import time
from typing import Optional

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from kokoro import KPipeline


DEFAULT_VOICE = os.environ.get("KOKORO_DEFAULT_VOICE", "am_echo")
DEFAULT_SPEED = float(os.environ.get("KOKORO_DEFAULT_SPEED", "1.05"))
DEVICE = os.environ.get("KOKORO_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
SAMPLE_RATE = 24000

app = FastAPI(title="Orb Weaver Kokoro TTS", version="1.0.0")
generation_lock = threading.Lock()
pipelines: dict[str, KPipeline] = {}
started_at = time.time()
prewarm_seconds: Optional[float] = None


class SpeechRequest(BaseModel):
    input: Optional[str] = None
    text: Optional[str] = None
    model: str = "kokoro"
    voice: str = DEFAULT_VOICE
    response_format: str = Field(default="wav")
    speed: float = Field(default=DEFAULT_SPEED, ge=0.5, le=2.0)


def _voice_language(voice: str) -> str:
    return (voice or DEFAULT_VOICE)[0].lower()


def _pipeline_for_voice(voice: str) -> KPipeline:
    lang = _voice_language(voice)
    pipeline = pipelines.get(lang)
    if pipeline is None:
        pipeline = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M", device=DEVICE)
        pipelines[lang] = pipeline
    return pipeline


def _synthesize(text: str, voice: str, speed: float) -> bytes:
    pipeline = _pipeline_for_voice(voice)
    chunks: list[np.ndarray] = []
    for _, _, audio in pipeline(text, voice=voice, speed=speed, split_pattern=r"\n+"):
        if audio is None:
            continue
        if hasattr(audio, "detach"):
            chunks.append(audio.detach().cpu().numpy())
        else:
            chunks.append(np.asarray(audio))
    if not chunks:
        raise RuntimeError("Kokoro produced no audio")

    wav_buffer = io.BytesIO()
    sf.write(wav_buffer, np.concatenate(chunks), SAMPLE_RATE, format="WAV")
    wav_buffer.seek(0)
    return wav_buffer.read()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "engine": "kokoro",
        "device": DEVICE,
        "cuda": torch.cuda.is_available(),
        "default_voice": DEFAULT_VOICE,
        "sample_rate": SAMPLE_RATE,
        "loaded_languages": sorted(pipelines.keys()),
        "prewarm_seconds": prewarm_seconds,
        "uptime_seconds": round(time.time() - started_at, 3),
    }


@app.on_event("startup")
def startup_prewarm():
    global prewarm_seconds
    started = time.time()
    _synthesize("I am ready.", DEFAULT_VOICE, DEFAULT_SPEED)
    prewarm_seconds = round(time.time() - started, 3)


def _speech_response(payload: SpeechRequest):
    text = (payload.input or payload.text or "").strip()
    if not text:
        return JSONResponse({"error": "Empty text"}, status_code=400)
    if payload.response_format.lower().strip(".") != "wav":
        return JSONResponse({"error": "Only wav response_format is enabled"}, status_code=400)
    if not generation_lock.acquire(timeout=30):
        return JSONResponse(
            {"error": "Kokoro TTS is busy", "retry_after_seconds": 0.5},
            status_code=503,
            headers={"Retry-After": "1"},
        )

    started = time.time()
    try:
        audio = _synthesize(text=text[:1200], voice=payload.voice or DEFAULT_VOICE, speed=payload.speed)
        elapsed = round(time.time() - started, 3)
        return StreamingResponse(
            io.BytesIO(audio),
            media_type="audio/wav",
            headers={
                "X-TTS-Engine": "kokoro",
                "X-TTS-Device": DEVICE,
                "X-TTS-Voice": payload.voice or DEFAULT_VOICE,
                "X-TTS-Generation-Seconds": str(elapsed),
            },
        )
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    finally:
        generation_lock.release()


@app.post("/speak")
def speak(payload: SpeechRequest):
    return _speech_response(payload)


@app.post("/v1/audio/speech")
def speech(payload: SpeechRequest):
    return _speech_response(payload)
