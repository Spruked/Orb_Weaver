"""
Results Vault — persistent evidence trail for TPC reasoning engine.

Writes every query result and test run to structured JSON files under ./results/
so the system accumulates an auditable, regression-comparable history.

Directory layout
────────────────
results/
  index.json                           ← rolling index of all saved records
  YYYY-MM-DD/
    query_0001.json                    ← one file per /reason query
    query_0002.json
  tests/
    hard_tests_YYYYMMDD_HHMM.json     ← one file per /run-tests call
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import Any, Dict

# Root folder relative to this file
_VAULT_ROOT = Path(__file__).parent / "results"
_INDEX_PATH = _VAULT_ROOT / "index.json"


# ── helpers ────────────────────────────────────────────────────────────────────

def _ensure(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_index() -> list:
    if _INDEX_PATH.exists():
        try:
            return json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_index(index: list) -> None:
    _VAULT_ROOT.mkdir(parents=True, exist_ok=True)
    _INDEX_PATH.write_text(
        json.dumps(index, indent=2, default=str),
        encoding="utf-8",
    )


def _default(obj: Any) -> Any:
    """JSON serialiser fallback — handles numpy scalars, etc."""
    try:
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    return str(obj)


# ── public API ─────────────────────────────────────────────────────────────────

def save_query_result(result: Dict[str, Any]) -> Path:
    """
    Persist a single /reason result.

    Strips the large combined_glyph array from the synthesis block before
    writing (it is reconstructable and bloats the file), then saves to:
        results/YYYY-MM-DD/query_NNNN.json

    Returns the Path written.
    """
    now = datetime.datetime.now()
    day_str = now.date().isoformat()          # "2026-04-20"
    folder = _ensure(_VAULT_ROOT / day_str)

    # Determine next query number from existing files in today's folder
    existing = sorted(folder.glob("query_*.json"))
    next_num = len(existing) + 1
    filename = f"query_{next_num:04d}.json"

    # Build a clean, audit-friendly record
    synthesis = result.get("synthesis", {}) or {}
    conf = synthesis.get("confidence") or result.get("confidence") or 0.0
    raw_verdict = (
        "admit" if conf > 0.6 else
        "reject" if conf < 0.3 else
        "suspend"
    )
    verdict = (
        "suspend"
        if synthesis.get("contract_violated") and raw_verdict == "admit"
        else raw_verdict
    )

    record: Dict[str, Any] = {
        "timestamp": now.isoformat(timespec="seconds"),
        "query_id": result.get("query_id", filename),
        "input": result.get("_input_text", ""),
        "input_type": result.get("input_type", "text"),
        "verdict": verdict.upper(),
        "confidence": round(float(conf), 6),
        "phase_coherence": result.get("phase_coherence"),
        "vault_status": result.get("vault_status"),
        "beam_results": {
            name: {
                "confidence": round(float(data.get("confidence", 0)), 6),
                "verdict": data.get("verdict"),
                "rationale_trace": data.get("rationale_trace", []),
            }
            for name, data in (result.get("philosopher_results") or {}).items()
        },
        "invariants": {
            "passed": (result.get("invariants") or {}).get("passed"),
            "violations": (result.get("invariants") or {}).get("violations", []),
        },
        "contract_violated": synthesis.get("contract_violated", False),
        "escalation": result.get("escalation"),
        "synthesis_trace": synthesis.get("synthesis_trace", []),
        "drift_ping": result.get("drift_ping"),
        "trace_id": result.get("query_id", ""),
        "runtime_ms": result.get("latency_ms"),
    }

    dest = folder / filename
    dest.write_text(json.dumps(record, indent=2, default=_default), encoding="utf-8")

    # Update rolling index
    index = _load_index()
    index.append({
        "type": "query",
        "file": str(dest.relative_to(_VAULT_ROOT)),
        "timestamp": record["timestamp"],
        "query_id": record["query_id"],
        "verdict": record["verdict"],
        "confidence": record["confidence"],
        "runtime_ms": record["runtime_ms"],
    })
    _save_index(index)

    return dest


def save_test_run(test_results: Dict[str, Any]) -> Path:
    """
    Persist a full hard-test run.

    Written to: results/tests/hard_tests_YYYYMMDD_HHMM.json
    Returns the Path written.
    """
    now = datetime.datetime.now()
    folder = _ensure(_VAULT_ROOT / "tests")
    stamp = now.strftime("%Y%m%d_%H%M")
    filename = f"hard_tests_{stamp}.json"

    pass_count = sum(1 for v in test_results.values() if isinstance(v, dict) and v.get("status") == "PASS")
    total = len(test_results)

    record = {
        "timestamp": now.isoformat(timespec="seconds"),
        "pass_count": pass_count,
        "total": total,
        "all_pass": pass_count == total,
        "results": test_results,
    }

    dest = folder / filename
    dest.write_text(json.dumps(record, indent=2, default=_default), encoding="utf-8")

    # Update rolling index
    index = _load_index()
    index.append({
        "type": "test_run",
        "file": str(dest.relative_to(_VAULT_ROOT)),
        "timestamp": record["timestamp"],
        "pass_count": pass_count,
        "total": total,
        "all_pass": record["all_pass"],
    })
    _save_index(index)

    return dest


def load_index() -> list:
    """Return the full rolling index (list of summary dicts)."""
    return _load_index()


def get_vault_stats() -> Dict[str, Any]:
    """Quick summary for health/status endpoints."""
    index = _load_index()
    queries = [e for e in index if e.get("type") == "query"]
    tests   = [e for e in index if e.get("type") == "test_run"]
    return {
        "total_queries_saved": len(queries),
        "total_test_runs_saved": len(tests),
        "vault_root": str(_VAULT_ROOT),
        "index_entries": len(index),
    }
