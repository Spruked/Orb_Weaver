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
    CALI_CRM_URL: str = "http://localhost:16610"
    CALI_CRM_SUBSTRATE_ROOT: str = "R:\\R_Drive_Substrate\\cali_crm"

    # Database
    DATABASE_URL: str = "sqlite:///./data/orb_weaver.db"
    REDIS_URL: str = "redis://redis:6379/0"

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
    LOCAL_LLM_TIMEOUT_SECONDS: float = 60.0
    LOCAL_LLM_KEEP_ALIVE: str = "30m"
    LOCAL_LLM_NUM_CTX: int = 512
    LOCAL_LLM_NUM_PREDICT: int = 32
    LOCAL_LLM_TEMPERATURE: float = 0.35
    FASTER_WHISPER_STT_URL: str = "http://127.0.0.1:9000/stt"
    ORB_ASSISTANT_ROOT: str = "../Orb_Assistant"
    ORB_TTS_CACHE_DIR: str = "data/tts_cache"
    ORB_TTS_TIMEOUT_SECONDS: float = 45.0
    ORB_TTS_QWEN_URL: Optional[str] = None
    ORB_TTS_QWEN_API_KEY: Optional[str] = None
    ORB_TTS_QWEN_MODEL: str = "qwen-tts"
    ORB_TTS_QWEN_VOICE: str = "OrbWeaver"
    ORB_TTS_QWEN_LANGUAGE: str = "English"
    ORB_TTS_QWEN_INSTRUCT: str = "A warm, confident adult male assistant voice. Clear, calm, lightly theatrical, friendly, and concise."
    ORB_TTS_QWEN_FORMAT: str = "wav"
    ORB_TTS_QWEN_PAYLOAD_MODE: str = "qwen-custom"
    ORB_TTS_KOKORO_URL: str = "http://127.0.0.1:8880/speak"
    ORB_TTS_KOKORO_API_KEY: Optional[str] = None
    ORB_TTS_KOKORO_MODEL: str = "kokoro"
    ORB_TTS_KOKORO_VOICE: str = "am_echo"
    ORB_TTS_KOKORO_FORMAT: str = "wav"
    ORB_TTS_KOKORO_PAYLOAD_MODE: str = "kokoro-direct"

    # Browser review / install verification
    CHROME_DEVTOOLS_ENABLED: bool = False
    CHROME_DEVTOOLS_PUBLIC_ENABLED: bool = False
    CHROME_DEVTOOLS_CLI: str = "chrome-devtools-mcp"
    CHROME_DEVTOOLS_OUTPUT_ROOT: str = "browser_reviews"
    CHROME_DEVTOOLS_TIMEOUT_SECONDS: int = 60
    CHROME_DEVTOOLS_START_ARGS: List[str] = []
    CHROME_DEVTOOLS_BROWSER_START_CMD: Optional[str] = None
    ORB_DESKTOP_MCP_ENABLED: bool = True
    ORB_DESKTOP_MCP_ROOT: str = "/mnt/r/mpc_server"
    ORB_DESKTOP_MCP_PYTHON: str = "python3.12"
    ORB_DESKTOP_MCP_TIMEOUT_SECONDS: float = 20.0
    ORB_DESKTOP_MCP_URL: Optional[str] = None
    ORB_DESKTOP_MCP_TOKEN: Optional[str] = None

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
