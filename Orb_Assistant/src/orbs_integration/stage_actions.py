"""Submission gate for governor-approved actions only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .confirmation_policy import ConfirmationEvidence, ConfirmationPolicy
from .stage_client import OrbWeaverStageClient, StageActionRejected, StageContractError
from .stage_snapshot import StageSnapshot


@dataclass(frozen=True)
class ActionSubmissionRejected(RuntimeError):
    message: str
    fresh_snapshot: StageSnapshot

    def __str__(self) -> str:
        return self.message


class StageActionService:
    def __init__(self, client: OrbWeaverStageClient, confirmation_policy: Optional[ConfirmationPolicy] = None):
        self._client = client
        self._confirmation_policy = confirmation_policy or ConfirmationPolicy()

    def submit(
        self,
        snapshot: StageSnapshot,
        action_name: str,
        idempotency_key: str,
        confirmation: Optional[ConfirmationEvidence] = None,
        inputs: Optional[Mapping[str, Any]] = None,
    ) -> StageSnapshot:
        action = snapshot.action(action_name)
        if not action:
            raise ValueError("action is not present in allowed_actions")
        self._confirmation_policy.validate(snapshot, action, confirmation)
        provided_inputs = dict(inputs or {})
        unexpected = set(provided_inputs) - set(action.allowed_input_fields)
        if unexpected:
            raise ValueError(f"action inputs are not approved by the snapshot: {sorted(unexpected)}")
        payload: dict[str, Any] = {
            "project_id": snapshot.project_id,
            "action": action.name,
            "expected_stage": snapshot.current_stage,
            "snapshot_version": snapshot.snapshot_version,
            "inputs": provided_inputs,
        }
        if snapshot.build_order_id:
            payload["build_order_id"] = snapshot.build_order_id
        if confirmation:
            payload["confirmation_evidence"] = confirmation.payload()

        try:
            return self._client.submit_action(payload, idempotency_key)
        except (StageActionRejected, StageContractError) as exc:
            # Never infer a transition. Refresh even after rejection or malformed action response.
            fresh = self._client.current_stage(snapshot.project_id)
            raise ActionSubmissionRejected(str(exc), fresh) from exc

