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
    assert pack["candidate_claims"]
    assert pack["risky_claims"]
    assert pack["suggested_ad_reads"]["15s"]
    assert pack["owner_approval"]["owner_approved"] is False
    assert pack["catalog_quality"]["status"] == "not_available"
    assert pack["offers"][0]["offer_id"] == "offer_001"
    assert pack["candidate_claims"][0]["claim_id"] == "claim_001"
    assert pack["cta"]["url"] in {"https://example.test/", "https://example.test/about"}
    assert all(item["source_url"] for item in pack["candidate_claims"])


def test_dandy_pack_degrades_to_empty_without_pages():
    pack = build_dandy_promo_pack([], domain="empty.test", crawl_job_id=8)

    assert pack["status"] == "empty"
    assert pack["business"]["name"] == "empty.test"
    assert pack["listener_urls"] == []
    assert pack["owner_approval"]["status"] == "pending"


def test_dandy_pack_excludes_sensitive_routes_from_marketing_evidence():
    pack = build_dandy_promo_pack(
        [
            {"url": "https://example.test/", "title": "Public business"},
            {"url": "https://example.test/admin/customers", "title": "Private customer list", "h1": "Private claim"},
            {"url": "https://example.test/cart", "title": "Checkout total", "h1": "$999 offer"},
        ],
        domain="example.test",
        crawl_job_id=11,
    )
    assert pack["source"]["page_count"] == 1
    assert all("admin" not in str(row.get("source_url")) for row in pack["candidate_claims"])
    assert all("cart" not in str(url) for url in pack["listener_urls"])


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
        "approved_claim_ids": [row["claim_id"] for row in pack["candidate_claims"]],
        "approved_offer_ids": [],
        "approved_ad_read_ids": ["ad_read_15s"],
    }
    exported = build_approved_dandy_payload(pack)
    assert exported["schema"] == "orb_weaver.dandy_approved_promo_payload.v1"
    assert exported["ad_reads"].keys() == {"15s"}
    assert "risky_claims" not in exported


def test_dandy_pack_blocks_catalog_quality_failures():
    pack = build_dandy_promo_pack(
        [{"url": "https://example.test", "title": "Acme", "h1": "Reliable service"}],
        domain="example.test",
        crawl_job_id=10,
        catalog={"entries": [], "data_quality": {"status": "contaminated"}},
    )
    assert pack["status"] == "blocked_quality"
    pack["owner_approval"] = {
        "status": "approved",
        "owner_approved": True,
        "approved_claim_ids": [],
        "approved_offer_ids": [],
        "approved_ad_read_ids": [],
    }
    with pytest.raises(ValueError, match="data quality"):
        build_approved_dandy_payload(pack)
