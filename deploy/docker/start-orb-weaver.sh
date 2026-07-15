#!/bin/sh
set -eu

: "${ORB_WEAVER_VAULT_ROOT:=/app/vault_system}"
: "${ORB_WEAVER_SUBSTRATE_ROOT:=$ORB_WEAVER_VAULT_ROOT}"
: "${DATABASE_URL:=sqlite:////app/vault_system/databases/orb_weaver.db}"
: "${ORB_TTS_CACHE_DIR:=$ORB_WEAVER_VAULT_ROOT/runtime/tts_cache}"
: "${CHROME_DEVTOOLS_OUTPUT_ROOT:=$ORB_WEAVER_VAULT_ROOT/runtime/browser_reviews}"

export ORB_WEAVER_VAULT_ROOT
export ORB_WEAVER_SUBSTRATE_ROOT
export DATABASE_URL
export ORB_TTS_CACHE_DIR
export CHROME_DEVTOOLS_OUTPUT_ROOT

mkdir -p \
    "$ORB_WEAVER_VAULT_ROOT/clients" \
    "$ORB_WEAVER_VAULT_ROOT/databases" \
    "$ORB_WEAVER_VAULT_ROOT/posteriori" \
    "$ORB_WEAVER_VAULT_ROOT/reports" \
    "$ORB_WEAVER_VAULT_ROOT/indexes" \
    "$ORB_WEAVER_VAULT_ROOT/manifests" \
    "$ORB_WEAVER_VAULT_ROOT/schemas" \
    "$ORB_WEAVER_VAULT_ROOT/runtime/tts_cache" \
    "$ORB_WEAVER_VAULT_ROOT/runtime/browser_reviews" \
    "$ORB_WEAVER_VAULT_ROOT/runtime/state" \
    "$ORB_WEAVER_VAULT_ROOT/runtime/logs" \
    "$ORB_WEAVER_VAULT_ROOT/runtime/backend_data_compat"

# Legacy relative paths remain compatibility links only. They never become
# independent stores inside the container.
rm -rf /app/backend/data /app/backend/report_compiler
ln -s "$ORB_WEAVER_VAULT_ROOT/runtime/backend_data_compat" /app/backend/data
ln -s "$ORB_WEAVER_VAULT_ROOT/reports" /app/backend/report_compiler

uvicorn main:app --host 0.0.0.0 --port 16500 &
BACKEND_PID="$!"

nginx -g "daemon off;" &
FRONTEND_PID="$!"

trap 'kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true' INT TERM

while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
    sleep 1
done

kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
