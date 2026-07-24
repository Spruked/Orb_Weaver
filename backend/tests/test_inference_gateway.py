from __future__ import annotations

from pathlib import Path

import pytest

from app.inference_gateway.config import GatewayConfig, ProviderConfig
from app.inference_gateway.contracts import GenerationResult, ProviderHealth
from app.inference_gateway.providers import ProviderError
from app.inference_gateway.service import InferenceGateway
from app.inference_gateway.telemetry import VaultTelemetry


class FakeProvider:
    def __init__(self, name: str, *, ready: bool = True, fail: bool = False) -> None:
        self.name = name
        self.enabled = True
        self.ready = ready
        self.fail = fail
        self.calls = 0

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            name=self.name,
            enabled=True,
            ready=self.ready,
            model=f"{self.name}-model",
            base_url=f"http://{self.name}",
            checked_at=1.0,
            latency_ms=1.0,
            error=None if self.ready else "offline",
        )

    async def complete(self, messages, **kwargs) -> GenerationResult:
        self.calls += 1
        if self.fail:
            raise ProviderError(f"{self.name} failed")
        return GenerationResult(
            text=f"answer from {self.name}",
            provider=self.name,
            model=f"{self.name}-model",
            latency_ms=2.5,
            prompt_tokens=4,
            completion_tokens=3,
        )

    async def stream_chat(self, messages, **kwargs):
        yield f"data: {self.name}\n\n".encode()


def make_config(tmp_path: Path) -> GatewayConfig:
    providers = {
        name: ProviderConfig(name=name, kind="openai", base_url=f"http://{name}", model="model")
        for name in ("llamacpp", "aphrodite", "tensorrt", "ollama")
    }
    return GatewayConfig(
        host="127.0.0.1",
        port=16520,
        api_key="",
        provider_order=("llamacpp", "aphrodite", "tensorrt", "ollama"),
        default_lane="universal",
        scale_threshold=3,
        health_ttl_seconds=30.0,
        allow_model_override=False,
        max_prompt_chars=1000,
        telemetry_path=tmp_path / "events.jsonl",
        providers=providers,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("lane", "expected"),
    [
        ("universal", "llamacpp"),
        ("scale", "aphrodite"),
        ("accelerated", "tensorrt"),
        ("fallback", "ollama"),
    ],
)
async def test_lane_selects_expected_provider(tmp_path: Path, lane: str, expected: str) -> None:
    config = make_config(tmp_path)
    providers = {name: FakeProvider(name) for name in config.providers}
    gateway = InferenceGateway(config, providers, VaultTelemetry(config.telemetry_path))

    result = await gateway.generate(
        [{"role": "user", "content": "hello"}],
        lane=lane,
        temperature=0.2,
        max_tokens=20,
    )

    assert result.provider == expected
    assert providers[expected].calls == 1
    assert config.telemetry_path.exists()


@pytest.mark.asyncio
async def test_provider_failure_falls_through_without_rewriting_orb(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    providers = {
        "llamacpp": FakeProvider("llamacpp", fail=True),
        "aphrodite": FakeProvider("aphrodite"),
        "tensorrt": FakeProvider("tensorrt"),
        "ollama": FakeProvider("ollama"),
    }
    gateway = InferenceGateway(config, providers, VaultTelemetry(config.telemetry_path))

    result = await gateway.generate(
        [{"role": "user", "content": "hello"}],
        lane="universal",
        temperature=0.2,
        max_tokens=20,
    )

    assert result.provider == "aphrodite"
    assert providers["llamacpp"].calls == 1
    assert providers["aphrodite"].calls == 1


@pytest.mark.asyncio
async def test_prompt_limit_is_enforced_before_provider_call(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config = GatewayConfig(**{**config.__dict__, "max_prompt_chars": 5})
    providers = {name: FakeProvider(name) for name in config.providers}
    gateway = InferenceGateway(config, providers, VaultTelemetry(config.telemetry_path))

    with pytest.raises(ValueError, match="prompt exceeds"):
        await gateway.generate(
            [{"role": "user", "content": "too long"}],
            lane="universal",
            temperature=0.2,
            max_tokens=20,
        )

    assert all(provider.calls == 0 for provider in providers.values())


@pytest.mark.asyncio
async def test_unhealthy_provider_is_skipped(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    providers = {
        "llamacpp": FakeProvider("llamacpp", ready=False),
        "aphrodite": FakeProvider("aphrodite"),
        "tensorrt": FakeProvider("tensorrt"),
        "ollama": FakeProvider("ollama"),
    }
    gateway = InferenceGateway(config, providers, VaultTelemetry(config.telemetry_path))

    result = await gateway.generate(
        [{"role": "user", "content": "hello"}],
        lane="universal",
        temperature=0.2,
        max_tokens=20,
    )

    assert result.provider == "aphrodite"
    assert providers["llamacpp"].calls == 0
