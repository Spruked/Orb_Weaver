from __future__ import annotations

from functools import wraps
from typing import Any, Dict


def install_pointer_recovery_optimizer() -> None:
    """Enrich every normal Pointer Recovery result without a parallel pipeline.

    `backend.main` imports `app.orb` before importing the recovery functions.
    Installing the wrapper here means the existing lifecycle job, tests, and
    callers all continue to use `reconcile_pointer_recovery`; the function now
    also adds DOM mutability, evidence-only geometry, and safe alias compaction.
    """

    from app.orb import pointer_recovery
    from app.orb.pointer_map_optimizer import optimize_pointer_map

    original = pointer_recovery.reconcile_pointer_recovery
    if getattr(original, "_orb_pointer_optimizer_installed", False):
        return

    @wraps(original)
    def reconciled_and_optimized(
        baseline_map: Dict[str, Any],
        capture: Dict[str, Any],
    ) -> Dict[str, Any]:
        recovered = original(baseline_map, capture)
        return optimize_pointer_map(recovered, capture)

    setattr(reconciled_and_optimized, "_orb_pointer_optimizer_installed", True)
    pointer_recovery.reconcile_pointer_recovery = reconciled_and_optimized
