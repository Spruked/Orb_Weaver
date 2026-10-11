from decimal import Decimal

import pytest

from app.orb.site_operations import (
    AllowListGovernor,
    InMemoryEvidence,
    PriceUpdateService,
    SiteMesh,
    assign_morb,
    create_pointer_pings,
    inspect_similar_products,
)


class Adapter:
    def __init__(self):
        self.prices = {"a": {"amount": "10.00", "currency": "USD"}, "b": {"amount": "12.00", "currency": "USD"}}
        self.writes = []

    def read_price(self, entity_id):
        if entity_id not in self.prices:
            return {"found": False}
        return {"found": True, **self.prices[entity_id]}

    def write_price(self, entity_id, amount, currency):
        self.writes.append(entity_id)
        self.prices[entity_id] = {"amount": str(amount), "currency": currency}
        return {"accepted": True}


def products():
    return [
        {"entity_id": "a", "name": "Warm Desk Lamp", "category": "lighting", "description": "warm reading light", "attributes": {"style": "desk"}, "route": "/p/a", "verified": True},
        {"entity_id": "b", "name": "Warm Floor Lamp", "category": "lighting", "description": "warm reading light", "attributes": {"style": "floor"}, "route": "/p/b", "verified": True},
    ]


def test_morb_reports_similar_products_and_can_only_emit_pointer_targets():
    mesh = SiteMesh()
    assignment = assign_morb(morb_id="lighting-1", department="lighting", task="find related products", scope={"entity_id": "a"}, capabilities={"research_similar_products"})
    report = inspect_similar_products(assignment=assignment, source=products()[0], records=products(), mesh=mesh)
    assert report.status == "completed"
    assert report.findings[0]["entity_id"] == "b"
    assert mesh.messages[0]["destination"] == "primary_orb"
    assert create_pointer_pings(report.findings)[0]["target_id"] == "b"


def test_morb_cannot_receive_write_authority():
    with pytest.raises(ValueError):
        assign_morb(morb_id="lighting-1", department="lighting", task="update prices", scope={}, capabilities={"research_similar_products"})
    with pytest.raises(ValueError):
        from app.orb.site_operations import MorbAssignment
        MorbAssignment("lighting-1", "lighting", frozenset({"research_similar_products"}), "x", {}, frozenset({"modify_product_prices"}))


def test_price_updates_are_dry_run_validated_governed_and_verified():
    adapter, evidence, mesh = Adapter(), InMemoryEvidence(), SiteMesh()
    service = PriceUpdateService(adapter=adapter, governor=AllowListGovernor({"modify_product_prices"}), evidence=evidence, mesh=mesh)
    result = service.execute([{"entity_id": "a", "amount": "15.50", "currency": "USD"}])
    assert result["status"] == "completed"
    assert result["counts"]["succeeded"] == 1
    assert adapter.writes == ["a"]
    assert evidence.records[0]["job_id"] == result["job_id"]
    assert mesh.messages[0]["type"] == "price_job_report"


def test_invalid_batch_never_writes_and_is_recorded():
    adapter, evidence = Adapter(), InMemoryEvidence()
    service = PriceUpdateService(adapter=adapter, governor=AllowListGovernor({"modify_product_prices"}), evidence=evidence)
    result = service.execute([{"entity_id": "a", "amount": "9.999"}, {"entity_id": "missing", "amount": "3"}])
    assert result["status"] == "validation_failed"
    assert adapter.writes == []
    assert evidence.records[0]["status"] == "validation_failed"


def test_governor_denial_never_writes():
    adapter, evidence = Adapter(), InMemoryEvidence()
    service = PriceUpdateService(adapter=adapter, governor=AllowListGovernor(), evidence=evidence)
    result = service.execute([{"entity_id": "a", "amount": "15"}])
    assert result["status"] == "governor_denied"
    assert adapter.writes == []

