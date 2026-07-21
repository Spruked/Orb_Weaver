# IMMUTABLE VAULT STORAGE LAW

> **REQUIRED REPOSITORY INVARIANT — MAY NOT BE BYPASSED**

The repository-root `vault_system/` is Orb Weaver's sole authoritative data
system. Every component that creates, receives, transforms, caches, indexes,
or consumes persisted data MUST write that data into—and read authoritative
state back from—a namespace beneath this one Vault.

This law applies without exception to persisted:

- preflight, crawl, scan, audit, browser, OCR, pointer, and raw evidence;
- uploaded or generated files, reports, indexes, manifests, logs, caches,
  observations, learned memory, and verified outcomes;
- customer profiles, authentication sessions, project ownership, carts,
  checkout orders, payment-verification records, entitlements, signatures,
  build orders, installation records, and lifecycle/workflow state;
- Website ORB packages and any customer/site intelligence they contain.

## Required behavior

1. Code MUST resolve storage through `backend/app/core/storage.py` or
   `vault_system/paths.py`.
2. The authoritative application database MUST be the Vault-backed database
   beneath `vault_system/databases/`. Customer and checkout state may not be
   sourced from a component-local or parallel database.
3. Client/site evidence MUST remain beneath `vault_system/clients/<domain>/`.
4. Global anonymized intelligence MUST remain beneath
   `vault_system/indexes/global_intelligence/`.
5. A legacy path such as `substrate/` may exist only as a compatibility link
   into the canonical Vault. It may not own files or independent truth.
6. An external provider response may exist transiently in memory, but any
   persisted or authoritative result must be verified and recorded in the
   Vault before the system relies on it.
7. OS-managed temporary request buffers are permitted only while processing a
   request. They must never become authoritative state and must be removed when
   processing ends.

## Prohibited behavior

- component-local `data/`, `database/`, `reports/`, `cache/`, `vault/`, or
  `substrate/` stores;
- storing authoritative workflow truth only in frontend state, conversation
  memory, Orb Assistant memory, redirects, or third-party provider state;
- accepting a caller-selected output directory outside `vault_system/` for a
  scan, report, pack, raw-data export, browser review, or durable artifact;
- reading customer, checkout, entitlement, scan, or lifecycle truth from a
  legacy copy when a canonical Vault record exists.

## Immutability

This is an architectural invariant, not a preference. A change that weakens
this law is invalid unless it also provides an explicit repository-wide data
migration, audit manifest, updated enforcement tests, and direct owner
authorization to revise this law. Convenience, compatibility, or a new
integration is not sufficient authority to create a second store.

