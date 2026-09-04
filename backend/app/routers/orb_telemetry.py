import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field, ValidationError

from app.agency import agency_contract_status

logger = logging.getLogger('orb.telemetry')

router = APIRouter(prefix='/ws', tags=['orb-telemetry'])


class TelemetryFrame(BaseModel):
  event_type: str = Field(default='pointer_target_lock', pattern='^(pointer_target_lock|map_refresh|heartbeat_ack)$')
  target_id: str = Field(..., min_length=1)
  absolute_top: float = Field(..., ge=0)
  absolute_left: float = Field(..., ge=0)
  width: float = Field(..., ge=0)
  height: float = Field(..., ge=0)
  semantic_intent: str = Field(..., min_length=1)
  movement_vector: str = Field(default='glide', pattern='^(snap|glide|pulse|hover)$')
  confidence: Optional[float] = Field(default=None, le=0.75, ge=0.0)
  metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
  timestamp_iso: Optional[str] = None


class ClientInboundMessage(BaseModel):
  event_type: str = Field(..., pattern='^(heartbeat|pointer_drift_alert|target_acquired_ack)$')
  current_route: str = Field(..., min_length=1)
  pointing_target_id: Optional[str] = Field(default=None)
  status: str = Field(default='ready', pattern='^(ready|active|drift_detected|error)$')
  viewport_width: Optional[int] = Field(default=None, ge=100)
  viewport_height: Optional[int] = Field(default=None, ge=100)
  scroll_y: Optional[float] = Field(default=None, ge=0)
  scroll_x: Optional[float] = Field(default=None, ge=0)


class OrbTelemetryManager:
  def __init__(self):
    self.active_connections: List[WebSocket] = []
    self._lock = asyncio.Lock()

  async def connect(self, websocket: WebSocket) -> None:
    await websocket.accept()
    async with self._lock:
      self.active_connections.append(websocket)
    client_host = websocket.client.host if websocket.client else 'unknown'
    logger.info('[Telemetry] ORB instance connected from %s. Active: %s', client_host, len(self.active_connections))

  async def disconnect(self, websocket: WebSocket) -> None:
    async with self._lock:
      if websocket in self.active_connections:
        self.active_connections.remove(websocket)
    logger.info('[Telemetry] ORB instance disconnected. Remaining: %s', len(self.active_connections))

  async def broadcast_frame(self, frame: TelemetryFrame) -> None:
    payload = frame.model_dump_json(exclude_none=True)
    dead_connections: List[WebSocket] = []

    async with self._lock:
      connections = list(self.active_connections)

    for conn in connections:
      try:
        await conn.send_text(payload)
      except Exception as exc:
        logger.warning('[Telemetry] Frame drop on %s: %s', conn.client, exc)
        dead_connections.append(conn)

    if dead_connections:
      async with self._lock:
        for dead in dead_connections:
          if dead in self.active_connections:
            self.active_connections.remove(dead)
          try:
            await dead.close(code=status.WS_1011_INTERNAL_ERROR)
          except Exception:
            pass

  def get_connection_count(self) -> int:
    return len(self.active_connections)


telemetry_manager = OrbTelemetryManager()


@router.get('/agency-status')
async def agency_status_endpoint():
  """Read-only agency-contract and ORB telemetry health for the owner dashboard."""
  return agency_contract_status(telemetry_manager.get_connection_count())


@router.websocket('/orb-pointer')
async def orb_telemetry_endpoint(websocket: WebSocket):
  await telemetry_manager.connect(websocket)
  try:
    while True:
      raw_text = await websocket.receive_text()

      try:
        raw_json = json.loads(raw_text)
        inbound = ClientInboundMessage(**raw_json)

        if inbound.event_type == 'heartbeat':
          ack = TelemetryFrame(
            event_type='heartbeat_ack',
            target_id='system',
            absolute_top=0.0,
            absolute_left=0.0,
            width=0.0,
            height=0.0,
            semantic_intent='keepalive',
            movement_vector='hover',
            timestamp_iso=datetime.utcnow().isoformat(),
          )
          await websocket.send_text(ack.model_dump_json(exclude_none=True))
        elif inbound.event_type == 'pointer_drift_alert':
          logger.warning(
            '[SLAM Drift] target=%s route=%s viewport=%sx%s scroll=(%s, %s)',
            inbound.pointing_target_id,
            inbound.current_route,
            inbound.viewport_width,
            inbound.viewport_height,
            inbound.scroll_x,
            inbound.scroll_y,
          )
        elif inbound.event_type == 'target_acquired_ack':
          logger.info('[Telemetry] Target acquisition confirmed: %s', inbound.pointing_target_id)
      except (json.JSONDecodeError, ValidationError) as err:
        logger.error('[Telemetry] Inbound schema violation: %s', err)
  except WebSocketDisconnect:
    await telemetry_manager.disconnect(websocket)
  except Exception as exc:
    logger.error('[Telemetry] Critical loop failure: %s', exc)
    await telemetry_manager.disconnect(websocket)


async def trigger_pointer_lock(
  target_id: str,
  element_data: Dict[str, Any],
  intent: str,
  movement_vector: str = 'glide',
  confidence: Optional[float] = None,
) -> None:
  if confidence is not None:
    confidence = min(confidence, 0.75)

  frame = TelemetryFrame(
    event_type='pointer_target_lock',
    target_id=target_id,
    absolute_top=float(element_data.get('absoluteTop', 0)),
    absolute_left=float(element_data.get('absoluteLeft', 0)),
    width=float(element_data.get('width', 50)),
    height=float(element_data.get('height', 50)),
    semantic_intent=intent,
    movement_vector=movement_vector,
    confidence=confidence,
    metadata=element_data.get('metadata') if isinstance(element_data.get('metadata'), dict) else {},
    timestamp_iso=datetime.utcnow().isoformat(),
  )
  await telemetry_manager.broadcast_frame(frame)
