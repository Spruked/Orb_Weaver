"""Deterministic retention policy for Website ORB memory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


RETENTION_POLICY_VERSION = "account-memory-policy.v1"
CONSENT_VERSION = "account-memory-consent.v1"

# Stable machine-readable types. Customer-facing consent copy should be
# generated from this registry rather than from free-form descriptions.
RETENTION_ALLOWLIST: Mapping[str, Mapping[str, object]] = {
    "preferred_name": {"label": "Preferred name", "inference_allowed": False},
    "communication_preference": {"label": "Communication preference", "inference_allowed": False},
    "project_context": {"label": "Project context", "inference_allowed": False},
    "scan_context": {"label": "Scan context", "inference_allowed": False},
    "orb_entitlement": {"label": "ORB entitlement", "inference_allowed": False},
    "explicit_preference": {"label": "Explicit preference", "inference_allowed": False},
}

EXPLICIT_SOURCES = frozenset({"explicit_user_preference", "account_user_action"})


@dataclass(frozen=True)
class MemoryCandidate:
    memory_type: str
    value: str
    source: str
    account_id: str
    consent_version: str
    inferred: bool = False


@dataclass(frozen=True)
class MemoryAuthorization:
    memory_type: str
    account_id: str
    consent_version: str
    retention_policy_version: str = RETENTION_POLICY_VERSION


class MemoryPolicyRejection(ValueError):
    """Raised when a candidate fails a deterministic retention gate."""


def authorize_account_memory(
    candidate: MemoryCandidate,
    *,
    allowed_types: frozenset[str] | set[str] | None = None,
) -> MemoryAuthorization:
    """Authorize one candidate or fail closed."""
    memory_type = candidate.memory_type.strip().lower()
    if not candidate.account_id.strip():
        raise MemoryPolicyRejection("Account ownership is required")
    if memory_type not in RETENTION_ALLOWLIST:
        raise MemoryPolicyRejection("Memory type is not on the retention allowlist")
    if allowed_types is not None and memory_type not in allowed_types:
        raise MemoryPolicyRejection("Account consent does not allow this memory type")
    if candidate.consent_version != CONSENT_VERSION:
        raise MemoryPolicyRejection("Consent version is missing or outdated")
    if candidate.inferred or candidate.source.strip().lower() not in EXPLICIT_SOURCES:
        raise MemoryPolicyRejection("Inferred memory requires an explicit account action")
    if not candidate.value.strip():
        raise MemoryPolicyRejection("Memory value is required")
    return MemoryAuthorization(memory_type, candidate.account_id, candidate.consent_version)


def allowlist_document() -> dict[str, object]:
    """Return the canonical registry for policy/consent UI generation."""
    return {
        "retention_policy_version": RETENTION_POLICY_VERSION,
        "consent_version": CONSENT_VERSION,
        "memory_types": [
            {"type": memory_type, **dict(metadata)}
            for memory_type, metadata in RETENTION_ALLOWLIST.items()
        ],
    }
