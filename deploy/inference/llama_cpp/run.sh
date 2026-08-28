#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${ORB_INFERENCE_ENV_FILE:-$ROOT/.env.inference}"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

BIN="${LLAMACPP_BIN:-$HOME/opt/llama.cpp/build/bin/llama-server}"
MODEL="${LLAMACPP_MODEL_PATH:-}"
ALIAS="${LLAMACPP_ALIAS:-orb-local}"
PORT="${LLAMACPP_PORT:-8080}"
CTX="${LLAMACPP_CTX_SIZE:-2048}"
GPU_LAYERS="${LLAMACPP_GPU_LAYERS:-99}"
PARALLEL="${LLAMACPP_PARALLEL:-1}"

[[ -x "$BIN" ]] || { echo "llama-server not found: $BIN" >&2; exit 1; }
[[ -f "$MODEL" ]] || { echo "GGUF model not found. Set LLAMACPP_MODEL_PATH in $ENV_FILE" >&2; exit 1; }

read -r -a EXTRA <<< "${LLAMACPP_EXTRA_ARGS:-}"
exec "$BIN" \
  --model "$MODEL" \
  --alias "$ALIAS" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --mmap \
  --n-gpu-layers "$GPU_LAYERS" \
  --ctx-size "$CTX" \
  --parallel "$PARALLEL" \
  --flash-attn on \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --metrics \
  "${EXTRA[@]}"
