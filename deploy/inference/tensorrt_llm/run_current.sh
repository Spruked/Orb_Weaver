#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${ORB_INFERENCE_ENV_FILE:-$ROOT/.env.inference}"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

VENV="${TENSORRT_LLM_VENV:-$HOME/.venvs/orb-tensorrt-llm}"
MODEL="${TENSORRT_LLM_MODEL_PATH:-}"
PORT="${TENSORRT_LLM_PORT:-8000}"

[[ -x "$VENV/bin/trtllm-serve" ]] || { echo "trtllm-serve not found in $VENV" >&2; exit 1; }
[[ -n "$MODEL" ]] || { echo "Set TENSORRT_LLM_MODEL_PATH in $ENV_FILE" >&2; exit 1; }
read -r -a EXTRA <<< "${TENSORRT_LLM_EXTRA_ARGS:-}"

exec "$VENV/bin/trtllm-serve" "$MODEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  "${EXTRA[@]}"
