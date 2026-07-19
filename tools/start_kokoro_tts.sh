#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VAULT_ROOT="${ORB_WEAVER_VAULT_ROOT:-$ROOT/vault_system}"
PID_FILE="$VAULT_ROOT/runtime/state/kokoro_tts.pid"
LOG_FILE="$VAULT_ROOT/runtime/logs/kokoro_tts.log"
PYTHON_BIN="${KOKORO_PYTHON:-/home/bryan/py312/bin/python}"
HOST="${KOKORO_HOST:-0.0.0.0}"
PORT="${KOKORO_PORT:-8880}"

mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "Kokoro TTS already running: pid $old_pid"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

cd "$ROOT"
export KOKORO_DEVICE="${KOKORO_DEVICE:-cuda}"
export KOKORO_DEFAULT_VOICE="${KOKORO_DEFAULT_VOICE:-am_echo}"
export KOKORO_DEFAULT_SPEED="${KOKORO_DEFAULT_SPEED:-1.05}"

setsid "$PYTHON_BIN" -m uvicorn tools.kokoro_openai_tts_server:app \
  --host "$HOST" \
  --port "$PORT" \
  > "$LOG_FILE" 2>&1 < /dev/null &

echo "$!" > "$PID_FILE"
echo "Kokoro TTS started: pid $(cat "$PID_FILE"), log $LOG_FILE"
