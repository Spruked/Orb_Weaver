/**
 * ORB LiDAR 2D Mapping Protocol v1.0
 *
 * World-frame coordinates are document CSS pixels. Runtime movement must still
 * verify the live DOM/accessibility target before pointing or acting.
 */

export type LidarMovementVector = 'snap' | 'glide' | 'pulse' | 'hover';

export interface LidarTelemetryFrame {
  event_type: 'pointer_target_lock' | 'map_refresh' | 'heartbeat_ack';
  target_id: string;
  absolute_top: number;
  absolute_left: number;
  width: number;
  height: number;
  semantic_intent: string;
  movement_vector: LidarMovementVector;
  confidence?: number;
  metadata?: Record<string, unknown>;
  timestamp_iso?: string;
}

export interface LidarClientInboundMessage {
  event_type: 'heartbeat' | 'pointer_drift_alert' | 'target_acquired_ack';
  current_route: string;
  pointing_target_id?: string;
  status: 'ready' | 'active' | 'drift_detected' | 'error';
  viewport_width?: number;
  viewport_height?: number;
  scroll_y?: number;
  scroll_x?: number;
}

export type LidarAnchorStrategy =
  | 'element_center'
  | 'element_top_left'
  | 'element_top_right'
  | 'element_bottom_left'
  | 'element_bottom_right';

export interface LidarPointerCoordinate {
  target_id: string;
  absoluteTop: number;
  absoluteLeft: number;
  width: number;
  height: number;
  anchor_strategy: LidarAnchorStrategy;
  last_resolved_at: number;
  semantic_locator?: string;
}

export interface LidarViewportCoordinate {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface LidarPointerRecord {
  target_id: string;
  semantic_locator: string;
  anchor_strategy?: string;
}

export type Lidar2DMappingStatus =
  | 'uninitialized'
  | 'scanning'
  | 'ready'
  | 'stale'
  | 'rebuilding';
