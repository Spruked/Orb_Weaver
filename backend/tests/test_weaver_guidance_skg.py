import asyncio
import importlib
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.orb.nine_of_clubs import GuidanceSKG, MAX_GUIDANCE_BYTES, guidance_skg, showcase_guidance_mode
from app.orb.site_lexicon import weaver_lexical_context


@pytest.mark.parametrize("route,mode", [("/signup", "account_setup"), ("/login", "login"),
                                      ("/founding-beta", "beta"), ("/investor-contact", "investor")])
def test_showcase_modes_are_route_scoped_and_bounded(route, mode):
    assert showcase_guidance_mode({"current_url": "https://orbweaver.spruked.com" + route}) == mode
    assert showcase_guidance_mode({"current_url": "https://customer.example" + route}) is None
    assert len(guidance_skg().render(mode).encode()) <= MAX_GUIDANCE_BYTES
    assert showcase_guidance_mode({"current_url": "http://localhost:16667/"}, {"guidance_mode": "account_setup"}) == "discovery"


def test_policy_validation_rejects_incomplete_rules():
    policy = guidance_skg().model_dump(by_alias=True)
    policy["modes"].pop("login")
    with pytest.raises(ValidationError):
        GuidanceSKG.model_validate(policy)


def test_host_uses_its_scan_lexicon_without_leaking_to_customer():
    context = {"domain": "orbweaver.spruked.com", "page_knowledge": [{"route": "/signup", "title": "Workspace", "content_hash": "observed"}],
               "lexical_index": {"aliases": {"nav: Workspace": ["create account"]}}}
    host = {"current_url": "https://orbweaver.spruked.com/"}
    match = weaver_lexical_context(context, host, "create account")
    assert match["status"] == "matched"
    assert match["candidates"][0]["route"] == "/signup"
    assert match["authority"] == "advisory_only"
    assert weaver_lexical_context(context, {"current_url": "https://customer.example/"}, "create account") == {}
    assert weaver_lexical_context({**context, "domain": "customer.example"}, host, "create account") == {}


def test_actual_host_prompt_receives_guidance_and_lexicon(monkeypatch):
    main = importlib.import_module("main")
    prompts = []
    class Provider:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, json):
            prompts.append(json["prompt"])
            return main.httpx.Response(200, json={"response": "Which account step do you see?"}, request=main.httpx.Request("POST", url))
    monkeypatch.setattr(main, "_local_llm_is_locked_llamacpp", lambda: True)
    monkeypatch.setattr(main, "_build_website_weaver_envelope", lambda *args: {})
    monkeypatch.setattr(main.httpx, "AsyncClient", Provider)
    monkeypatch.setattr(main, "_synthesize_orb_tts", AsyncMock(return_value={"tts_audio_url": "/guide.wav"}))
    result = asyncio.run(main._first_visitor_act_response(
        transcript="create account", experience_context={"phase": "agency", "objective": "Guide account setup", "guidance_mode": "account_setup"},
        cognitive_pulse=None, memory_context=None,
        website_context={"domain": "orbweaver.spruked.com", "page_knowledge": [{"route": "/signup", "title": "Workspace"}],
                         "lexical_index": {"aliases": {"nav: Workspace": ["create account"]}}},
        page_capsule={"current_url": "https://orbweaver.spruked.com/signup", "route": "/signup"}, operating_policy=None))
    assert result["spoken_output"] == "Which account step do you see?"
    assert len(prompts) == 1
    assert "NINE OF CLUBS GUIDANCE" in prompts[0]
    assert "SITE LEXICON" in prompts[0]
    assert "Never fill, select agreements or submit" in prompts[0]
    assert '"route": "/signup"' in prompts[0]


def test_api_accepts_short_mode_but_rejects_arbitrary_guidance():
    main = importlib.import_module("main")
    context = main.WebsiteOrbExperienceContext(phase="agency", objective="Guide current signup field", guidance_mode="account_setup")
    assert context.guidance_mode == "account_setup"
    with pytest.raises(ValidationError):
        main.WebsiteOrbExperienceContext(phase="agency", objective="Guide current signup field", guidance_mode="bypass_governor")
