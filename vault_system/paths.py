"""Shared path authority for Orb Weaver's single repository vault."""

from __future__ import annotations

import os
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
_WINDOWS_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def _configured_vault_root() -> Path | None:
    value = os.getenv("ORB_WEAVER_VAULT_ROOT", "").strip()
    if not value or (os.name != "nt" and _WINDOWS_DRIVE_PATH.match(value)):
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


VAULT_ROOT = _configured_vault_root() or (REPO_ROOT / "vault_system")
CLIENTS_ROOT = VAULT_ROOT / "clients"
DATABASES_ROOT = VAULT_ROOT / "databases"
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
APRIORI_ROOT = VAULT_ROOT / "apriori"
POSTERIORI_ROOT = VAULT_ROOT / "posteriori"
TPC_ROOT = LONG_TERM_MEMORY_ROOT / "tpc"
WORKER_VAULTS_ROOT = COGNITION_ROOT / "workers"
REPORTS_ROOT = VAULT_ROOT / "reports"
INDEXES_ROOT = VAULT_ROOT / "indexes"
MANIFESTS_ROOT = VAULT_ROOT / "manifests"
SCHEMAS_ROOT = VAULT_ROOT / "schemas"
INTEGRATIONS_ROOT = VAULT_ROOT / "integrations"
RUNTIME_ROOT = VAULT_ROOT / "runtime"
TTS_CACHE_ROOT = RUNTIME_ROOT / "tts_cache"
BROWSER_REVIEWS_ROOT = RUNTIME_ROOT / "browser_reviews"
STATE_ROOT = RUNTIME_ROOT / "state"
LOGS_ROOT = RUNTIME_ROOT / "logs"
BACKUPS_ROOT = VAULT_ROOT / "backups"


def normalize_client_key(domain_or_url: str) -> str:
    normalized = (domain_or_url or "unknown-client").strip().lower()
    normalized = re.sub(r"^https?://", "", normalized)
    normalized = normalized.split("/", 1)[0]
    normalized = re.sub(r"[^a-z0-9._-]+", "-", normalized).strip(".-")
    return normalized or "unknown-client"


def client_root(domain_or_url: str) -> Path:
    """Return the isolated client vault inside the one storage authority."""
    return CLIENTS_ROOT / normalize_client_key(domain_or_url)


def worker_vault(worker_name: str) -> Path:
    """Return a cognition worker's namespace inside the canonical vault."""
    safe_name = re.sub(r"[^a-z0-9._-]+", "-", worker_name.lower()).strip(".-")
    return WORKER_VAULTS_ROOT / (safe_name or "unknown-worker")
