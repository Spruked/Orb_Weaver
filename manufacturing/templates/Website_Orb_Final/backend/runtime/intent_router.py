from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple


INTENT_KEYWORDS = {
    "preflight": ("preflight", "scan", "check my site", "readiness", "audit"),
    "marketplace": ("marketplace", "buy", "price", "skin", "voice", "bundle"),
    "website_orb": ("website orb", "visitor orb", "basic", "premium", "enhanced"),
    "desktop_boundary": ("desktop", "dock", "mcp", "computer", "local machine"),
    "account": ("account", "login", "signup", "dashboard", "saved"),
    "about": ("what is", "who are", "about", "orb weaver", "what do you do"),
}


def classify_intent(message: str, route_record: Dict[str, Any]) -> Tuple[str, float]:
    text = message.lower()
    best = ("about", 0.0)
    for intent, keywords in INTENT_KEYWORDS.items():
        score = _keyword_score(text, keywords)
        if score > best[1]:
            best = (intent, score)

    route_terms = " ".join(str(value) for value in route_record.get("keywords", []))
    if route_terms:
        route_score = _keyword_score(text, route_terms.lower().split())
        if route_score > best[1]:
            best = ("current_route", route_score)

    return best if best[1] > 0 else ("general_site_help", 0.1)


def _keyword_score(text: str, keywords: Iterable[str]) -> float:
    hits = 0
    total = 0
    for keyword in keywords:
        key = str(keyword).lower().strip()
        if not key:
            continue
        total += 1
        if key in text:
            hits += 1
    return hits / max(total, 1)

