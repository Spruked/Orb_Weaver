import { Lidar2DMappingCoordinateCache } from './Lidar2DMappingCoordinateCache';
import {
  createLidar2DMappingTelemetryState,
  LIDAR_HEARTBEAT_INTERVAL_MS,
  LIDAR_HEARTBEAT_TIMEOUT_MS,
  LIDAR_MAX_RECONNECT_ATTEMPTS,
  LIDAR_RECONNECT_BASE_DELAY_MS,
  type Lidar2DMappingTelemetryState,
  type LidarTelemetryConnectionStatus,
} from './Lidar2DMappingTelemetry.state';
import type {
  LidarClientInboundMessage,
  LidarTelemetryFrame,
} from './Lidar2DMapping.types';

const LOCAL_API_PORT_PAIRS: Record<string, string> = {
  '16510': '16500',
  '16610': '16600',
  '16666': '19667',
  '16667': '19667',
  '16777': '16776',
};

export function defaultLidarTelemetryUrl(): string {
  if (typeof window === 'undefined') {
    return 'ws://127.0.0.1:16500/ws/lidar-2d-mapping';
  }

  const { hostname, port, protocol } = window.location;
  const websocketProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
  const normalizedHostname = hostname === '0.0.0.0' ? '127.0.0.1' : hostname;
  const websocketHostname = normalizedHostname.includes(':') && !normalizedHostname.startsWith('[')
    ? `[${normalizedHostname}]`
    : normalizedHostname;
  const localOrPrivateHost =
    port === '16510' ||
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '0.0.0.0' ||
    hostname === '::1' ||
    hostname === '[::1]' ||
    hostname.startsWith('192.168.') ||
    hostname.startsWith('10.') ||
    /^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname);

  if (localOrPrivateHost) {
    const backendPort = LOCAL_API_PORT_PAIRS[port] || '16500';
    return `${websocketProtocol}//${websocketHostname}:${backendPort}/ws/lidar-2d-mapping`;
  }

  return `${websocketProtocol}//${window.location.host}/ws/lidar-2d-mapping`;
}

/** Bidirectional telemetry lane for the LiDAR 2D Mapping package. */
export class Lidar2DMappingTelemetryClient {
  private readonly state: Lidar2DMappingTelemetryState;
  private readonly lidar = Lidar2DMappingCoordinateCache.getInstance();

  constructor(wsUrl = defaultLidarTelemetryUrl()) {
    this.state = createLidar2DMappingTelemetryState(wsUrl);
  }

  connect(): void {
    if (
      this.state.socket?.readyState === WebSocket.OPEN ||
      this.state.socket?.readyState === WebSocket.CONNECTING
    ) return;

    this.setStatus('connecting');
    try {
      this.state.socket = new WebSocket(this.state.url);
    } catch (error) {
      console.error('[LiDAR 2D Mapping] WebSocket construction failed', error);
      this.setStatus('error');
      this.scheduleReconnect();
      return;
    }

    this.state.socket.onopen = () => {
      this.setStatus('connected');
      this.state.reconnectAttempt = 0;
      this.startHeartbeatLoop();
      this.sendStatusSync();
    };
    this.state.socket.onmessage = (event) => this.handleMessage(String(event.data));
    this.state.socket.onclose = () => {
      this.cleanupConnection();
      this.scheduleReconnect();
    };
    this.state.socket.onerror = (error) => {
      console.error('[LiDAR 2D Mapping] WebSocket error', error);
    };
  }

  onFrameReceived(callback: (frame: LidarTelemetryFrame) => void): void {
    this.state.onFrameCallback = callback;
  }

  onStatusChange(callback: (status: LidarTelemetryConnectionStatus) => void): void {
    this.state.onStatusChangeCallback = callback;
  }

