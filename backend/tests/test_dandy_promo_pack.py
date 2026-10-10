import sys
from pathlib import Path


BACKEND_PATH = str((Path.cwd() / "backend").resolve())
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

import pytest

from app.dandy import build_approved_dandy_payload, build_dandy_promo_pack


def test_dandy_pack_is_source_grounded_and_contains_ad_inventory():
    pages = [
        {
            "url": "https://example.test/",
            "title": "Acme Coffee | Small-batch coffee",
            "h1": "Small-batch coffee for busy mornings",
            "meta_description": "Order roasted coffee beans and join our monthly coffee club.",
            "h2_tags": ["Shop coffee", "Join the coffee club"],
            "schema_markup": [
                {
                    "@type": "Product",
                    "name": "Monthly Coffee Club",
                    "description": "Freshly roasted coffee delivered each month.",
                    "offers": {"price": "24.00"},
                }
            ],
        },
        {
            "url": "https://example.test/about",
            "title": "About Acme Coffee",
            "h1": "Roasted in small batches",
            "meta_description": "Award-winning coffee for every morning.",
            "h2_tags": [],
            "schema_markup": [],
        },
    ]

    pack = build_dandy_promo_pack(pages, domain="example.test", crawl_job_id=7)

    assert pack["schema"] == "orb_weaver.dandy_promo_pack.v1"
    assert pack["status"] == "complete"
    assert pack["source"]["crawl_job_id"] == "7"
    assert pack["business"]["name"] == "Acme Coffee"
    assert pack["offers"][0]["name"] == "Monthly Coffee Club"
    assert pack["pricing_public"][0]["price"] == "24.00"
    assert pack["approved_claims"]
    assert pack["risky_claims"]
    assert pack["suggested_ad_reads"]["15s"]
    assert pack["owner_approval"]["owner_approved"] is False
    assert pack["offers"][0]["offer_id"] == "offer_001"
    assert pack["approved_claims"][0]["claim_id"] == "claim_001"
    assert pack["cta"]["url"] in {"https://example.test/", "https://example.test/about"}
    assert all(item["source_url"] for item in pack["approved_claims"])


def test_dandy_pack_degrades_to_empty_without_pages():
    pack = build_dandy_promo_pack([], domain="empty.test", crawl_job_id=8)

    assert pack["status"] == "empty"
    assert pack["business"]["name"] == "empty.test"
    assert pack["listener_urls"] == []
    assert pack["owner_approval"]["status"] == "pending"


def test_dandy_approved_export_fails_closed_and_excludes_risky_claims():
    pack = build_dandy_promo_pack(
        [{"url": "https://example.test", "title": "Acme", "h1": "Reliable service"}],
        domain="example.test",
        crawl_job_id=9,
    )
    with pytest.raises(ValueError):
        build_approved_dandy_payload(pack)

    pack["owner_approval"] = {
        "status": "approved",
        "owner_approved": True,
        "approved_at": "2026-10-10T00:00:00+00:00",
        "approved_by": {"customer_id": "1", "email": "owner@example.test"},
        "approved_claim_ids": [row["claim_id"] for row in pack["approved_claims"]],
        "approved_offer_ids": [],
        "approved_ad_read_ids": ["ad_read_15s"],
    }
    exported = build_approved_dandy_payload(pack)
    assert exported["schema"] == "orb_weaver.dandy_approved_promo_payload.v1"
    assert exported["ad_reads"].keys() == {"15s"}
    assert "risky_claims" not in exported
