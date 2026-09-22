"""Owner-authored guidance SKG; supplies wording policy, never execution grants.

The canonical discovery registry and Governor retain selection and progression.
This module deliberately has no crawler, pointer executor, or session store.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

GuidanceMode = Literal[
    "tour_narration", "tour_question", "discovery", "account_setup", "login",
    "preflight", "preflight_review", "beta", "investor",
]
ShowcaseInteraction = Literal["tour_question", "account_setup"]
_MODES = frozenset(GuidanceMode.__args__)
_POLICY_PATH = Path(__file__).with_name("nine_of_clubs_skg.json")
_SHOWCASE_HOSTS = frozenset({"orbweaver.spruked.com", "localhost", "127.0.0.1"})
MAX_GUIDANCE_BYTES = 4096


class GuidanceSKG(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_id: Literal["orb_weaver.nine_of_clubs.guidance.v2"] = Field(alias="schema")
    purpose: str = Field(min_length=1)
    registry: Literal["frontend/src/tour/discovery/patterns.json"]
    common_rules: tuple[str, ...]
    modes: dict[GuidanceMode, tuple[str, ...]]
    showcase_routes: dict[str, GuidanceMode]
    compilation_rules: tuple[str, ...]
    continuity_rules: tuple[str, ...]

    @model_validator(mode="after")
    def valid_policy(self):
        if set(self.modes) != _MODES:
            raise ValueError("Incomplete guidance modes")
        for rules in (self.common_rules, self.compilation_rules, self.continuity_rules, *self.modes.values()):
            if not rules or any(not rule.strip() for rule in rules):
                raise ValueError("Guidance rules must not be empty")
        for route, mode in self.showcase_routes.items():
            if not route.startswith("/") or route.startswith("//") or urlsplit(route).query or urlsplit(route).fragment:
                raise ValueError("Showcase routes must be exact local paths")
            if mode not in self.modes:
                raise ValueError("Unknown guidance mode")
        for mode in self.modes:
            if len(self.render(mode).encode("utf-8")) > MAX_GUIDANCE_BYTES:
                raise ValueError("Guidance exceeds bounded prompt budget")
        return self

    def render(self, mode: GuidanceMode) -> str:
        return (
            "NINE OF CLUBS GUIDANCE (private wording policy; no execution authority):\n"
            + "\n".join((*self.common_rules, *self.modes[mode]))
        )


@lru_cache(maxsize=1)
def guidance_skg() -> GuidanceSKG:
    return GuidanceSKG.model_validate_json(_POLICY_PATH.read_text(encoding="utf-8"))


def showcase_guidance_mode(
    page: Optional[dict], experience: Optional[dict] = None,
) -> Optional[GuidanceMode]:
    """Select speech policy only. Browser-reported state does not grant authority."""
    page = page or {}
    source_domain = page.get("context_domain") or page.get("domain")
    if source_domain and source_domain not in _SHOWCASE_HOSTS:
        return None
    url = str(page.get("current_url") or "")
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in _SHOWCASE_HOSTS:
            return None
    except ValueError:
        return None
    experience = experience or {}
    route = parsed.path.rstrip("/") or "/"
    # Explicit tour narration remains an authored stop even on a form route.
    if experience.get("tour"):
        return "preflight_review" if experience["tour"].get("chapter_id") == "preflight-results" else "tour_narration"
    if experience.get("guidance_mode") == "tour_question":
        return "tour_question"
    # A mode hint cannot convert a different page into the account form.
    return guidance_skg().showcase_routes.get(route, "discovery")


def guidance_prompt(mode: Optional[GuidanceMode]) -> str:
    return guidance_skg().render(mode) if mode else ""
