#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

HOST="${ORB_MCP_RELAY_HOST:-0.0.0.0}"
PORT="${ORB_MCP_RELAY_PORT:-8765}"
ROOT="${ORB_DESKTOP_MCP_ROOT:-/mnt/r/mpc_server}"
PYTHON_CMD="${ORB_DESKTOP_MCP_PYTHON:-py.exe -3.12}"
TOKEN="${ORB_MCP_RELAY_TOKEN:-}"

exec python3.12 tools/orb_mcp_host_relay.py \
  --host "$HOST" \
  --port "$PORT" \
  --root "$ROOT" \
  --python "$PYTHON_CMD" \
  --token "$TOKEN"
