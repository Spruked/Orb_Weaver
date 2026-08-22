from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name, "true" if default else "false").lower()
    return raw in {"1", "true", "yes", "on", "enabled"}


def _env_float(name: str, default: float) -> float:
    raw = _env(name, str(default))
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = _env(name, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def _csv(name: str, default: str) -> Tuple[str, ...]:
    values = tuple(part.strip().lower() for part in _env(name, default).split(",") if part.strip())
    return values or tuple(part.strip().lower() for part in default.split(",") if part.strip())


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    kind: str
    base_url: str
    model: str
    api_key: str = ""
    timeout_seconds: float = 60.0

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.model)


@dataclass(frozen=True)
class GatewayConfig:
    host: str
    port: int
    api_key: str
    provider_order: Tuple[str, ...]
    default_lane: str
    scale_threshold: int
    health_ttl_seconds: float
    allow_model_override: bool
    max_prompt_chars: int
    telemetry_path: Path
    providers: Dict[str, ProviderConfig]

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        vault_root = Path(_env("ORB_WEAVER_VAULT_ROOT", "../vault_system")).expanduser().resolve()
        telemetry_path = vault_root / "runtime" / "inference_gateway" / "events.jsonl"

        default_timeout = _env_float("ORB_INFERENCE_TIMEOUT_SECONDS", 60.0)
        providers = {
            "llamacpp": ProviderConfig(
                name="llamacpp",
                kind="openai",
                base_url=_env("LLAMACPP_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/"),
                model=_env("LLAMACPP_MODEL", "auto"),
                api_key=_env("LLAMACPP_API_KEY"),
                timeout_seconds=_env_float("LLAMACPP_TIMEOUT_SECONDS", default_timeout),
            ),
            "aphrodite": ProviderConfig(
                name="aphrodite",
                kind="openai",
                base_url=_env("APHRODITE_BASE_URL", "http://127.0.0.1:2242/v1").rstrip("/"),
                model=_env("APHRODITE_MODEL", "auto"),
                api_key=_env("APHRODITE_API_KEY"),
                timeout_seconds=_env_float("APHRODITE_TIMEOUT_SECONDS", default_timeout),
            ),
            "tensorrt": ProviderConfig(
                name="tensorrt",
                kind="openai",
                base_url=_env("TENSORRT_LLM_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/"),
                model=_env("TENSORRT_LLM_MODEL", "auto"),
                api_key=_env("TENSORRT_LLM_API_KEY"),
                timeout_seconds=_env_float("TENSORRT_LLM_TIMEOUT_SECONDS", default_timeout),
            ),
            "ollama": ProviderConfig(
                name="ollama",
                kind="ollama",
                base_url=_env("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
                model=_env("OLLAMA_MODEL", _env("LOCAL_LLM_MODEL", "qwen2.5:1.5b")),
                api_key="",
                timeout_seconds=_env_float("OLLAMA_TIMEOUT_SECONDS", default_timeout),
            ),
        }

        return cls(
            host=_env("ORB_INFERENCE_GATEWAY_HOST", "127.0.0.1"),
            port=_env_int("ORB_INFERENCE_GATEWAY_PORT", 16520),
            api_key=_env("ORB_INFERENCE_API_KEY"),
            provider_order=_csv(
                "ORB_INFERENCE_PROVIDER_ORDER",
                "llamacpp,aphrodite,tensorrt,ollama",
            ),
            default_lane=_env("ORB_INFERENCE_DEFAULT_LANE", "universal").lower(),
            scale_threshold=max(1, _env_int("ORB_INFERENCE_SCALE_THRESHOLD", 3)),
            health_ttl_seconds=max(0.5, _env_float("ORB_INFERENCE_HEALTH_TTL_SECONDS", 5.0)),
            allow_model_override=_env_bool("ORB_INFERENCE_ALLOW_MODEL_OVERRIDE", False),
            max_prompt_chars=max(1000, _env_int("ORB_INFERENCE_MAX_PROMPT_CHARS", 24000)),
            telemetry_path=telemetry_path,
            providers=providers,
        )
