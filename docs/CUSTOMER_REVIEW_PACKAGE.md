# Orb Weaver Customer Review Package

Status: implemented in source on 2026-09-12. Runtime validation remains required before deployment.

## Purpose

A completed Orb Weaver crawl/audit must not leave a paying customer with only raw CSV files. Package 1 and Package 2 customers receive a complete human-readable and machine-readable review bundle assembled from the authoritative project evidence.

## Entitlement rule

The Full Review Package is available only after the governed ORBS checkout has produced an active project-bound entitlement backed by a verified checkout payment for one of these canonical products:

| Commercial package | Canonical SKU | Verified price | Currency | Entitlement key |
| --- | --- | ---: | --- | --- |
| Package 1 | `OW-FULL-REVIEW-PACKAGE-1` | $49.00 | `usd` | `package_1` |
| Package 2 | `OW-FULL-REVIEW-PACKAGE-2` | $99.00 | `usd` | `package_2` |

Price alone is never package identity. The backend requires the active `OrbsEntitlement`, exact customer/project binding, verified `CheckoutOrder.payment_verified_at`, non-null governed build-order binding, allowlisted SKU, exact USD price, line-item USD currency, order USD currency, positive quantity, and matching order total.

Generic `/api/cart/checkout` orders are intentionally non-qualifying because that flow is not project-bound and does not create the governor-issued entitlement used by this package gate. The canonical Package 1/2 products must therefore be sold through the existing project-bound ORBS checkout path. A browser flag, unrelated $49/$99 product, legacy unbound order, or price collision cannot unlock this bundle.

Existing individual crawl/audit exports remain basic report-library outputs. The eight-file Full Review Package is the paid deliverable.

## Required evidence

The bundle requires:

1. an authenticated customer who owns the project;
2. an active project-bound governor entitlement for the canonical Package 1 or Package 2 SKU;
3. the verified checkout order that produced that entitlement;
4. the latest completed crawl for the project; and
5. a completed audit explicitly tied to that exact crawl ID.

The package status endpoint returns a waiting reason when the paid entitlement exists but crawl or matching audit evidence is incomplete. It never substitutes an older project audit for a newer crawl.

## Bundle contents

The generated ZIP contains exactly these customer-facing files:

```text
report.html
manifest.json
crawl.csv
crawl.json
audit.csv
audit.json
website_context.json
pointer_map.json
```

### `report.html`

Primary human-readable report. It summarizes project identity, page count, audit totals, scores, priority findings, recommendations, and the contents of the package.

### `manifest.json`

Package provenance: schema version, generation time, customer/project identity, source crawl and audit IDs, verified entitlement evidence, filenames, file sizes, and SHA-256 hashes for generated evidence files.

### `crawl.csv`

Spreadsheet-friendly crawl rows for operational review.

### `crawl.json`

Structured crawl metadata plus complete serialized page evidence, including semantic, entity, schema, mobile UX, link, image, and crawl-depth fields available in the database.

### `audit.csv`

Spreadsheet-friendly flattened audit findings with severity, category, description, recommendation, impact score, and affected URLs.

### `audit.json`

Authoritative structured audit report data and source IDs.

### `website_context.json`

The canonical `website_orb_context/latest_context.json` when present. If that artifact has not yet been materialized, Orb Weaver emits an explicit review-context fallback derived from the completed crawl instead of silently omitting the file.

### `pointer_map.json`

The canonical `website_orb_context/pointer_plot_map.json` when present. If the stored map is absent, Orb Weaver regenerates a map from the crawl's stored `pointer_plot_records` through the existing `pointer_plot_map_from_pages` contract.

## Storage and publication

Durable package files obey the Immutable Vault Storage Law and are written under a source- and entitlement-keyed path:

```text
vault_system/clients/<domain>/customer_review_packages/crawl_<crawl_id>_audit_<audit_id>_order_<checkout_order_id>/
```

No customer review package is written to a component-local application data store. The package builder reuses an existing artifact when its manifest matches the same customer, crawl, audit, checkout order, and canonical SKU. Generation is protected by a per-package lock. ZIP creation occurs at a temporary path and is atomically published with `os.replace`, so a concurrent status/download request cannot observe a partially written archive.

## API

```text
GET /api/projects/{project_id}/customer-review-package
GET /api/projects/{project_id}/customer-review-package/download
```

The status endpoint revalidates entitlement and materializes the current package only when evidence is complete. Once the same source-keyed package exists, subsequent status/download requests reuse it rather than recompressing the evidence. The download endpoint revalidates entitlement before returning the ZIP archive. Unpaid or incorrectly bound access fails closed.

## Frontend

`frontend/src/pages/ReportCompiler.tsx` displays a dedicated Full Review Package card.

- Eligible + ready: `Download Full Review Package`.
- Eligible + incomplete evidence: paid access is confirmed and the page states what is still required.
- Not eligible: the bundle is shown as locked to verified Package 1 ($49) or Package 2 ($99) purchase.
- Existing individual CSV/PDF controls remain under `Basic Exports`.

## Source files

```text
backend/app/routers/customer_review_package.py
backend/app/routers/orb_telemetry.py
frontend/src/services/customerReviewPackage.ts
frontend/src/pages/ReportCompiler.tsx
```

## Validation boundary

This source change does not claim deployment or runtime acceptance. Before release, run backend compile/tests, frontend typecheck/build, authentication/ownership tests, canonical-SKU and currency rejection tests, project-bound entitlement tests, exact crawl/audit lineage tests, ZIP-content/hash verification, cache-reuse checks, concurrency/atomic-publication checks, and a real verified-payment acceptance test in the isolated development runtime.
