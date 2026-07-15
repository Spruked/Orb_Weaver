# Orb Weaver Intelligence Preservation

Orb Weaver learns locally from each website and globally from anonymized patterns across all scanned sites.

All stored intelligence resolves through the repository-root `vault_system/`. No backend, ORB component, crawler, scanner, or legacy substrate path may maintain an independent store.

## Private Client Intelligence

Each client/site gets an isolated pack:

```text
vault_system/clients/<client_or_domain>/
  current/
  history/
  recommendations/
  website_orb_context/
  dandy_sponsor_pack/
  crm_context/
  mail_context/
  claims/
  local_index/
  reports/
  visitor_questions/
  owner_seed_changes/
```

See `PACK_CONTRACT_V0_1.md` for the exact consumer-facing contract.

Preserved private data includes:

- crawl snapshots
- score history
- semantic gaps
- entity gaps
- authority flow changes
- internal-link changes
- mobile/template issues
- generated recommendations
- approved/completed recommendations when those states exist
- visitor questions when the Website ORB supplies them
- owner seed changes
- safe claims and banned claims
- Dandy sponsor packs when relevant
- compiled Site World records
- verified pointer maps and manifests

## Global Anonymized Intelligence

Global learning writes pattern-only records under the same canonical vault:

```text
vault_system/indexes/global_intelligence/
  crawl_patterns.jsonl
  audit_patterns.jsonl
```

The global layer may store:

- issue category counts
- score buckets
- page-count buckets
- common missing FAQ/question patterns
- schema/internal-link/template weakness counts
- recommendation pattern categories
- before/after trend metrics

## Hard Wall

Do not write client-identifying material into global intelligence:

- customer records
- account info
- domains
- URLs
- protected/admin paths
- checkout details
- private business notes
- unpublished pricing
- secrets/tokens/passwords
- proprietary client claims

Global intelligence is pattern-based only. Client intelligence remains private to the client/site pack.

## Runtime Flow

```text
Orb Weaver scans
  -> vault_system/clients/<domain> is updated
  -> anonymized global pattern event is appended under vault_system/indexes
  -> Website ORB reads the current client Site World and verified pointer map
  -> Website ORB can improve responses and recommendations over time
```

## Storage boundary

The following are compatibility paths only after migration and must point into the root vault rather than contain independent records:

- `substrate/clients`
- malformed `backend/R:\R_Drive_Substrate/.../clients` trees
- `backend/data`
- `data/tts_cache`
- `Orb_Assistant/vault_system/posteriori`
- `Orb_Assistant/src/vault_system/posteriori`

Use `scripts/migrate_to_canonical_vault.py` to inventory, verify, consolidate, and finalize these paths without overwriting conflicting records.
