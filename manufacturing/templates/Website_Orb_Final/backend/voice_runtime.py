"""Customer-configured speech transport; all cached audio stays in the Vault."""
from __future__ import annotations
import hashlib
import os
import httpx
from .storage import canonical_vault_root, require_vault_path

VOICE_CACHE = require_vault_path(canonical_vault_root() / "cache/voice", "speech cache")
STT_URL = os.getenv("FASTER_WHISPER_STT_URL", "")
TTS_URL = os.getenv("ORB_TTS_KOKORO_URL", "")


async def transcribe(file_name: str, content_type: str, content: bytes) -> str:
    if not STT_URL:
        raise ValueError("Speech recognition is not configured on this customer runtime; use text.")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(STT_URL, files={"file": (file_name, content, content_type)})
        response.raise_for_status()
    transcript = str(response.json().get("text") or response.json().get("transcript") or "").strip()
    if not transcript:
        raise ValueError("Speech recognition returned no transcript")
    return transcript


async def speak(text: str) -> dict:
    if not TTS_URL:
        return {"tts_audio_url": None, "tts_error": "Speech synthesis is not configured; text is available."}
    import json
    config = json.loads((canonical_vault_root() / "payload/site_config.json").read_text())
    voice = os.getenv("ORB_TTS_KOKORO_VOICE") or config["voice"]["voice"]
    key = hashlib.sha256((TTS_URL + voice + text).encode()).hexdigest()
    path = require_vault_path(VOICE_CACHE / (key + ".wav"), "speech audio")
    try:
        if not path.is_file():
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(TTS_URL, json={"input": text, "text": text, "voice": voice,
                                                          "model": "kokoro", "response_format": "wav"})
                response.raise_for_status()
            if response.content[:4] != b"RIFF" or response.content[8:12] != b"WAVE":
                raise ValueError("Speech provider did not return WAV audio")
            VOICE_CACHE.mkdir(parents=True, exist_ok=True)
            path.write_bytes(response.content)
        return {"tts_audio_url": "/orb/audio/" + path.name, "tts_provider": "kokoro", "tts_voice": voice}
    except (httpx.HTTPError, ValueError):
        return {"tts_audio_url": None, "tts_error": "Speech provider unavailable; text is available."}
