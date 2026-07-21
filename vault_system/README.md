# Orb Weaver Canonical Vault

> **IMMUTABLE AND REQUIRED:** This directory is the sole authoritative home
> for all persisted Orb Weaver data, including raw scans, customer and session
> records, projects, checkout, verified payments, entitlements, workflow state,
> reports, caches, and cognition. Every producer and consumer must write here
> and read authoritative state from here. No component-local store is valid.
> The complete law is in `../IMMUTABLE_VAULT_STORAGE_LAW.md`.

`vault_system/` is the single storage authority for this repository and for
every downloadable customer ORB. A repository or installed ORB must contain
exactly one directory named `vault_system`; components receive namespaces
inside it and may not create independent stores.

All subsystems resolve persistent and runtime data through this root. Component
folders such as `backend/`, `Orb_Assistant/`, and legacy `substrate/` paths may
contain source code, but they must not own independent data stores.

## Layout

```text
vault_system/
├── apriori/                 # canonical seed truths
├── posteriori/              # learned deterministic memory
├── identity/                # ORB identity and installed configuration
├── permissions/             # consent, capability and access policy
├── site_or_environment_data/# scanned site/environment knowledge
├── client_or_owner_data/    # governed owner/client records
├── short_term_memory/       # durable bounded working memory
├── long_term_memory/        # durable learned memory and TPC state
├── workflow_state/          # resumable operational workflows
├── observations/            # cognition and tool observations
├── verified_outcomes/       # approved or verified results
├── runtime_state/           # durable runtime state
├── persistent_cache/        # reusable generated cache
├── audit/                   # audit events and evidence
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
Finalization does not recreate compatibility storage paths.
Every applied migration writes a manifest under `vault_system/manifests/`.
