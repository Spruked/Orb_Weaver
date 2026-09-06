"""LiDAR 2D Mapping telemetry WebSocket for Website ORB geometry frames."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("orb.lidar_2d_mapping")
router = APIRouter(tags=["lidar-2d-mapping"])


class Lidar2DMappingTelemetryFrame(BaseModel):
    event_type: Literal["pointer_target_lock", "map_refresh"] = "pointer_target_lock"
    target_id: str = Field(min_length=1)
    absolute_top: float = Field(ge=0)
    absolute_left: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    semantic_intent: str = Field(min_length=1)
    movement_vector: Literal["snap", "glide", "pulse", "hover"] = "glide"
    confidence: Optional[float] = Field(default=None, ge=0, le=0.75)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp_iso: Optional[str] = None


class Lidar2DMappingInboundMessage(BaseModel):
    event_type: Literal["heartbeat", "pointer_drift_alert", "target_acquired_ack"]
    current_route: str = Field(min_length=1)
    pointing_target_id: Optional[str] = None
    status: Literal["ready", "active", "drift_detected", "error"] = "ready"
    viewport_width: Optional[int] = Field(default=None, ge=100)
    viewport_height: Optional[int] = Field(default=None, ge=100)
    scroll_y: Optional[float] = Field(default=None, ge=0)
    scroll_x: Optional[float] = Field(default=None, ge=0)


class Lidar2DMappingTelemetryManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast_frame(self, frame: Lidar2DMappingTelemetryFrame) -> None:
        payload = frame.model_dump_json(exclude_none=True)
        async with self._lock:
            connections = list(self.active_connections)
        dead: List[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead.append(connection)
        if dead:
            async with self._lock:
                for connection in dead:
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)


lidar_2d_mapping_telemetry = Lidar2DMappingTelemetryManager()


@router.websocket("/lidar-2d-mapping")
async def lidar_2d_mapping_endpoint(websocket: WebSocket) -> None:
    """Serve the LiDAR lane under the parent `/ws` telemetry namespace."""
    await lidar_2d_mapping_telemetry.connect(websocket)
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                inbound = Lidar2DMappingInboundMessage(**json.loads(raw_text))
            except (json.JSONDecodeError, ValidationError) as error:
                logger.warning("LiDAR 2D Mapping inbound frame rejected: %s", error)
                continue

            if inbound.event_type == "heartbeat":
                await websocket.send_json(
                    {
                        "event_type": "heartbeat_ack",
                        "target_id": "system",
                        "absolute_top": 0,
                        "absolute_left": 0,
                        "width": 0,
                        "height": 0,
                        "semantic_intent": "keepalive",
                        "movement_vector": "hover",
                        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
                    }
                )
            elif inbound.event_type == "pointer_drift_alert":
                logger.warning(
                    "LiDAR 2D Mapping drift target=%s route=%s viewport=%sx%s scroll=(%s,%s)",
                    inbound.pointing_target_id,
                    inbound.current_route,
                    inbound.viewport_width,
                    inbound.viewport_height,
                    inbound.scroll_x,
                    inbound.scroll_y,
                )

    except WebSocketDisconnect:
        await lidar_2d_mapping_telemetry.disconnect(websocket)
    except Exception:
        logger.exception("LiDAR 2D Mapping telemetry loop failed")
        await lidar_2d_mapping_telemetry.disconnect(websocket)


async def trigger_lidar_2d_mapping_target_lock(
    *,
    target_id: str,
    element_data: Dict[str, Any],
    intent: str,
    movement_vector: Literal["snap", "glide", "pulse", "hover"] = "glide",
    confidence: Optional[float] = None,
) -> None:
    frame = Lidar2DMappingTelemetryFrame(
        target_id=target_id,
        absolute_top=float(element_data.get("absoluteTop", 0)),
        absolute_left=float(element_data.get("absoluteLeft", 0)),
        width=float(element_data.get("width", 1)),
        height=float(element_data.get("height", 1)),
        semantic_intent=intent,
        movement_vector=movement_vector,
        confidence=min(confidence, 0.75) if confidence is not None else None,
        timestamp_iso=datetime.now(timezone.utc).isoformat(),
    )
    await lidar_2d_mapping_telemetry.broadcast_frame(frame)
