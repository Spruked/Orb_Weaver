#!/usr/bin/env bash
set -euo pipefail

SERVICE_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/iss-scale-widget.service"
systemctl --user disable --now iss-scale-widget.service 2>/dev/null || true
rm -f "$SERVICE_FILE"
systemctl --user daemon-reload
echo "Removed $SERVICE_FILE"
