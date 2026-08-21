from types import SimpleNamespace

from app.catalog.compiler import compile_commercial_catalog


def page(url: str, payload, product_names=None):
    return SimpleNamespace(
        url=url,
        schema_markup=[{"type": "json-ld", "data": payload}],
        entity_analysis={"product_names": product_names or []},
    )


def test_catalog_compiles_product_offer_variant_and_specs():
    payload = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Trail 500",
        "sku": "TR-500",
        "brand": {"@type": "Brand", "name": "Example Motors"},
        "category": "ATV",
        "description": "Utility ATV",
        "additionalProperty": [
            {"@type": "PropertyValue", "name": "Engine", "value": "500cc"},
        ],
        "offers": {
            "@type": "Offer",
            "price": "6,999.00",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
            "url": "/trail-500",
        },
        "hasVariant": [
            {
                "@type": "Product",
                "name": "Trail 500 Camo",
                "sku": "TR-500-CAMO",
                "offers": {"@type": "Offer", "price": "7199", "priceCurrency": "USD"},
            }
        ],
    }

    catalog = compile_commercial_catalog([page("https://example.com/trail-500", payload)])

    assert catalog["entry_count"] == 1
    assert catalog["product_count"] == 1
    assert catalog["priced_entry_count"] == 1
    assert catalog["sku_model_count"] == 1
    assert catalog["availability_count"] == 1
    assert catalog["variant_count"] == 1
    assert catalog["specification_count"] >= 1
    entry = catalog["entries"][0]
    assert entry["name"] == "Trail 500"
    assert entry["sku"] == "TR-500"
    assert entry["offers"][0]["price"] == "6999"
    assert entry["offers"][0]["availability"] == "in_stock"
    assert entry["specifications"]["Engine"] == "500cc"
    assert catalog["indexes"]["by_sku_model"]["tr-500"] == [entry["catalog_id"]]
    assert catalog["runtime_policy"]["deterministic_lookup_first"] is True


def test_catalog_falls_back_to_extracted_product_names_without_inventing_prices():
    p = SimpleNamespace(
        url="https://example.com/products",
        schema_markup=[],
        entity_analysis={"product_names": ["Widget One"]},
    )
    catalog = compile_commercial_catalog([p])
    assert catalog["entry_count"] == 1
    assert catalog["priced_entry_count"] == 0
    assert catalog["entries"][0]["name"] == "Widget One"
    assert catalog["entries"][0]["offers"] == []
    assert catalog["entries"][0]["evidence"] == ["entity_extraction"]


def test_catalog_compiles_services_as_first_class_entries():
    payload = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": "Implementation Service",
        "category": "Professional Services",
        "offers": {"@type": "Offer", "price": "1200", "priceCurrency": "USD"},
    }
    catalog = compile_commercial_catalog([page("https://example.com/services", payload)])
    assert catalog["service_count"] == 1
    assert catalog["priced_entry_count"] == 1
    assert catalog["entries"][0]["kind"] == "Service"
