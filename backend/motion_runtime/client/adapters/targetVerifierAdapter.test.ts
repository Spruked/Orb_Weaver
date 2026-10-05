import {
  createTargetVerifierAdapter,
  HAL_LIVE_CACHE_MAX_AGE_MS,
} from './targetVerifierAdapter';
import type { Target } from '../../shared/types/types';
import type { RobotCommand } from '../pointer/robotMovement.types';

const target: Target = {
  id: 'target-a',
  kind: 'element',
  geometry: {
    rect: { x: 10, y: 10, width: 100, height: 40 },
    center: { x: 60, y: 30 },
    inViewport: true,
    visibility: 1,
  },
};

const command = (overrides: Partial<RobotCommand> = {}): RobotCommand => ({
  commandId: 'command-a',
  actionType: 'PRESENT_NEAR_TARGET',
  targetId: 'target-a',
  intent: 'Guide',
  urgency: 'normal',
  approachBehavior: 'decelerate_on_arrive',
  reason: 'test',
  worldStateSequence: 7,
  ...overrides,
});

const build = (overrides: Partial<Parameters<typeof createTargetVerifierAdapter>[0]> = {}) => {
  let now = 1000;
  let worldState = 7;
  let live: { ok: boolean; reason?: string } = { ok: true };
  const adapter = createTargetVerifierAdapter({
    now: () => now,
    getWorldStateSequence: () => worldState,
    getKnownTarget: (id) => id === target.id ? target : undefined,
    getCommand: () => command(),
    verifyLive: () => live,
    ...overrides,
  });
  return {
    adapter,
    setNow: (value: number) => { now = value; },
    setWorldState: (value: number) => { worldState = value; },
    setLive: (value: { ok: boolean; reason?: string }) => { live = value; },
  };
};

const verify = (adapter: ReturnType<typeof build>['adapter']) =>
  adapter.verifier(target, { now: 1000, geometryAgeMs: 0 });

test('unknown target id fails closed', () => {
  const { adapter } = build({ getKnownTarget: () => undefined });
  expect(verify(adapter)).toEqual({ ok: false, reason: 'target_unknown' });
});

test('world state mismatch fails before policy and live checks', () => {
  const fixture = build();
  fixture.setWorldState(8);
  expect(verify(fixture.adapter)).toEqual({ ok: false, reason: 'world_state_stale' });
});

test('ontology violation is policy rejected', () => {
  const fixture = build({ getCommand: () => command({ intent: 'BadIntent' as RobotCommand['intent'] }) });
  expect(verify(fixture.adapter)).toEqual({ ok: false, reason: 'policy_rejected:ontology_invalid_intent' });
});

test('identity mismatch fails before live verification', () => {
  const fixture = build({ getBoundTargetId: () => 'different-target' });
  expect(verify(fixture.adapter)).toEqual({ ok: false, reason: 'identity_mismatch' });
});

test('missing or failed live cache is unverified', () => {
  const fixture = build();
  expect(verify(fixture.adapter)).toEqual({ ok: false, reason: 'live_dom_unverified' });
  fixture.adapter.refreshTarget(target);
  fixture.setLive({ ok: false, reason: 'hidden' });
  fixture.adapter.refreshTarget(target);
  expect(verify(fixture.adapter)).toEqual({ ok: false, reason: 'live_dom_unverified' });
});

test('stale live cache fails closed at the named age boundary', () => {
  const fixture = build();
  fixture.adapter.refreshTarget(target);
  fixture.setNow(1000 + HAL_LIVE_CACHE_MAX_AGE_MS + 1);
  expect(fixture.adapter.verifier(target, { now: 1000 + HAL_LIVE_CACHE_MAX_AGE_MS + 1, geometryAgeMs: 0 }))
    .toEqual({ ok: false, reason: 'live_dom_unverified' });
});

test('HAL exceptions become verifier_error and never escape', () => {
  const fixture = build({ verifyLive: () => { throw new Error('DOM failure'); } });
  fixture.adapter.refreshTarget(target);
  expect(() => verify(fixture.adapter)).not.toThrow();
  expect(verify(fixture.adapter)).toEqual({ ok: false, reason: 'verifier_error' });
});

test('valid cached live result succeeds', () => {
  const fixture = build();
  fixture.adapter.refreshTarget(target);
  expect(verify(fixture.adapter)).toEqual({ ok: true });
});

test('stage lifecycle locks on acquire and unlocks on bow out', () => {
  const fixture = build();
  let locks = 0;
  let unlocks = 0;
  const adapter = createTargetVerifierAdapter({
    getWorldStateSequence: () => 7,
    getKnownTarget: () => target,
    getCommand: () => command(),
    verifyLive: () => ({ ok: true }),
    startTargetLock: () => { locks += 1; return () => { unlocks += 1; }; },
  });
  adapter.onPointStage({ id: 1, targetId: target.id, stage: 'acquire', startedAt: 0, stageAt: 0 });
  adapter.onPointStage({ id: 1, targetId: target.id, stage: 'target_lost', startedAt: 0, stageAt: 1 });
  expect(locks).toBe(1);
  expect(unlocks).toBe(0);
  adapter.onPointStage({ id: 1, targetId: target.id, stage: 'bow_out', startedAt: 0, stageAt: 2 });
  expect(unlocks).toBe(1);
  fixture.adapter.dispose();
});
