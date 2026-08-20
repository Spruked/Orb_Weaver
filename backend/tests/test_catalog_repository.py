from __future__ import annotations

from app.orb.catalog_repository import CatalogRepository, create_catalog_database


def _entries():
    return [
        {
            "entity_id": "product-1",
            "entity_type": "product",
            "name": "Verified Trail Camera",
            "description": "A weatherproof camera.",
            "sku": "CAM-4421",
            "category": "cameras",
            "price": {"amount": 149.0, "currency": "USD", "display_text": "$149", "billing_period": None},
            "availability": "in_stock",
            "route": "/camera",
            "source_url": "https://example.com/camera",
            "source_evidence_ids": ["evidence-product-1"],
            "pointer_target_id": "camera-buy",
            "confidence": 0.99,
            "content_hash": "hash-product-1",
            "attributes": {"sale_price": {"amount": 129.0}},
            "verified": True,
        },
        {
            "entity_id": "service-1",
            "entity_type": "service",
            "name": "Installation Service",
            "description": "Professional installation.",
            "sku": None,
            "category": "services",
            "price": {"amount": 75.0, "currency": "USD", "display_text": "$75", "billing_period": None},
            "availability": True,
            "route": "/installation",
            "source_url": "https://example.com/installation",
            "source_evidence_ids": ["evidence-service-1"],
            "pointer_target_id": None,
            "confidence": 1.0,
            "content_hash": "hash-service-1",
            "attributes": {},
            "verified": True,
        },
    ]


def test_catalog_database_exact_sku_price_service_and_provenance(tmp_path):
    path = tmp_path / "catalog.db"
    result = create_catalog_database(path, _entries())
    repository = CatalogRepository(path)

    assert result["entry_count"] == 2
    assert repository.validate() == {"valid": True, "reason": None, "entry_count": 2}
    exact = repository.lookup("Verified Trail Camera")
    assert exact and exact.match_type == "exact"
    assert exact.record["price"]["amount"] == 149.0
    assert exact.record["price"]["sale_amount"] == 129.0
    assert exact.record["source_evidence_ids"] == ["evidence-product-1"]
    sku = repository.lookup_sku("cam-4421")
    assert sku and sku.record["name"] == "Verified Trail Camera"
    service = repository.lookup("installation", entity_type="service")
    assert service and service.record["entity_type"] == "service"
    assert repository.lookup("not a catalog item") is None


def test_catalog_database_excludes_unverified_entries(tmp_path):
    entries = _entries()
    entries[0]["verified"] = False
    path = tmp_path / "catalog.db"
    create_catalog_database(path, entries)
    repository = CatalogRepository(path)
    assert repository.lookup_sku("CAM-4421") is None
    assert repository.validate()["entry_count"] == 1
