"""CALI-proven voice transport shared by every manufactured Website ORB.

Identity is supplied by a deployment's environment; the transport, provider
order, payloads, timeouts, WAV validation, and cache key are universal.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
from typing import Any

import httpx

VOICE_CACHE = Path(os.getenv("ORB_TTS_CACHE_DIR", "runtime/voice_cache"))
STT_URL = os.getenv("FASTER_WHISPER_STT_URL", "http://127.0.0.1:9000/stt")
KOKORO_URL = os.getenv("ORB_TTS_KOKORO_URL", "http://127.0.0.1:8880/speak")
KOKORO_MODEL = os.getenv("ORB_TTS_KOKORO_MODEL", "kokoro")
KOKORO_VOICE = os.getenv("ORB_TTS_KOKORO_VOICE", "af_heart")
KOKORO_FORMAT = os.getenv("ORB_TTS_KOKORO_FORMAT", "wav")
KOKORO_SPEED = float(os.getenv("ORB_TTS_KOKORO_SPEED", "1.05"))
QWEN_URL = os.getenv("ORB_TTS_QWEN_URL", "http://127.0.0.1:9880/speak")
QWEN_VOICE = os.getenv("ORB_TTS_QWEN_VOICE", "cali_voice_profile")
KOKORO_TIMEOUT = float(os.getenv("ORB_TTS_TIMEOUT_SECONDS", "45"))
QWEN_TIMEOUT = float(os.getenv("ORB_TTS_QWEN_TIMEOUT_SECONDS", "220"))
_locks: dict[str, asyncio.Lock] = {}


def _wav(payload: bytes) -> bool:
    return len(payload) >= 12 and payload[:4] == b"RIFF" and payload[8:12] == b"WAVE"


def _cached(provider: str, profile: str, text: str) -> tuple[Path, str]:
    digest = hashlib.sha256(f"{provider}{profile}{text}".encode()).hexdigest()[:24]
    path = VOICE_CACHE / f"{provider}-{digest}.wav"
    return path, f"/orb/audio/{path.name}"


async def transcribe(file_name: str, content_type: str, content: bytes) -> str:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(STT_URL, files={"file": (file_name, content, content_type)})
        response.raise_for_status()
    transcript = str(response.json().get("text") or response.json().get("transcript") or "").strip()
    if not transcript:
        raise ValueError("Faster-Whisper did not return a transcript")
    return transcript


async def speak(text: str) -> dict[str, Any]:
    """Kokoro af_heart first; Qwen3 voice-clone only if Kokoro fails."""
    errors: list[str] = []
    for provider, url, profile, timeout, payload in (
        ("kokoro", KOKORO_URL, KOKORO_VOICE, KOKORO_TIMEOUT, {
            "input": text, "text": text, "model": KOKORO_MODEL, "voice": KOKORO_VOICE,
            "response_format": KOKORO_FORMAT, "speed": KOKORO_SPEED,
        }),
        ("qwen", QWEN_URL, QWEN_VOICE, QWEN_TIMEOUT, {"text": text, "language": "English", "mode": "voice_clone"}),
    ):
        path, audio_url = _cached(provider, profile, text)
        # CALI's live route only short-circuits an existing Qwen voice-clone
        # file. Kokoro is invoked on each request and overwrites its stable
        # cache path; preserve that exact provider-specific behavior.
        if provider == "qwen" and path.is_file() and _wav(path.read_bytes()):
            return {"tts_audio_url": audio_url, "tts_provider": provider, "tts_voice": profile,
                    "tts_fallback_used": provider == "qwen", "primary_tts_error": errors[0] if errors else None,
                    "tts_cache_hit": True}
        lock = _locks.setdefault(f"{provider}:{path.name}", asyncio.Lock())
        try:
            async with lock:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                if "audio/wav" not in response.headers.get("content-type", "").lower() or not _wav(response.content):
                    raise ValueError(f"{provider} returned non-WAV audio")
                VOICE_CACHE.mkdir(parents=True, exist_ok=True)
                path.write_bytes(response.content)
            return {"tts_audio_url": audio_url, "tts_provider": provider, "tts_voice": profile,
                    "tts_fallback_used": provider == "qwen", "primary_tts_error": errors[0] if errors else None,
                    "tts_cache_hit": False}
        except Exception as exc:
            errors.append(f"{provider}: {exc}")
    return {"tts_audio_url": None, "tts_provider": None, "tts_voice": None,
            "tts_fallback_used": False, "tts_error": "; ".join(errors)}
