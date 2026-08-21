#!/usr/bin/env python3
"""Verify the Website ORB local Ollama model and GPU residency.

Run this on the Windows/WSL host that owns Ollama. It does not infer CUDA from
configuration: it requires runtime evidence from Ollama /api/ps and, when
available, nvidia-smi.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

EXPECTED_MODEL = os.getenv("LOCAL_LLM_MODEL", "qwen2.5:1.5b-instruct")
GENERATE_URL = os.getenv("LOCAL_LLM_URL", "http://127.0.0.1:11434/api/generate")


def ollama_base_url() -> str:
    parsed = urlparse(GENERATE_URL)
    scheme = parsed.scheme or "http"
    host = parsed.netloc or "127.0.0.1:11434"
    return f"{scheme}://{host}"


def model_matches(actual: str, expected: str) -> bool:
    a = (actual or "").lower().replace(":latest", "")
    e = (expected or "").lower().replace(":latest", "")
    return a == e or a.startswith(e + ":") or e.startswith(a + ":")


def main() -> int:
    result = {
        "ollama_url": ollama_base_url(),
        "expected_model": EXPECTED_MODEL,
        "ollama_reachable": False,
        "model_loaded": False,
        "loaded_model": None,
        "size_vram": 0,
        "gpu_resident": False,
        "nvidia_smi_available": bool(shutil.which("nvidia-smi")),
        "nvidia_gpu": None,
        "cuda_verified": False,
        "errors": [],
    }

    try:
        with urlopen(f"{ollama_base_url()}/api/ps", timeout=5) as response:
            payload = json.load(response)
        result["ollama_reachable"] = True
        models = payload.get("models") or []
        for row in models:
            name = str(row.get("name") or row.get("model") or "")
            if model_matches(name, EXPECTED_MODEL):
                result["model_loaded"] = True
                result["loaded_model"] = name
                result["size_vram"] = int(row.get("size_vram") or 0)
                result["gpu_resident"] = result["size_vram"] > 0
                break
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        result["errors"].append(f"Ollama /api/ps: {exc}")

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
            line = next((line.strip() for line in proc.stdout.splitlines() if line.strip()), "")
            if line:
                result["nvidia_gpu"] = line
        except Exception as exc:
            result["errors"].append(f"nvidia-smi: {exc}")

    result["cuda_verified"] = bool(
        result["ollama_reachable"]
        and result["model_loaded"]
        and result["gpu_resident"]
        and result["nvidia_gpu"]
    )

    print(json.dumps(result, indent=2))
    if not result["ollama_reachable"]:
        print("FAIL: Ollama is not reachable.", file=sys.stderr)
        return 2
    if not result["model_loaded"]:
        print(f"FAIL: {EXPECTED_MODEL} is not loaded in Ollama.", file=sys.stderr)
        return 3
    if not result["gpu_resident"]:
        print("FAIL: Ollama reports zero VRAM residency for the configured model.", file=sys.stderr)
        return 4
    if not result["nvidia_gpu"]:
        print("WARN: model is VRAM-resident, but nvidia-smi evidence is unavailable; CUDA cannot be fully certified.", file=sys.stderr)
        return 5
    print(f"PASS: {result['loaded_model']} is loaded in Ollama with VRAM residency and NVIDIA CUDA evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
