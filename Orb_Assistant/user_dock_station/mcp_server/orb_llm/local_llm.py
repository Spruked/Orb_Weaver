"""
ORB Local LLM Client â€” OPTIONAL articulation layer only.

ARCHITECTURAL RULE:
  ORB cognition (TPC + R-Substrate) is the PRIMARY reasoning layer.
  This LLM client is an OPTIONAL fallback for when TPC confidence < 0.30
  AND the user has explicitly set use_llm=True.

  The LLM is an articulation layer only.
  It must NEVER receive governance doctrine.
  It must NEVER be the primary decision maker.
  All LLM output is re-routed through TPC for validation before execution.

Supported backends (in priority order):
  1. Ollama (local, preferred)
  2. LM Studio (local)
  3. Any OpenAI-compatible local endpoint
"""

from __future__ import annotations
import os
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResult:
    success: bool
    text: str = ""
    error: str = ""
    backend: str = ""
    tokens_used: int = 0


class LocalLLMClient:
    """
    Detects and wraps a locally running LLM.
    Returns LLMResult â€” callers must check result.success.
    """

    # Endpoints to probe, in order
    PROBE_ENDPOINTS = [
        ("ollama",    os.getenv("ORB_LOCAL_LLM_ENDPOINT") or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11435")),
        ("lmstudio",  "http://localhost:1234"),
        ("localai",   "http://localhost:8080"),
        ("textgen",   "http://localhost:5000"),
    ]

    def __init__(self):
        self._backend:  Optional[str] = None
        self._base_url: Optional[str] = None
        self._model:    Optional[str] = None
        self._ready:    bool          = False
        self._probe()

    def _probe(self) -> None:
        """Probe each known endpoint. First success wins."""
        try:
            import requests
            for name, url in self.PROBE_ENDPOINTS:
                for attempt in range(self._retry_count()):
                    try:
                        probe_url = f"{url}/api/tags" if name == "ollama" else f"{url}/"
                        r = requests.get(probe_url, timeout=min(self._timeout_sec(), 8.0))
                        if r.status_code < 500:
                            self._backend  = name
                            self._base_url = url
                            self._ready    = True
                            self._model    = self._detect_model(name, url)
                            return
                    except Exception:
                        if attempt + 1 < self._retry_count():
                            time.sleep(self._retry_sleep_sec())
        except ImportError:
            pass  # requests not installed - stay unavailable

    def _timeout_sec(self) -> float:
        try:
            return float(os.getenv("ORB_OLLAMA_TIMEOUT_SEC", "45"))
        except ValueError:
            return 45.0

    def _retry_count(self) -> int:
        try:
            return max(1, int(os.getenv("ORB_OLLAMA_RETRIES", "3")))
        except ValueError:
            return 3

    def _retry_sleep_sec(self) -> float:
        try:
            return max(0.0, float(os.getenv("ORB_OLLAMA_RETRY_SLEEP_SEC", "0.45")))
        except ValueError:
            return 0.45

    def _detect_model(self, backend: str, url: str) -> Optional[str]:
        """Try to detect the loaded model name."""
        import requests
        preferred_model = (
            os.getenv("ORB_LOCAL_LLM_MODEL")
            or os.getenv("ORB_LLM_MODEL")
            or os.getenv("OLLAMA_MODEL")
            or ""
        ).strip()
        try:
            if backend == "ollama":
                r = requests.get(f"{url}/api/tags", timeout=2.0)
                if r.status_code == 200:
                    models = r.json().get("models", [])
                    names = [str(model.get("name", "")).strip() for model in models]
                    if preferred_model and preferred_model in names:
                        return preferred_model
                    if models:
                        return models[0].get("name", "unknown")
            elif backend in ("lmstudio", "localai", "textgen"):
                r = requests.get(f"{url}/v1/models", timeout=2.0)
                if r.status_code == 200:
                    data = r.json()
                    items = data.get("data", [])
                    if items:
                        return items[0].get("id", "unknown")
        except Exception:
            pass
        return "unknown"

    @property
    def available(self) -> bool:
        return self._ready

    @property
    def backend(self) -> Optional[str]:
        return self._backend

    @property
    def model(self) -> Optional[str]:
        return self._model

    def generate(self, prompt: str, max_tokens: int = 256, temperature: float = 0.1) -> LLMResult:
        """
        Generate a completion from the local LLM.
        Temperature defaults low (0.1) â€” we want deterministic articulation.
        """
        if not self._ready:
            return LLMResult(
                success=False,
                error="No local LLM available",
                backend="none",
            )

        try:
            if self._backend == "ollama":
                return self._call_ollama(prompt, max_tokens, temperature)
            else:
                return self._call_openai_compat(prompt, max_tokens, temperature)
        except Exception as e:
            return LLMResult(success=False, error=str(e), backend=self._backend or "unknown")

    def _call_ollama(self, prompt: str, max_tokens: int, temperature: float) -> LLMResult:
        import requests, json
        payload = {
            "model":  self._model or os.getenv("ORB_LOCAL_LLM_MODEL", "qwen2.5:3b"),
            "prompt": prompt,
            "stream": os.getenv("ORB_OLLAMA_STREAM", "1").strip().lower() in {"1", "true", "yes", "on"},
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            }
        }
        last_error = ""
        for attempt in range(self._retry_count()):
            try:
                r = requests.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                    stream=bool(payload.get("stream")),
                    timeout=self._timeout_sec(),
                )
                r.raise_for_status()
                if payload.get("stream"):
                    text_parts = []
                    data = {}
                    for line in r.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        data = json.loads(line)
                        piece = str(data.get("response") or "")
                        if piece:
                            text_parts.append(piece)
                        if data.get("done"):
                            break
                    response_text = "".join(text_parts).strip()
                else:
                    data = r.json()
                    response_text = data.get("response", "").strip()
                break
            except Exception as exc:
                last_error = str(exc)
                if attempt + 1 < self._retry_count():
                    time.sleep(self._retry_sleep_sec())
        else:
            return LLMResult(success=False, error=last_error, backend="ollama")
        return LLMResult(
            success=True,
            text=response_text,
            backend="ollama",
            tokens_used=data.get("eval_count", 0),
        )

    def _call_openai_compat(self, prompt: str, max_tokens: int, temperature: float) -> LLMResult:
        import requests
        payload = {
            "model":       self._model or "local-model",
            "messages":    [{"role": "user", "content": prompt}],
            "max_tokens":  max_tokens,
            "temperature": temperature,
        }
        r = requests.post(
            f"{self._base_url}/v1/chat/completions",
            json=payload,
            timeout=30.0
        )
        r.raise_for_status()
        data    = r.json()
        choices = data.get("choices", [])
        text    = choices[0]["message"]["content"].strip() if choices else ""
        return LLMResult(
            success=True,
            text=text,
            backend=self._backend or "openai-compat",
            tokens_used=data.get("usage", {}).get("completion_tokens", 0),
        )

    def status(self) -> dict:
        return {
            "available": self._ready,
            "backend":   self._backend,
            "model":     self._model,
            "base_url":  self._base_url,
        }

