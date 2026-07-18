import { validateOrbPointerTarget } from "./targetValidation";

declare const describe: (name: string, testSuite: () => void) => void;
declare const beforeEach: (setup: () => void) => void;
declare const it: (name: string, test: () => void) => void;
declare const expect: (value: unknown) => {
  toBe: (expected: unknown) => void;
  toHaveBeenCalled: () => void;
};
declare const jest: {
  fn: () => (...args: unknown[]) => void;
};

describe("validateOrbPointerTarget", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("resolves a visible semantic target whose identity matches", () => {
    document.body.innerHTML = '<nav><a href="/demo">Demonstration Station</a></nav>';
    const element = document.querySelector("a") as HTMLAnchorElement;
    element.getBoundingClientRect = () => ({
      x: 20,
      y: 30,
      left: 20,
      top: 30,
      right: 220,
      bottom: 70,
      width: 200,
      height: 40,
      toJSON: () => ({}),
    });

    const result = validateOrbPointerTarget({
      target_id: "demo-link",
      semantic_locator: "a[href='/demo']",
      content_fingerprint: "demo",
      meaning: "nav: Demonstration Station",
      structural_context: { parent_locator: "nav", tag: "a" },
    });

    expect(result.ok).toBe(true);
    if (result.ok) expect(result.element).toBe(element);
  });

  it("refuses a locator when the live element identity does not match", () => {
    document.body.innerHTML = '<nav><a href="/checkout">Account settings</a></nav>';
    const element = document.querySelector("a") as HTMLAnchorElement;
    element.getBoundingClientRect = () => ({
      x: 20,
      y: 30,
      left: 20,
      top: 30,
      right: 220,
      bottom: 70,
      width: 200,
      height: 40,
      toJSON: () => ({}),
    });

    const result = validateOrbPointerTarget({
      target_id: "checkout-link",
      semantic_locator: "a[href='/checkout']",
      content_fingerprint: "checkout",
      meaning: "nav: Checkout",
      structural_context: { parent_locator: "nav", tag: "a" },
    }, { logger: { warn: jest.fn(), info: jest.fn() } });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("identity_mismatch");
  });

  it("refuses uncertain pointers before resolving the DOM target", () => {
    document.body.innerHTML = '<button data-orb-target="delete">Delete</button>';
    const haltToSafePosition = jest.fn();

    const result = validateOrbPointerTarget({
      target_id: "delete",
      semantic_locator: "button[data-orb-target='delete']",
      content_fingerprint: "delete",
      meaning: "action: Delete",
      confidence_class: "UNCERTAIN",
      runtime_policy: { may_point: true },
    }, {
      kineticTransit: { haltToSafePosition } as never,
      logger: { warn: jest.fn(), info: jest.fn() },
    });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("policy_blocked");
    expect(haltToSafePosition).toHaveBeenCalled();
  });

  it("honors an explicit runtime may-point denial", () => {
    document.body.innerHTML = '<a href="/account">Account</a>';

    const result = validateOrbPointerTarget({
      target_id: "account",
      semantic_locator: "a[href='/account']",
      content_fingerprint: "account",
      meaning: "nav: Account",
      confidence_class: "VERIFIED",
      runtime_policy: { may_point: false, reason: "manual_review_required" },
    }, { logger: { warn: jest.fn(), info: jest.fn() } });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("policy_blocked");
  });
});
