#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${LLAMACPP_INSTALL_ROOT:-$HOME/opt/llama.cpp}"
JOBS="${LLAMACPP_BUILD_JOBS:-$(nproc)}"

sudo apt-get update
sudo apt-get install -y build-essential cmake git curl libcurl4-openssl-dev

if [[ -d "$INSTALL_ROOT/.git" ]]; then
  git -C "$INSTALL_ROOT" pull --ff-only
else
  mkdir -p "$(dirname "$INSTALL_ROOT")"
  git clone https://github.com/ggml-org/llama.cpp.git "$INSTALL_ROOT"
fi

cmake -S "$INSTALL_ROOT" -B "$INSTALL_ROOT/build" \
  -DGGML_CUDA=ON \
  -DLLAMA_CURL=ON \
  -DCMAKE_BUILD_TYPE=Release
cmake --build "$INSTALL_ROOT/build" --config Release -j "$JOBS" --target llama-server

printf 'llama-server built at %s\n' "$INSTALL_ROOT/build/bin/llama-server"
