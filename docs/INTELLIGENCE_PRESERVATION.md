# Orb Weaver Intelligence Preservation

Orb Weaver learns locally from each website and globally from anonymized patterns across all scanned sites.

## Private Client Intelligence

Each client/site gets an isolated pack:

```text
R:\R_Drive_Substrate\orb_weaver\clients\<client_or_domain>\
  current\
  history\
  recommendations\
  website_orb_context\
  dandy_sponsor_pack\
  crm_context\
  mail_context\
  claims\
  local_index\
  reports\
  visitor_questions\
  owner_seed_changes\
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

## Global Anonymized Intelligence

Global learning writes pattern-only records:

```text
R:\R_Drive_Substrate\orb_weaver\global_intelligence\
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
  -> private client pack is updated
  -> anonymized global pattern event is appended
  -> Website ORB reads current + historical client context
  -> Website ORB can improve responses and recommendations over time
```
