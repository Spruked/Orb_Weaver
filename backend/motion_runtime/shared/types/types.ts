/**
 * motion_runtime — shared types
 *
 * Generic concepts only. No product names, customer names,
 * site-specific selectors, routes, or business rules.
 */

// ---------------------------------------------------------------------------
// Geometry & physics primitives
// ---------------------------------------------------------------------------

export interface Point {
  x: number;
  y: number;
}

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Velocity {
  vx: number;
  vy: number;
}

export interface MovementVector {
  from: Point;
  to: Point;
  velocity: Velocity;
  /** Normalized direction (unit vector) when length > 0 */
  direction: Point;
  length: number;
}

// ---------------------------------------------------------------------------
// Viewport & DOM geometry (generic)
// ---------------------------------------------------------------------------

export interface Viewport {
  width: number;
  height: number;
  scrollX: number;
  scrollY: number;
  /** Device pixel ratio */
  dpr: number;
}

export interface DOMGeometry {
  /** Bounding client rect relative to viewport */
  rect: Rect;
  /** Center point in viewport coordinates */
  center: Point;
  /** Whether the element is currently intersecting the viewport */
  inViewport: boolean;
  /** Intersection ratio 0–1 */
  visibility: number;
}

// ---------------------------------------------------------------------------
// Targets, anchors, obstacles
// ---------------------------------------------------------------------------

export type TargetKind = 'element' | 'region' | 'point' | 'cursor';

export interface Target {
  id: string;
  kind: TargetKind;
  /** Optional human-readable label (config-supplied) */
  label?: string;
  geometry: DOMGeometry;
  /** Priority / weight for orbital attention (config-supplied) */
  priority?: number;
  /** Opaque metadata from deployment config — runtime never interprets keys */
  meta?: Record<string, unknown>;
}

export interface Anchor {
  id: string;
  point: Point;
  /** Soft radius for orbital attraction */
  radius: number;
  strength: number;
}

export interface Obstacle {
  id: string;
  rect: Rect;
  /** Hard (impassable) vs soft (repulsion field) */
  kind: 'hard' | 'soft';
  repulsion?: number;
}

// ---------------------------------------------------------------------------
// Cursor & physical presence
// ---------------------------------------------------------------------------

export interface CursorState {
  position: Point;
  velocity: Velocity;
  /** true when a pointing device is actively tracked */
  present: boolean;
  lastUpdated: number;
}

export interface PhysicalPresence {
  cursor: CursorState;
  /** Approximate “attention” focus derived from cursor + viewport */
  focusPoint: Point | null;
}

// ---------------------------------------------------------------------------
// Behavioral intent & ambient / hold / guided states
// ---------------------------------------------------------------------------

export type BehavioralState = 'ambient' | 'hold' | 'guided';

export type BehavioralIntent =
  | 'idle'
  | 'approach'
  | 'orbit'
  | 'point'
  | 'follow'
  | 'retreat'
  | 'hold'
  | 'ping';

export interface IntentSignal {
  intent: BehavioralIntent;
  /** Target this intent refers to (if any) */
  targetId?: string;
  confidence: number; // 0–1
  /** Optional intensity / urgency from config or SKG */
  intensity?: number;
}

// ---------------------------------------------------------------------------
// Point / Ping events
// ---------------------------------------------------------------------------

export interface Ping {
  id: string;
  origin: Point;
  targetId?: string;
  /** Visual / haptic strength (config-driven) */
  strength: number;
  createdAt: number;
  ttl: number;
}

// ---------------------------------------------------------------------------
// MORB (Motion Orb) deployment — generic
// ---------------------------------------------------------------------------

export type MorbPhase = 'idle' | 'deploying' | 'active' | 'retracting' | 'dormant';

export interface MorbInstance {
  id: string;
  position: Point;
  velocity: Velocity;
  phase: MorbPhase;
  /** Linked target or anchor, if any */
  attachedTo?: string;
  /** Opaque visual config reference — runtime does not interpret */
  visualRef?: string;
}

// ---------------------------------------------------------------------------
// LiDAR confidence & sensing
// ---------------------------------------------------------------------------

export interface LidarReading {
  /** Confidence that the sensed geometry is valid (0–1) */
  confidence: number;
  obstacles: Obstacle[];
  freeSpaceRatio: number;
  timestamp: number;
}

// ---------------------------------------------------------------------------
// Route / viewport change events
// ---------------------------------------------------------------------------

export interface ViewportChange {
  previous: Viewport;
  current: Viewport;
  deltaScroll: Point;
  timestamp: number;
}

export interface RouteChange {
  /** Opaque path/token supplied by the host — runtime never parses site routes */
  pathToken: string;
  timestamp: number;
}

// ---------------------------------------------------------------------------
// Motion snapshot (the sole outward contract)
// ---------------------------------------------------------------------------

export interface MotionSnapshot {
  timestamp: number;
  viewport: Viewport;
  presence: PhysicalPresence;
  targets: Target[];
  anchors: Anchor[];
  obstacles: Obstacle[];
  morbs: MorbInstance[];
  activePings: Ping[];
  behavioralState: BehavioralState;
  intent: IntentSignal | null;
  lidar: LidarReading | null;
  /** Last known movement vector of primary MORB / pointer */
  primaryVector: MovementVector | null;
}

// ---------------------------------------------------------------------------
// Configuration injected by the host (site / deployment)
// ---------------------------------------------------------------------------

/**
 * Everything site-specific or product-specific arrives through this config.
 * The runtime treats all fields as opaque data + generic numbers.
 */
export interface MotionRuntimeConfig {
  /** Targets the runtime may attend to (IDs + initial geometry hints) */
  targets?: Array<{
    id: string;
    kind: TargetKind;
    label?: string;
    priority?: number;
    /** Selector or other locator is host responsibility; runtime receives geometry updates */
    meta?: Record<string, unknown>;
  }>;

  /** Behavior profile — pure numbers / enums, no product language */
  behavior?: {
    defaultState?: BehavioralState;
    ambientWanderRadius?: number;
    orbitRadius?: number;
    approachSpeed?: number;
    maxSpeed?: number;
    damping?: number;
    holdTimeoutMs?: number;
  };

  /** Permitted actions the runtime may emit */
  permittedActions?: BehavioralIntent[];

  /** Visual config references (opaque strings) */
  visual?: {
    defaultMorbVisualRef?: string;
    pingVisualRef?: string;
  };

  /** LiDAR / sensing tuning */
  lidar?: {
    enabled?: boolean;
    sampleIntervalMs?: number;
    confidenceThreshold?: number;
  };
}

// ---------------------------------------------------------------------------
// Events the runtime can emit (host listens)
// ---------------------------------------------------------------------------

export type MotionEventType =
  | 'snapshot'
  | 'intent'
  | 'ping'
  | 'morb-phase'
  | 'viewport-change'
  | 'route-change'
  | 'presence-change';

export interface MotionEvent {
  type: MotionEventType;
  payload: unknown;
  timestamp: number;
}

export type MotionEventHandler = (event: MotionEvent) => void;
