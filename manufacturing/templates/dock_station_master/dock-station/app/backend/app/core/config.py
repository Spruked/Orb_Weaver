"""ORB Dock Station — Configuration"""
import os
from pydantic_settings import BaseSettings

def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}

class Settings(BaseSettings):
    APP_NAME: str = "ORB Dock Station Authority"
    VERSION: str = "2.0.0"
    DOCK_STATION_DEBUG: str = os.getenv("DOCK_STATION_DEBUG", "false")

    @property
    def DEBUG(self) -> bool:
        return _as_bool(self.DOCK_STATION_DEBUG)

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "orb-dock-station-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000", "app://.*"]

    # Data paths
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    PROFILES_PATH: str = os.getenv("PROFILES_PATH", "./data/profiles.json")
    VERSIONS_PATH: str = os.getenv("VERSIONS_PATH", "./data/versions.json")
    CONVERSATIONS_PATH: str = os.getenv("CONVERSATIONS_PATH", "./data/conversations.json")
    STATS_PATH: str = os.getenv("STATS_PATH", "./data/statistics.json")
    DIAGNOSTICS_PATH: str = os.getenv("DIAGNOSTICS_PATH", "./data/diagnostics.json")

    # Gateway
    GATEWAY_URL: str = os.getenv("GATEWAY_URL", "http://localhost:16520")

    class Config:
        env_file = ".env"

settings = Settings()
