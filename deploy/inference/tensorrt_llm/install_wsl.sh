#!/usr/bin/env bash
set -euo pipefail

VENV="${TENSORRT_LLM_VENV:-$HOME/.venvs/orb-tensorrt-llm}"
PYTHON="${TENSORRT_LLM_PYTHON:-python3.12}"

command -v nvidia-smi >/dev/null || { echo "NVIDIA WSL driver is not visible (nvidia-smi missing)." >&2; exit 1; }
command -v "$PYTHON" >/dev/null || PYTHON=python3

"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip wheel setuptools
"$VENV/bin/python" -m pip install --upgrade tensorrt_llm

"$VENV/bin/trtllm-serve" --help >/dev/null
printf 'TensorRT-LLM installed in %s\n' "$VENV"
