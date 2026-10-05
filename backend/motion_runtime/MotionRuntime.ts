/**
 * MotionRuntime — top-level orchestrator
 *
 * Site / deployment configuration is injected; the runtime itself only
 * understands generic concepts listed in the boundary contract.
 *
 * Arbitration rule
 * ----------------
 * While a point session is active it outranks the behavioral SKG
 * (cursor-follow, ambient drift). A Ping is emitted ONLY from inside a
 * session, ONLY after arrival in stance, and ONLY if the target passes the
 * live check on that same tick. No verifier injected => no pointing.
 * Fail closed.
 *
 * Session choreography
 * --------------------
 * acquire -> approach -> arrive -> point -> ping -> release
 *   fault path: target_lost -> (re-acquire -> approach) | bow_out
 *   never:      target_lost -> ping
 *   refused:    request rejected before a session starts
 */

import type {
  Anchor,
  BehavioralIntent,
  CursorState,
  IntentSignal,
  MotionEvent,
  MotionEventHandler,
  MotionEventType,
  MotionRuntimeConfig,
  MotionSnapshot,
  Obstacle,
  PhysicalPresence,
  Point,
  Rect,
  Target,
  Viewport,
  ViewportChange,
  RouteChange,
} from './shared/types/types';
import { OrbitalBehaviorSKG } from './client/orbital_behavior_skg';
import { SpatialIntelligence } from './client/spatial_intelligence/SpatialIntelligence';
import { PointerController } from './client/pointer';

// ---------------------------------------------------------------------------
// Point session types
// ---------------------------------------------------------------------------

export type PointStage =
  | 'acquire'
  | 'approach'
  | 'arrive'
  | 'point'
  | 'ping'
  | 'release'
  | 'target_lost'
  | 'bow_out'
  | 'refused';

export interface PointOptions {
  /** GLIDE is the default. BRISK only on explicit visitor impatience. */
  speed?: 'glide' | 'brisk';
  /** Stance distance class: close=70 / normal=95 / wide=130 px */
  distance?: 'close' | 'normal' | 'wide';
}

export interface PointSession {
  id: number;
  targetId: string;
  stage: PointStage;
  startedAt: number;
  stageAt: number;
  reason?: string;
}

export type PointStageHandler = (session: Readonly<PointSession>) => void;

export interface TargetCheckContext {
  now: number;
  geometryAgeMs: number;
}

export interface TargetCheckResult {
  ok: boolean;
  reason?: string;
}

/**
 * Host-supplied authority check (Stage Governor / pointer authority).
 * The runtime never decides whether a target is legal — only the host can.
 */
export type TargetVerifier = (
  target: Target,
  ctx: TargetCheckContext,
) => TargetCheckResult;

export interface MotionRuntimeOptions {
  targetVerifier?: TargetVerifier;
  /** Min visibility (0..1) for a target to be pointable. Default 0.6 */
  minVisibility?: number;
  /** Reject geometry older than this. Default: off (staleness is event-based) */
  maxGeometryAgeMs?: number;
  arriveTolerancePx?: number;
  settleSpeedPx?: number;
  settleMs?: number;
  pointDwellMs?: number;
  pingHoldMs?: number;
  reacquireWindowMs?: number;
  viewportMargin?: number;
}

interface ResolvedOptions {
  minVisibility: number;
  maxGeometryAgeMs: number | null;
  arriveTolerancePx: number;
  settleSpeedPx: number;
  settleMs: number;
  pointDwellMs: number;
  pingHoldMs: number;
  reacquireWindowMs: number;
  viewportMargin: number;
}

// Stance distances come from the glide/stance doctrine. Everything else in
// DEFAULTS is a tunable placeholder, not a doctrine value.
const STANCE_DISTANCE = { close: 70, normal: 95, wide: 130 } as const;
const SPEED_INTENSITY = { glide: 0.5, brisk: 0.8 } as const;

const DEFAULTS: ResolvedOptions = {
  minVisibility: 0.6,
  maxGeometryAgeMs: null,
  arriveTolerancePx: 12,
  settleSpeedPx: 30,
  settleMs: 80,
  pointDwellMs: 350,
  pingHoldMs: 400,
  reacquireWindowMs: 1500,
  viewportMargin: 24,
};