  reportDrift(targetId: string): void {
    if (this.state.socket?.readyState !== WebSocket.OPEN) return;
    const payload: LidarClientInboundMessage = {
      event_type: 'pointer_drift_alert',
      current_route: window.location.pathname + window.location.hash,
      pointing_target_id: targetId,
      status: 'drift_detected',
      viewport_width: window.innerWidth,
      viewport_height: window.innerHeight,
      scroll_y: window.scrollY,
      scroll_x: window.scrollX,
    };
    this.state.socket.send(JSON.stringify(payload));
  }

  disconnect(): void {
    this.setStatus('disconnected');
    if (this.state.reconnectTimer) {
      clearTimeout(this.state.reconnectTimer);
      this.state.reconnectTimer = null;
    }
    this.state.reconnectAttempt = LIDAR_MAX_RECONNECT_ATTEMPTS;
    this.cleanupConnection();
  }

  getStatus(): LidarTelemetryConnectionStatus {
    return this.state.status;
  }

  private handleMessage(rawData: string): void {
    try {
      const message = JSON.parse(rawData) as LidarTelemetryFrame;
      if (message.event_type === 'heartbeat_ack') {
        this.state.lastHeartbeatAckAt = Date.now();
        return;
      }
      if (message.event_type !== 'pointer_target_lock' && message.event_type !== 'map_refresh') return;
      const frame = { ...message };
      if (typeof frame.confidence === 'number') frame.confidence = Math.min(frame.confidence, 0.75);
      this.lidar.injectFrame(frame);
      this.state.lastFrameAt = Date.now();
      this.state.onFrameCallback?.(frame);
    } catch (error) {
      console.error('[LiDAR 2D Mapping] Malformed telemetry frame', error);
    }
  }

  private sendStatusSync(): void {
    if (this.state.socket?.readyState !== WebSocket.OPEN) return;
    const payload: LidarClientInboundMessage = {
      event_type: 'heartbeat',
      current_route: window.location.pathname + window.location.hash,
      status: 'active',
      viewport_width: window.innerWidth,
      viewport_height: window.innerHeight,
      scroll_y: window.scrollY,
      scroll_x: window.scrollX,
    };
    this.state.socket.send(JSON.stringify(payload));
  }

  private startHeartbeatLoop(): void {
    if (this.state.heartbeatTimer) return;
    this.state.heartbeatTimer = setInterval(() => {
      if (this.state.socket?.readyState !== WebSocket.OPEN) return;
      this.sendStatusSync();
      const age = Date.now() - this.state.lastHeartbeatAckAt;
      if (this.state.lastHeartbeatAckAt > 0 && age > LIDAR_HEARTBEAT_TIMEOUT_MS) {
        this.state.socket.close();
      }
    }, LIDAR_HEARTBEAT_INTERVAL_MS);
  }

  private scheduleReconnect(): void {
    if (this.state.reconnectTimer || this.state.reconnectAttempt >= LIDAR_MAX_RECONNECT_ATTEMPTS) {
      if (this.state.reconnectAttempt >= LIDAR_MAX_RECONNECT_ATTEMPTS) this.setStatus('error');
      return;
    }
    this.setStatus('reconnecting');
    const delay = LIDAR_RECONNECT_BASE_DELAY_MS * 2 ** this.state.reconnectAttempt;
    this.state.reconnectTimer = setTimeout(() => {
      this.state.reconnectTimer = null;
      this.state.reconnectAttempt += 1;
      this.connect();
    }, delay);
  }

  private cleanupConnection(): void {
    if (this.state.heartbeatTimer) {
      clearInterval(this.state.heartbeatTimer);
      this.state.heartbeatTimer = null;
    }
    if (this.state.socket) {
      this.state.socket.onopen = null;
      this.state.socket.onmessage = null;
      this.state.socket.onclose = null;
      this.state.socket.onerror = null;
      this.state.socket.close();
      this.state.socket = null;
    }
  }

  private setStatus(status: LidarTelemetryConnectionStatus): void {
    this.state.status = status;
    this.state.onStatusChangeCallback?.(status);
  }
}
