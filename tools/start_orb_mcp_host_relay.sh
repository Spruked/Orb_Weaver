#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

HOST="${ORB_MCP_RELAY_HOST:-0.0.0.0}"
PORT="${ORB_MCP_RELAY_PORT:-8765}"
LOCAL_ROOT="$PWD/.runtime/rdrive_mcp_server"
PREFERRED_FALLBACK_ROOT="/mnt/r/mcp_server"
LEGACY_FALLBACK_ROOT="/mnt/r/mpc_server"
FALLBACK_ROOT="$PREFERRED_FALLBACK_ROOT"
if [ ! -f "$FALLBACK_ROOT/orb_mcp_server.py" ] && [ -f "$LEGACY_FALLBACK_ROOT/orb_mcp_server.py" ]; then
    FALLBACK_ROOT="$LEGACY_FALLBACK_ROOT"
fi
if [[ -n "${ORB_DESKTOP_MCP_ROOT:-}" ]]; then
  ROOT="$ORB_DESKTOP_MCP_ROOT"
elif [[ -f "$LOCAL_ROOT/orb_mcp_server.py" ]]; then
  ROOT="$LOCAL_ROOT"
else
  ROOT="$FALLBACK_ROOT"
fi
PYTHON_CMD="${ORB_DESKTOP_MCP_PYTHON:-py.exe -3.12}"
TOKEN="${ORB_MCP_RELAY_TOKEN:-}"

exec python3.12 tools/orb_mcp_host_relay.py \
  --host "$HOST" \
  --port "$PORT" \
  --root "$ROOT" \
  --python "$PYTHON_CMD" \
  --token "$TOKEN"
