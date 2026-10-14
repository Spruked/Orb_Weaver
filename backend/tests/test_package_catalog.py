from app.orb.package_catalog import load_catalog, save_catalog, update_package


def test_customer_catalog_starts_tbd_and_unpurchasable(tmp_path, monkeypatch):
    monkeypatch.setattr("app.orb.package_catalog.require_vault_path", lambda path, purpose: path)
    packages = load_catalog(tmp_path)
    assert len(packages) == 8
    assert {item["category"] for item in packages} == {"scan", "specialized", "orb"}
    assert all(item["price_cents"] is None for item in packages)
    assert all(item["purchasable"] is False for item in packages)


def test_customer_catalog_requires_price_for_purchase(tmp_path, monkeypatch):
    monkeypatch.setattr("app.orb.package_catalog.require_vault_path", lambda path, purpose: path)
    packages = load_catalog(tmp_path)
    packages = update_package(tmp_path, "scan-seo-intelligence", {"price_cents": 1888, "purchasable": True})
    seo = next(item for item in packages if item["sku"] == "scan-seo-intelligence")
    assert seo["price_cents"] == 1888
    assert seo["pricing_status"] == "set"
    assert seo["purchasable"] is True

    save_catalog(tmp_path, [{**seo, "price_cents": None, "purchasable": True}])
    reset = next(item for item in load_catalog(tmp_path) if item["sku"] == "scan-seo-intelligence")
    assert reset["pricing_status"] == "tbd"
    assert reset["purchasable"] is False
