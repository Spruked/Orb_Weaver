# Orb Weaver Pack Contract v0.1

## Purpose

This contract defines the client intelligence pack that Orb Weaver writes and downstream local systems may read.

Consumers:

- Website ORB
- Dandy
- CRM
- Prime Mail
- Desktop ORB

## Storage Model

Orb Weaver uses a hybrid storage model:

- PostgreSQL or SQLite app database for customers, projects, jobs, ownership, access, and status metadata.
- R: drive filesystem packs for durable intelligence artifacts.
- Per-client SQLite index for fast local reads.
- Append-only JSONL for global anonymized intelligence.

Vector DBs are deferred until the pack and reader contract are stable.

## Client Pack Layout

```text
R:\R_Drive_Substrate\orb_weaver\clients\<domain>\
  current\
    latest_crawl.json
    latest_audit.json
  history\
    crawl_<id>.json
    audit_<id>.json
  recommendations\
    audit_<id>_recommendations.json
  website_orb_context\
    latest_context.json
  dandy_sponsor_pack\
    latest_pack.json
  crm_context\
    latest_context.json
  mail_context\
    latest_context.json
  claims\
    safe_claims.json
    banned_claims.json
  reports\
    audit_<id>_report.json
  visitor_questions\
  owner_seed_changes\
  local_index\
    client_index.sqlite
```

## Local Index

`local_index/client_index.sqlite` is the fast reader surface.

Current tables:

- `pack_meta`
- `crawl_snapshots`
- `audit_snapshots`
- `recommendation_index`
- `context_documents`

Do not store cross-client global data in this database. It is client-pack local.

## Privacy Boundary

Private pack data may include domains, URLs, recommendations, Website ORB context, owner claims, and client-specific history.

Global intelligence must not include:

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

## Tier Boundary

Basic:

- project/site history
- scan history
- site recommendations
- no customer-specific visitor memory

Premium:

- customer-aware context only when login integration exists
- approved customer pointers only
- governance layer required

Platinum:

- owner DockStation
- richer memory controls
- advanced history and recommendation timeline

## Scoring Weights

| Category | Weight |
| --- | ---: |
| Content / Semantic Depth | 25% |
| Technical SEO | 15% |
| Security | 12% |
| Performance | 12% |
| Accessibility | 10% |
| Mobile UX | 10% |
| Internal Links / Authority | 10% |
| Schema / Structured Data | 6% |
