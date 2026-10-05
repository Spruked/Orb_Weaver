import {
  createTargetVerifierAdapter,
  HAL_LIVE_CACHE_MAX_AGE_MS,
} from '../../backend/motion_runtime/client/adapters/targetVerifierAdapter';
import type { Target } from '../../backend/motion_runtime/shared/types/types';
import type { RobotCommand } from '../../backend/motion_runtime/client/pointer/robotMovement.types';

const target: Target = {
  id: 'target-a',
  kind: 'element',
  geometry: {
    rect: { x: 0, y: 0, width: 100, height: 40 },
    center: { x: 50, y: 20 },
    inViewport: true,
    visibility: 1,
  },
};

const makeCommand = (overrides: Partial<RobotCommand> = {}): RobotCommand => ({
  commandId: 'command-a', actionType: 'PRESENT_NEAR_TARGET', targetId: target.id,
  intent: 'Guide', urgency: 'normal', approachBehavior: 'decelerate_on_arrive',
  reason: 'test', worldStateSequence: 7, ...overrides,
});

const fixture = (overrides: Partial<Parameters<typeof createTargetVerifierAdapter>[0]> = {}) => {
  let now = 1000;
  let sequence = 7;
  let live: { ok: boolean; reason?: string } = { ok: true };
  const adapter = createTargetVerifierAdapter({
    now: () => now,
    getWorldStateSequence: () => sequence,
    getKnownTarget: (id) => id === target.id ? target : undefined,
    getCommand: () => makeCommand(),
    verifyLive: () => live,
    ...overrides,
  });
  return {
    adapter,
    setNow: (value: number) => { now = value; },
    setSequence: (value: number) => { sequence = value; },
    setLive: (value: { ok: boolean; reason?: string }) => { live = value; },
  };
};

const check = (adapter: ReturnType<typeof fixture>['adapter'], now = 1000) =>
  adapter.verifier(target, { now, geometryAgeMs: 0 });

test('target verifier fails closed for every authority gate', () => {
  expect(check(fixture({ getKnownTarget: () => undefined }).adapter)).toEqual({ ok: false, reason: 'target_unknown' });
  const stale = fixture();
  stale.setSequence(8);
  expect(check(stale.adapter)).toEqual({ ok: false, reason: 'world_state_stale' });
  expect(check(fixture({ getCommand: () => makeCommand({ intent: 'invalid' as RobotCommand['intent'] }) }).adapter))
    .toEqual({ ok: false, reason: 'policy_rejected:ontology_invalid_intent' });
  expect(check(fixture({ getBoundTargetId: () => 'wrong' }).adapter)).toEqual({ ok: false, reason: 'identity_mismatch' });
});

test('live verification is cached, bounded, and fail closed', () => {
  const missing = fixture();
  expect(check(missing.adapter)).toEqual({ ok: false, reason: 'live_dom_unverified' });

  const failed = fixture();
  failed.setLive({ ok: false, reason: 'hidden' });
  failed.adapter.refreshTarget(target);
  expect(check(failed.adapter)).toEqual({ ok: false, reason: 'live_dom_unverified' });

  const stale = fixture();
  stale.adapter.refreshTarget(target);
  stale.setNow(1000 + HAL_LIVE_CACHE_MAX_AGE_MS + 1);
  expect(check(stale.adapter, 1000 + HAL_LIVE_CACHE_MAX_AGE_MS + 1)).toEqual({ ok: false, reason: 'live_dom_unverified' });
});

test('HAL exceptions never escape the synchronous verifier', () => {
  const adapter = fixture({ verifyLive: () => { throw new Error('DOM failure'); } }).adapter;
  adapter.refreshTarget(target);
  expect(() => check(adapter)).not.toThrow();
  expect(check(adapter)).toEqual({ ok: false, reason: 'verifier_error' });
});

test('valid live verification succeeds and stage lifecycle unlocks only on bow out', () => {
  let unlocks = 0;
  const adapter = fixture({
    startTargetLock: () => () => { unlocks += 1; },
  }).adapter;
  adapter.refreshTarget(target);
  expect(check(adapter)).toEqual({ ok: true });
  adapter.onPointStage({ id: 1, targetId: target.id, stage: 'acquire', startedAt: 0, stageAt: 0 });
  adapter.onPointStage({ id: 1, targetId: target.id, stage: 'target_lost', startedAt: 0, stageAt: 1 });
  expect(unlocks).toBe(0);
  adapter.onPointStage({ id: 1, targetId: target.id, stage: 'bow_out', startedAt: 0, stageAt: 2 });
  expect(unlocks).toBe(1);
});
