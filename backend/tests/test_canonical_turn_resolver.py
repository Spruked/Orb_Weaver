from __future__ import annotations

import httpx
import pytest

from app.orb.catalog_repository import create_catalog_database
from app.orb.provider_router import invoke_provider
from app.orb.turn_resolver import CanonicalTurnResolver


def _catalog_entry():
    return {
        "entity_id": "trail-camera",
        "entity_type": "product",
        "name": "Trail Camera",
        "sku": "CAM-1",
        "description": None,
        "category": None,
        "price": {"amount": 149.0, "currency": "USD", "display_text": "$149", "billing_period": None},
        "availability": "in_stock",
        "route": "/camera",
        "source_url": "https://example.com/camera",
        "source_evidence_ids": ["product-evidence"],
        "pointer_target_id": "buy-camera",
        "confidence": 1.0,
        "content_hash": "product-hash",
        "attributes": {},
        "verified": True,
    }


@pytest.mark.asyncio
async def test_resolution_order_control_catalog_apriori_posteriori_site_world(tmp_path):
    catalog = tmp_path / "catalog.db"
    create_catalog_database(catalog, [_catalog_entry()])
    resolver = CanonicalTurnResolver(
        posteriori_lookup=lambda domain, query, route: {
            "spoken_output": "The owner-approved resolved answer.", "evidence_refs": ["case-1"], "cache_score": 0.9
        } if "resolved question" in query else None
    )
    apriori = {"qa": {"entries": [{"question": "When do you ship?", "aliases": ["shipping days"], "answer": "We ship weekdays.", "source_evidence_ids": ["faq-1"]}]}}
    site_world = {"route_hints": {"Contact": "/contact"}}

    control = await resolver.resolve("Who are you?", domain="example.com", catalog_path=catalog, apriori=apriori, site_world=site_world)
    assert control["source_lane"] == "control"
    catalog_result = await resolver.resolve("What is the Trail Camera price?", domain="example.com", catalog_path=catalog, apriori=apriori, site_world=site_world)
    assert catalog_result["source_lane"] == "catalog"
    assert "$149" in catalog_result["spoken_output"]
    apriori_result = await resolver.resolve("What are your shipping days?", domain="example.com", catalog_path=catalog, apriori=apriori, site_world=site_world)
    assert apriori_result["source_lane"] == "apriori"
    posteriori = await resolver.resolve("resolved question", domain="example.com", catalog_path=catalog, apriori=apriori, site_world=site_world)
    assert posteriori["source_lane"] == "posteriori"
    site = await resolver.resolve("Where is contact?", domain="example.com", catalog_path=catalog, apriori=apriori, site_world=site_world)
    assert site["source_lane"] == "site_world"
    assert site["trace"]["resolution_order"][-1] == "articulation"


@pytest.mark.asyncio
async def test_local_then_external_provider_and_structured_failure():
    calls = []

    async def local_model(query, context):
        calls.append("local")
        return {"failed": True, "error": "offline"}

    async def provider(configuration, **kwargs):
        calls.append("external")
        return {"success": True, "provider": "openai_api", "model": "test", "text": "Provider answer.", "error": None}

    resolver = CanonicalTurnResolver(local_model=local_model, provider_invoke=provider)
    result = await resolver.resolve(
        "An unmatched question", domain="example.com",
        provider_configuration={"provider": "openai_api", "model": "test", "api_key_env": "TEST_KEY"},
    )
    assert calls == ["local", "external"]
    assert result["source_lane"] == "external_provider"
    assert result["trace"]["articulation"]["checksum"]["passed"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "payload", "expected"),
    [
        ("openai_compatible", {"choices": [{"message": {"content": "OpenAI text"}}]}, "OpenAI text"),
        ("anthropic_api", {"content": [{"type": "text", "text": "Anthropic text"}]}, "Anthropic text"),
        ("google_api", {"candidates": [{"content": {"parts": [{"text": "Google text"}]}}]}, "Google text"),
    ],
)
async def test_provider_adapters(monkeypatch, provider, payload, expected):
    monkeypatch.setenv("TEST_PROVIDER_KEY", "secret-for-test")

    async def handler(request):
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await invoke_provider(
            {
                "provider": provider,
                "model": "test-model",
                "base_url": "https://provider.invalid/v1",
                "api_key_env": "TEST_PROVIDER_KEY",
            },
            prompt="Question",
            system_instruction="System",
            client=client,
        )
    assert result["success"] is True
    assert result["text"] == expected
    assert "secret-for-test" not in str(result)


@pytest.mark.asyncio
async def test_provider_failure_is_structured():
    result = await invoke_provider(
        {"provider": "openai_api", "model": "test", "api_key_env": "MISSING_TEST_KEY"},
        prompt="Question", system_instruction="System",
    )
    assert result["success"] is False
    assert result["error"] == "provider_credential_missing"
