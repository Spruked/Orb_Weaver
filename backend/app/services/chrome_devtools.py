from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ChromeDevToolsReviewRunner:
    def __init__(
        self,
        cli: str = "chrome-devtools-mcp",
        output_root: str = "browser_reviews",
        timeout_seconds: int = 60,
        start_args: Optional[List[str]] = None,
        browser_start_cmd: Optional[str] = None,
    ):
        self.cli = cli
        self.output_root = Path(output_root)
        self.timeout_seconds = timeout_seconds
        self.start_args = start_args or []
        self.browser_start_cmd = browser_start_cmd

    def _command_base(self) -> List[str]:
        if self.cli.endswith("chrome-devtools-mcp"):
            return ["chrome-devtools"]
        return [self.cli]

    def _run(self, args: List[str], run_dir: Path) -> Dict[str, Any]:
        command = self._command_base() + args
        completed = subprocess.run(
            command,
            cwd=str(run_dir),
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            env={**os.environ, "CI": "1", "CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS": "1"},
        )
        stdout: Any = completed.stdout.strip()
        if stdout:
            try:
                stdout = json.loads(stdout)
            except Exception:
                pass
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": completed.stderr.strip(),
            "ok": completed.returncode == 0,
            "mcp_error": None,
        }

    def _start_devtools(self, run_dir: Path) -> Optional[Dict[str, Any]]:
        if self.browser_start_cmd:
            try:
                subprocess.Popen(self.browser_start_cmd, shell=True)
                time.sleep(1)
            except Exception as exc:
                return {"ok": False, "mcp_error": str(exc)}

        start_args = ["start", "--headless", "--isolated", "--viewport", "1365x900"]
        chrome_path = os.environ.get("CHROME_PATH") or os.environ.get("CHROME_BIN")
        if chrome_path:
            start_args.extend(["--executablePath", chrome_path])
        for arg in self.start_args:
            start_args.extend(["--chromeArg", arg])
        if "--no-sandbox" not in self.start_args:
            start_args.extend(["--chromeArg", "--no-sandbox", "--chromeArg", "--disable-dev-shm-usage"])
        return self._run(start_args, run_dir)

    def review(self, url: str, label: str = "review") -> Dict[str, Any]:
        run_dir = self.output_root / label / datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        actions: List[Dict[str, Any]] = []
        payload = {
            "schema": "orb_weaver.browser_review.v1",
            "status": "not_run",
            "generated_at": datetime.utcnow().isoformat(),
            "url": url,
            "label": label,
            "review_dir": str(run_dir),
            "reason": "Chrome DevTools runner is configured as an external optional verifier.",
            "artifacts": {"screenshot": None, "lighthouse_dir": None},
            "summary": {"console_message_count": 0, "network_request_count": 0, "lighthouse_scores": {}},
            "error": None,
            "actions": actions,
        }
        try:
            start_result = self._start_devtools(run_dir)
            if start_result:
                actions.append({"tool": "start", "result": start_result})
                if not start_result.get("ok"):
                    raise RuntimeError(start_result.get("mcp_error") or start_result.get("stderr") or "Chrome DevTools start failed")

            for tool, args in [
                ("new_page", ["new_page", url, "--timeout", str(self.timeout_seconds * 1000)]),
                ("take_snapshot", ["take_snapshot", "--filePath", str(run_dir / "snapshot.json")]),
                ("list_console_messages", ["list_console_messages"]),
                ("list_network_requests", ["list_network_requests"]),
                ("take_screenshot", ["take_screenshot", "--filePath", str(run_dir / "screenshot.png"), "--fullPage"]),
                ("lighthouse_audit", ["lighthouse_audit", "--outputDirPath", str(run_dir / "lighthouse")]),
            ]:
                result = self._run(args, run_dir)
                actions.append({"tool": tool, "result": result})

            console_action = next((item for item in actions if item["tool"] == "list_console_messages"), None)
            network_action = next((item for item in actions if item["tool"] == "list_network_requests"), None)
            lighthouse_action = next((item for item in actions if item["tool"] == "lighthouse_audit"), None)
            console_stdout = ((console_action or {}).get("result") or {}).get("stdout")
            network_stdout = ((network_action or {}).get("result") or {}).get("stdout")
            lighthouse_stdout = ((lighthouse_action or {}).get("result") or {}).get("stdout")

            payload["status"] = "completed" if any(item["result"].get("ok") for item in actions if item["tool"] != "start") else "failed"
            payload["reason"] = "Chrome DevTools MCP browser review completed." if payload["status"] == "completed" else "Chrome DevTools MCP commands did not complete successfully."
            payload["artifacts"] = {
                "screenshot": str(run_dir / "screenshot.png") if (run_dir / "screenshot.png").exists() else None,
                "lighthouse_dir": str(run_dir / "lighthouse") if (run_dir / "lighthouse").exists() else None,
            }
            payload["summary"] = {
                "console_message_count": len(console_stdout) if isinstance(console_stdout, list) else 0,
                "network_request_count": len(network_stdout) if isinstance(network_stdout, list) else 0,
                "lighthouse_scores": lighthouse_stdout if isinstance(lighthouse_stdout, dict) else {},
            }
        except Exception as exc:
            payload["status"] = "failed"
            payload["reason"] = "Chrome DevTools MCP browser review failed."
            payload["error"] = str(exc)
        finally:
            try:
                actions.append({"tool": "stop", "result": self._run(["stop"], run_dir)})
            except Exception:
                pass
        (run_dir / "browser_review.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def run_tool(self, tool: str, params: Dict[str, Any], label: str = "browser_lab") -> Dict[str, Any]:
        run_dir = self.output_root / label / datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        args = [tool]
        positional_url = params.pop("url", None) if tool == "new_page" else None
        if positional_url:
            args.append(str(positional_url))
        for key, value in params.items():
            flag = f"--{key}"
            if isinstance(value, bool):
                if value:
                    args.append(flag)
            elif isinstance(value, (dict, list)):
                args.extend([flag, json.dumps(value)])
            else:
                args.extend([flag, str(value)])
        result: Dict[str, Any] = {
            "schema": "orb_weaver.chrome_devtools_browser_lab_result.v1",
            "tool": tool,
            "status": "not_run",
            "generated_at": datetime.utcnow().isoformat(),
            "run_dir": str(run_dir),
            "reason": "Chrome DevTools MCP command execution.",
            "result": {"command": self._command_base() + args, "returncode": None, "stdout": None, "stderr": "", "ok": False, "mcp_error": None},
        }
        try:
            result["result"] = self._run(args, run_dir)
            result["status"] = "completed" if result["result"].get("ok") else "failed"
        except Exception as exc:
            result["status"] = "failed"
            result["result"]["mcp_error"] = str(exc)
        (run_dir / "browser_lab_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
