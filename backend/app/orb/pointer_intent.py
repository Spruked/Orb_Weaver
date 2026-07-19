from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse


STOP_WORDS = {
    "a", "an", "and", "are", "can", "could", "do", "does", "for", "how", "i", "in", "is",
    "it", "me", "my", "of", "on", "please", "the", "there", "this", "to", "where", "with",
}

CONCEPTS = {
    "book": {"book", "booking", "reserve", "reservation", "schedule", "scheduled", "arrange", "setup", "set"},
    "consult": {"consult", "consultation", "conversation", "discussion", "meeting", "call", "appointment"},
    "buy": {"buy", "purchase", "order", "checkout"},
    "price": {"price", "prices", "pricing", "cost", "costs", "rate", "rates"},
    "contact": {"contact", "reach", "email", "message", "talk"},
    "start": {"start", "begin", "launch", "join", "signup", "register"},
    "demo": {"demo", "demonstration", "preview", "example"},
}

CONCEPT_BY_TOKEN = {
    token: concept
    for concept, tokens in CONCEPTS.items()
    for token in tokens
}


@dataclass(frozen=True)
class PointerIntentMatch:
    score: float
    record: Dict[str, Any]
    guidance_eligible: bool


def route_of(value: Any) -> str:
    raw = str(value or "/")
    parsed = urlparse(raw if "://" in raw else f"https://pointer.invalid{raw if raw.startswith('/') else '/' + raw}")
    return (parsed.path or "/").rstrip("/") or "/"


def semantic_tokens(value: Any) -> set[str]:
    raw_tokens = re.findall(r"[a-z0-9]+", str(value or "").lower())
    tokens: set[str] = set()
    for token in raw_tokens:
        if token in STOP_WORDS:
            continue
        concept = CONCEPT_BY_TOKEN.get(token)
        if concept:
            tokens.add(concept)
            continue
        if len(token) > 4 and token.endswith("ing"):
            token = token[:-3]
        elif len(token) > 3 and token.endswith("s"):
            token = token[:-1]
        if len(token) >= 2:
            tokens.add(token)
    return tokens


def pointer_text(record: Dict[str, Any]) -> str:
    values = [
        record.get("meaning"),
        record.get("target_type"),
        (record.get("structural_context") or {}).get("parent_heading"),
    ]
    for key in ("intent_aliases", "direct_aliases", "topic_aliases"):
        values.extend(record.get(key) or [])
    return " ".join(str(value) for value in values if value)


def guidance_eligible(record: Dict[str, Any]) -> bool:
    if record.get("status") not in (None, "active"):
        return False
    if record.get("confidence_class") not in {"VERIFIED", "STABLE"}:
        return False
    return (record.get("runtime_policy") or {}).get("may_point") is not False


def resolve_pointer_intent(
    records: Iterable[Dict[str, Any]],
    transcript: str,
    current_url: str,
    *,
    max_records: int = 6,
    minimum_score: float = 0.42,
    ambiguity_margin: float = 0.08,
) -> List[PointerIntentMatch]:
    query_tokens = semantic_tokens(transcript)
    if not query_tokens:
        return []
    current_route = route_of(current_url)
    scored: List[PointerIntentMatch] = []
    for record in records:
        if record.get("status") not in (None, "active") or route_of(record.get("page_route")) != current_route:
            continue
        record_tokens = semantic_tokens(pointer_text(record))
        overlap = query_tokens & record_tokens
        if not overlap:
            continue
        query_coverage = len(overlap) / len(query_tokens)
        record_precision = len(overlap) / max(1, len(record_tokens))
        score = 0.72 * query_coverage + 0.28 * record_precision
        normalized_query = " ".join(str(transcript).lower().split())
        direct_phrases = [
            str(value).lower().strip()
            for key in ("direct_aliases", "intent_aliases")
            for value in record.get(key) or []
            if str(value).strip()
        ]
        if any(phrase == normalized_query for phrase in direct_phrases):
            score += 0.35
        elif any(phrase in normalized_query for phrase in direct_phrases if len(phrase) >= 5):
            score += 0.15
        if record.get("target_type") in {"button", "nav", "link", "form_field"}:
            score += 0.04
        if score >= minimum_score:
            scored.append(PointerIntentMatch(round(score, 4), record, guidance_eligible(record)))

    scored.sort(key=lambda match: (match.score, match.guidance_eligible), reverse=True)
    eligible = [match for match in scored if match.guidance_eligible]
    candidates = eligible or scored
    if len(candidates) > 1:
        first, second = candidates[0], candidates[1]
        distinct = str(first.record.get("target_id")) != str(second.record.get("target_id"))
        if distinct and first.score - second.score < ambiguity_margin:
            return []
    return candidates[:max_records]
