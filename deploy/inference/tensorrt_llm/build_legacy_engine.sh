#!/usr/bin/env bash
set -euo pipefail

# Use only inside a pinned TensorRT-LLM environment that still ships
# trtllm-build. Current releases may not provide that command.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${ORB_INFERENCE_ENV_FILE:-$ROOT/.env.inference}"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

VENV="${TENSORRT_LLM_VENV:-$HOME/.venvs/orb-tensorrt-llm}"
CHECKPOINT="${TENSORRT_LLM_CHECKPOINT_DIR:-}"
ENGINE_DIR="${TENSORRT_LLM_ENGINE_DIR:-}"
MAX_BATCH="${TENSORRT_LLM_MAX_BATCH_SIZE:-1}"
MAX_INPUT="${TENSORRT_LLM_MAX_INPUT_LEN:-1536}"
MAX_SEQ="${TENSORRT_LLM_MAX_SEQ_LEN:-2048}"

BUILD="$VENV/bin/trtllm-build"
[[ -x "$BUILD" ]] || {
  echo "trtllm-build is not present. Install the deliberately pinned legacy TensorRT-LLM release selected for this engine lane." >&2
  exit 2
}
[[ -d "$CHECKPOINT" ]] || { echo "Set TENSORRT_LLM_CHECKPOINT_DIR to a converted TensorRT-LLM checkpoint." >&2; exit 1; }
[[ -n "$ENGINE_DIR" ]] || { echo "Set TENSORRT_LLM_ENGINE_DIR." >&2; exit 1; }

mkdir -p "$ENGINE_DIR"
exec "$BUILD" \
  --checkpoint_dir "$CHECKPOINT" \
  --output_dir "$ENGINE_DIR" \
  --max_batch_size "$MAX_BATCH" \
  --max_input_len "$MAX_INPUT" \
  --max_seq_len "$MAX_SEQ"
