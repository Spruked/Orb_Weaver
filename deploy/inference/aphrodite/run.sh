#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${ORB_INFERENCE_ENV_FILE:-$ROOT/.env.inference}"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

VENV="${APHRODITE_VENV:-$HOME/.venvs/orb-aphrodite}"
MODEL="${APHRODITE_MODEL_ID:-Qwen/Qwen3.5-0.8B}"
PORT="${APHRODITE_PORT:-2242}"
GPU_MEMORY="${APHRODITE_GPU_MEMORY_UTILIZATION:-0.72}"
MAX_LEN="${APHRODITE_MAX_MODEL_LEN:-2048}"
MAX_SEQS="${APHRODITE_MAX_NUM_SEQS:-4}"

[[ -x "$VENV/bin/aphrodite" ]] || { echo "Aphrodite is not installed in $VENV" >&2; exit 1; }
read -r -a EXTRA <<< "${APHRODITE_EXTRA_ARGS:-}"

exec "$VENV/bin/aphrodite" run "$MODEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --served-model-name orb-scale \
  --gpu-memory-utilization "$GPU_MEMORY" \
  --max-model-len "$MAX_LEN" \
  --max-num-seqs "$MAX_SEQS" \
  "${EXTRA[@]}"
