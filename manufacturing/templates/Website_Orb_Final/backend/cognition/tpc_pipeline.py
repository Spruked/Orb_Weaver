from __future__ import annotations

from typing import Any, Dict, List

from .tpc_runtime import tpc_runtime


def run_tpc(
    message: str,
    intent: str,
    route_record: Dict[str, Any],
    runtime_language: Dict[str, Any],
    pointer_targets: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Run the Website ORB through TPC-only cognition."""

    return tpc_runtime.evaluate(message, intent, route_record, runtime_language, pointer_targets or [])
