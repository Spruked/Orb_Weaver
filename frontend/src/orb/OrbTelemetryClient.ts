import { LidarCoordinateCache } from './LidarCoordinateCache';
import {
  HEARTBEAT_INTERVAL_MS,
  HEARTBEAT_TIMEOUT_MS,
  MAX_RECONNECT_ATTEMPTS,
  RECONNECT_BASE_DELAY_MS,
  createTelemetryState,
  type TelemetryClientState,
} from './OrbTelemetryClient.state';
import type { ClientInboundMessage, TelemetryFrame } from './types';

export class OrbTelemetryClient {
  private state: TelemetryClientState;

  private lidar: LidarCoordinateCache;

  constructor(wsUrl: string = 'ws://localhost:8000/ws/orb-pointer') {
    this.state = createTelemetryState(wsUrl);
    this.lidar = LidarCoordinateCache.getInstance();
  }

  connect(): void {
    if (
      this.state.socket?.readyState === WebSocket.OPEN
      || this.state.socket?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }

    this.setStatus('connecting');

    try {
      this.state.socket = new WebSocket(this.state.url);
    } catch (err) {
      console.error('[Telemetry] Socket construction failed:', err);
      this.setStatus('error');
      this.scheduleReconnect();
      return;
    }

    this.state.socket.onopen = () => {
      this.setStatus('connected');
      this.state.reconnectAttempt = 0;
      this.startHeartbeatLoop();
      this.sendStatusSync('active');
    };

    this.state.socket.onmessage = (event) => {
      this.handleMessage(event.data);
    };

    this.state.socket.onclose = (event) => {
      console.warn(`[Telemetry] Channel closed. Code: ${event.code}.`);
      this.cleanupConnection();
      this.scheduleReconnect();
    };

    this.state.socket.onerror = (error) => {
      console.error('[Telemetry] Socket exception:', error);
    };
  }

  onFrameReceived(callback: (frame: TelemetryFrame) => void): void {
    this.state.onFrameCallback = callback;
  }

  onStatusChange(callback: (status: TelemetryClientState['status']) => void): void {
    this.state.onStatusChangeCallback = callback;
  }

  reportDrift(targetId: string, reason = 'layout_mismatch'): void {
    if (this.state.socket?.readyState !== WebSocket.OPEN) return;

    const payload: ClientInboundMessage = {
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
    console.log(`[Telemetry] Drift alert dispatched: ${targetId} (${reason})`);
  }

  disconnect(): void {
    this.setStatus('disconnected');
    if (this.state.reconnectTimer) {
      clearTimeout(this.state.reconnectTimer);
      this.state.reconnectTimer = null;
    }
    this.state.reconnectAttempt = MAX_RECONNECT_ATTEMPTS;
    this.cleanupConnection();
  }

  getStatus(): string {
    return this.state.status;
  }

  private handleMessage(rawData: string): void {
    try {
      const message = JSON.parse(rawData) as TelemetryFrame | { event_type: string };

      if (message.event_type === 'heartbeat_ack') {
        this.state.lastHeartbeatAckAt = Date.now();
        return;
      }

      if (message.event_type === 'pointer_target_lock' || message.event_type === 'map_refresh') {
        const frame = message as TelemetryFrame;
        if (frame.confidence && frame.confidence > 0.75) {
          frame.confidence = 0.75;
        }
        this.lidar.injectFrame(frame);
        this.state.lastFrameAt = Date.now();
        this.state.onFrameCallback?.(frame);
      }
    } catch (err) {
      console.error('[Telemetry] Malformed frame segment:', err);
    }
  }

  private sendStatusSync(status: ClientInboundMessage['status']): void {
    if (this.state.socket?.readyState !== WebSocket.OPEN) return;

    const payload: ClientInboundMessage = {
      event_type: 'heartbeat',
      current_route: window.location.pathname + window.location.hash,
      status,
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
      if (this.state.socket?.readyState === WebSocket.OPEN) {
        this.sendStatusSync('active');
        const sinceLastAck = Date.now() - this.state.lastHeartbeatAckAt;
        if (this.state.lastHeartbeatAckAt > 0 && sinceLastAck > HEARTBEAT_TIMEOUT_MS) {
          this.state.socket.close();
        }
      }
    }, HEARTBEAT_INTERVAL_MS);
  }

  private scheduleReconnect(): void {
    if (this.state.reconnectTimer) return;
    if (this.state.reconnectAttempt >= MAX_RECONNECT_ATTEMPTS) {
      this.setStatus('error');
      console.error('[Telemetry] Max reconnection attempts reached.');
      return;
    }

    this.setStatus('reconnecting');
    const delay = RECONNECT_BASE_DELAY_MS * Math.pow(2, this.state.reconnectAttempt);
    const jitter = Math.random() * 1000;

    this.state.reconnectTimer = setTimeout(() => {
      this.state.reconnectTimer = null;
      this.state.reconnectAttempt += 1;
      this.connect();
    }, delay + jitter);
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
      this.state.socket = null;
    }
  }

  private setStatus(status: TelemetryClientState['status']): void {
    this.state.status = status;
    this.state.onStatusChangeCallback?.(status);
  }
}