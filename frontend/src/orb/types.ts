export type MovementVector = 'snap' | 'glide' | 'pulse' | 'hover';

export interface TelemetryFrame {
  event_type: 'pointer_target_lock' | 'map_refresh' | 'heartbeat_ack';
  target_id: string;
  absolute_top: number;
  absolute_left: number;
  width: number;
  height: number;
  semantic_intent: string;
  movement_vector: MovementVector;
  confidence?: number;
  metadata?: Record<string, unknown>;
  timestamp_iso?: string;
}

export interface ClientInboundMessage {
  event_type: 'heartbeat' | 'pointer_drift_alert' | 'target_acquired_ack';
  current_route: string;
  pointing_target_id?: string;
  status: 'ready' | 'active' | 'drift_detected' | 'error';
  viewport_width?: number;
  viewport_height?: number;
  scroll_y?: number;
  scroll_x?: number;
}

export interface PointerCoordinate {
  target_id: string;
  absoluteTop: number;
  absoluteLeft: number;
  width: number;
  height: number;
  anchor_strategy: 'element_center' | 'element_top_left' | 'element_top_right' | 'element_bottom_left' | 'element_bottom_right';
  last_resolved_at: number;
  semantic_locator?: string;
}

export interface ViewportCoordinate {
  top: number;
  left: number;
  width: number;
  height: number;
}

export type LidarCacheStatus = 'uninitialized' | 'scanning' | 'ready' | 'stale' | 'rebuilding';