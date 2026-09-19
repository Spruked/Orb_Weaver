# Customer Review Package Validation Checklist

Run this in the native Orb Weaver development environment before any Docker packaging or deployment.

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate

python -m py_compile \
  backend/app/routers/customer_review_package.py \
  backend/app/routers/orb_telemetry.py

cd backend
pytest -q tests/test_customer_review_package.py

cd ../frontend
npm run typecheck
npm run build
```

Then verify in the development UI:

1. A generic cart order, unrelated $99 SKU, wrong-currency order, unverified payment, or revoked entitlement does not unlock the Full Review Package.
2. Verified canonical Package 1 (`OW-FULL-REVIEW-PACKAGE-1`, USD $49) purchased through the project-bound governed checkout becomes eligible after its matching crawl + audit complete.
3. Verified canonical Package 2 (`OW-FULL-REVIEW-PACKAGE-2`, USD $99) purchased through the project-bound governed checkout receives the same bundle entitlement.
4. The latest completed crawl is never paired with an older audit; package readiness remains blocked until an audit tied to that exact crawl exists.
5. Downloaded ZIP contains exactly:
   - `report.html`
   - `manifest.json`
   - `crawl.csv`
   - `crawl.json`
   - `audit.csv`
   - `audit.json`
   - `website_context.json`
   - `pointer_map.json`
6. Confirm `manifest.json` source crawl/audit IDs match the project and entitlement identifiers match the verified project-bound order.
7. Confirm every manifest SHA-256 matches its listed evidence file.
8. Confirm repeated status/download requests reuse the same source-keyed package instead of rebuilding it.
9. Confirm concurrent package requests cannot expose a partially written ZIP; publication must remain atomic.
10. Confirm another customer cannot read or download the project's package.
11. Confirm `/ws/orb-pointer` and `/ws/lidar-2d-mapping` still connect at their existing URLs.

Do not Dockerize this change until these checks pass.
