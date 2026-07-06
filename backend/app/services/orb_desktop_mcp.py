from __future__ import annotations

import json
import select
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_ORB_MCP_TOOLS = [
    "orb_control",
    "orb_click",
    "orb_double_click",
    "orb_scroll",
    "orb_type",
    "orb_hotkey",
    "orb_move_mouse",
    "orb_drag",
    "orb_screenshot",
    "orb_ocr_status",
    "orb_ocr_screen",
    "orb_read_desktop_region",
    "orb_open_app",
    "orb_browser_open",
    "orb_browser_navigate",
    "orb_browser_click",
    "orb_browser_type",
    "orb_browser_scroll",
    "orb_browser_screenshot",
    "orb_clipboard_read",
    "orb_clipboard_write",
    "orb_list_windows",
    "orb_get_display_size",
    "orb_wait",
    "orb_snapshot",
    "orb_substrate_status",
    "orb_session_status",
    "orb_macro_1_verify",
]


class ORBDesktopMCPClient:
    def __init__(
        self,
        root: str,
        python_bin: str = "python3.12",
        timeout_seconds: float = 20.0,
        remote_url: Optional[str] = None,
        remote_token: Optional[str] = None,
    ):
        self.root = Path(root).expanduser()
        self.python_bin = python_bin
        self.timeout_seconds = timeout_seconds
        self.remote_url = (remote_url or "").rstrip("/")
        self.remote_token = remote_token or ""
        self._lock = threading.RLock()
        self._process: Optional[subprocess.Popen[str]] = None
        self._request_id = 1
        self._tools_cache: Optional[List[Dict[str, Any]]] = None

    @property
    def server_path(self) -> Path:
        return self.root / "orb_mcp_server.py"

    def available(self) -> bool:
        if self.remote_url:
            return self._remote_health().get("ok", False)
        return self._direct_available()

    def _direct_available(self) -> bool:
        return self.server_path.exists()

    def close(self) -> None:
        with self._lock:
            if self._process and self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except Exception:
                    self._process.kill()
            self._process = None

    def list_tools(self) -> Dict[str, Any]:
        if self.remote_url:
            try:
                payload = self._remote_get("/tools/list")
                tools = (((payload or {}).get("result") or {}).get("tools") or [])
                return {
                    "status": "available",
                    "root": self.remote_url,
                    "transport": "http_relay",
                    "tools": tools if isinstance(tools, list) else [],
                    "cached": False,
                }
            except Exception as exc:
                fallback = self._list_tools_direct()
                fallback["remote_error"] = str(exc)
                return fallback
        return self._list_tools_direct()

    def _list_tools_direct(self) -> Dict[str, Any]:
        if not self._direct_available():
            return {
                "status": "unavailable",
                "root": str(self.root),
                "tools": [],
                "error": f"ORB MCP server not found: {self.server_path}",
            }
        if self._tools_cache is not None:
            return {"status": "available", "root": str(self.root), "tools": self._tools_cache, "cached": True}
        response = self._request("tools/list", {})
        tools = (((response or {}).get("result") or {}).get("tools") or [])
        self._tools_cache = tools if isinstance(tools, list) else []
        return {"status": "available", "root": str(self.root), "tools": self._tools_cache, "cached": False}

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.remote_url:
            try:
                response = self._remote_post("/tools/call", {"name": name, "arguments": arguments})
                if "error" in response:
                    return {
                        "content": [{"type": "text", "text": response["error"]}],
                        "isError": True,
                    }
                return (response.get("result") or {"content": [], "isError": True})
            except Exception as exc:
                return {
                    "content": [{"type": "text", "text": f"ORB MCP host relay unavailable: {exc}"}],
                    "isError": True,
                }
        if not self.available():
            return {
                "content": [{"type": "text", "text": f"ORB MCP server not found: {self.server_path}"}],
                "isError": True,
            }
        response = self._request("tools/call", {"name": name, "arguments": arguments})
        if "error" in response:
            return {
                "content": [{"type": "text", "text": response["error"].get("message", "ORB MCP error")}],
                "isError": True,
                "jsonrpc_error": response["error"],
            }
        return (response.get("result") or {"content": [], "isError": True})

    def _remote_health(self) -> Dict[str, Any]:
        if not self.remote_url:
            return {"ok": False}
        try:
            return self._remote_get("/health")
        except Exception:
            return {"ok": False}

    def _remote_get(self, path: str) -> Dict[str, Any]:
        request = urllib.request.Request(f"{self.remote_url}{path}", headers=self._remote_headers())
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _remote_post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw = json.dumps(payload).encode("utf-8")
        headers = {**self._remote_headers(), "Content-Type": "application/json"}
        request = urllib.request.Request(f"{self.remote_url}{path}", data=raw, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _remote_headers(self) -> Dict[str, str]:
        if not self.remote_token:
            return {}
        return {"Authorization": f"Bearer {self.remote_token}"}

    def _request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            process = self._ensure_process()
            req_id = self._request_id
            self._request_id += 1
            payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
            try:
                assert process.stdin is not None
                process.stdin.write(json.dumps(payload) + "\n")
                process.stdin.flush()
                return self._read_response(req_id)
            except Exception:
                self.close()
                raise

    def _ensure_process(self) -> subprocess.Popen[str]:
        if self._process and self._process.poll() is None:
            return self._process
        self._tools_cache = None
        self._process = subprocess.Popen(
            [self.python_bin, str(self.server_path)],
            cwd=str(self.root),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        try:
            self._read_response(0, allow_other_ids=False)
        except Exception:
            self.close()
            raise
        return self._process

    def _read_response(self, req_id: int, allow_other_ids: bool = True) -> Dict[str, Any]:
        if not self._process or not self._process.stdout:
            raise RuntimeError("ORB MCP process is not running")
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            remaining = max(0.05, deadline - time.monotonic())
            ready, _, _ = select.select([self._process.stdout], [], [], min(remaining, 0.25))
            if not ready:
                if self._process.poll() is not None:
                    stderr = self._process.stderr.read() if self._process.stderr else ""
                    raise RuntimeError(f"ORB MCP exited early: {stderr.strip()}")
                continue
            line = self._process.stdout.readline()
            if not line:
                continue
            parsed = json.loads(line)
            if parsed.get("id") == req_id or allow_other_ids:
                return parsed
        raise TimeoutError(f"Timed out waiting for ORB MCP response id={req_id}")
