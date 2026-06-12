from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Orb Weaver - Website ORB Intelligence Engine"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    ORB_WEAVER_SUBSTRATE_ROOT: str = "R:\\R_Drive_Substrate\\orb_weaver"
    PUBLIC_BASE_URL: str = "https://orbweaver.spruked.com"

    # Database
    DATABASE_URL: str = "sqlite:///./data/orb_weaver.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Admin
    ADMIN_TOKEN: Optional[str] = None

    # Checkout
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_API_VERSION: str = "2026-02-25.clover"
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_API_BASE: str = "https://api-m.paypal.com"

    # Google Analytics
    GA4_PROPERTY_ID: Optional[str] = None
    GA4_CREDENTIALS_PATH: Optional[str] = None
    GA4_SCOPES: List[str] = ["https://www.googleapis.com/auth/analytics.readonly"]

    # Crawler
    CRAWL_MAX_PAGES: int = 1000
    CRAWL_DELAY: float = 1.0
    CRAWL_TIMEOUT: int = 30
    CRAWL_USER_AGENT: str = "Orb-Weaver/1.0"
    CRAWL_RESPECT_ROBOTS: bool = True
    CRAWL_MAX_DEPTH: int = 5
    LOCAL_LLM_URL: Optional[str] = None
    LOCAL_LLM_MODEL: Optional[str] = None

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Audit Thresholds
    MIN_PAGE_SPEED_SCORE: int = 50
    MAX_TITLE_LENGTH: int = 60
    MAX_META_DESC_LENGTH: int = 160
    MIN_CONTENT_WORDS: int = 300

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"dev", "development"}:
                return True
        return value

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
