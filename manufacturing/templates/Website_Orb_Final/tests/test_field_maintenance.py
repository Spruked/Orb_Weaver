from copy import deepcopy

from Website_ORB.backend.runtime.field_maintenance import (
    FieldMaintenanceEngine,
    FieldMaintenanceStore,
)


def _target(*, target_id="buy-widget", selector="[data-orb-target=buy-widget]", verified=True):
    return {
        "target_id": target_id,
        "target_type": "cta",
        "meaning": "Buy widget",
        "selector": selector,
        "verified": verified,
        "depends_on": ["price", "availability"],
        "evidence": [{"kind": "live_dom", "unique_match": verified, "visible": verified}],
    }


def _product(*, price=49, targets=None, verified=True):
    return {
        "product_id": "widget-1",
        "title": "Widget",
        "sku": "W-1",
        "price": price,
        "availability": "in stock",
        "verified": verified,
        "targets": targets if targets is not None else [_target(verified=verified)],
    }


def _engine(tmp_path):
    return FieldMaintenanceEngine(
        FieldMaintenanceStore(tmp_path / "field-maintenance"),
        known_products=[{"entity_id": "widget-1"}],
    )


def test_baseline_requires_target_reverification_before_publish(tmp_path):
    engine = _engine(tmp_path)

    scan = engine.product_delta_scan([_product()])

    assert scan["results"][0]["status"] == "baseline"
    assert scan["results"][0]["authoritative"] is False
    assert engine.status()["targets_tracked"] == 1

    result = engine.reverify_targets("widget-1", [_target()])
    assert result["published"] is True
    answer = engine.answer("What is the price of the Widget?")
    assert answer["answer"] == "Widget is currently listed at 49."


def test_price_delta_requires_affected_target_reverification(tmp_path):
    engine = _engine(tmp_path)
    first = _product()
    engine.product_delta_scan([first])
    engine.reverify_targets("widget-1", first["targets"])

    changed = _product(price=59)
    scan = engine.product_delta_scan([changed])
    assert scan["results"][0]["status"] == "changed"
    assert scan["results"][0]["authoritative"] is False
    assert engine.answer("What is the price of the Widget?")["answer"].endswith("49.")

    result = engine.reverify_targets("widget-1", changed["targets"])
    assert result["published"] is True
    assert engine.answer("What is the price of the Widget?")["answer"].endswith("59.")


def test_repeat_observation_is_unchanged_when_values_and_target_identity_match(tmp_path):
    engine = _engine(tmp_path)
    observation = _product()
    engine.product_delta_scan([observation])
    engine.reverify_targets("widget-1", observation["targets"])

    repeat = engine.product_delta_scan([deepcopy(observation)])

    assert repeat["results"][0]["status"] == "unchanged"
    assert repeat["results"][0]["changed_fields"] == []


def test_target_identity_delta_is_detected_without_product_field_change(tmp_path):
    engine = _engine(tmp_path)
    first = _product()
    engine.product_delta_scan([first])
    engine.reverify_targets("widget-1", first["targets"])

    changed_target = _target(selector="[data-orb-target=buy-widget-renamed]")
    scan = engine.product_delta_scan([_product(targets=[changed_target])])

    assert scan["results"][0]["status"] == "changed"
    assert scan["results"][0]["structural_drift"] is True
    result = engine.reverify_targets("widget-1", [changed_target])
    assert result["quarantined"] == ["buy-widget"]
    assert result["published"] is False


def test_changed_target_is_quarantined_before_verified_replacement(tmp_path):
    engine = _engine(tmp_path)
    first = _product()
    engine.product_delta_scan([first])
    engine.reverify_targets("widget-1", first["targets"])

    changed = _product(
        price=59,
        targets=[_target(target_id="buy-widget-v2", selector="[data-orb-target=buy-widget-v2]")],
    )
    engine.product_delta_scan([changed])
    result = engine.reverify_targets("widget-1", changed["targets"])

    assert result["quarantined"] == ["buy-widget"]
    assert result["promoted"] == ["buy-widget-v2"]
    assert result["published"] is True
    state = engine.store.load()
    assert state["targets"]["widget-1"]["buy-widget"]["status"] == "quarantined"
    assert state["targets"]["widget-1"]["buy-widget-v2"]["status"] == "verified"


def test_unverified_delta_remains_pending_and_non_authoritative(tmp_path):
    engine = _engine(tmp_path)
    first = _product()
    engine.product_delta_scan([first])
    engine.reverify_targets("widget-1", first["targets"])

    changed = _product(price=79, targets=[_target(verified=False)])
    scan = engine.product_delta_scan([changed])
    assert scan["deep_rescan_required"] is False
    result = engine.reverify_targets("widget-1", changed["targets"])

    assert result["published"] is False
    assert result["pending"] == ["buy-widget"]
    assert engine.answer("What is the price of the Widget?")["answer"].endswith("49.")


def test_structural_drift_requests_deep_rescan(tmp_path):
    engine = _engine(tmp_path)

    scan = engine.product_delta_scan([{
        **_product(),
        "page_structure_hash": "changed-layout",
    }])

    assert scan["deep_rescan_required"] is True
    assert scan["results"][0]["structural_drift"] is True


def test_unknown_product_never_becomes_authoritative(tmp_path):
    engine = FieldMaintenanceEngine(
        FieldMaintenanceStore(tmp_path / "field-maintenance"),
        known_products=[{"entity_id": "different-product"}],
    )
    observation = _product()

    engine.product_delta_scan([observation])
    result = engine.reverify_targets("widget-1", observation["targets"])

    assert result["published"] is False
    assert engine.answer("What is the price of the Widget?") is None


def test_dry_run_does_not_write_observed_state(tmp_path):
    engine = _engine(tmp_path)

    scan = engine.product_delta_scan([_product()], dry_run=True)

    assert scan["mode"] == "dry_run"
    assert engine.status()["products_tracked"] == 0
