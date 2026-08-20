# Website ORB Manufacturing Contract

This directory contains **manufacturing code and contracts only**. It is not a second Vault System.

Orb Weaver remains the manufacturer. `Website_Orb_Final` remains the golden runtime template. A customer ORB is created only after a fresh site scan has been compiled, owner-verified, injected into a clean runtime clone, validated, and packaged.

## Storage boundary

All persistent manufacturing evidence and generated customer artifacts belong under Orb Weaver's one canonical Vault System:

```text
vault_system/clients/<domain>/manufacturing/
  evidence/
    full_scan_evidence.json
  current/
    compiled_orb/
      site_world.json
      pointer_plot_map.json
      pointer_correspondence.json
      runtime_language.json
      tool_cache.json
    A_Priori_Vault/
      catalog.json
      ontology.json
      qa.json
      policies.json
    verification_manifest.json
  history/<build_id>/...
```

`vault_system/apriori/` is Orb Weaver's own builder/runtime truth and MUST NOT be copied into a customer ORB as site knowledge.

## Manufacturing sequence

1. Scan/weave the target site and write canonical `full_scan_evidence.json`.
2. Validate the evidence against `schemas/full_scan_evidence.v1.json`.
3. Compile the operating environment (`compiled_orb/`).
4. Compile settled site truth (`A_Priori_Vault/`).
5. Build pointer-semantic correspondence.
6. Present compiled artifacts for owner verification.
7. Write `verification_manifest.json` recording approvals/rejections.
8. Clone the clean `Website_Orb_Final` golden template.
9. Inject the approved compiled artifacts.
10. Initialize a clean A Posteriori Vault for that customer.
11. Validate the package and run acceptance tests.
12. Only then expose download/deployment.

## Required A Priori artifacts

- `catalog.json` — products, services, plans, fees, prices, SKUs, availability, and pointer correspondence where applicable.
- `ontology.json` — verified business/site entities and relationships.
- `qa.json` — verified question/answer correspondences and phrasing aliases.
- `policies.json` — owner-approved policy and rule text with source provenance.

The A Priori Vault is read-only at customer runtime. It is refreshed only by a new Orb Weaver build/rescan and owner approval.

## Required provenance

Every compiled fact that can affect an answer or pointer action must retain enough evidence to trace it back to the scan:

- `source_url`
- `route`
- `source_evidence_ids`
- `verified`
- `confidence`
- `content_hash`
- `compiler_version`

No compiler may silently convert an unverified guess into settled truth.

## Pointer correspondence

Pointer targets are not inferred at answer time when a verified correspondence already exists. The canonical correspondence artifact is `pointer_correspondence.json` and ties site semantics to the physical target map using stable target IDs.

Minimum correspondence:

```text
entity_id + route + pointer_target_id + source_url + verified
```

The ORB may guide or point only to targets allowed by the target's action policy. User control remains authoritative.

## A Posteriori rule

Every newly manufactured customer ORB starts with a clean A Posteriori Vault. Learned experience is site-specific and must never be inherited from Orb Weaver or another customer deployment.
