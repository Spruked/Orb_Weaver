"""
orb/vault/shared/constants.py
Operational constants and thresholds for both vault systems.
"""

from __future__ import annotations


class VaultConstants:
    """Shared constants — single source of truth for thresholds."""

    # -----------------------------------------------------------------------
    # A Posteriori — Experience & Learning
    # -----------------------------------------------------------------------

    # Verification
    VERIFICATION_MIN_SIGNALS = 2
    VERIFICATION_MIN_CONFIDENCE = 0.60
    VERIFICATION_MAX_AGE_DAYS = 14  # Candidate expires if not verified

    # Promotion
    PROMOTION_MIN_SUCCESS_STREAK = 2
    PROMOTION_MIN_ACCESS_COUNT = 3

    # Reinforcement
    REINFORCEMENT_DELTA = 0.03
    REINFORCEMENT_MAX_TOTAL = 0.15
    SUCCESS_STREAK_BONUS = 0.02

    # Pruning
    PRUNE_CONFIDENCE_THRESHOLD = 0.25
    PRUNE_STALENESS_DAYS = 90
    PRUNE_MIN_ACCESS_COUNT = 3
    PRUNE_WEAKEN_THRESHOLD = 0.40

    # Compression
    COMPRESSION_SIMILARITY_THRESHOLD = 0.85
    COMPRESSION_MIN_AGE_DAYS = 30

    # Ledger
    LEDGER_MAX_ENTRIES_PER_FILE = 10000
    LEDGER_RETENTION_DAYS = 365

    # -----------------------------------------------------------------------
    # A Priori — Settled Truth
    # -----------------------------------------------------------------------

    # Catalog
    CATALOG_CONFIDENCE_BASE = 0.85
    CATALOG_OWNER_VERIFIED_BONUS = 0.10

    # Ontology
    ONTOLOGY_INFERENCE_DEPTH = 3
    ONTOLOGY_RELATION_MIN_CONFIDENCE = 0.70

    # Policy
    POLICY_DEFAULT_PRIORITY = 5
    POLICY_MAX_PRIORITY = 1

    # QA
    QA_CONFIDENCE_BASE = 0.90
    QA_PATTERN_MATCH_THRESHOLD = 0.80

    # -----------------------------------------------------------------------
    # Query Routing
    # -----------------------------------------------------------------------

    # Intent types that should route to A Priori catalog first
    CATALOG_INTENTS = [
        "PRODUCT_PRICE",
        "PRODUCT_AVAILABILITY", 
        "PRODUCT_INFO",
        "CATEGORY_BROWSE",
        "SERVICE_INQUIRY",
        "HOURS_LOCATION",
        "CONTACT_INFO",
    ]

    # Confidence thresholds for routing decisions
    ROUTE_APRIORI_MIN_CONFIDENCE = 0.75
    ROUTE_APOSTERIORI_MIN_CONFIDENCE = 0.65
    ROUTE_LLM_FALLBACK = 0.50

    # -----------------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------------

    SAVE_INTERVAL_SECONDS = 300
    BACKUP_COUNT = 5

    # -----------------------------------------------------------------------
    # Governance
    # -----------------------------------------------------------------------

    MAX_CONFIDENCE_CAP = 0.95
    TENSION_CONFIDENCE_CAP = 0.75
    DEFAULT_CONFIDENCE_CAP = 0.95
