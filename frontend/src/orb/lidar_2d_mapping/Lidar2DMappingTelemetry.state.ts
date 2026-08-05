import type { LidarTelemetryFrame } from './Lidar2DMapping.types';

export type LidarTelemetryConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error';

export interface Lidar2DMappingTelemetryState {
  socket: WebSocket | null;
  status: LidarTelemetryConnectionStatus;
  url: string;
  reconnectAttempt: number;
  reconnectTimer: ReturnType<typeof setTimeout> | null;
  heartbeatTimer: ReturnType<typeof setInterval> | null;
  lastFrameAt: number;
  lastHeartbeatAckAt: number;
  onFrameCallback: ((frame: LidarTelemetryFrame) => void) | null;
  onStatusChangeCallback: ((status: LidarTelemetryConnectionStatus) => void) | null;
}

export const LIDAR_MAX_RECONNECT_ATTEMPTS = 5;
export const LIDAR_RECONNECT_BASE_DELAY_MS = 3_000;
export const LIDAR_HEARTBEAT_INTERVAL_MS = 15_000;
export const LIDAR_HEARTBEAT_TIMEOUT_MS = 35_000;

export function createLidar2DMappingTelemetryState(url: string): Lidar2DMappingTelemetryState {
  return {
    socket: null,
    status: 'disconnected',
    url,
    reconnectAttempt: 0,
    reconnectTimer: null,
    heartbeatTimer: null,
    lastFrameAt: 0,
    lastHeartbeatAckAt: 0,
    onFrameCallback: null,
    onStatusChangeCallback: null,
  };
}
