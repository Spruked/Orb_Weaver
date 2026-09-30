#!/usr/bin/env bash
set -euo pipefail

WIDGET_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BINARY="$WIDGET_ROOT/src-tauri/target/release/iss-scale-widget"
SERVICE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
SERVICE_FILE="$SERVICE_DIR/iss-scale-widget.service"

if [[ ! -x "$BINARY" ]]; then
  echo "Release binary not found: $BINARY" >&2
  echo "Run 'npm run tauri:build' in widget/ first." >&2
  exit 1
fi

mkdir -p "$SERVICE_DIR"
sed "s|__ISS_WIDGET_ROOT__|$WIDGET_ROOT|g; s|__ISS_WIDGET_BINARY__|$BINARY|g" \
  "$WIDGET_ROOT/scripts/iss-scale-widget.service.in" > "$SERVICE_FILE"

systemctl --user daemon-reload
systemctl --user enable --now iss-scale-widget.service
echo "Installed and started $SERVICE_FILE"
