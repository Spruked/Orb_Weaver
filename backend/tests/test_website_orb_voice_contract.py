import pytest

from main import WebsiteOrbExperienceContext


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
