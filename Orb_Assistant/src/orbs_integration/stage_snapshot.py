"""Immutable, stage-scoped sanitization boundary for Orb Weaver responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple


SUPPORTED_SCHEMA = "orb_weaver.orbs_stage_snapshot.v1"


class StageSnapshotError(ValueError):
    """The authoritative response is malformed or contract-incompatible."""


def _required_text(source: Mapping[str, Any], field: str) -> str:
    value = source.get(field)
    if not isinstance(value, (str, int)) or not str(value).strip():
        raise StageSnapshotError(f"{field} must be a non-empty string")
    return str(value).strip()


def _optional_text(source: Mapping[str, Any], field: str) -> Optional[str]:
    value = source.get(field)
    if value is None:
        return None
    if not isinstance(value, (str, int)) or not str(value).strip():
        raise StageSnapshotError(f"{field} must be a non-empty string when present")
    return str(value).strip()


def _freeze_json(value: Any, path: str = "approved_evidence") -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item, f"{path}.{key}") for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, f"{path}[]") for item in value)
    raise StageSnapshotError(f"{path} contains a non-JSON value")


def thaw_json(value: Any) -> Any:
    """Return a plain JSON-compatible copy without exposing mutable snapshot data."""
    if isinstance(value, Mapping):
        return {key: thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw_json(item) for item in value]
    return value


@dataclass(frozen=True)
class AllowedAction:
    name: str
    display_label: str
    description: Optional[str]
    destination_route: Optional[str]
    confirmation_required: bool
    confirmation_prompt: Optional[str]
    confirmation_kind: Optional[str]
    allowed_input_fields: Tuple[str, ...]
    reason_available: Optional[str]
    idempotency_required: bool

    @classmethod
    def from_authoritative(cls, raw: Mapping[str, Any]) -> "AllowedAction":
        if not isinstance(raw, Mapping):
            raise StageSnapshotError("allowed_actions entries must be objects")
        name = _required_text(raw, "name")
        display_label = _required_text(raw, "display_label")
        destination = _optional_text(raw, "destination_route")
        if destination and raw.get("destination_verified") is not True:
            raise StageSnapshotError(f"action {name} has an unverified destination_route")
        input_fields = raw.get("allowed_input_fields") or []
        if not isinstance(input_fields, list) or not all(isinstance(item, str) and item.strip() for item in input_fields):
            raise StageSnapshotError(f"action {name} has invalid allowed_input_fields")
        return cls(
            name=name,
            display_label=display_label,
            description=_optional_text(raw, "description"),
            destination_route=destination,
            confirmation_required=bool(raw.get("confirmation_required", False)),
            confirmation_prompt=_optional_text(raw, "confirmation_prompt"),
            confirmation_kind=_optional_text(raw, "confirmation_kind"),
            allowed_input_fields=tuple(dict.fromkeys(item.strip() for item in input_fields)),
            reason_available=_optional_text(raw, "reason_available"),
            idempotency_required=bool(raw.get("idempotency_required", True)),
        )

    @property
    def label(self) -> str:
        """Compatibility accessor for embodiment code; wire schema uses display_label."""
        return self.display_label

    def public_payload(self) -> Mapping[str, Any]:
        return MappingProxyType({
            "name": self.name,
            "display_label": self.display_label,
            "description": self.description,
            "destination_route": self.destination_route,
            "confirmation_required": self.confirmation_required,
            "confirmation_prompt": self.confirmation_prompt,
            "reason_available": self.reason_available,
        })


@dataclass(frozen=True)
class StageSnapshot:
    schema: str
    snapshot_version: str
    project_id: str
    project_display_name: str
    current_stage: str
    stage_status: str
    completed_stages: Tuple[str, ...]
    blocking_reason: Optional[str]
    customer_action_required: Optional[str]
    allowed_actions: Tuple[AllowedAction, ...]
    next_recommended_action: Optional[str]
    approved_stage_evidence: Mapping[str, Any]
    approved_destination_route: Optional[str]
    updated_at: str
    build_order_id: Optional[str]

    @classmethod
    def from_authoritative(cls, raw: Mapping[str, Any]) -> "StageSnapshot":
        if not isinstance(raw, Mapping):
            raise StageSnapshotError("stage response must be an object")
        schema = _required_text(raw, "schema")
        if schema != SUPPORTED_SCHEMA:
            raise StageSnapshotError(f"unsupported stage schema {schema!r}; expected {SUPPORTED_SCHEMA!r}")

        completed = raw.get("completed_stages") or []
        if not isinstance(completed, list) or not all(isinstance(item, str) and item.strip() for item in completed):
            raise StageSnapshotError("completed_stages must be a string list")
        actions_raw = raw.get("allowed_actions") or []
        if not isinstance(actions_raw, list):
            raise StageSnapshotError("allowed_actions must be a list")
        actions = tuple(AllowedAction.from_authoritative(item) for item in actions_raw)
        action_names = [action.name for action in actions]
        if len(action_names) != len(set(action_names)):
            raise StageSnapshotError("allowed_actions contains duplicate action names")

        next_action = _optional_text(raw, "next_recommended_action")
        if next_action and next_action not in action_names:
            raise StageSnapshotError("next_recommended_action is not present in allowed_actions")
        approved_destination = _optional_text(raw, "approved_destination_route")
        if approved_destination and raw.get("approved_destination_verified") is not True:
            raise StageSnapshotError("approved_destination_route is not verified")
        updated_at = _required_text(raw, "updated_at")
        try:
            datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise StageSnapshotError("updated_at must be an ISO-8601 timestamp") from exc

        evidence = raw.get("approved_stage_evidence") or {}
        if not isinstance(evidence, Mapping):
            raise StageSnapshotError("approved_stage_evidence must be an object")

        snapshot = cls(
            schema=schema,
            snapshot_version=_required_text(raw, "snapshot_version"),
            project_id=_required_text(raw, "project_id"),
            project_display_name=_required_text(raw, "project_display_name"),
            current_stage=_required_text(raw, "current_stage"),
            stage_status=_required_text(raw, "stage_status"),
            completed_stages=tuple(dict.fromkeys(item.strip() for item in completed)),
            blocking_reason=_optional_text(raw, "blocking_reason"),
            customer_action_required=_optional_text(raw, "customer_action_required"),
            allowed_actions=actions,
            next_recommended_action=next_action,
            approved_stage_evidence=_freeze_json(evidence, "approved_stage_evidence"),
            approved_destination_route=approved_destination,
            updated_at=updated_at,
            build_order_id=_optional_text(raw, "build_order_id"),
        )
        return snapshot

    def action(self, name: str) -> Optional[AllowedAction]:
        return next((action for action in self.allowed_actions if action.name == name), None)
