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

Orb Weaver uses one repository-native storage authority:

- `vault_system/databases/` for SQLite application databases.
- `vault_system/clients/<domain>/` for durable client intelligence artifacts.
- per-client SQLite indexes inside each client pack for fast local reads.
- append-only JSONL under `vault_system/indexes/global_intelligence/` for global anonymized intelligence.
- `vault_system/runtime/` for generated caches, browser-review output, logs and temporary runtime state.

PostgreSQL may replace SQLite as the application database when deliberately configured, but all repository-owned filesystem storage still resolves through `vault_system/`.

Vector databases are deferred until the pack and reader contract are stable.

The same rule is embedded in every downloadable `.orbpack`: it contains one
top-level `vault_system/`, a `vault-manifest.json`, and the site's isolated
`clients/<domain>/` namespace. Installed adapters, cognition engines, voice
services, and scanners may write only within that root. They must never create
a second `vault_system` or store site data beside the ORB runtime.

## Client Pack Layout

```text
vault_system/clients/<domain>/
  current/
    latest_crawl.json
    latest_audit.json
  history/
    crawl_<id>.json
    audit_<id>.json
  recommendations/
    audit_<id>_recommendations.json
  website_orb_context/
    latest_context.json
    pointer_plot_map.json
    pointer_manifest.json
    site_world.json
    tool_cache.json
  dandy_sponsor_pack/
    latest_pack.json
  crm_context/
    latest_context.json
  mail_context/
    latest_context.json
  claims/
    safe_claims.json
    banned_claims.json
  reports/
    audit_<id>_report.json
  visitor_questions/
  owner_seed_changes/
  local_index/
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

## Website ORB Runtime Artifacts

`website_orb_context/pointer_plot_map.json` is the pointable target map generated from the crawl. It contains stable target IDs, semantic locators, intent aliases, allowed actions, and confidence values for visible website targets.

`website_orb_context/site_world.json` is the compiled website truth used to ground answers, route selection, tools and pointer guidance. The ORB must not invent information outside this compiled record.

`website_orb_context/tool_cache.json` is the low-latency voice cache generated during the build phase. Basic customer ORBs must be able to run from this file, approved static context, and pre-generated audio without probing Desktop MCP or host OCR.

Enhanced/showcase caches may include MCP tool metadata only when built with explicit intent:

```bash
ORB_BUILD_ALLOW_MCP=true python3 scripts/build_preflight_tool_cache.py --allow-mcp
```

The default build is customer-safe:

```bash
python3 scripts/build_preflight_tool_cache.py --domain example.com
```

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

Pointer capability is universal. Every ORB tier receives a Pointer Plot Map and runtime pointer resolution. Tiers control coverage, density, maintenance, verification depth, branded behavior, and adaptive recovery; tiers do not control whether pointing exists.

Basic:

- project/site history
- scan history
- site recommendations
- pointer map for important visitor routes, navigation, forms, service/contact paths, and major conversions
- static tool cache and voice manifest
- no customer-specific visitor memory
- no Desktop MCP dependency

Premium:

- customer-aware context only when login integration exists
- approved customer pointers only
- denser maintained pointer coverage and richer route-specific intents
- governance layer required
- explicit adapters only; no implicit inheritance from the Orb Weaver showcase ORB

Platinum:

- owner DockStation
- richer memory controls
- advanced history and recommendation timeline
- desktop/app-window pointer targets where applicable
- deeper MCP/Desktop workflows through DockStation or deliberately configured adapters

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
