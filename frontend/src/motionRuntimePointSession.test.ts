import { MotionRuntime } from '../../backend/motion_runtime/MotionRuntime';
import { createTargetVerifierAdapter } from '../../backend/motion_runtime/client/adapters/targetVerifierAdapter';
import type { Target } from '../../backend/motion_runtime/shared/types/types';
import type { RobotCommand } from '../../backend/motion_runtime/client/pointer/robotMovement.types';

const target: Target = {
  id: 'session-target', kind: 'element',
  geometry: {
    rect: { x: 150, y: 180, width: 100, height: 40 },
    center: { x: 200, y: 200 }, inViewport: true, visibility: 1,
  },
};

const command = (sequence: number): RobotCommand => ({
  commandId: 'session-command', actionType: 'PRESENT_NEAR_TARGET', targetId: target.id,
  intent: 'Guide', urgency: 'normal', approachBehavior: 'decelerate_on_arrive',
  reason: 'session-test', worldStateSequence: sequence,
});

const makeRuntime = (options: { withVerifier?: boolean; sequence?: number } = {}) => {
  let sequence = options.sequence ?? 1;
  let now = performance.now();
  let live = true;
  const runtime = new MotionRuntime({}, {
    settleMs: 0, pointDwellMs: 10, pingHoldMs: 1, reacquireWindowMs: 1500,
  });
  runtime.setTargets([target]);
  const adapter = createTargetVerifierAdapter({
    now: () => now,
    getWorldStateSequence: () => sequence,
    getKnownTarget: (id) => id === target.id ? target : undefined,
    getCommand: () => command(1),
    verifyLive: () => live ? { ok: true } : { ok: false, reason: 'revoked' },
  });
  adapter.refreshTarget(target);
  if (options.withVerifier !== false) {
    runtime.setTargetVerifier(adapter.verifier);
    runtime.onPointStage(adapter.onPointStage);
  }
  // Position the primary MORB at the normal upward stance so the fake clock
  // can exercise the complete stage sequence without a browser RAF loop.
  (runtime as any).pointer.setPosition({ x: 200, y: 105 });
  const tickAt = (delta: number) => {
    now = performance.now() + delta;
    (runtime as any).tick(now, 0.016);
  };
  return {
    runtime, adapter, tickAt,
    revoke: () => { live = false; adapter.refreshTarget(target); },
    restore: () => { live = true; adapter.refreshTarget(target); },
    setClock: (value: number) => { now = performance.now() + value; },
    bumpWorld: () => { sequence = 2; },
  };
};

test('no verifier and requestPing without an id refuse without pings', () => {
  const fixture = makeRuntime({ withVerifier: false });
  let pings = 0;
  fixture.runtime.on('ping', () => { pings += 1; });
  expect(fixture.runtime.requestPoint(target.id)).toBe(false);
  expect(fixture.runtime.requestPing()).toBe(false);
  expect(pings).toBe(0);
});

test('verified target runs the complete session and emits exactly one ping', () => {
  const fixture = makeRuntime();
  const stages: string[] = [];
  let pings = 0;
  fixture.runtime.onPointStage((session) => stages.push(session.stage));
  fixture.runtime.on('ping', () => { pings += 1; });
  expect(fixture.runtime.requestPoint(target.id)).toBe(true);
  fixture.tickAt(1);
  fixture.tickAt(2);
  fixture.tickAt(20);
  expect(stages.slice(0, 5)).toEqual(['acquire', 'approach', 'arrive', 'point', 'ping']);
  expect(pings).toBe(1);
});

test('HAL revocation stops the session before ping', () => {
  const fixture = makeRuntime();
  let pings = 0;
  const stages: string[] = [];
  fixture.runtime.on('ping', () => { pings += 1; });
  fixture.runtime.onPointStage((session) => stages.push(session.stage));
  expect(fixture.runtime.requestPoint(target.id)).toBe(true);
  fixture.revoke();
  fixture.tickAt(1);
  fixture.tickAt(1601);
  expect(stages).toContain('target_lost');
  expect(stages).toContain('bow_out');
  expect(pings).toBe(0);
});

test('HAL restoration inside the reacquire window resumes and emits one ping', () => {
  const fixture = makeRuntime();
  let pings = 0;
  const stages: string[] = [];
  fixture.runtime.on('ping', () => { pings += 1; });
  fixture.runtime.onPointStage((session) => stages.push(session.stage));
  expect(fixture.runtime.requestPoint(target.id)).toBe(true);
  fixture.revoke();
  fixture.tickAt(1);
  fixture.setClock(500);
  fixture.restore();
  fixture.tickAt(500);
  fixture.tickAt(520);
  fixture.tickAt(540);
  expect(stages).toContain('target_lost');
  expect(stages).toContain('approach');
  expect(pings).toBe(1);
});

test('scroll/resize staleness refuses until the host pushes targets again', () => {
  const fixture = makeRuntime();
  const originalScrollX = window.scrollX;
  Object.defineProperty(window, 'scrollX', { configurable: true, value: originalScrollX + 10 });
  (fixture.runtime as any).lastViewport = {
    width: window.innerWidth, height: window.innerHeight,
    scrollX: originalScrollX, scrollY: window.scrollY, dpr: window.devicePixelRatio || 1,
  };
  (fixture.runtime as any).refreshViewport();
  expect(fixture.runtime.requestPoint(target.id)).toBe(false);
  fixture.runtime.setTargets([target]);
  fixture.adapter.refreshTarget(target);
  expect(fixture.runtime.requestPoint(target.id)).toBe(true);
  Object.defineProperty(window, 'scrollX', { configurable: true, value: originalScrollX });
});

test('world-state bump fails closed before ping', () => {
  const fixture = makeRuntime();
  let pings = 0;
  fixture.runtime.on('ping', () => { pings += 1; });
  expect(fixture.runtime.requestPoint(target.id)).toBe(true);
  fixture.bumpWorld();
  fixture.tickAt(1);
  fixture.tickAt(20);
  expect(pings).toBe(0);
});
