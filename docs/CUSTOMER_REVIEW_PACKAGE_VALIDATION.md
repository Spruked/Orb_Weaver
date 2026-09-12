# Customer Review Package Validation Checklist

Run this in the native Orb Weaver development environment before any Docker packaging or deployment.

```bash
cd /home/bryan/projects/Orb_Weaver
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

1. Unpaid account: Reports shows Full Review Package locked; basic CSV/PDF exports remain available.
2. Verified $49 Package 1 account: package status becomes eligible after crawl + audit complete.
3. Verified $99 Package 2 account: same full-package entitlement.
4. Downloaded ZIP contains exactly:
   - `report.html`
   - `manifest.json`
   - `crawl.csv`
   - `crawl.json`
   - `audit.csv`
   - `audit.json`
   - `website_context.json`
   - `pointer_map.json`
5. Confirm `manifest.json` source crawl/audit IDs match the project.
6. Confirm every manifest SHA-256 matches its listed evidence file.
7. Confirm another customer cannot read or download the project's package.
8. Confirm `/ws/orb-pointer` and `/ws/lidar-2d-mapping` still connect at their existing URLs.

Do not Dockerize this change until these checks pass.
