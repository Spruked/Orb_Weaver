#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="${ORB_WEAVER_BACKEND_URL:-http://127.0.0.1:16666}"
FRONTEND_URL="${ORB_WEAVER_FRONTEND_URL:-http://127.0.0.1:16667}"
INFERENCE_URL="${ORB_WEAVER_INFERENCE_URL:-http://127.0.0.1:16520}"

say() { printf '\n=== %s ===\n' "$1"; }
fail() { printf 'FAILED: %s\n' "$1" >&2; exit 1; }

say "Development service reachability"
curl -fsS "${BACKEND_URL}/health" >/dev/null || fail "backend ${BACKEND_URL}/health"
printf 'backend:   OK %s\n' "$BACKEND_URL"
curl -fsS "${FRONTEND_URL}/" >/dev/null || fail "frontend ${FRONTEND_URL}/"
printf 'frontend:  OK %s\n' "$FRONTEND_URL"
curl -fsS "${INFERENCE_URL}/health/live" >/dev/null || fail "inference live ${INFERENCE_URL}/health/live"
printf 'inference: OK %s\n' "$INFERENCE_URL"

say "Inference readiness"
READY_JSON="$(curl -fsS "${INFERENCE_URL}/health/ready")"
printf '%s\n' "$READY_JSON"
python3 - "$READY_JSON" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
if payload.get("ready") is not True:
    raise SystemExit("inference gateway is not ready")
providers = payload.get("providers") or {}
if not any(bool(item.get("ready")) for item in providers.values() if isinstance(item, dict)):
    raise SystemExit("no inference provider is ready")
PY

say "Backend Agency and A.I.M.S. focused tests"
(
  cd "$ROOT/backend"
  python3 -m pytest -q \
    tests/test_agency_cognition.py \
    tests/test_aims_memory_bridge.py \
    tests/test_site_world_runtime_context.py
)

say "Frontend TypeScript"
(
  cd "$ROOT/frontend"
  npm run typecheck
)

say "Frontend Agency/Governor/continuity tests"
(
  cd "$ROOT/frontend"
  CI=true npm test -- --watchAll=false --runInBand \
    agency.test.ts \
    agencyRuntime.test.ts \
    agencySessionCache.test.ts \
    agencyExcursionRuntime.test.ts
)

say "Agency acceptance summary"
printf 'PASS: service reachability, inference readiness, backend Agency/A.I.M.S. tests, frontend typecheck, and focused Agency continuity tests.\n'
printf 'NEXT: browser proof on %s must still verify actual voice + LiDAR excursion + automatic return/resume.\n' "$FRONTEND_URL"
