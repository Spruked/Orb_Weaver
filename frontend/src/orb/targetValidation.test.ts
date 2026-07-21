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
      confidence_class: "VERIFIED",
      runtime_policy: { may_point: true },
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
      confidence_class: "VERIFIED",
      runtime_policy: { may_point: true },
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

  it("refuses unclassified pointers by default", () => {
    document.body.innerHTML = '<button data-orb-target="legacy">Legacy target</button>';

    const result = validateOrbPointerTarget({
      target_id: "legacy",
      semantic_locator: "button[data-orb-target='legacy']",
      content_fingerprint: "legacy",
      meaning: "button: Legacy target",
    }, { logger: { warn: jest.fn(), info: jest.fn() } });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("policy_blocked");
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

  it("rejects a stale selector that now identifies different content", () => {
    document.body.innerHTML = '<main><button id="book-consult">Download brochure</button></main>';
    const element = document.querySelector("button") as HTMLButtonElement;
    element.getBoundingClientRect = () => ({
      x: 10, y: 10, left: 10, top: 10, right: 210, bottom: 50, width: 200, height: 40,
      toJSON: () => ({}),
    });

    const result = validateOrbPointerTarget({
      target_id: "book-consult",
      semantic_locator: "#book-consult",
      content_fingerprint: "consult",
      meaning: "button: Book consultation",
      confidence_class: "VERIFIED",
      runtime_policy: { may_point: true },
      structural_context: { parent_locator: "main", tag: "button" },
    }, { logger: { warn: jest.fn(), info: jest.fn() } });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("identity_mismatch");
  });

  it("selects the matching identity when a selector returns competing elements", () => {
    document.body.innerHTML = '<main><button class="cta">Download brochure</button><button class="cta">Book consultation</button></main>';
    const elements = Array.from(document.querySelectorAll("button")) as HTMLButtonElement[];
    elements.forEach((element, index) => {
      element.getBoundingClientRect = () => ({
        x: 10, y: 10 + index * 50, left: 10, top: 10 + index * 50, right: 210,
        bottom: 50 + index * 50, width: 200, height: 40, toJSON: () => ({}),
      });
    });

    const result = validateOrbPointerTarget({
      target_id: "book-consult",
      semantic_locator: "button.cta",
      content_fingerprint: "consult",
      meaning: "button: Book consultation",
      confidence_class: "VERIFIED",
      runtime_policy: { may_point: true },
      structural_context: { parent_locator: "main", tag: "button" },
    });

    expect(result.ok).toBe(true);
    if (result.ok) expect(result.element).toBe(elements[1]);
  });

  it("does not fall back outside an authoritative parent locator", () => {
    document.body.innerHTML = '<section id="changed"></section><footer><button class="cta">Join the Founding Beta</button></footer>';
    const element = document.querySelector("button") as HTMLButtonElement;
    element.getBoundingClientRect = () => ({
      x: 10, y: 10, left: 10, top: 10, right: 210, bottom: 50, width: 200, height: 40,
      toJSON: () => ({}),
    });

    const result = validateOrbPointerTarget({
      target_id: "approved-beta",
      semantic_locator: "button.cta",
      content_fingerprint: "beta",
      meaning: "button: Join the Founding Beta",
      confidence_class: "VERIFIED",
      runtime_policy: { may_point: true },
      structural_context: { parent_locator: "#changed", tag: "button" },
    }, { logger: { warn: jest.fn(), info: jest.fn() } });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("identity_mismatch");
  });

  it("rejects a short similarly named identity", () => {
    document.body.innerHTML = '<nav><a href="#beta">Beta</a></nav>';
    const element = document.querySelector("a") as HTMLAnchorElement;
    element.getBoundingClientRect = () => ({
      x: 10, y: 10, left: 10, top: 10, right: 110, bottom: 50, width: 100, height: 40,
      toJSON: () => ({}),
    });

    const result = validateOrbPointerTarget({
      target_id: "approved-beta",
      semantic_locator: "a",
      content_fingerprint: "beta",
      meaning: "button: Join the Founding Beta",
      confidence_class: "VERIFIED",
      runtime_policy: { may_point: true },
      structural_context: { parent_locator: "nav", tag: "a" },
    }, { logger: { warn: jest.fn(), info: jest.fn() } });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("identity_mismatch");
  });
});
