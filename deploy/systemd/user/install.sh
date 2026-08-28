#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
UNIT_DIR="${HOME}/.config/systemd/user"
CONFIG_DIR="${HOME}/.config/orb-weaver"
INFERENCE_ENV="${CONFIG_DIR}/inference.env"
RUNTIME_ENV="${CONFIG_DIR}/runtime.env"

install -d -m 0755 "${UNIT_DIR}" "${CONFIG_DIR}"

install -m 0644 "${SCRIPT_DIR}/orb-kokoro-tts.service" "${UNIT_DIR}/orb-kokoro-tts.service"
install -m 0644 "${SCRIPT_DIR}/orb-llamacpp.service" "${UNIT_DIR}/orb-llamacpp.service"
install -m 0644 "${SCRIPT_DIR}/orb-llamacpp.path" "${UNIT_DIR}/orb-llamacpp.path"
install -m 0644 "${SCRIPT_DIR}/orb-inference-gateway.service" "${UNIT_DIR}/orb-inference-gateway.service"
install -m 0644 "${SCRIPT_DIR}/orb-weaver-api.service" "${UNIT_DIR}/orb-weaver-api.service"

if [[ ! -f "${INFERENCE_ENV}" ]]; then
  install -m 0644 "${SCRIPT_DIR}/inference.env.example" "${INFERENCE_ENV}"
fi

if [[ ! -f "${RUNTIME_ENV}" ]]; then
  install -m 0644 "${SCRIPT_DIR}/runtime.env.example" "${RUNTIME_ENV}"
fi

if command -v loginctl >/dev/null 2>&1; then
  loginctl enable-linger "${USER}" || true
fi

systemctl --user daemon-reload
systemctl --user enable orb-kokoro-tts.service
systemctl --user enable orb-llamacpp.path
systemctl --user enable orb-inference-gateway.service
systemctl --user enable orb-weaver-api.service

systemctl --user start orb-kokoro-tts.service
systemctl --user start orb-inference-gateway.service
systemctl --user start orb-weaver-api.service

MODEL_PATH="$(grep -E '^LLAMACPP_MODEL_PATH=' "${INFERENCE_ENV}" | tail -n 1 | cut -d= -f2-)"
if [[ -n "${MODEL_PATH}" && -f "${MODEL_PATH}" ]]; then
  systemctl --user enable orb-llamacpp.service
  systemctl --user start orb-llamacpp.service
else
  systemctl --user start orb-llamacpp.path
  echo "llama.cpp service armed by path watcher; model not found at ${MODEL_PATH:-<unset>}"
fi

echo "Orb runtime user services installed."
systemctl --user --no-pager --full status \
  orb-kokoro-tts.service \
  orb-llamacpp.service \
  orb-inference-gateway.service \
  orb-weaver-api.service || true
