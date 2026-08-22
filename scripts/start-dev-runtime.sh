#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VAULT_ROOT="${ROOT_DIR}/vault_system"
DEV_ROOT="${VAULT_ROOT}/development"
LOG_ROOT="${DEV_ROOT}/logs"
PID_ROOT="${DEV_ROOT}/pids"

mkdir -p "${DEV_ROOT}/databases" "${DEV_ROOT}/runtime/tts_cache" "${LOG_ROOT}" "${PID_ROOT}"

export DEBUG="${DEBUG:-development}"
export ORB_WEAVER_VAULT_ROOT="${VAULT_ROOT}"
export ORB_WEAVER_SUBSTRATE_ROOT="${VAULT_ROOT}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///${DEV_ROOT}/databases/orb_weaver_dev.db}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/1}"
export PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-http://127.0.0.1:16610}"
export LOCAL_LLM_URL="${LOCAL_LLM_URL:-http://127.0.0.1:16520/api/generate}"
export LOCAL_LLM_MODEL="${LOCAL_LLM_MODEL:-orb-auto}"
export ORB_TTS_CACHE_DIR="${ORB_TTS_CACHE_DIR:-${DEV_ROOT}/runtime/tts_cache}"
export FASTER_WHISPER_STT_URL="${FASTER_WHISPER_STT_URL:-http://127.0.0.1:9000/stt}"
export ORB_TTS_QWEN_URL="${ORB_TTS_QWEN_URL:-http://127.0.0.1:9880/speak}"
export ORB_TTS_TIMEOUT_SECONDS="${ORB_TTS_TIMEOUT_SECONDS:-180}"
export ORB_TTS_QWEN_VOICE="${ORB_TTS_QWEN_VOICE:-OrbWeaver}"
export ORB_TTS_QWEN_PAYLOAD_MODE="${ORB_TTS_QWEN_PAYLOAD_MODE:-qwen-voice-clone}"
export ORB_TTS_KOKORO_URL="${ORB_TTS_KOKORO_URL:-http://127.0.0.1:8880/speak}"
export ORB_WEAVER_SITE_ORB_SOURCE_CRAWL_ID="${ORB_WEAVER_SITE_ORB_SOURCE_CRAWL_ID:-59}"
export BACKEND_PORT="${BACKEND_PORT:-16600}"
export FRONTEND_PORT="${FRONTEND_PORT:-16610}"
export REACT_APP_API_URL="${REACT_APP_API_URL:-http://127.0.0.1:${BACKEND_PORT}}"
export BROWSER="${BROWSER:-none}"
export PORT="${FRONTEND_PORT}"
BACKEND_PYTHON="${BACKEND_PYTHON:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${BACKEND_PYTHON}" ]]; then
  BACKEND_PYTHON="python3.12"
fi

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

cd "${ROOT_DIR}/backend"
"${BACKEND_PYTHON}" -m uvicorn main:app --host 0.0.0.0 --port "${BACKEND_PORT}" >"${LOG_ROOT}/backend-${BACKEND_PORT}.log" 2>&1 &
BACKEND_PID="$!"
echo "${BACKEND_PID}" >"${PID_ROOT}/backend-${BACKEND_PORT}.pid"

cd "${ROOT_DIR}/frontend"
npm start >"${LOG_ROOT}/frontend-${FRONTEND_PORT}.log" 2>&1 &
FRONTEND_PID="$!"
echo "${FRONTEND_PID}" >"${PID_ROOT}/frontend-${FRONTEND_PORT}.pid"

echo "Orb Weaver dev backend:  http://127.0.0.1:${BACKEND_PORT}"
echo "Orb Weaver dev frontend: http://127.0.0.1:${FRONTEND_PORT}"
echo "Dev vault namespace:     ${DEV_ROOT}"
echo "Logs:                    ${LOG_ROOT}"

wait -n "${BACKEND_PID}" "${FRONTEND_PID}"
