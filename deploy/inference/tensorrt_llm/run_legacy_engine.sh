#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${ORB_INFERENCE_ENV_FILE:-$ROOT/.env.inference}"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

VENV="${TENSORRT_LLM_VENV:-$HOME/.venvs/orb-tensorrt-llm}"
ENGINE_DIR="${TENSORRT_LLM_ENGINE_DIR:-}"
PORT="${TENSORRT_LLM_PORT:-8000}"

[[ -x "$VENV/bin/trtllm-serve" ]] || { echo "trtllm-serve not found in $VENV" >&2; exit 1; }
[[ -d "$ENGINE_DIR" ]] || { echo "Compiled engine not found: $ENGINE_DIR" >&2; exit 1; }

exec "$VENV/bin/trtllm-serve" "$ENGINE_DIR" --host 127.0.0.1 --port "$PORT"
