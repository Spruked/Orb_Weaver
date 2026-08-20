"""
orb/vault/orb_assistant/query_router.py
Intent classification and vault routing.
Determines which vault layer to query first.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple

from ..shared.types import IntentType, ResolutionResult


class QueryRouter:
    """
    Routes queries to appropriate vault subsystem.
    Lightweight intent classification for routing decisions.
    """

    INTENT_KEYWORDS: Dict[IntentType, List[str]] = {
        IntentType.PRODUCT_PRICE: [
            "price", "cost", "how much", "what does it cost", "pricing",
            "cheap", "expensive", "discount", "sale"
        ],
        IntentType.PRODUCT_AVAILABILITY: [
            "in stock", "available", "when will", "backorder", "sold out",
            "ship", "delivery", "when can i get"
        ],
        IntentType.PRODUCT_INFO: [
            "spec", "dimension", "weight", "size", "color", "material",
            "what is", "tell me about", "details"
        ],
        IntentType.CATEGORY_BROWSE: [
            "do you have", "what kind of", "show me", "category",
            "types of", "looking for", "browse"
        ],
        IntentType.SERVICE_INQUIRY: [
            "service", "repair", "warranty", "support", "help with",
            "installation", "maintenance"
        ],
        IntentType.POLICY_QUESTION: [
            "policy", "return", "refund", "exchange", "cancel",
            "privacy", "terms", "shipping policy"
        ],
        IntentType.CONTACT_INFO: [
            "phone", "email", "contact", "reach", "call", "talk to",
            "speak with", "customer service"
        ],
        IntentType.HOURS_LOCATION: [
            "hours", "open", "close", "location", "address", "where",
            "find you", "directions", "when are you"
        ],
        IntentType.COMPARISON: [
            "compare", "difference between", "vs", "versus", "better",
            "which one", "or"
        ],
        IntentType.RECOMMENDATION: [
            "recommend", "suggest", "best", "top", "good", "what should",
            "help me choose"
        ],
    }

    @classmethod
    def classify_intent(cls, query_text: str) -> Tuple[IntentType, float]:
        query_lower = query_text.lower()
        best_intent = IntentType.GENERAL
        best_score = 0.0

        for intent, keywords in cls.INTENT_KEYWORDS.items():
            score = 0.0
            for kw in keywords:
                if kw in query_lower:
                    score += 1.0
            if score > best_score:
                best_score = score
                best_intent = intent

        # Normalize confidence
        confidence = min(1.0, best_score / 3.0) if best_score > 0 else 0.0
        return best_intent, confidence

    @classmethod
    def extract_entities(cls, query_text: str, catalog_names: Optional[List[str]] = None) -> List[str]:
        """
        Extract entity mentions from query.
        Simple keyword matching against known catalog items.
        """
        entities = []
        query_lower = query_text.lower()

        if catalog_names:
            for name in catalog_names:
                if name.lower() in query_lower:
                    entities.append(name)

        return entities

    @classmethod
    def route(cls, query_text: str, catalog_names: Optional[List[str]] = None) -> Tuple[IntentType, List[str], float]:
        """
        Full routing: classify intent + extract entities.
        Returns (intent, entities, confidence).
        """
        intent, conf = cls.classify_intent(query_text)
        entities = cls.extract_entities(query_text, catalog_names)
        return intent, entities, conf
