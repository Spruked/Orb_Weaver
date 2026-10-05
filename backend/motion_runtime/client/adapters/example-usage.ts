/**
 * Example: wiring motion_runtime into a host page.
 * All site-specific knowledge lives here, not inside the runtime.
 */

import { MotionRuntime, type Target, type MotionSnapshot } from '../../MotionRuntime';
import { createTargetVerifierAdapter } from './targetVerifierAdapter';
import { requireVerifiedTargetElement, startTargetLock } from '../pointer/webActuator.hal';
import type { RobotCommand } from '../pointer/robotMovement.types';

// ---------------------------------------------------------------------------
// 1. Create runtime with pure behavior config (no product names)
// ---------------------------------------------------------------------------

const runtime = new MotionRuntime({
  behavior: {
    defaultState: 'ambient',
    ambientWanderRadius: 100,
    orbitRadius: 72,
    approachSpeed: 280,
    maxSpeed: 420,
    damping: 0.86,
    holdTimeoutMs: 2000,
  },
  permittedActions: [
    'idle',
    'approach',
    'orbit',
    'point',
    'follow',
    'retreat',
    'hold',
    'ping',
  ],
  lidar: {
    enabled: true,
    sampleIntervalMs: 80,
    confidenceThreshold: 0.35,
  },
  visual: {
    defaultMorbVisualRef: 'orb-default', // host interprets this
    pingVisualRef: 'ping-default',
  },
});

let latestTargets: Target[] = [];
let worldStateSequence = 0;

const verifierAdapter = createTargetVerifierAdapter({
  getWorldStateSequence: () => worldStateSequence,
  getKnownTarget: (targetId) => latestTargets.find((target) => target.id === targetId),
  getCommand: (target): RobotCommand => ({
    commandId: `motion-runtime-${target.id}`,
    actionType: 'PRESENT_NEAR_TARGET',
    targetId: target.id,
    intent: 'Guide',
    urgency: 'normal',
    approachBehavior: 'decelerate_on_arrive',
    reason: 'host_point_request',
    worldStateSequence,
  }),
  getBoundTargetId: (target) =>
    document.querySelector<HTMLElement>(`[data-motion-target="${target.id}"]`)
      ?.getAttribute('data-motion-target') ?? undefined,
  verifyLive: (target) => {
    const element = document.querySelector<HTMLElement>(`[data-motion-target="${target.id}"]`);
    const result = requireVerifiedTargetElement(element, target.id);
    return result.ok ? { ok: true } : { ok: false, reason: result.reason };
  },
  startTargetLock: (target, onRefresh, onLost) => {
    const element = document.querySelector<HTMLElement>(`[data-motion-target="${target.id}"]`);
    if (!element) return () => undefined;
    return startTargetLock(element, onRefresh, onLost);
  },
});
runtime.setTargetVerifier(verifierAdapter.verifier);
runtime.onPointStage(verifierAdapter.onPointStage);

// ---------------------------------------------------------------------------
// 2. Host measures DOM and pushes generic Target geometries
// ---------------------------------------------------------------------------

function measureElement(el: Element, id: string, priority = 1): Target | null {
  const rect = el.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return null;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const visible =
    rect.bottom > 0 && rect.right > 0 && rect.top < vh && rect.left < vw;
  const intersectionArea =
    Math.max(0, Math.min(rect.bottom, vh) - Math.max(rect.top, 0)) *
    Math.max(0, Math.min(rect.right, vw) - Math.max(rect.left, 0));
  const visibility = rect.width * rect.height > 0
    ? intersectionArea / (rect.width * rect.height)
    : 0;

  return {
    id,
    kind: 'element',
    priority,
    geometry: {
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      center: { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 },
      inViewport: visible,
      visibility,
    },
  };
}

function pushTargetsFromHost(): void {
  // Host decides which elements matter — runtime only receives geometry
  const targets: Target[] = [];
  document.querySelectorAll('[data-motion-target]').forEach((el) => {
    const id = el.getAttribute('data-motion-target') || el.id || 'anon';
    const prio = Number(el.getAttribute('data-motion-priority') || 1);
    const t = measureElement(el, id, prio);
    if (t) targets.push(t);
  });
  latestTargets = targets;
  worldStateSequence += 1;
  runtime.setTargets(targets);
}

export function requestPointFromHost(targetId: string): boolean {
  const target = latestTargets.find((candidate) => candidate.id === targetId);
  if (!target) return false;
  verifierAdapter.refreshTarget(target);
  return runtime.requestPoint(targetId);
}

// ---------------------------------------------------------------------------
// 3. Subscribe & drive visuals
// ---------------------------------------------------------------------------

runtime.on('snapshot', (event) => {
  const snap = event.payload as MotionSnapshot;
  // Example: position a visual orb element
  const orb = document.getElementById('motion-orb');
  if (orb && snap.morbs[0]) {
    const m = snap.morbs[0];
    orb.style.transform = `translate(${m.position.x}px, ${m.position.y}px)`;
    orb.dataset.phase = m.phase;
  }
  // Intent can drive secondary UI (glow, trail, etc.)
  if (snap.intent) {
    document.documentElement.dataset.motionIntent = snap.intent.intent;
  }
});

runtime.on('ping', (event) => {
  console.debug('[motion] ping', event.payload);
});

// ---------------------------------------------------------------------------
// 4. Lifecycle
// ---------------------------------------------------------------------------

function boot(): void {
  pushTargetsFromHost();
  runtime.start();

  // Keep geometries fresh on layout changes
  const ro = new ResizeObserver(() => pushTargetsFromHost());
  document.querySelectorAll('[data-motion-target]').forEach((el) => ro.observe(el));
  window.addEventListener('scroll', () => pushTargetsFromHost(), { passive: true });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}

// Optional: expose for debugging / host control
(window as unknown as { __motionRuntime: MotionRuntime }).__motionRuntime = runtime;
