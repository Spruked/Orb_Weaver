from app.routers.customer_review_package import PACKAGE_PRICE_TIERS, _line_item_paid_tier
from app.routers.orb_telemetry import router


def test_only_package_one_and_two_prices_unlock_full_review_package():
    assert PACKAGE_PRICE_TIERS == {4900: "package_1", 9900: "package_2"}
    assert _line_item_paid_tier({"unit_amount_cents": 4900, "quantity": 1})["tier"] == "package_1"
    assert _line_item_paid_tier({"unit_amount_cents": 9900, "quantity": 1})["tier"] == "package_2"
    assert _line_item_paid_tier({"unit_amount_cents": 0, "quantity": 1}) is None
    assert _line_item_paid_tier({"unit_amount_cents": 4900, "quantity": 0}) is None


def test_router_preserves_pointer_lidar_urls_and_mounts_review_package_api():
    paths = {getattr(route, "path", "") for route in router.routes}
    assert "/ws/orb-pointer" in paths
    assert "/ws/lidar-2d-mapping" in paths
    assert "/api/projects/{project_id}/customer-review-package" in paths
    assert "/api/projects/{project_id}/customer-review-package/download" in paths
