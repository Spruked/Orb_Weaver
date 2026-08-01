"""
Context & Correspondence Orchestrator - Configuration
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class CCOConfig(BaseSettings):
    """Configuration for Context & Correspondence Orchestrator system."""

    # Storage
    HANDLE_STORE_PATH: str = "./data/handles"
    DEFAULT_TTL_SECONDS: int = 86400  # 24 hours
    MAX_HANDLES_PER_USER: int = 100

    # Compression
    DEFAULT_TARGET_BUDGET: int = 8000
    MIN_TARGET_BUDGET: int = 100
    MAX_TARGET_BUDGET: int = 32000
    CHUNK_SIZE_TOKENS: int = 512
    CHUNK_OVERLAP_TOKENS: int = 50

    # Strategy thresholds
    SUMMARY_MAX_SOURCE_TOKENS: int = 500000
    SEMANTIC_MAX_SOURCE_TOKENS: int = 2000000
    HIERARCHICAL_MIN_SOURCE_TOKENS: int = 100000

    # Hierarchical levels
    HIERARCHY_LEVELS: int = 4
    LEVEL0_CHUNK_SIZE: int = 2000    # Raw sections
    LEVEL1_CHUNK_SIZE: int = 8000    # Topic summaries  
    LEVEL2_CHUNK_SIZE: int = 32000   # Domain summaries
    LEVEL3_MAX_TOKENS: int = 1250    # Working crystal

    # Semantic retrieval
    TOP_K_RETRIEVE: int = 5
    SIMILARITY_THRESHOLD: float = 0.3

    # LLM (abstracted - can plug into Qwen, OpenAI, etc.)
    LLM_PROVIDER: str = "abstract"  # "openai", "anthropic", "qwen", "abstract"
    LLM_MODEL: str = "default"
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    LLM_MAX_TOKENS: int = 4000
    LLM_TEMPERATURE: float = 0.2

    # ORBS Integration
    ORBS_VAULT_PATH: Optional[str] = None
    ORBS_CONFIDENCE_CAP: float = 0.75

    # Canary testing
    CANARY_SAMPLE_SIZE: int = 20
    CANARY_FACT_THRESHOLD: float = 0.7

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080
    API_WORKERS: int = 1

    class Config:
        env_prefix = "CCO_"
        case_sensitive = True


# Global config instance
config = CCOConfig()
