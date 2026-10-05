/**
 * Pointer / MORB layer
 *
 * Owns position, velocity, phase of motion orbs (MORBs) and the primary
 * pointer. Integrates intent + LiDAR repulsion into movement.
 * Fully generic — no product or site knowledge.
 */

import type {
  BehavioralIntent,
  IntentSignal,
  LidarReading,
  MorbInstance,
  MorbPhase,
  MotionRuntimeConfig,
  MovementVector,
  Ping,
  Point,
  Velocity,
} from '../../shared/types/types';
import { computeRepulsion } from '../spatial_intelligence/SpatialIntelligence';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function length(v: Velocity | Point): number {
  if ('vx' in v) return Math.hypot(v.vx, v.vy);
  return Math.hypot(v.x, v.y);
}

function normalizeVec(v: Velocity): Velocity {
  const len = length(v);
  if (len < 1e-6) return { vx: 0, vy: 0 };
  return { vx: v.vx / len, vy: v.vy / len };
}

function clampMag(v: Velocity, max: number): Velocity {
  const len = length(v);
  if (len <= max) return v;
  const s = max / len;
  return { vx: v.vx * s, vy: v.vy * s };
}

// ---------------------------------------------------------------------------
// PointerController
// ---------------------------------------------------------------------------

export interface PointerTickInput {
  now: number;
  dt: number; // seconds
  intent: IntentSignal | null;
  attractionPoint: Point | null;
  lidar: LidarReading | null;
  viewportWidth: number;
  viewportHeight: number;
  config: MotionRuntimeConfig;
}

export class PointerController {
  private primary: MorbInstance;
  private morbs: Map<string, MorbInstance> = new Map();
  private pings: Ping[] = [];
  private lastVector: MovementVector | null = null;
  private orbitAngle = 0;

  constructor(initial?: Partial<MorbInstance>) {
    this.primary = {
      id: 'primary',
      position: { x: 0, y: 0 },
      velocity: { vx: 0, vy: 0 },
      phase: 'idle',
      ...initial,
    };
    this.morbs.set(this.primary.id, this.primary);
  }

  getPrimary(): Readonly<MorbInstance> {
    return this.primary;
  }

  getMorbs(): MorbInstance[] {
    return Array.from(this.morbs.values());
  }

  getActivePings(now: number): Ping[] {
    this.pings = this.pings.filter((p) => now - p.createdAt < p.ttl);
    return this.pings;
  }

  getPrimaryVector(): MovementVector | null {
    return this.lastVector;
  }

  /** Place the primary MORB at a point (e.g. on first mount) */
  setPosition(p: Point): void {
    this.primary.position = { ...p };
    this.primary.velocity = { vx: 0, vy: 0 };
  }

  /** Spawn an additional MORB */
  spawnMorb(id: string, position: Point, visualRef?: string): MorbInstance {
    const m: MorbInstance = {
      id,
      position: { ...position },
      velocity: { vx: 0, vy: 0 },
      phase: 'deploying',
      visualRef,
    };
    this.morbs.set(id, m);
    return m;
  }

  setPhase(id: string, phase: MorbPhase): void {
    const m = this.morbs.get(id);
    if (m) m.phase = phase;
  }

