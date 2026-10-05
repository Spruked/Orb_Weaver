/**
 * Orbital Behavior SKG (Situation–Knowledge–Goal)
 *
 * Pure behavioral layer. Consumes generic geometry, presence, and intent
 * signals. Emits BehavioralIntent and state transitions.
 * No product names, selectors, or business rules.
 */

import type {
  Anchor,
  BehavioralIntent,
  BehavioralState,
  CursorState,
  IntentSignal,
  MotionRuntimeConfig,
  Point,
  Target,
  Velocity,
} from '../../shared/types/types';

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function distance(a: Point, b: Point): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  return Math.hypot(dx, dy);
}

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

function normalize(v: Velocity): Velocity {
  const len = Math.hypot(v.vx, v.vy);
  if (len < 1e-6) return { vx: 0, vy: 0 };
  return { vx: v.vx / len, vy: v.vy / len };
}

// ---------------------------------------------------------------------------
// SKG state
// ---------------------------------------------------------------------------

export interface OrbitalSKGState {
  behavioralState: BehavioralState;
  intent: IntentSignal | null;
  /** Primary focus target id */
  focusTargetId: string | null;
  /** Soft attraction point (orbit center or ambient wander) */
  attractionPoint: Point | null;
  lastStateChange: number;
}

export interface OrbitalSKGInput {
  now: number;
  cursor: CursorState;
  targets: Target[];
  anchors: Anchor[];
  /** Current primary MORB / pointer position */
  position: Point;
  velocity: Velocity;
  config: MotionRuntimeConfig;
}

export class OrbitalBehaviorSKG {
  private state: OrbitalSKGState = {
    behavioralState: 'ambient',
    intent: null,
    focusTargetId: null,
    attractionPoint: null,
    lastStateChange: 0,
  };

  private wanderAngle = 0;
  private holdUntil = 0;

  constructor(private config: MotionRuntimeConfig = {}) {
    if (config.behavior?.defaultState) {
      this.state.behavioralState = config.behavior.defaultState;
    }
  }

  updateConfig(config: MotionRuntimeConfig): void {
    this.config = config;
  }

  getState(): Readonly<OrbitalSKGState> {
    return this.state;
  }

  /**
   * Main tick. Returns the next IntentSignal (or null).
   */
  tick(input: OrbitalSKGInput): IntentSignal | null {
    const { now, cursor, targets, anchors, position, velocity, config } = input;
    const behavior = config.behavior ?? {};
    const maxSpeed = behavior.maxSpeed ?? 400;
    const orbitRadius = behavior.orbitRadius ?? 80;
    const ambientRadius = behavior.ambientWanderRadius ?? 120;
    const holdTimeout = behavior.holdTimeoutMs ?? 2500;
    const permitted = new Set(config.permittedActions ?? [
      'idle', 'approach', 'orbit', 'point', 'follow', 'retreat', 'hold', 'ping',
    ]);

    // 1. Presence-driven state
    const cursorActive = cursor.present && now - cursor.lastUpdated < 800;
    const cursorSpeed = Math.hypot(cursor.velocity.vx, cursor.velocity.vy);

    // 2. Choose focus target (highest priority that is visible)
    let best: Target | null = null;
    let bestScore = -Infinity;
    for (const t of targets) {
      if (!t.geometry.inViewport && t.geometry.visibility < 0.15) continue;
      const prio = t.priority ?? 1;
      const dist = distance(position, t.geometry.center);
      const score = prio * 1000 - dist + t.geometry.visibility * 200;
      if (score > bestScore) {
        bestScore = score;
        best = t;
      }
    }

    // 3. State machine
    let nextState = this.state.behavioralState;
    let nextIntent: BehavioralIntent = 'idle';
    let confidence = 0.5;
    let intensity = 0.5;
    let targetId: string | undefined;

    if (this.state.behavioralState === 'hold') {
      if (now < this.holdUntil) {
        nextIntent = 'hold';
        confidence = 0.9;
      } else {
        nextState = 'ambient';
        nextIntent = 'idle';
      }
    } else if (cursorActive && cursorSpeed > 80) {
      // Fast cursor → follow or retreat
      const distToCursor = distance(position, cursor.position);
      if (distToCursor < 40) {
        nextIntent = 'retreat';
        confidence = 0.75;
        intensity = clamp(cursorSpeed / 400, 0.3, 1);
      } else {
        nextIntent = 'follow';
        confidence = 0.7;
        intensity = clamp(cursorSpeed / 300, 0.2, 1);
      }
      nextState = 'guided';
    } else if (best) {
      targetId = best.id;
      const dist = distance(position, best.geometry.center);
      if (dist > orbitRadius * 1.8) {
        nextIntent = 'approach';
        nextState = 'guided';
        confidence = 0.85;
        intensity = clamp(1 - orbitRadius / Math.max(dist, 1), 0.3, 1);
      } else {
        nextIntent = 'orbit';
        nextState = 'guided';
        confidence = 0.9;
        intensity = 0.6;
      }
      this.state.focusTargetId = best.id;
      this.state.attractionPoint = best.geometry.center;
    } else if (anchors.length > 0) {
      // Fall back to strongest anchor
      const a = anchors.reduce((bestA, cur) =>
        cur.strength > bestA.strength ? cur : bestA,
      );
      const dist = distance(position, a.point);
      if (dist > a.radius * 1.5) {
        nextIntent = 'approach';
        confidence = 0.6;
      } else {
        nextIntent = 'orbit';
        confidence = 0.7;
      }
      nextState = 'ambient';
      this.state.attractionPoint = a.point;
    } else {
      // Ambient wander
      nextIntent = 'idle';
      nextState = 'ambient';
      this.wanderAngle += 0.02;
      const cx = position.x + Math.cos(this.wanderAngle) * ambientRadius * 0.3;
      const cy = position.y + Math.sin(this.wanderAngle * 0.7) * ambientRadius * 0.3;
      this.state.attractionPoint = { x: cx, y: cy };
      confidence = 0.4;
    }

    // Respect permitted actions
    if (!permitted.has(nextIntent)) {
      nextIntent = 'idle';
      confidence = 0.3;
    }

    // State transition bookkeeping
    if (nextState !== this.state.behavioralState) {
      this.state.lastStateChange = now;
      if (nextState === 'hold') {
        this.holdUntil = now + holdTimeout;
      }
    }
    this.state.behavioralState = nextState;

    const signal: IntentSignal = {
      intent: nextIntent,
      targetId,
      confidence,
      intensity,
    };
    this.state.intent = signal;
    return signal;
  }

  /** Force a hold state (e.g. after a ping or user pause) */
  requestHold(durationMs?: number): void {
    const timeout = durationMs ?? this.config.behavior?.holdTimeoutMs ?? 2500;
    this.state.behavioralState = 'hold';
    this.holdUntil = performance.now() + timeout;
    this.state.intent = {
      intent: 'hold',
      confidence: 1,
      intensity: 0.5,
    };
  }

  /** Emit a high-confidence ping intent */
  requestPing(targetId?: string): IntentSignal {
    const signal: IntentSignal = {
      intent: 'ping',
      targetId,
      confidence: 1,
      intensity: 1,
    };
    this.state.intent = signal;
    return signal;
  }
}
