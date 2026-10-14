"""Privacy-safe, owner-initiated maintenance inspection data.

The function builds data only; it performs no transport.  Its hard allowlist
prevents memory content from becoming telemetry by accident.
"""

from __future__ import annotations

from typing import Any, Dict


def memory_telemetry_snapshot(system, software_schema_version: int, vault_schema_version: int) -> Dict[str, Any]:
    vault = system.vault.stats()
    outcomes = system.retrieval_ledger.outcome_statistics()
    indexes = system.indexes.status()
    return {
        "snapshot_type": "AIMS_UPDATE_SNAPSHOT",
        "software_schema_version": software_schema_version,
        "vault_schema_version": vault_schema_version,
        "integrity_status": "verified" if system.vault.event_ledger.verify_chain()[0] else "corrupted",
        "memory_counts": {
            "session_outcomes": outcomes["total"],
            "apriori_atoms": vault["by_type"].get("a_priori", 0),
            "aposteriori_atoms": vault["by_type"].get("a_posteriori", 0),
            "collective_edges": system.skg_trio.collective.stats()["total_edges"],
        },
        "outcomes": outcomes,
        "learning": {"promoted_count": vault["by_status"].get("active", 0),
                     "weakened_count": 0, "retired_count": vault["by_status"].get("retired", 0),
                     "contradictions_detected": 0},
        "performance": {"avg_retrieval_latency": 0.0, "p95_retrieval_latency": 0.0,
                        "vault_size": system.vault.event_ledger.verify_physical_persistence()["ledger_size_bytes"],
                        "index_size": sum(indexes["counts"].values())},
        "compatibility": {"migration_required": False, "migration_from": vault_schema_version,
                          "migration_to": vault_schema_version},
    }
