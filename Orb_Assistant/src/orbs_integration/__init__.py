"""Thin, non-authoritative ORBS integration adapters.

Orb Weaver owns every workflow transition.  This package only retrieves,
sanitizes, articulates, confirms, and submits governor-approved actions.
"""

from .confirmation_policy import ConfirmationEvidence, ConfirmationPolicy
from .stage_actions import ActionSubmissionRejected, StageActionService
from .stage_articulation import StageArticulation, StageArticulator
from .stage_client import (
    HttpStageTransport,
    OrbWeaverStageClient,
    StageActionRejected,
    StageContractError,
    StageUnavailable,
)
from .stage_snapshot import AllowedAction, StageSnapshot, StageSnapshotError

__all__ = [
    "ActionSubmissionRejected",
    "AllowedAction",
    "ConfirmationEvidence",
    "ConfirmationPolicy",
    "HttpStageTransport",
    "OrbWeaverStageClient",
    "StageActionRejected",
    "StageActionService",
    "StageArticulation",
    "StageArticulator",
    "StageContractError",
    "StageSnapshot",
    "StageSnapshotError",
    "StageUnavailable",
]
