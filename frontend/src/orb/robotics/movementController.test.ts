import { OrbRoboticsMovementController } from './movementController';
import { deactivateEndEffector } from './webActuator.hal';
import type { RobotCommand } from './robotMovement.types';
import type { OrbPointerRecord } from '../targetValidation';

declare const test: (name: string, testCase: () => void) => void;
declare const expect: (value: unknown) => { toBe: (expected: unknown) => void };

const setup = () => {
  deactivateEndEffector();
  document.body.innerHTML = '<nav><a href="/demo">Demonstration Station</a></nav>';
  const element = document.querySelector('a')!;
  element.getBoundingClientRect = () => ({
    x: 20, y: 30, left: 20, top: 30, right: 220, bottom: 70,
    width: 200, height: 40, toJSON: () => ({}),
  } as DOMRect);
  const pointerRecord: OrbPointerRecord = {
    target_id: 'demo-link', semantic_locator: 'a[href="/demo"]',
    content_fingerprint: 'demo', meaning: 'nav: Demonstration Station',
    confidence_class: 'VERIFIED', runtime_policy: { may_point: true },
    structural_context: { parent_locator: 'nav', tag: 'a' },
  };
  const command: RobotCommand = {
    commandId: 'test-point-ping', actionType: 'NAVIGATE_AND_ILLUMINATE',
    targetId: 'demo-link', intent: 'Guide', urgency: 'normal',
    approachBehavior: 'decelerate_on_arrive', worldStateSequence: 1,
    endEffector: { type: 'PING_LIGHT', duration: 'brief', intensity: 'medium' },
    reason: 'verify arrival before ping',
  };
  return { element, pointerRecord, command };
};

test('beginMovement does not ping until the verified arrival boundary', () => {
  const { pointerRecord, command } = setup();
  const controller = new OrbRoboticsMovementController();
  const events: string[] = [];
  const movement = controller.beginMovement({ command, pointerRecord, currentWorldStateSequence: 1,
    onTelemetry: event => events.push(event.event) });
  expect(movement.ok).toBe(true);
  expect(document.getElementById('orb-active-ping')).toBe(null);
  expect(events.includes('END_EFFECTOR_ACTIVE')).toBe(false);
  if (movement.ok) {
    expect(movement.activateEndEffector()).toBe(true);
    expect(movement.activateEndEffector()).toBe(false);
    expect(Boolean(document.getElementById('orb-active-ping'))).toBe(true);
    movement.complete();
    expect(Boolean(document.getElementById('orb-active-ping'))).toBe(true);
  }
  controller.dispose();
  expect(document.getElementById('orb-active-ping')).toBe(null);
});

test('target loss before arrival prevents end-effector activation', () => {
  const { element, pointerRecord, command } = setup();
  const controller = new OrbRoboticsMovementController();
  const movement = controller.beginMovement({ command, pointerRecord, currentWorldStateSequence: 1 });
  expect(movement.ok).toBe(true);
  element.remove();
  if (movement.ok) {
    expect(movement.activateEndEffector()).toBe(false);
    movement.cancel('target_lost');
  }
  expect(document.getElementById('orb-active-ping')).toBe(null);
  controller.dispose();
});
