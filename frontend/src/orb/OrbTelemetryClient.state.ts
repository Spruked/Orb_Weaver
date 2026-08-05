import type { TelemetryFrame } from './types';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

export interface TelemetryClientState {
  socket: WebSocket | null;
  status: ConnectionStatus;
  url: string;
  reconnectAttempt: number;
  reconnectTimer: ReturnType<typeof setTimeout> | null;
  heartbeatTimer: ReturnType<typeof setInterval> | null;
  lastFrameAt: number;
  lastHeartbeatAckAt: number;
  onFrameCallback: ((frame: TelemetryFrame) => void) | null;
  onStatusChangeCallback: ((status: ConnectionStatus) => void) | null;
}

export const MAX_RECONNECT_ATTEMPTS = 5;
export const RECONNECT_BASE_DELAY_MS = 3000;
export const HEARTBEAT_INTERVAL_MS = 15000;
export const HEARTBEAT_TIMEOUT_MS = 35000;

export function createTelemetryState(url: string): TelemetryClientState {
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