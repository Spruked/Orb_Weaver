import { OrbRoboticsMovementController } from "./movementController";
import { deactivateEndEffector, deployEndEffector } from "./webActuator.hal";
import type { RobotCommand } from "./robotMovement.types";

declare const describe: (name: string, testSuite: () => void) => void;
declare const beforeEach: (setup: () => void) => void;
declare const afterEach: (setup: () => void) => void;
declare const it: (name: string, test: () => void) => void;
declare const expect: (value: unknown) => {
  toBe: (expected: unknown) => void;
};
declare const jest: {
  fn: (implementation?: (...args: unknown[]) => unknown) => (...args: unknown[]) => unknown;
};

const visibleRect = (): DOMRect => ({
  x: 40,
  y: 60,
  left: 40,
  top: 60,
  right: 280,
  bottom: 108,
  width: 240,
  height: 48,
  toJSON: () => ({}),
});

describe("OrbRoboticsMovementController", () => {
  const originalRequestAnimationFrame = window.requestAnimationFrame;
  const originalCancelAnimationFrame = window.cancelAnimationFrame;

  beforeEach(() => {
    document.body.innerHTML = "";
    window.requestAnimationFrame = jest.fn(() => 1) as typeof window.requestAnimationFrame;
    window.cancelAnimationFrame = jest.fn() as typeof window.cancelAnimationFrame;
  });

  afterEach(() => {
    deactivateEndEffector();
    window.requestAnimationFrame = originalRequestAnimationFrame;
    window.cancelAnimationFrame = originalCancelAnimationFrame;
  });

  it("accepts a scan-generated target id after semantic validation of a data-orb-target element", () => {
    document.body.innerHTML = '<button data-orb-target="run-free-preflight">Run a Free Preflight Scan</button>';
    const element = document.querySelector("button") as HTMLButtonElement;
    element.getBoundingClientRect = visibleRect;

    const command: RobotCommand = {
      commandId: "pointer-test",
      actionType: "NAVIGATE_TO_TARGET",
      targetId: "target_5f8c0a7e11aa",
      intent: "Guide",
      urgency: "normal",
      approachBehavior: "decelerate_on_arrive",
      endEffector: { type: "NONE", duration: "standard", intensity: "medium" },
      reason: "Show the visitor where to begin the free preflight.",
      worldStateSequence: 1,
    };

    const controller = new OrbRoboticsMovementController();
    const result = controller.beginMovement({
      command,
      currentWorldStateSequence: 1,
      pointerRecord: {
        target_id: "target_5f8c0a7e11aa",
        semantic_locator: '[data-orb-target="run-free-preflight"]',
        content_fingerprint: "preflight",
        meaning: "button: Run a Free Preflight Scan",
        direct_aliases: ["run a free preflight scan", "scan my website"],
        confidence_class: "VERIFIED",
        runtime_policy: { may_point: true },
        structural_context: { tag: "button" },
      },
      onTelemetry: () => undefined,
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.targetElement).toBe(element);
      result.cancel("test_complete");
    }
    controller.dispose();
  });

  it("builds the Ping Light from DOM and CSS without a missing image asset", () => {
    document.body.innerHTML = '<button data-orb-target="run-free-preflight">Run a Free Preflight Scan</button>';
    const element = document.querySelector("button") as HTMLButtonElement;
    element.getBoundingClientRect = visibleRect;

    deployEndEffector(element, "standard", "medium");

    const ping = document.getElementById("orb-active-ping");
    expect(Boolean(ping)).toBe(true);
    expect(Boolean(ping?.querySelector(".orb-pointer-core"))).toBe(true);
    expect(ping?.querySelector("img") || null).toBe(null);
  });
});
