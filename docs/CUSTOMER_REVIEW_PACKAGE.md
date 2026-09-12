# Orb Weaver Customer Review Package

Status: implemented in source on 2026-09-12. Runtime validation remains required before deployment.

## Purpose

A completed Orb Weaver crawl/audit must not leave a paying customer with only raw CSV files. Package 1 and Package 2 customers receive a complete human-readable and machine-readable review bundle assembled from the authoritative project evidence.

## Entitlement rule

The Full Review Package is available only after a verified checkout payment for one of these package prices:

| Commercial package | Verified price | Entitlement key |
| --- | ---: | --- |
| Package 1 | $49.00 | `package_1` |
| Package 2 | $99.00 | `package_2` |

A browser flag cannot unlock this bundle. The backend checks `CheckoutOrder.payment_verified_at` and the verified order/line-item price. Project-bound orders must match the requested project. Legacy customer orders without a project binding remain customer-scoped.

Existing individual crawl/audit exports remain basic report-library outputs. The eight-file Full Review Package is the paid deliverable.

## Required evidence

The bundle requires:

1. an authenticated customer who owns the project;
2. a verified Package 1 or Package 2 payment;
3. the latest completed crawl for the project; and
4. a completed audit with report data.

The package status endpoint returns a waiting reason when the paid entitlement exists but crawl or audit evidence is incomplete.

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

## Storage

Durable package files obey the Immutable Vault Storage Law and are written under:

```text
vault_system/clients/<domain>/customer_review_packages/crawl_<crawl_id>_audit_<audit_id>/
```

No customer review package is written to a component-local or temporary application data store.

## API

```text
GET /api/projects/{project_id}/customer-review-package
GET /api/projects/{project_id}/customer-review-package/download
```

The status endpoint checks entitlement and materializes the current package when evidence is complete. The download endpoint revalidates the entitlement and returns the ZIP archive. Unpaid access fails closed.

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

This source change does not claim deployment or runtime acceptance. Before release, run backend compile/tests, frontend typecheck/build, authentication/ownership tests, paid/unpaid entitlement tests, ZIP-content verification, and a real verified-payment acceptance test in the isolated development runtime.
