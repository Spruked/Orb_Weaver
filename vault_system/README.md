# Orb Weaver Canonical Vault

`vault_system/` is the single storage authority for this repository.

All subsystems resolve persistent and runtime data through this root. Component
folders such as `backend/`, `Orb_Assistant/`, and legacy `substrate/` paths may
contain source code, but they must not own independent data stores.

## Layout

```text
vault_system/
├── apriori/                 # canonical seed truths
├── posteriori/              # learned deterministic memory
├── clients/                 # per-domain scans, crawls, Site Worlds and pointer maps
├── databases/               # SQLite databases
├── reports/                 # generated reports
├── indexes/                 # generated search/semantic indexes
├── manifests/               # storage, scan and migration manifests
├── schemas/                 # vault-owned data schemas
├── runtime/
│   ├── tts_cache/           # generated speech audio
│   ├── browser_reviews/     # browser verification output
│   ├── state/               # local runtime state
│   └── logs/                # runtime logs
└── backups/
    └── migration_conflicts/ # data preserved when legacy copies disagree
```

## Client records

Each client domain retains its existing subtree beneath:

```text
vault_system/clients/<domain>/
```

This includes `current`, `history`, `reports`, `recommendations`,
`website_orb_context`, pointer maps, Site Worlds, scan summaries, manifests,
claims and any other client-owned intelligence.

## Migration

Run the migration utility from the repository root:

```bash
python3 scripts/migrate_to_canonical_vault.py
```

That is a dry run. After stopping Orb Weaver services, use `--apply` to copy
and verify data, then `--finalize` to remove only verified legacy copies.
Every applied migration writes a manifest under `vault_system/manifests/`.
