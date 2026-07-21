"""Local courtesy confirmation; never an authorization decision."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from .stage_snapshot import AllowedAction, StageSnapshot


@dataclass(frozen=True)
class ConfirmationEvidence:
    project_id: str
    action_name: str
    snapshot_version: str
    confirmed_at: str
    method: str
    statement_hash: str

    def payload(self) -> dict[str, str | bool]:
        return {
            "confirmed": True,
            "project_id": self.project_id,
            "action_name": self.action_name,
            "snapshot_version": self.snapshot_version,
            "confirmed_at": self.confirmed_at,
            "method": self.method,
            "statement_hash": self.statement_hash,
        }


class ConfirmationPolicy:
    _ALIASES = {
        "commit_package": "package_commitment",
        "package_commit": "package_commitment",
        "select_package": "package_commitment",
        "approve_pointer_uncertain": "approve_uncertain_pointer",
        "uncertain_pointer_approval": "approve_uncertain_pointer",
        "generate_orb_pack": "generate_entitled_orbpack",
        "generate_entitled_orb_pack": "generate_entitled_orbpack",
        "build_entitled_orbpack": "generate_entitled_orbpack",
    }

    @classmethod
    def normalize_action_name(cls, value: str) -> str:
        """Normalize casing/separators for courtesy policy only, never wire submission."""
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value.strip())
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", separated).strip("_").lower()
        return cls._ALIASES.get(normalized, normalized)

    def requires_confirmation(self, action: AllowedAction) -> bool:
        normalized = self.normalize_action_name(action.name)
        sensitive = (
            ("package" in normalized and any(term in normalized for term in ("commit", "commitment", "select", "change")))
            or ("tier" in normalized and any(term in normalized for term in ("commit", "select", "change", "upgrade", "downgrade")))
            or ("terms" in normalized and any(term in normalized for term in ("accept", "agree")))
            or "signature" in normalized
            or normalized.startswith("sign_")
            or "checkout" in normalized
            or ("personal" in normalized and any(term in normalized for term in ("submit", "share", "send")))
            or ("pointer" in normalized and any(term in normalized for term in ("approve", "accept", "confirm")))
            or ("orbpack" in normalized and any(term in normalized for term in ("generate", "build", "create")))
            or ("install" in normalized and "managed" in normalized)
            or "launch_verification" in normalized
            or ("live" in normalized and any(term in normalized for term in ("mark", "set", "publish", "launch")))
        )
        return action.confirmation_required or sensitive

    def confirm(
        self,
        snapshot: StageSnapshot,
        action_name: str,
        accepted: bool,
        statement: str,
        method: str = "explicit_yes",
    ) -> ConfirmationEvidence:
        action = snapshot.action(action_name)
        if not action:
            raise ValueError("action is not governor-approved in this snapshot")
        if not accepted:
            raise ValueError("explicit confirmation was not given")
        statement = statement.strip()
        if not statement:
            raise ValueError("confirmation statement is required")
        return ConfirmationEvidence(
            project_id=snapshot.project_id,
            action_name=action.name,
            snapshot_version=snapshot.snapshot_version,
            confirmed_at=datetime.now(timezone.utc).isoformat(),
            method=method,
            statement_hash=hashlib.sha256(statement.encode("utf-8")).hexdigest(),
        )

    def validate(self, snapshot: StageSnapshot, action: AllowedAction, evidence: ConfirmationEvidence | None) -> None:
        if not self.requires_confirmation(action):
            return
        if evidence is None:
            raise ValueError("explicit customer confirmation is required")
        if (
            evidence.project_id != snapshot.project_id
            or evidence.action_name != action.name
            or evidence.snapshot_version != snapshot.snapshot_version
        ):
            raise ValueError("confirmation evidence does not match the current action snapshot")
