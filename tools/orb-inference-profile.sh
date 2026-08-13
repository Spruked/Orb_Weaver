#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ORB_INFERENCE_ENV_FILE:-$ROOT/.env.inference}"
RUN_DIR="${ORB_INFERENCE_RUN_DIR:-$ROOT/vault_system/runtime/inference_gateway/pids}"
LOG_DIR="${ORB_INFERENCE_LOG_DIR:-$ROOT/vault_system/runtime/inference_gateway/logs}"
mkdir -p "$RUN_DIR" "$LOG_DIR"

[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

pid_file() { printf '%s/%s.pid' "$RUN_DIR" "$1"; }

alive() {
  local name="$1" file
  file="$(pid_file "$name")"
  [[ -f "$file" ]] && kill -0 "$(cat "$file")" 2>/dev/null
}

stop_one() {
  local name="$1" file pid
  file="$(pid_file "$name")"
  if [[ -f "$file" ]]; then
    pid="$(cat "$file")"
    kill "$pid" 2>/dev/null || true
    for _ in {1..30}; do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.2
    done
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$file"
  fi
}

start_bg() {
  local name="$1"; shift
  if alive "$name"; then
    echo "$name already running (PID $(cat "$(pid_file "$name")"))"
    return
  fi
  nohup "$@" >"$LOG_DIR/$name.log" 2>&1 &
  echo $! >"$(pid_file "$name")"
  echo "$name started (PID $!, log $LOG_DIR/$name.log)"
}

stop_engines() {
  stop_one llama
  stop_one aphrodite
  stop_one tensorrt
}

case "${1:-status}" in
  gateway)
    start_bg gateway bash -lc "cd '$ROOT/backend' && exec python -m uvicorn inference_gateway:app --host 127.0.0.1 --port ${ORB_INFERENCE_GATEWAY_PORT:-16520}"
    ;;
  llama|llamacpp)
    stop_engines
    start_bg llama bash "$ROOT/deploy/inference/llama_cpp/run.sh"
    ;;
  aphrodite|scale)
    stop_engines
    start_bg aphrodite bash "$ROOT/deploy/inference/aphrodite/run.sh"
    ;;
  tensorrt|accelerated)
    stop_engines
    start_bg tensorrt bash "$ROOT/deploy/inference/tensorrt_llm/run_current.sh"
    ;;
  tensorrt-engine)
    stop_engines
    start_bg tensorrt bash "$ROOT/deploy/inference/tensorrt_llm/run_legacy_engine.sh"
    ;;
  ollama|fallback)
    stop_engines
    echo "GPU engine profiles stopped. Ollama remains the configured fallback provider."
    ;;
  stop)
    stop_engines
    stop_one gateway
    ;;
  status)
    for name in gateway llama aphrodite tensorrt; do
      if alive "$name"; then echo "$name: running PID $(cat "$(pid_file "$name")")"; else echo "$name: stopped"; fi
    done
    curl -fsS "http://127.0.0.1:${ORB_INFERENCE_GATEWAY_PORT:-16520}/api/providers" || true
    echo
    ;;
  *)
    echo "Usage: $0 {gateway|llama|aphrodite|tensorrt|tensorrt-engine|ollama|status|stop}" >&2
    exit 2
    ;;
esac
