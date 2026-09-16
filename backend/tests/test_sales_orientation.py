import asyncio
import importlib
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock


def test_outcome_orient_does_not_require_stale_voice_mechanics(monkeypatch):
    backend_path = str((Path.cwd() / "backend").resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    main = importlib.import_module("main")

    async def generated(*_args, **_kwargs):
        return {
            "spoken_output": "Orb Weaver helps businesses guide visitors to the right next step on their website.",
            "llm_source": "test-live-cognition",
        }

    async def synthesized(_text):
        return {"tts_audio_url": "/speech.wav", "tts_provider": "test", "tts_error": None}

    monkeypatch.setattr(main, "_llm_orb_spoken_output", generated)
    monkeypatch.setattr(main, "_synthesize_orb_tts", synthesized)
    result = asyncio.run(main._first_visitor_act_response(
        transcript="Give a concise outcome-focused orientation.",
        experience_context={"phase": "orientation", "objective": "Orient the visitor", "verification_state": "not_applicable"},
        cognitive_pulse=None,
        memory_context=None,
        website_context=None,
        page_capsule=None,
        operating_policy=None,
    ))

    assert result["spoken_output"].startswith("Orb Weaver helps businesses")
    assert result["tts_audio_url"] == "/speech.wav"


def test_orientation_prompt_and_delivery_agree_on_product_outcomes(monkeypatch):
    main = importlib.import_module("main")
    speech = "Help customers find suitable products and complete their next step with less confusion."
    prompts = []

    class Provider:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json):
            prompts.append(json["prompt"])
            return main.httpx.Response(200, json={"response": speech}, request=main.httpx.Request("POST", url))

    monkeypatch.setattr(main, "_local_llm_is_locked_llamacpp", lambda: True)
    monkeypatch.setattr(main.settings, "LOCAL_LLM_URL", "http://test-provider/api/generate")
    monkeypatch.setattr(main, "_build_website_weaver_envelope", lambda *args: {})
    monkeypatch.setattr(main, "_fallback_orb_spoken_output", lambda *args: "Unavailable")
    monkeypatch.setattr(main.httpx, "AsyncClient", Provider)
    monkeypatch.setattr(main, "_synthesize_orb_tts", AsyncMock(return_value={"tts_audio_url": "/outcomes.wav"}))
    result = asyncio.run(main._first_visitor_act_response(
        transcript="Orient this visitor to product value.",
        experience_context={"phase": "orientation", "objective": "Explain product value"},
        cognitive_pulse=None, memory_context=None, website_context=None,
        page_capsule=None, operating_policy=None,
    ))
    assert result["spoken_output"] == speech
    assert len(prompts) == 1  # No second technical-coverage generation.
    assert "why it helps visitors or businesses" in prompts[0]
    assert "Explicitly tell the visitor to speak" not in prompts[0]


@pytest.mark.parametrize("speech,source,audio,detail", [
    ("", "test-live", "/speech.wav", "cognition is unavailable"),
    ("Product guidance", "local-fallback", "/speech.wav", "cognition is unavailable"),
    ("How can I help you?", "test-live", "/speech.wav", "did not satisfy"),
    ("Relevant website guidance", "test-live", None, "voice is unavailable"),
])
def test_orientation_still_blocks_failed_cognition_or_voice(monkeypatch, speech, source, audio, detail):
    main = importlib.import_module("main")
    monkeypatch.setattr(main, "_llm_orb_spoken_output", AsyncMock(return_value={"spoken_output": speech, "llm_source": source}))
    monkeypatch.setattr(main, "_synthesize_orb_tts", AsyncMock(return_value={"tts_audio_url": audio}))
    with pytest.raises(HTTPException) as error:
        asyncio.run(main._first_visitor_act_response(
            transcript="Orient the visitor.", experience_context={"phase": "orientation"},
            cognitive_pulse=None, memory_context=None, website_context=None,
            page_capsule=None, operating_policy=None,
        ))
    assert error.value.status_code == 503
    assert detail in error.value.detail
