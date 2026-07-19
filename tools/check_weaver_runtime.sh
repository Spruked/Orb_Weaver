#!/usr/bin/env bash
set -u

DEV_BACKEND_URL="${DEV_BACKEND_URL:-http://127.0.0.1:16500}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
WINDOWS_TESSERACT="${WINDOWS_TESSERACT:-/mnt/c/Program Files/Tesseract-OCR/tesseract.exe}"
OCR_IMAGE="${1:-}"
failures=0

if [ -z "${TESSDATA_PREFIX:-}" ] && [ -f /usr/share/tesseract-ocr/5/tessdata/eng.traineddata ]; then
  export TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
fi

check_url() {
  local label="$1"
  local url="$2"
  if curl --silent --show-error --fail --max-time 8 "$url" >/dev/null; then
    echo "PASS $label $url"
  else
    echo "FAIL $label $url"
    failures=$((failures + 1))
  fi
}

check_url "Weaver dev backend" "$DEV_BACKEND_URL/"
check_url "Ollama" "$OLLAMA_URL/api/tags"

if command -v tesseract >/dev/null 2>&1; then
  echo "PASS WSL Tesseract $(tesseract --version 2>&1 | head -n 1)"
else
  echo "FAIL WSL Tesseract missing"
  failures=$((failures + 1))
fi

if [ -x "$WINDOWS_TESSERACT" ]; then
  echo "PASS Windows Tesseract $("$WINDOWS_TESSERACT" --version 2>&1 | head -n 1 | tr -d '\r')"
else
  echo "FAIL Windows Tesseract missing at $WINDOWS_TESSERACT"
  failures=$((failures + 1))
fi

if [ -n "$OCR_IMAGE" ]; then
  if [ ! -f "$OCR_IMAGE" ]; then
    echo "FAIL OCR fixture missing: $OCR_IMAGE"
    failures=$((failures + 1))
  else
    wsl_text="$(tesseract "$OCR_IMAGE" stdout 2>/dev/null || true)"
    windows_image="$(wslpath -w "$(realpath "$OCR_IMAGE")")"
    windows_text="$("$WINDOWS_TESSERACT" "$windows_image" stdout 2>/dev/null | tr -d '\r' || true)"
    [ -n "$wsl_text" ] && echo "PASS WSL OCR recognition" || { echo "FAIL WSL OCR produced no text"; failures=$((failures + 1)); }
    [ -n "$windows_text" ] && echo "PASS Windows OCR recognition" || { echo "FAIL Windows OCR produced no text"; failures=$((failures + 1)); }
  fi
fi

exit "$failures"
