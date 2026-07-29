from __future__ import annotations

from functools import wraps
from typing import Any, Dict, Iterable


def install_pointer_recovery_optimizer() -> None:
    """Optimize normal map generation and Pointer Recovery in-place.

    `backend.main` imports `app.orb` before importing the map and recovery
    functions. Installing these wrappers here keeps the existing lifecycle,
    storage paths, review rules, and API unchanged:

    * baseline map generation receives safe repeated-alias compaction;
    * Pointer Recovery additionally receives DOM mutability and evidence-only
      viewport geometry from its existing Playwright capture.
    """

    from app.orb import pointer_plot, pointer_recovery
    from app.orb.pointer_map_optimizer import optimize_pointer_map

    original_map_builder = pointer_plot.pointer_plot_map_from_pages
    if not getattr(original_map_builder, "_orb_pointer_optimizer_installed", False):
        @wraps(original_map_builder)
        def map_and_compact(pages: Iterable[Any]) -> Dict[str, Any]:
            pointer_map = original_map_builder(pages)
            return optimize_pointer_map(pointer_map)

        setattr(map_and_compact, "_orb_pointer_optimizer_installed", True)
        pointer_plot.pointer_plot_map_from_pages = map_and_compact

    original_recovery = pointer_recovery.reconcile_pointer_recovery
    if not getattr(original_recovery, "_orb_pointer_optimizer_installed", False):
        @wraps(original_recovery)
        def reconciled_and_optimized(
            baseline_map: Dict[str, Any],
            capture: Dict[str, Any],
        ) -> Dict[str, Any]:
            recovered = original_recovery(baseline_map, capture)
            return optimize_pointer_map(recovered, capture)

        setattr(reconciled_and_optimized, "_orb_pointer_optimizer_installed", True)
        pointer_recovery.reconcile_pointer_recovery = reconciled_and_optimized
