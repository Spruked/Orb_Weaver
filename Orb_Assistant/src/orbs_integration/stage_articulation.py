"""Language-only rendering of sanitized stage snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping, Tuple

from .stage_snapshot import AllowedAction, StageSnapshot, thaw_json


@dataclass(frozen=True)
class StageArticulation:
    spoken_text: str
    actions: Tuple[AllowedAction, ...]
    approved_destination_route: str | None


class StageArticulator:
    """Keeps model-authored language separate from executable actions."""

    def __init__(self, language_model: Callable[[Mapping[str, Any]], str] | None = None):
        self._language_model = language_model

    def model_payload(self, snapshot: StageSnapshot) -> Mapping[str, Any]:
        """The only payload that may be sent to an articulation model."""
        return MappingProxyType({
            "project_id": snapshot.project_id,
            "project_display_name": snapshot.project_display_name,
            "current_stage": snapshot.current_stage,
            "stage_status": snapshot.stage_status,
            "completed_stages": list(snapshot.completed_stages),
            "blocking_reason": snapshot.blocking_reason,
            "customer_action_required": snapshot.customer_action_required,
            "allowed_actions": [dict(action.public_payload()) for action in snapshot.allowed_actions],
            "next_recommended_action": snapshot.next_recommended_action,
            "approved_stage_evidence": thaw_json(snapshot.approved_stage_evidence),
            "approved_destination_route": snapshot.approved_destination_route,
            "snapshot_version": snapshot.snapshot_version,
            "updated_at": snapshot.updated_at,
        })

    def articulate(self, snapshot: StageSnapshot) -> StageArticulation:
        payload = self.model_payload(snapshot)
        if self._language_model:
            spoken = str(self._language_model(payload)).strip()
        else:
            spoken = self._deterministic_explanation(snapshot)
        if not spoken:
            spoken = self._deterministic_explanation(snapshot)
        # Actions always come from the snapshot, never from generated language.
        return StageArticulation(spoken, snapshot.allowed_actions, snapshot.approved_destination_route)

    @staticmethod
    def _deterministic_explanation(snapshot: StageSnapshot) -> str:
        parts = [f"{snapshot.project_display_name} is at {snapshot.current_stage} with status {snapshot.stage_status}."]
        if snapshot.blocking_reason:
            parts.append(f"It is blocked because {snapshot.blocking_reason}.")
        if snapshot.customer_action_required:
            parts.append(snapshot.customer_action_required)
        if snapshot.next_recommended_action:
            action = snapshot.action(snapshot.next_recommended_action)
            if action:
                parts.append(f"The approved next action is {action.label}.")
        return " ".join(parts)
