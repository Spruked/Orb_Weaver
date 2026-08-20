from __future__ import annotations

from typing import Any, Dict

from .orb_desktop_mcp import ORBDesktopMCPClient


class DockStationAdapter:
    """Adapter boundary only; the Website ORB does not ship Electron."""

    def __init__(self, root: str = "", remote_url: str = "", remote_token: str = ""):
        self.enabled = bool(root or remote_url)
        self.client = ORBDesktopMCPClient(root=root or ".", remote_url=remote_url, remote_token=remote_token)

    def status(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "unconfigured", "message": "DockStation adapter is not configured for this Website ORB."}
        return {"status": "available" if self.client.available() else "unavailable"}

    def call(self, action: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "blocked", "message": "DockStation is separate from Website ORB and is not configured."}
        return self.client.call_tool(action, arguments)

