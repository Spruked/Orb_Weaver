import asyncio
from io import BytesIO

import pytest
from fastapi import UploadFile

import main
from main import WebsiteOrbExperienceContext
from app.orb.nine_of_clubs import GuidanceMode


@pytest.mark.parametrize(
    "guidance_mode",
    [
        "tour_narration",
        "tour_question",
        "discovery",
        "account_setup",
        "login",
        "preflight",
        "preflight_review",
        "beta",
        "investor",
    ],
)
def test_website_orb_experience_accepts_registered_guidance_modes(guidance_mode):
    context = WebsiteOrbExperienceContext(
        phase="agency",
        objective="Guide the visitor through the next useful step.",
        guidance_mode=guidance_mode,
    )
    assert context.guidance_mode == guidance_mode


def test_registered_guidance_modes_match_backend_registry():
    assert set(GuidanceMode.__args__) == {
        "tour_narration",
        "tour_question",
        "discovery",
        "account_setup",
        "login",
        "preflight",
        "preflight_review",
        "beta",
        "investor",
    }


def test_empty_stt_transcript_is_returned_to_no_speech_handler(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"text": ""}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **_kwargs: Client())
    audio = UploadFile(BytesIO(b"recorded-audio"), filename="voice.webm")

    assert asyncio.run(main._transcribe_with_faster_whisper(audio)) == ""
