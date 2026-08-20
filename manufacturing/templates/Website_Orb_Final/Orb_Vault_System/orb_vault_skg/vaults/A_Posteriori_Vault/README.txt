A Posteriori Vault — Learned Experience Data Store
===================================================

This directory holds the learned experience layer:

  posteriori_state.json    → Serialized knowledge nodes (candidates, promoted, retired)
  ledger/                  → Immutable append-only experience ledger
    ├── ledger_00000.jsonl
    ├── ledger_00001.jsonl
    └── ...

This vault is SELF-MANAGING:
  • New experiences append to the ledger automatically
  • Candidates are verified and promoted based on evidence
  • Successful usage reinforces knowledge weights
  • Degraded knowledge is weakened, merged, compressed, or retired
  • Periodic maintenance runs via coordinator.run_maintenance()

DO NOT DELETE the ledger/ folder. It is the immutable record.
DO NOT EDIT posteriori_state.json while the assistant is running.
