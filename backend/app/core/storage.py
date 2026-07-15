from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

from app.core.config import settings


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_VAULT_ROOT = REPO_ROOT / "vault_system"
_WINDOWS_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def _resolve_storage_root(raw_value: str | None) -> Path | None:
    """Resolve configured storage without creating Windows-looking folders on POSIX."""
    value = (raw_value or "").strip()
    if not value:
        return None

    if os.name != "nt" and _WINDOWS_DRIVE_PATH.match(value):
        return None

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path.resolve()


VAULT_ROOT = (
    _resolve_storage_root(settings.ORB_WEAVER_VAULT_ROOT)
    or _resolve_storage_root(settings.ORB_WEAVER_SUBSTRATE_ROOT)
    or DEFAULT_VAULT_ROOT
)

CLIENTS_ROOT = VAULT_ROOT / "clients"
DATABASES_ROOT = VAULT_ROOT / "databases"
POSTERIORI_ROOT = VAULT_ROOT / "posteriori"
APRIORI_ROOT = VAULT_ROOT / "apriori"
REPORTS_ROOT = VAULT_ROOT / "reports"
INDEXES_ROOT = VAULT_ROOT / "indexes"
MANIFESTS_ROOT = VAULT_ROOT / "manifests"
SCHEMAS_ROOT = VAULT_ROOT / "schemas"
INTEGRATIONS_ROOT = VAULT_ROOT / "integrations"
CALI_CRM_ROOT = INTEGRATIONS_ROOT / "cali_crm"
RUNTIME_ROOT = VAULT_ROOT / "runtime"
TTS_CACHE_ROOT = RUNTIME_ROOT / "tts_cache"
BROWSER_REVIEWS_ROOT = RUNTIME_ROOT / "browser_reviews"
STATE_ROOT = RUNTIME_ROOT / "state"
LOGS_ROOT = RUNTIME_ROOT / "logs"
BACKUPS_ROOT = VAULT_ROOT / "backups"


CANONICAL_VAULT_DIRECTORIES: tuple[Path, ...] = (
    VAULT_ROOT,
    CLIENTS_ROOT,
    DATABASES_ROOT,
    POSTERIORI_ROOT,
    APRIORI_ROOT,
    REPORTS_ROOT,
    INDEXES_ROOT,
    MANIFESTS_ROOT,
    SCHEMAS_ROOT,
    INTEGRATIONS_ROOT,
    CALI_CRM_ROOT,
    RUNTIME_ROOT,
    TTS_CACHE_ROOT,
    BROWSER_REVIEWS_ROOT,
    STATE_ROOT,
    LOGS_ROOT,
    BACKUPS_ROOT,
)


def ensure_vault_layout(extra_directories: Iterable[Path] = ()) -> None:
    for directory in (*CANONICAL_VAULT_DIRECTORIES, *tuple(extra_directories)):
        directory.mkdir(parents=True, exist_ok=True)


def canonical_database_url(configured_url: str | None) -> str:
    """Keep non-SQLite services unchanged; force every SQLite file into the vault."""
    value = (configured_url or "").strip()
    if value and not value.startswith("sqlite"):
        return value
    if value in {"sqlite:///:memory:", "sqlite+pysqlite:///:memory:"}:
        return value

    database_name = "orb_weaver.db"
    if value and "/" in value:
        candidate = value.rsplit("/", 1)[-1].split("?", 1)[0].strip()
        if candidate and candidate != ":memory:":
            database_name = Path(candidate).name

    database_path = (DATABASES_ROOT / database_name).resolve()
    return f"sqlite:///{database_path.as_posix()}"


def client_root(domain: str) -> Path:
    normalized = (domain or "unknown-client").strip().lower()
    normalized = re.sub(r"^https?://", "", normalized)
    normalized = normalized.split("/", 1)[0]
    normalized = re.sub(r"[^a-z0-9._-]+", "-", normalized).strip(".-")
    return CLIENTS_ROOT / (normalized or "unknown-client")
