import type { PointSession, TargetVerifier } from '../../MotionRuntime';
import type { Target } from '../../shared/types/types';
import {
  validateMovementOntologyCommand,
} from '../pointer/movementOntology';
import type { RobotCommand } from '../pointer/robotMovement.types';

/** HAL verification results must use the same performance.now() time base. */
export const HAL_LIVE_CACHE_MAX_AGE_MS = 250;

export type HalLiveCheck =
  | { ok: true }
  | { ok: false; reason?: string };

export type TargetLockStopper = () => void;

export interface TargetVerifierAdapterOptions {
  /** Current authoritative world-state sequence from the host. */
  getWorldStateSequence: () => number;
  /** Build the closed-vocabulary command associated with this target. */
  getCommand: (target: Target) => RobotCommand | null;
  /** Optional authoritative target registry; absent means the runtime list is authoritative. */
  getKnownTarget?: (targetId: string) => Target | undefined;
  /** The synchronous HAL check. It may query the DOM, but is never called by the frame verifier. */
  verifyLive: (target: Target) => HalLiveCheck;
  /** Begin continuous HAL tracking for the active target. */
  startTargetLock?: (
    target: Target,
    onRefresh: () => void,
    onLost: () => void,
  ) => TargetLockStopper;
  /** Optional identity witness from the host/HAL. */
  getBoundTargetId?: (target: Target) => string | undefined;
  now?: () => number;
}

type CacheEntry = {
  checkedAt: number;
  result: HalLiveCheck;
  threw: boolean;
};

export interface TargetVerifierAdapter {
  verifier: TargetVerifier;
  refreshTarget: (target: Target) => HalLiveCheck;
  onPointStage: (session: Readonly<PointSession>) => void;
  dispose: () => void;
}

const defaultNow = (): number =>
  typeof performance !== 'undefined' ? performance.now() : Date.now();

/**
 * Composes host authority in the required fail-closed order. The returned
 * verifier is synchronous and reads only the short-lived HAL cache.
 */
export function createTargetVerifierAdapter(
  options: TargetVerifierAdapterOptions,
): TargetVerifierAdapter {
  const now = options.now ?? defaultNow;
  const liveCache = new Map<string, CacheEntry>();
  let activeTargetId: string | null = null;
  let lockStopper: TargetLockStopper | null = null;

  const refreshTarget = (target: Target): HalLiveCheck => {
    const checkedAt = now();
    try {
      const result = options.verifyLive(target);
      liveCache.set(target.id, { checkedAt, result, threw: false });
      return result;
    } catch {
      const result: HalLiveCheck = { ok: false, reason: 'hal_exception' };
      liveCache.set(target.id, { checkedAt, result, threw: true });
      return result;
    }
  };

  const unlock = (): void => {
    lockStopper?.();
    lockStopper = null;
    activeTargetId = null;
  };

  const lock = (target: Target): void => {
    if (!options.startTargetLock) return;
    if (activeTargetId === target.id && lockStopper) return;
    unlock();
    activeTargetId = target.id;
    lockStopper = options.startTargetLock(
      target,
      () => { refreshTarget(target); },
      () => {
        liveCache.set(target.id, {
          checkedAt: now(),
          result: { ok: false, reason: 'target_lost' },
          threw: false,
        });
        lockStopper = null;
      },
    );
  };

  const verifier: TargetVerifier = (target, ctx) => {
    try {
      if (options.getKnownTarget && !options.getKnownTarget(target.id)) {
        return { ok: false, reason: 'target_unknown' };
      }

      const command = options.getCommand(target);
      if (command?.worldStateSequence !== options.getWorldStateSequence()) {
        return { ok: false, reason: 'world_state_stale' };
      }

      if (!command) {
        return { ok: false, reason: 'policy_rejected:command_missing' };
      }
      const ontology = validateMovementOntologyCommand(
        command,
        options.getWorldStateSequence(),
      );
      if (!ontology.ok) {
        if (ontology.reason === 'stale_world_state') {
          return { ok: false, reason: 'world_state_stale' };
        }
        return { ok: false, reason: `policy_rejected:${ontology.reason}` };
      }

      const boundTargetId = options.getBoundTargetId?.(target);
      if ((boundTargetId && boundTargetId !== target.id) ||
        (command.targetId && command.targetId !== target.id)) {
        return { ok: false, reason: 'identity_mismatch' };
      }

      const cached = liveCache.get(target.id);
      if (cached?.threw) return { ok: false, reason: 'verifier_error' };
      if (!cached || ctx.now - cached.checkedAt > HAL_LIVE_CACHE_MAX_AGE_MS) {
        return { ok: false, reason: 'live_dom_unverified' };
      }
      if (!cached.result.ok) return { ok: false, reason: 'live_dom_unverified' };
      return { ok: true };
    } catch {
      return { ok: false, reason: 'verifier_error' };
    }
  };

  const onPointStage = (session: Readonly<PointSession>): void => {
    if (session.stage === 'acquire') {
      const target = options.getKnownTarget?.(session.targetId);
      if (target) lock(target);
      return;
    }
    if (session.stage === 'approach' && session.reason === 'reacquired') {
      const target = options.getKnownTarget?.(session.targetId);
      if (target) lock(target);
      return;
    }
    if (session.stage === 'release' || session.stage === 'bow_out' || session.stage === 'refused') {
      unlock();
    }
    // target_lost intentionally holds the last lock state until bow_out.
  };

  return {
    verifier,
    refreshTarget,
    onPointStage,
    dispose: unlock,
  };
}
