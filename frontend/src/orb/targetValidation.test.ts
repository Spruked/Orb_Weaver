import { validateOrbPointerTarget } from "./targetValidation";

declare const describe: (name: string, testSuite: () => void) => void;
declare const beforeEach: (setup: () => void) => void;
declare const it: (name: string, test: () => void) => void;
declare const expect: (value: unknown) => {
  toBe: (expected: unknown) => void;
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
});
