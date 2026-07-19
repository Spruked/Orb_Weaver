#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vault_system.paths import LOGS_ROOT


DEFAULT_TOOLS = [
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

MUTATING_TOOLS = {
    "orb_click",
    "orb_double_click",
    "orb_scroll",
    "orb_type",
    "orb_hotkey",
    "orb_move_mouse",
    "orb_drag",
    "orb_open_app",
    "orb_browser_open",
    "orb_browser_navigate",
    "orb_browser_click",
    "orb_browser_type",
    "orb_browser_scroll",
    "orb_clipboard_write",
    "orb_wait",
}


class AuditWriter:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, event: Dict[str, Any]) -> None:
        event = {"ts": time.time(), **event}
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True) + "\n")


class MCPProcess:
    def __init__(self, root: str, python_cmd: List[str], timeout: float):
        self.root = root
        self.python_cmd = python_cmd
        self.timeout = timeout
        self._lock = threading.RLock()
        self._process: Optional[subprocess.Popen[str]] = None
        self._request_id = 1
        self._stderr_lines: "queue.Queue[str]" = queue.Queue(maxsize=100)

    @property
    def server_path(self) -> str:
        raw_path = Path(self.root) / "orb_mcp_server.py"
        if self.python_cmd and self.python_cmd[0].lower().endswith(".exe"):
            try:
                converted = subprocess.run(
                    ["wslpath", "-w", str(raw_path)],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=True,
                )
                return converted.stdout.strip()
            except Exception:
                return str(raw_path)
        return str(raw_path)

    @property
    def local_server_path(self) -> Path:
        return Path(self.root) / "orb_mcp_server.py"

    def health(self) -> Dict[str, Any]:
        return {
            "ok": self.local_server_path.exists(),
            "root": self.root,
            "server": self.server_path,
            "local_server": str(self.local_server_path),
            "python_cmd": self.python_cmd,
            "running": bool(self._process and self._process.poll() is None),
            "stderr_tail": list(self._stderr_lines.queue)[-20:],
        }

    def list_tools(self) -> Dict[str, Any]:
        return self.request("tools/list", {})

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
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
                self.stop()
                raise

    def stop(self) -> None:
        with self._lock:
            if self._process and self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except Exception:
                    self._process.kill()
            self._process = None

    def _ensure_process(self) -> subprocess.Popen[str]:
        if self._process and self._process.poll() is None:
            return self._process
        command = self.python_cmd + [self.server_path]
        self._process = subprocess.Popen(
            command,
            cwd=self.root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        self._read_response(0)
        return self._process

    def _drain_stderr(self) -> None:
        if not self._process or not self._process.stderr:
            return
        for line in self._process.stderr:
            line = line.rstrip()
            if not line:
                continue
            if self._stderr_lines.full():
                try:
                    self._stderr_lines.get_nowait()
                except Exception:
                    pass
            self._stderr_lines.put(line)

    def _read_response(self, req_id: int) -> Dict[str, Any]:
        if not self._process or not self._process.stdout:
            raise RuntimeError("MCP process is not running")
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            line = self._process.stdout.readline()
            if not line:
                if self._process.poll() is not None:
                    raise RuntimeError("MCP process exited before responding")
                time.sleep(0.05)
                continue
            parsed = json.loads(line)
            if parsed.get("id") == req_id:
                return parsed
        raise TimeoutError(f"Timed out waiting for MCP response id={req_id}")


class RelayHandler(BaseHTTPRequestHandler):
    mcp: MCPProcess
    token: str
    audit: AuditWriter
    enable_mutation: bool

    def do_GET(self) -> None:
        if not self._authorized():
            self._json({"error": "unauthorized"}, 401)
            return
        if self.path == "/health":
            self._json(self.mcp.health())
            return
        if self.path == "/tools/list":
            self._json(self.mcp.list_tools())
            return
        self._json({"error": "not_found"}, 404)

    def do_POST(self) -> None:
        if not self._authorized():
            self._json({"error": "unauthorized"}, 401)
            return
        payload = self._read_json()
        if self.path == "/tools/call":
            name = str(payload.get("name") or "")
            arguments = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {}
            if name in MUTATING_TOOLS and not self.enable_mutation:
                result = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "result": {
                        "content": [{"type": "text", "text": f"Host relay read-only clamp blocked mutating tool: {name}"}],
                        "isError": True,
                    },
                }
                self.audit.write({
                    "event": "tool_call_blocked",
                    "tool": name,
                    "reason": "read_only_macro_1_clamp",
                    "client": self.client_address[0],
                })
                self._json(result)
                return
            started = time.perf_counter()
            result = self.mcp.call_tool(name, arguments)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
            self.audit.write({
                "event": "tool_call",
                "tool": name,
                "client": self.client_address[0],
                "elapsed_ms": elapsed_ms,
                "is_error": bool(((result.get("result") or {}).get("isError"))),
                "arguments": arguments if name in {"orb_macro_1_verify", "orb_read_desktop_region"} else {},
                "result": result.get("result") if name in {"orb_macro_1_verify", "orb_read_desktop_region"} else None,
            })
            self._json(result)
            return
        if self.path == "/stop":
            self.mcp.stop()
            self._json({"ok": True})
            return
        self._json({"error": "not_found"}, 404)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[orb-mcp-relay] {self.address_string()} {fmt % args}", flush=True)

    def _authorized(self) -> bool:
        if not self.token:
            return True
        auth = self.headers.get("Authorization", "")
        return auth == f"Bearer {self.token}"

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _json(self, data: Dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Host HTTP relay for the R-drive ORB MCP stdio server.")
    parser.add_argument("--host", default=os.getenv("ORB_MCP_RELAY_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("ORB_MCP_RELAY_PORT", "8765")))
    default_mcp_root = (
        "/mnt/r/mcp_server"
        if os.path.isdir("/mnt/r/mcp_server")
        else "/mnt/r/mpc_server"
    )
    parser.add_argument(
        "--root",
        default=os.getenv("ORB_DESKTOP_MCP_ROOT", default_mcp_root),
    )
    parser.add_argument("--python", default=os.getenv("ORB_DESKTOP_MCP_PYTHON", "python3.12"))
    parser.add_argument("--token", default=os.getenv("ORB_MCP_RELAY_TOKEN", ""))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("ORB_MCP_RELAY_TIMEOUT", "30")))
    parser.add_argument("--audit-log", default=os.getenv("ORB_MCP_RELAY_AUDIT_LOG", str(LOGS_ROOT / "orb_mcp_host_relay_audit.jsonl")))
    parser.add_argument("--enable-mutation", action="store_true", default=os.getenv("ORB_MCP_ENABLE_MUTATION", "").lower() in {"1", "true", "yes"})
    args = parser.parse_args()

    python_cmd = args.python.split()
    RelayHandler.mcp = MCPProcess(args.root, python_cmd, args.timeout)
    RelayHandler.token = args.token
    RelayHandler.audit = AuditWriter(args.audit_log)
    RelayHandler.enable_mutation = bool(args.enable_mutation)
    server = ThreadingHTTPServer((args.host, args.port), RelayHandler)
    print(
        json.dumps({
            "status": "listening",
            "host": args.host,
            "port": args.port,
            "root": args.root,
            "python_cmd": python_cmd,
            "read_only_clamp": not RelayHandler.enable_mutation,
            "audit_log": args.audit_log,
            "tools": DEFAULT_TOOLS,
        }),
        flush=True,
    )
    try:
        server.serve_forever()
    finally:
        RelayHandler.mcp.stop()


if __name__ == "__main__":
    main()
