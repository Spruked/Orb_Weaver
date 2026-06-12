#!/usr/bin/env bash
# setup_orb.sh
# Shell wrapper for ORB SSI installation.
# Supports: --preflight, --delta, default full install.
# Preflight always runs before SSI. Not skippable.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFLIGHT_SCRIPT="${SCRIPT_DIR}/orbs_preflight.py"
INSTALL_SCRIPT="${SCRIPT_DIR}/install_ssi.py"

# Defaults
MODE="full"
ROOT_URL=""
OUTPUT_DIR=""

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --preflight)
            MODE="preflight_only"
            shift
            ;;
        --delta)
            MODE="delta"
            shift
            ;;
        --root)
            ROOT_URL="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help|-h)
            cat <<EOF
Usage: ./setup_orb.sh [OPTIONS]

Options:
  --preflight          Run preflight scan only, print report, exit.
  --delta              Run preflight first, then delta SSI rescan.
  --root <url>         Target site root URL (required).
  --output <dir>       Output directory (required).
  --help, -h           Show this help message.

Default behavior (no flags):
  Runs preflight first, then full SSI install.
  If preflight finds warnings, prompts to continue.
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Run ./setup_orb.sh --help for usage." >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Validate required args
# ---------------------------------------------------------------------------
if [[ -z "${ROOT_URL}" ]]; then
    echo "ERROR: --root <url> is required." >&2
    exit 1
fi

if [[ -z "${OUTPUT_DIR}" ]]; then
    echo "ERROR: --output <dir> is required." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Preflight scan (always runs)
# ---------------------------------------------------------------------------
run_preflight() {
    echo ""
    echo "[setup_orb] Running preflight scan..."
    if [[ ! -f "${PREFLIGHT_SCRIPT}" ]]; then
        echo "ERROR: Preflight script not found: ${PREFLIGHT_SCRIPT}" >&2
        exit 1
    fi

    python3 "${PREFLIGHT_SCRIPT}" --root "${ROOT_URL}" --output "${OUTPUT_DIR}"
    PREFLIGHT_EXIT=$?
    if [[ ${PREFLIGHT_EXIT} -ne 0 ]]; then
        echo "ERROR: Preflight scan failed (exit ${PREFLIGHT_EXIT})." >&2
        exit 1
    fi

    # Check for warnings in report
    REPORT_FILE="${OUTPUT_DIR}/site_preflight_report.json"
    if [[ -f "${REPORT_FILE}" ]]; then
        WARNINGS=$(python3 -c "
import json,sys
try:
    with open('${REPORT_FILE}') as f:
        r=json.load(f)
        w=r.get('warnings',[])
        print(len(w))
except Exception:
    print(0)
" 2>/dev/null || echo "0")
        if [[ "${WARNINGS}" =~ ^[0-9]+$ && ${WARNINGS} -gt 0 ]]; then
            echo ""
            echo "[setup_orb] Preflight detected ${WARNINGS} warning(s)."
            read -rp "Continue with install? (y/n) " CHOICE
            case "${CHOICE}" in
                [Yy]*)
                    echo "[setup_orb] Proceeding with install..."
                    ;;
                [Nn]*|"")
                    echo "[setup_orb] Install aborted by user."
                    exit 0
                    ;;
                *)
                    echo "[setup_orb] Unrecognized choice. Aborting."
                    exit 0
                    ;;
            esac
        fi
    fi
}

# ---------------------------------------------------------------------------
# Full SSI install
# ---------------------------------------------------------------------------
run_full_install() {
    echo ""
    echo "[setup_orb] Running full SSI install..."
    if [[ ! -f "${INSTALL_SCRIPT}" ]]; then
        echo "ERROR: Install script not found: ${INSTALL_SCRIPT}" >&2
        exit 1
    fi
    python3 "${INSTALL_SCRIPT}" --root "${ROOT_URL}" --output "${OUTPUT_DIR}"
}

# ---------------------------------------------------------------------------
# Delta SSI rescan
# ---------------------------------------------------------------------------
run_delta_rescan() {
    echo ""
    echo "[setup_orb] Running delta SSI rescan..."
    if [[ ! -f "${INSTALL_SCRIPT}" ]]; then
        echo "ERROR: Install script not found: ${INSTALL_SCRIPT}" >&2
        exit 1
    fi
    python3 "${INSTALL_SCRIPT}" --root "${ROOT_URL}" --output "${OUTPUT_DIR}" --delta
}

# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

case "${MODE}" in
    preflight_only)
        run_preflight
        echo ""
        echo "[setup_orb] Preflight complete. Exiting (--preflight mode)."
        exit 0
        ;;
    full)
        run_preflight
        run_full_install
        ;;
    delta)
        run_preflight
        run_delta_rescan
        ;;
    *)
        echo "ERROR: Unknown mode: ${MODE}" >&2
        exit 1
        ;;
esac

echo ""
echo "[setup_orb] All done."
exit 0
