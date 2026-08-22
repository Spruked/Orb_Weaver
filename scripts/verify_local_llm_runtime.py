#!/usr/bin/env python3
"""Verify the Website ORB llama.cpp cognition model lock."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


def load_repo_inference_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env.inference"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_repo_inference_env()

EXPECTED_MODEL_LOCK = "Qwen 2.5 1.5B Instruct Q4_K_M"
GENERATE_URL = os.getenv("LOCAL_LLM_URL", "http://127.0.0.1:16520/api/generate")
RUNTIME_MODEL = os.getenv("LOCAL_LLM_MODEL", "orb-auto")
LLAMACPP_MODEL_PATH = Path(os.path.expandvars(os.path.expanduser(
    os.getenv("LLAMACPP_MODEL_PATH", "$HOME/models/qwen2.5-1.5b-instruct-q4_k_m.gguf")
)))


def base_url() -> str:
    parsed = urlparse(GENERATE_URL)
    return f"{parsed.scheme or 'http'}://{parsed.netloc or '127.0.0.1:16520'}"


def http_json(method: str, url: str, payload: dict | None = None, timeout: int = 8) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def main() -> int:
    gateway = base_url()
    result = {
        "provider": "llamacpp",
        "expected_model_lock": EXPECTED_MODEL_LOCK,
        "generate_url": GENERATE_URL,
        "runtime_model": RUNTIME_MODEL,
        "model_path": str(LLAMACPP_MODEL_PATH),
        "model_file_exists": LLAMACPP_MODEL_PATH.is_file(),
        "gateway_reachable": False,
        "generate_ok": False,
        "response_text": "",
        "nvidia_smi_available": bool(shutil.which("nvidia-smi")),
        "nvidia_gpu": None,
        "errors": [],
    }

    try:
        try:
            http_json("GET", urljoin(gateway + "/", "health"), timeout=4)
            result["gateway_reachable"] = True
        except Exception:
            http_json("GET", urljoin(gateway + "/", "v1/models"), timeout=4)
            result["gateway_reachable"] = True
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        result["errors"].append(f"llama.cpp gateway health: {exc}")

    if result["gateway_reachable"]:
        try:
            payload = http_json("POST", GENERATE_URL, {
                "model": RUNTIME_MODEL,
                "prompt": "Say Weaver online in three words.",
                "stream": False,
                "options": {"num_predict": 8, "temperature": 0},
            }, timeout=20)
            text = str(payload.get("response") or payload.get("text") or "")
            result["response_text"] = text.strip()
            result["generate_ok"] = bool(result["response_text"])
        except Exception as exc:
            result["errors"].append(f"llama.cpp generate: {exc}")

    if shutil.which("nvidia-smi"):
        try:
            proc = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used", "--format=csv,noheader,nounits"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=8,
            )
            result["nvidia_gpu"] = next((line.strip() for line in proc.stdout.splitlines() if line.strip()), None)
        except Exception as exc:
            result["errors"].append(f"nvidia-smi: {exc}")

    print(json.dumps(result, indent=2))
    if not result["model_file_exists"]:
        print(f"FAIL: GGUF model file is missing: {LLAMACPP_MODEL_PATH}", file=sys.stderr)
        return 2
    if not result["gateway_reachable"]:
        print(f"FAIL: llama.cpp inference gateway is not reachable at {gateway}.", file=sys.stderr)
        return 3
    if not result["generate_ok"]:
        print("FAIL: llama.cpp inference gateway did not generate text.", file=sys.stderr)
        return 4
    print(f"PASS: {EXPECTED_MODEL_LOCK} is reachable through llama.cpp gateway.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