// ---------------------------------------------------------------------------
// Default / empty helpers
// ---------------------------------------------------------------------------

function emptyViewport(): Viewport {
  if (typeof window !== 'undefined') {
    return {
      width: window.innerWidth,
      height: window.innerHeight,
      scrollX: window.scrollX,
      scrollY: window.scrollY,
      dpr: window.devicePixelRatio || 1,
    };
  }
  return { width: 1280, height: 720, scrollX: 0, scrollY: 0, dpr: 1 };
}

function emptyCursor(): CursorState {
  return {
    position: { x: 0, y: 0 },
    velocity: { vx: 0, vy: 0 },
    present: false,
    lastUpdated: 0,
  };
}

function distance(a: Point, b: Point): number {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

// ---------------------------------------------------------------------------
// MotionRuntime
// ---------------------------------------------------------------------------

export class MotionRuntime {
  private config: MotionRuntimeConfig;
  private opts: ResolvedOptions;
  private verifier: TargetVerifier | null;
  private skg: OrbitalBehaviorSKG;
  private spatial: SpatialIntelligence;
  private pointer: PointerController;

  private viewport: Viewport = emptyViewport();
  private cursor: CursorState = emptyCursor();
  private targets: Target[] = [];
  private anchors: Anchor[] = [];
  private extraObstacles: Obstacle[] = [];
  private candidateRects: Rect[] = [];

  // Geometry freshness (fail-closed pointing)
  private targetsUpdatedAt = 0;
  private geometryStale = false;

  // Point session state
  private session: PointSession | null = null;
  private sessionSeq = 0;
  private sessionDir: Point = { x: 0, y: -1 };
  private sessionSpeed: 'glide' | 'brisk' = 'glide';
  private sessionDistance: 'close' | 'normal' | 'wide' = 'normal';
  private lastStance: Point | null = null;
  private settledSince: number | null = null;
  private stageHandlers = new Set<PointStageHandler>();

  private listeners = new Map<MotionEventType | '*', Set<MotionEventHandler>>();
  private rafId: number | null = null;
  private lastFrameTime = 0;
  private running = false;
  private positioned = false;
  private lastViewport: Viewport | null = null;

  // Bound handlers so we can remove them
  private onMouseMove = (e: MouseEvent) => this.handlePointerMove(e.clientX, e.clientY);
  private onTouchMove = (e: TouchEvent) => {
    if (e.touches[0]) this.handlePointerMove(e.touches[0].clientX, e.touches[0].clientY);
  };
  private onResize = () => this.refreshViewport();
  private onScroll = () => this.refreshViewport();

  constructor(config: MotionRuntimeConfig = {}, options: MotionRuntimeOptions = {}) {
    this.config = config;
    this.opts = {
      minVisibility: options.minVisibility ?? DEFAULTS.minVisibility,
      maxGeometryAgeMs: options.maxGeometryAgeMs ?? DEFAULTS.maxGeometryAgeMs,
      arriveTolerancePx: options.arriveTolerancePx ?? DEFAULTS.arriveTolerancePx,
      settleSpeedPx: options.settleSpeedPx ?? DEFAULTS.settleSpeedPx,
      settleMs: options.settleMs ?? DEFAULTS.settleMs,
      pointDwellMs: options.pointDwellMs ?? DEFAULTS.pointDwellMs,
      pingHoldMs: options.pingHoldMs ?? DEFAULTS.pingHoldMs,
      reacquireWindowMs: options.reacquireWindowMs ?? DEFAULTS.reacquireWindowMs,
      viewportMargin: options.viewportMargin ?? DEFAULTS.viewportMargin,
    };
    this.verifier = options.targetVerifier ?? null;

    this.skg = new OrbitalBehaviorSKG(config);
    // SI-RENAME: `config.lidar` is a public contract field defined in
    // shared/types/types.ts. Rename it there and here in the same commit.
    this.spatial = new SpatialIntelligence(config.lidar);
    this.pointer = new PointerController({
      visualRef: config.visual?.defaultMorbVisualRef,
    });

    // Seed targets from config (geometry will be updated by host)
    if (config.targets) {
      this.targets = config.targets.map((t) => ({
        id: t.id,
        kind: t.kind,
        label: t.label,
        priority: t.priority,
        meta: t.meta,
        geometry: {
          rect: { x: 0, y: 0, width: 0, height: 0 },
          center: { x: 0, y: 0 },
          inViewport: false,
          visibility: 0,
        },
      }));
    }
  }

  // -----------------------------------------------------------------------
  // Lifecycle
  // -----------------------------------------------------------------------

  start(): void {
    if (this.running) return;
    this.running = true;
    this.refreshViewport();

    // Center only on the very first start; a restart keeps her where she is.
    if (!this.positioned) {
      this.pointer.setPosition({
        x: this.viewport.width * 0.5,
        y: this.viewport.height * 0.5,
      });
      this.positioned = true;
    }

    if (typeof window !== 'undefined') {
      window.addEventListener('mousemove', this.onMouseMove, { passive: true });
      window.addEventListener('touchmove', this.onTouchMove, { passive: true });
      window.addEventListener('resize', this.onResize, { passive: true });
      window.addEventListener('scroll', this.onScroll, { passive: true });
    }

    this.lastFrameTime = performance.now();
    const loop = (now: number) => {
      if (!this.running) return;
      const dt = Math.min(0.05, (now - this.lastFrameTime) / 1000);
      this.lastFrameTime = now;
      this.tick(now, dt);
      this.rafId = requestAnimationFrame(loop);
    };
    this.rafId = requestAnimationFrame(loop);
  }

  stop(): void {
    this.running = false;
    if (this.session) {
      this.setStage('bow_out', performance.now(), 'runtime_stopped');
      this.session = null;
    }
    if (this.rafId != null && typeof cancelAnimationFrame !== 'undefined') {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    if (typeof window !== 'undefined') {
      window.removeEventListener('mousemove', this.onMouseMove);
      window.removeEventListener('touchmove', this.onTouchMove);
      window.removeEventListener('resize', this.onResize);
      window.removeEventListener('scroll', this.onScroll);
    }
  }

  /** Replace or merge configuration at runtime */
  updateConfig(config: MotionRuntimeConfig): void {
    this.config = { ...this.config, ...config };
    this.skg.updateConfig(this.config);
    // SI-RENAME: see constructor note.
    this.spatial.updateConfig(this.config.lidar);
  }

  // -----------------------------------------------------------------------
  // Host-driven inputs (the only way site knowledge enters)
  // -----------------------------------------------------------------------

  /**
   * Host supplies up-to-date target geometries.
   * Runtime never queries the DOM itself for site-specific selectors.
   * Calling this clears the stale-geometry flag set by scroll/resize.
   */
  setTargets(targets: Target[]): void {
    this.targets = targets;
    this.targetsUpdatedAt = performance.now();
    this.geometryStale = false;
  }

  setAnchors(anchors: Anchor[]): void {
    this.anchors = anchors;
  }

  setExtraObstacles(obstacles: Obstacle[]): void {
    this.extraObstacles = obstacles;
  }

  /** Optional: host can push candidate obstacle rects (e.g. fixed chrome) */
  setCandidateRects(rects: Rect[]): void {
    this.candidateRects = rects;
  }

  /**
   * Host-supplied authority check. Without one, every point request is
   * refused (fail closed).
   */
  setTargetVerifier(verifier: TargetVerifier | null): void {
    this.verifier = verifier;
  }

  /** Notify runtime of a route / view change (opaque token) */
  notifyRouteChange(pathToken: string): void {
    const event: RouteChange = { pathToken, timestamp: performance.now() };
    this.emit('route-change', event);
  }

  // -----------------------------------------------------------------------
  // Public actions
  // -----------------------------------------------------------------------

  requestHold(durationMs?: number): void {
    this.skg.requestHold(durationMs);
  }

  /**
   * Start a point session toward a target. Returns false if refused.
   * Subscribe with onPointStage() to sync voice and audio to the gesture.
   * A new request supersedes any session in progress.
   */
  requestPoint(targetId: string, options: PointOptions = {}): boolean {
    const now = performance.now();

    if (this.session) {
      this.setStage('bow_out', now, 'superseded');
      this.session = null;
    }

    const target = this.targets.find((t) => t.id === targetId);
    const check = this.checkTarget(target, now);
    if (!check.ok || !target) {
      this.notifyRefused(targetId, now, check.reason ?? 'target_unverified');
      return false;
    }

    this.sessionSpeed = options.speed ?? 'glide';
    this.sessionDistance = options.distance ?? 'normal';

    // Lock the approach direction once so the stance does not drift while
    // she travels along it.
    const pos = this.pointer.getPrimary().position;
    const c = target.geometry.center;
    const dx = pos.x - c.x;
    const dy = pos.y - c.y;
    const len = Math.hypot(dx, dy);
    this.sessionDir = len < 1e-3 ? { x: 0, y: -1 } : { x: dx / len, y: dy / len };

    this.settledSince = null;
    this.lastStance = null;
    this.session = {
      id: ++this.sessionSeq,
      targetId,
      stage: 'acquire',
      startedAt: now,
      stageAt: now,
    };
    this.notifyStage();
    this.setStage('approach', now);
    return true;
  }

  /**
   * Legacy entry point. Ping is no longer immediate: this starts a gated
   * point session, and the Ping fires only on arrival. Requires a target id.
   */
  requestPing(targetId?: string): boolean {
    if (!targetId) {
      this.notifyRefused('', performance.now(), 'no_target_id');
      return false;
    }
    return this.requestPoint(targetId);
  }

  getPointSession(): Readonly<PointSession> | null {
    return this.session ? { ...this.session } : null;
  }

  onPointStage(handler: PointStageHandler): () => void {
    this.stageHandlers.add(handler);
    return () => this.stageHandlers.delete(handler);
  }

  // -----------------------------------------------------------------------
  // Snapshot & events
  // -----------------------------------------------------------------------

  getSnapshot(): MotionSnapshot {
    const now = performance.now();
    const skgState = this.skg.getState();
    return {
      timestamp: now,
      viewport: { ...this.viewport },
      presence: this.buildPresence(),
      targets: this.targets.map((t) => ({ ...t, geometry: { ...t.geometry } })),
      anchors: [...this.anchors],
      obstacles: this.spatial.getLastReading()?.obstacles ?? [],
      morbs: this.pointer.getMorbs().map((m) => ({ ...m, position: { ...m.position } })),
      activePings: this.pointer.getActivePings(now),
      behavioralState: skgState.behavioralState,
      intent: skgState.intent,
      // SI-RENAME: snapshot field name is a public contract (types.ts).
      lidar: this.spatial.getLastReading(),
      primaryVector: this.pointer.getPrimaryVector(),
    };
  }

  on(type: MotionEventType | '*', handler: MotionEventHandler): () => void {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(handler);
    return () => this.listeners.get(type)?.delete(handler);
  }

  // -----------------------------------------------------------------------
  // Internal: frame tick
  // -----------------------------------------------------------------------

  private tick(now: number, dt: number): void {
    const reading = this.spatial.sample({
      now,
      viewport: this.viewport,
      candidateRects: this.candidateRects,
      targets: this.targets,
      extraObstacles: this.extraObstacles,
    });

    // The SKG always runs so its state stays current, but while a point
    // session is active its output is overridden below.
    const skgIntent = this.skg.tick({
      now,
      cursor: this.cursor,
      targets: this.targets,
      anchors: this.anchors,
      position: this.pointer.getPrimary().position,
      velocity: this.pointer.getPrimary().velocity,
      config: this.config,
    });

    let intent: IntentSignal | null = skgIntent;
    let attraction: Point | null = this.skg.getState().attractionPoint;

    if (this.session) {
      const driven = this.advanceSession(now);
      intent = driven.intent;
      attraction = driven.attraction;
    }

    this.pointer.tick({
      now,
      dt,
      intent,
      attractionPoint: attraction,
      // SI-RENAME: this key is the pointer module's input contract.
      lidar: reading,
      viewportWidth: this.viewport.width,
      viewportHeight: this.viewport.height,
      config: this.config,
    });

    this.emit('snapshot', this.getSnapshot());
    if (intent) this.emit('intent', intent);
  }

  // -----------------------------------------------------------------------
  // Internal: point session
  // -----------------------------------------------------------------------

  private advanceSession(now: number): { intent: IntentSignal; attraction: Point | null } {
    const s = this.session as PointSession;

    // After the Ping has fired the target no longer matters; just hold the
    // gesture, then release.
    if (s.stage === 'ping') {
      if (now - s.stageAt >= this.opts.pingHoldMs) {
        this.setStage('release', now);
        this.session = null;
        this.skg.requestHold();
        return { intent: this.makeIntent('hold', s.targetId, 0.9, 0.3), attraction: this.lastStance };
      }
      return { intent: this.makeIntent('ping', s.targetId, 1, 1), attraction: this.lastStance };
    }

    // Live check every tick: includes the tick that would emit the Ping.
    const target = this.targets.find((t) => t.id === s.targetId);
    const check = this.checkTarget(target, now);
    if (!check.ok || !target) {
      return this.advanceLost(now, s, check.reason ?? 'target_unverified');
    }

    if (s.stage === 'target_lost') {
      this.settledSince = null;
      this.setStage('approach', now, 'reacquired');
    }

    const stance = this.resolveStance(target);
    this.lastStance = stance;

    if (this.session && this.session.stage === 'point') {
      return this.advancePoint(now, s, target, stance);
    }
    return this.advanceApproach(now, s, stance);
  }

  private advanceApproach(
    now: number,
    s: PointSession,
    stance: Point,
  ): { intent: IntentSignal; attraction: Point | null } {
    if (this.updateSettled(stance, now)) {
      this.setStage('arrive', now);
      this.setStage('point', now);
      return {
        intent: this.makeIntent('point', s.targetId, 1, 0.5),
        attraction: stance,
      };
    }
    return {
      intent: this.makeIntent('approach', s.targetId, 0.9, SPEED_INTENSITY[this.sessionSpeed]),
      attraction: stance,
    };
  }

  private advancePoint(
    now: number,
    s: PointSession,
    target: Target,
    stance: Point,
  ): { intent: IntentSignal; attraction: Point | null } {
    // Drifted out of stance: go back to approach rather than pinging early.
    if (!this.isSettled(stance)) {
      this.settledSince = null;
      this.setStage('approach', now, 'drifted');
      return {
        intent: this.makeIntent('approach', s.targetId, 0.9, SPEED_INTENSITY[this.sessionSpeed]),
        attraction: stance,
      };
    }

    if (now - s.stageAt >= this.opts.pointDwellMs) {
      // The one and only place a Ping is emitted.
      const signal = this.skg.requestPing(target.id);
      const origin = this.pointer.getPrimary().position;
      const ping = this.pointer.emitPing(origin, target.id, signal.intensity ?? 1);
      this.emit('ping', ping);
      this.emit('intent', signal);
      this.setStage('ping', now);
      return { intent: signal, attraction: stance };
    }

    return { intent: this.makeIntent('point', s.targetId, 1, 0.5), attraction: stance };
  }

  private advanceLost(
    now: number,
    s: PointSession,
    reason: string,
  ): { intent: IntentSignal; attraction: Point | null } {
    if (s.stage !== 'target_lost') {
      this.settledSince = null;
      this.setStage('target_lost', now, reason);
    }
    if (now - s.stageAt > this.opts.reacquireWindowMs) {
      this.setStage('bow_out', now, reason);
      this.session = null;
    }
    // Hold last confirmed position; never gesture at a lost target.
    return { intent: this.makeIntent('hold', s.targetId, 0.9, 0.3), attraction: null };
  }

  /** Geometry + authority gate. Fail closed on any doubt. */
  private checkTarget(target: Target | undefined, now: number): TargetCheckResult {
    if (!target) return { ok: false, reason: 'target_unknown' };
    if (this.geometryStale) return { ok: false, reason: 'geometry_stale' };

    const ageMs = now - this.targetsUpdatedAt;
    if (this.opts.maxGeometryAgeMs != null && ageMs > this.opts.maxGeometryAgeMs) {
      return { ok: false, reason: 'geometry_aged' };
    }
    if (!target.geometry.inViewport) return { ok: false, reason: 'out_of_viewport' };
    if (target.geometry.visibility < this.opts.minVisibility) {
      return { ok: false, reason: 'occluded' };
    }
    if (!this.verifier) return { ok: false, reason: 'no_verifier' };
    try {
      return this.verifier(target, { now, geometryAgeMs: ageMs });
    } catch {
      return { ok: false, reason: 'verifier_error' };
    }
  }

  private resolveStance(target: Target): Point {
    const c = target.geometry.center;
    const n = STANCE_DISTANCE[this.sessionDistance];
    const m = this.opts.viewportMargin;
    return {
      x: clamp(c.x + this.sessionDir.x * n, m, Math.max(m, this.viewport.width - m)),
      y: clamp(c.y + this.sessionDir.y * n, m, Math.max(m, this.viewport.height - m)),
    };
  }

  private isSettled(stance: Point): boolean {
    const p = this.pointer.getPrimary();
    const speed = Math.hypot(p.velocity.vx, p.velocity.vy);
    return (
      distance(p.position, stance) <= this.opts.arriveTolerancePx &&
      speed <= this.opts.settleSpeedPx
    );
  }

  private updateSettled(stance: Point, now: number): boolean {
    if (!this.isSettled(stance)) {
      this.settledSince = null;
      return false;
    }
    if (this.settledSince == null) this.settledSince = now;
    return now - this.settledSince >= this.opts.settleMs;
  }

  private makeIntent(
    intent: BehavioralIntent,
    targetId: string | undefined,
    confidence: number,
    intensity: number,
  ): IntentSignal {
    return { intent, targetId, confidence, intensity };
  }

  private setStage(stage: PointStage, now: number, reason?: string): void {
    if (!this.session) return;
    this.session.stage = stage;
    this.session.stageAt = now;
    this.session.reason = reason;
    this.notifyStage();
  }

  private notifyStage(): void {
    if (!this.session) return;
    const snapshot: PointSession = { ...this.session };
    this.stageHandlers.forEach((h) => h(snapshot));
  }

  private notifyRefused(targetId: string, now: number, reason: string): void {
    const refused: PointSession = {
      id: ++this.sessionSeq,
      targetId,
      stage: 'refused',
      startedAt: now,
      stageAt: now,
      reason,
    };
    this.stageHandlers.forEach((h) => h({ ...refused }));
  }

  // -----------------------------------------------------------------------
  // Internal: input + viewport
  // -----------------------------------------------------------------------

  private handlePointerMove(x: number, y: number): void {
    const now = performance.now();
    let velocity = { vx: 0, vy: 0 };

    // First sample has no valid previous position; do not invent a velocity.
    if (this.cursor.present) {
      const prev = this.cursor.position;
      const dt = Math.max(0.001, (now - this.cursor.lastUpdated) / 1000);
      velocity = { vx: (x - prev.x) / dt, vy: (y - prev.y) / dt };
    }

    this.cursor = {
      position: { x, y },
      velocity,
      present: true,
      lastUpdated: now,
    };
    this.emit('presence-change', this.buildPresence());
  }

  private refreshViewport(): void {
    const prev = this.lastViewport;
    this.viewport = emptyViewport();
    if (prev) {
      const moved =
        prev.scrollX !== this.viewport.scrollX ||
        prev.scrollY !== this.viewport.scrollY ||
        prev.width !== this.viewport.width ||
        prev.height !== this.viewport.height;
      // Geometry the host measured before this change can no longer be
      // trusted until the host pushes fresh targets.
      if (moved) this.geometryStale = true;

      const change: ViewportChange = {
        previous: prev,
        current: { ...this.viewport },
        deltaScroll: {
          x: this.viewport.scrollX - prev.scrollX,
          y: this.viewport.scrollY - prev.scrollY,
        },
        timestamp: performance.now(),
      };
      this.emit('viewport-change', change);
    }
    this.lastViewport = { ...this.viewport };
  }

  private buildPresence(): PhysicalPresence {
    return {
      cursor: { ...this.cursor },
      focusPoint: this.cursor.present ? { ...this.cursor.position } : null,
    };
  }

  private emit(type: MotionEventType, payload: unknown): void {
    const event: MotionEvent = {
      type,
      payload,
      timestamp: performance.now(),
    };
    this.listeners.get(type)?.forEach((h) => h(event));
    this.listeners.get('*')?.forEach((h) => h(event));
  }
}

// Re-export commonly used types for consumers
export type {
  MotionRuntimeConfig,
  MotionSnapshot,
  MotionEvent,
  Target,
  Anchor,
  Obstacle,
  Point,
  Viewport,
  BehavioralState,
  BehavioralIntent,
  MorbInstance,
  Ping,
} from './shared/types/types';