  /** Create a ping at origin (optionally linked to a target) */
  emitPing(origin: Point, targetId?: string, strength = 1, ttl = 1200): Ping {
    const ping: Ping = {
      id: `ping-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      origin: { ...origin },
      targetId,
      strength,
      createdAt: performance.now(),
      ttl,
    };
    this.pings.push(ping);
    return ping;
  }

  /**
   * Integrate one frame of motion for the primary MORB.
   */
  tick(input: PointerTickInput): void {
    const { now, dt, intent, attractionPoint, lidar, viewportWidth, viewportHeight, config } =
      input;
    const behavior = config.behavior ?? {};
    const maxSpeed = behavior.maxSpeed ?? 420;
    const damping = behavior.damping ?? 0.86;
    const approachSpeed = behavior.approachSpeed ?? 280;
    const orbitRadius = behavior.orbitRadius ?? 72;

    const prev = { ...this.primary.position };
    let desired: Velocity = { vx: 0, vy: 0 };
    const intentName: BehavioralIntent = intent?.intent ?? 'idle';
    const intensity = intent?.intensity ?? 0.5;

    switch (intentName) {
      case 'approach':
      case 'follow': {
        if (attractionPoint) {
          const dx = attractionPoint.x - this.primary.position.x;
          const dy = attractionPoint.y - this.primary.position.y;
          const dist = Math.hypot(dx, dy) || 1;
          const speed = approachSpeed * intensity;
          desired = { vx: (dx / dist) * speed, vy: (dy / dist) * speed };
        }
        break;
      }
      case 'orbit': {
        if (attractionPoint) {
          this.orbitAngle += dt * 1.4 * intensity;
          const tx = attractionPoint.x + Math.cos(this.orbitAngle) * orbitRadius;
          const ty = attractionPoint.y + Math.sin(this.orbitAngle) * orbitRadius;
          const dx = tx - this.primary.position.x;
          const dy = ty - this.primary.position.y;
          desired = { vx: dx * 3.2, vy: dy * 3.2 };
        }
        break;
      }
      case 'retreat': {
        if (attractionPoint) {
          // Push away from attraction (cursor)
          const dx = this.primary.position.x - attractionPoint.x;
          const dy = this.primary.position.y - attractionPoint.y;
          const dist = Math.hypot(dx, dy) || 1;
          desired = {
            vx: (dx / dist) * approachSpeed * 0.9,
            vy: (dy / dist) * approachSpeed * 0.9,
          };
        }
        break;
      }
      case 'point':
      case 'ping': {
        // Snap attention; small hold
        desired = { vx: 0, vy: 0 };
        break;
      }
      case 'hold':
      case 'idle':
      default: {
        // Gentle damping toward attraction or stay
        if (attractionPoint) {
          const dx = attractionPoint.x - this.primary.position.x;
          const dy = attractionPoint.y - this.primary.position.y;
          desired = { vx: dx * 0.8, vy: dy * 0.8 };
        }
        break;
      }
    }

    // LiDAR repulsion
    if (lidar && lidar.obstacles.length > 0) {
      const rep = computeRepulsion(this.primary.position, lidar.obstacles);
      desired.vx += rep.vx;
      desired.vy += rep.vy;
    }

    // Integrate with damping
    let vel: Velocity = {
      vx: this.primary.velocity.vx * damping + desired.vx * (1 - damping),
      vy: this.primary.velocity.vy * damping + desired.vy * (1 - damping),
    };
    vel = clampMag(vel, maxSpeed);

    this.primary.velocity = vel;
    this.primary.position = {
      x: this.primary.position.x + vel.vx * dt,
      y: this.primary.position.y + vel.vy * dt,
    };

    // Soft clamp inside viewport with margin
    const margin = 24;
    this.primary.position.x = Math.max(
      margin,
      Math.min(viewportWidth - margin, this.primary.position.x),
    );
    this.primary.position.y = Math.max(
      margin,
      Math.min(viewportHeight - margin, this.primary.position.y),
    );

    // Phase
    const speed = length(vel);
    if (intentName === 'ping' || intentName === 'point') {
      this.primary.phase = 'active';
    } else if (speed > 30) {
      this.primary.phase = 'active';
    } else if (speed < 5) {
      this.primary.phase = this.primary.phase === 'deploying' ? 'active' : 'idle';
    }

    // Movement vector
    const dx = this.primary.position.x - prev.x;
    const dy = this.primary.position.y - prev.y;
    const len = Math.hypot(dx, dy);
    this.lastVector = {
      from: prev,
      to: { ...this.primary.position },
      velocity: { ...vel },
      direction: len > 1e-6 ? { x: dx / len, y: dy / len } : { x: 0, y: 0 },
      length: len,
    };

    // Keep map in sync
    this.morbs.set(this.primary.id, this.primary);
  }
}
