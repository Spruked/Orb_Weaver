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
async def test_site_world_identity_summary_bypasses_local_model():
    calls = []

    async def local_model(query, context):
        calls.append(query)
        return {"text": "Model answer."}

    result = await CanonicalTurnResolver(local_model=local_model).resolve(
        "What does ORB Weaver do?",
        domain="orbweaver.spruked.com",
        site_world={
            "site_name": "ORB Weaver",
            "site_summary": "ORB Weaver scans sites and builds Website ORBs.",
        },
    )

    assert result["source_lane"] == "site_world"
    assert result["spoken_output"] == "ORB Weaver scans sites and builds Website ORBs."
    assert calls == []


@pytest.mark.asyncio
async def test_site_world_identity_summary_is_not_overridden_by_raw_crawl_chunk():
    summary = "ORB Weaver scans sites and builds Website ORBs."
    result = await CanonicalTurnResolver().resolve(
        "What does ORB Weaver do?",
        domain="orbweaver.spruked.com",
        site_world={
            "site_name": "ORB Weaver",
            "site_summary": summary,
            "knowledge_chunks": {
                "chunks": [{
                    "route": "/",
                    "title": "ORB Weaver",
                    "text": "ORB Weaver | Website Intelligence You need to enable JavaScript to run this app. " * 12,
                    "chunk_id": "raw-home-page",
                }],
            },
        },
    )

    assert result["source_lane"] == "site_world"
    assert result["spoken_output"] == summary
    assert result["evidence_ids"] == ["site_world:site_summary"]


@pytest.mark.asyncio
@pytest.mark.parametrize("utterance", [
    "Weaver, move out of the way.", "move out of the way", "Move over.", "Scoot over.", "Move up.",
    "Move down.", "Move left.", "Move right.", "Come back.", "Come here.",
    "Stay there.", "Stop moving.", "Wait there.", "Wake up.", "Go back to listening.",
])
async def test_spoken_motion_commands_are_deterministic_control_intents(utterance):
    result = await CanonicalTurnResolver().resolve(utterance, domain="example.com")
    assert result["source_lane"] == "control"
    assert result["control_action"]["type"] == "orb_motion"
    assert result["trace"]["attempts"] == [{"lane": "control", "matched": True}]


@pytest.mark.asyncio
async def test_move_out_of_way_acknowledgement_is_brief_and_conversational():
    result = await CanonicalTurnResolver().resolve("Weaver, move out of the way.", domain="example.com")
    assert result["spoken_output"] == "Oh, excuse me."
    assert result["control_action"] == {"type": "orb_motion", "command": "move_out_of_way"}


@pytest.mark.asyncio
@pytest.mark.parametrize("transcript", [
    "Closing arguments are expected to begin on Fox News.",
    "Bigfoot aliens and federal government documents.",
])
async def test_unrelated_ambient_transcript_cannot_admit_an_apriori_skg_match(transcript):
    def skg_lookup(lane, query):
        if lane != "apriori":
            return None
        return {
            "answer": "I can help compare pricing and point you to the right plan.",
            "evidence_ids": ["pricing_overview"],
            "confidence": 1.0,
            "data": {"title": "Pricing overview", "keywords": ["pricing", "plans", "cost"]},
        }

    result = await CanonicalTurnResolver(vault_skg_lookup=skg_lookup).resolve(transcript, domain="example.com")

    assert result["source_lane"] != "apriori"
    assert result["answer_state"] != "known"
    assert result["confidence"] != 1.0
    attempt = next(item for item in result["trace"]["attempts"] if item["lane"] == "apriori_skg")
    assert attempt["matched"] is False
    assert attempt["query_correspondence"] == 0.0


@pytest.mark.asyncio
async def test_strong_apriori_skg_correspondence_remains_fast_path():
    def skg_lookup(lane, query):
        return {
            "answer": "Basic plan pricing is available on the pricing page.",
            "evidence_ids": ["pricing_overview"],
            "confidence": 1.0,
            "data": {"title": "Pricing overview", "keywords": ["pricing", "plans", "cost"]},
        } if lane == "apriori" else None

    result = await CanonicalTurnResolver(vault_skg_lookup=skg_lookup).resolve(
        "What are the pricing plans?", domain="example.com"
    )

    assert result["source_lane"] == "apriori"
    assert result["query_correspondence_verified"] is True
    assert result["source_truth_confidence"] == 1.0


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
