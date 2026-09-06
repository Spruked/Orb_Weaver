from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.crawler import OrbWeaverCrawler
from app.routers.orb_telemetry import router as orb_telemetry_router


def test_canonical_crawler_has_lidar_weave_support_installed():
    """The production crawler class, not a helper double, must carry the weave wrapper."""
    assert getattr(OrbWeaverCrawler, "_orb_scope_support_installed", False) is True
    assert OrbWeaverCrawler._crawl_page.__name__ == "weave_crawl_page"


def test_lidar_websocket_is_registered_under_runtime_ws_namespace():
    """The same router included by backend/main.py must expose the LiDAR lane."""
    app = FastAPI()
    app.include_router(orb_telemetry_router)
    client = TestClient(app)

    with client.websocket_connect("/ws/lidar-2d-mapping") as websocket:
        websocket.send_json(
            {
                "event_type": "heartbeat",
                "current_route": "/",
                "status": "active",
                "viewport_width": 1280,
                "viewport_height": 720,
                "scroll_y": 0,
                "scroll_x": 0,
            }
        )
        payload = websocket.receive_json()

    assert payload["event_type"] == "heartbeat_ack"
    assert payload["target_id"] == "system"
    assert payload["semantic_intent"] == "keepalive"
