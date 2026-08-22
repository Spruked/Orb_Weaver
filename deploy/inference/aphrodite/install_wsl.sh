#!/usr/bin/env bash
set -euo pipefail

VENV="${APHRODITE_VENV:-$HOME/.venvs/orb-aphrodite}"
PYTHON="${APHRODITE_PYTHON:-python3.12}"

command -v nvidia-smi >/dev/null || { echo "NVIDIA WSL driver is not visible (nvidia-smi missing)." >&2; exit 1; }
command -v "$PYTHON" >/dev/null || PYTHON=python3

"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip wheel setuptools
"$VENV/bin/python" -m pip install --upgrade aphrodite-engine

"$VENV/bin/aphrodite" --help >/dev/null
printf 'Aphrodite installed in %s\n' "$VENV"
