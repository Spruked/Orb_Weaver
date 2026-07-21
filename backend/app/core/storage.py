from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

from app.core.config import settings


IMMUTABLE_STORAGE_LAW = (
    "All persisted Orb Weaver data—including scans, raw evidence, customer, "
    "checkout, payment, entitlement, and workflow records—must be written "
    "beneath and read authoritatively from the sole vault_system root."
)


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
    or DEFAULT_VAULT_ROOT
)

CLIENTS_ROOT = VAULT_ROOT / "clients"
DATABASES_ROOT = VAULT_ROOT / "databases"
POSTERIORI_ROOT = VAULT_ROOT / "posteriori"
APRIORI_ROOT = VAULT_ROOT / "apriori"
IDENTITY_ROOT = VAULT_ROOT / "identity"
PERMISSIONS_ROOT = VAULT_ROOT / "permissions"
SITE_OR_ENVIRONMENT_DATA_ROOT = VAULT_ROOT / "site_or_environment_data"
CLIENT_OR_OWNER_DATA_ROOT = VAULT_ROOT / "client_or_owner_data"
SHORT_TERM_MEMORY_ROOT = VAULT_ROOT / "short_term_memory"
LONG_TERM_MEMORY_ROOT = VAULT_ROOT / "long_term_memory"
WORKFLOW_STATE_ROOT = VAULT_ROOT / "workflow_state"
OBSERVATIONS_ROOT = VAULT_ROOT / "observations"
VERIFIED_OUTCOMES_ROOT = VAULT_ROOT / "verified_outcomes"
RUNTIME_STATE_ROOT = VAULT_ROOT / "runtime_state"
PERSISTENT_CACHE_ROOT = VAULT_ROOT / "persistent_cache"
AUDIT_ROOT = VAULT_ROOT / "audit"
COGNITION_ROOT = OBSERVATIONS_ROOT / "cognition"
TPC_ROOT = LONG_TERM_MEMORY_ROOT / "tpc"
WORKER_VAULTS_ROOT = COGNITION_ROOT / "workers"
REPORTS_ROOT = VAULT_ROOT / "reports"
INDEXES_ROOT = VAULT_ROOT / "indexes"
GLOBAL_INTELLIGENCE_ROOT = INDEXES_ROOT / "global_intelligence"
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
    IDENTITY_ROOT,
    PERMISSIONS_ROOT,
    SITE_OR_ENVIRONMENT_DATA_ROOT,
    CLIENT_OR_OWNER_DATA_ROOT,
    SHORT_TERM_MEMORY_ROOT,
    LONG_TERM_MEMORY_ROOT,
    WORKFLOW_STATE_ROOT,
    OBSERVATIONS_ROOT,
    VERIFIED_OUTCOMES_ROOT,
    RUNTIME_STATE_ROOT,
    PERSISTENT_CACHE_ROOT,
    AUDIT_ROOT,
    COGNITION_ROOT,
    TPC_ROOT,
    WORKER_VAULTS_ROOT,
    REPORTS_ROOT,
    INDEXES_ROOT,
    GLOBAL_INTELLIGENCE_ROOT,
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


def require_vault_path(path: Path | str, purpose: str = "persistent data") -> Path:
    """Fail closed when a durable artifact is directed outside the sole Vault."""
    resolved = Path(path).expanduser().resolve()
    vault = VAULT_ROOT.resolve()
    if resolved != vault and vault not in resolved.parents:
        raise ValueError(f"{purpose} must remain inside the canonical vault_system: {resolved}")
    return resolved


def ensure_vault_layout(extra_directories: Iterable[Path] = ()) -> None:
    for directory in (*CANONICAL_VAULT_DIRECTORIES, *tuple(extra_directories)):
        require_vault_path(directory, "Vault directory").mkdir(parents=True, exist_ok=True)


def canonical_database_url(configured_url: str | None) -> str:
    """Force the authoritative application database into Vault databases."""
    value = (configured_url or "").strip()
    if value and not value.startswith("sqlite"):
        raise ValueError("External application databases violate the immutable Vault storage law")
    if value in {"sqlite:///:memory:", "sqlite+pysqlite:///:memory:"}:
        raise ValueError("In-memory application databases violate the immutable Vault storage law")

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
