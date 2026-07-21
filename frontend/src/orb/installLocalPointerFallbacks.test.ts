import {
  collectLivePointerRecords,
  markKnownOrbWeaverTargets,
} from "./installLocalPointerFallbacks";

declare const describe: (name: string, testSuite: () => void) => void;
declare const beforeEach: (setup: () => void) => void;
declare const afterEach: (setup: () => void) => void;
declare const it: (name: string, test: () => void) => void;
declare const expect: (value: unknown) => {
  toBe: (expected: unknown) => void;
};

describe("Orb Weaver live pointer fallbacks", () => {
  const originalPath = window.location.pathname;

  beforeEach(() => {
    document.body.innerHTML = "";
  });

  afterEach(() => {
    window.history.replaceState(null, "", originalPath || "/");
  });

  it("marks the public Preflight URL field and submit button deterministically", () => {
    window.history.replaceState(null, "", "/preflight");
    document.body.innerHTML = `
      <form>
        <input aria-label="Website URL" placeholder="https://example.com" />
        <button type="submit">Run Preflight</button>
      </form>
    `;

    markKnownOrbWeaverTargets();

    expect(document.querySelector("input")?.getAttribute("data-orb-target")).toBe("preflight-website-url");
    expect(document.querySelector("button")?.getAttribute("data-orb-target")).toBe("run-preflight");
  });

  it("creates VERIFIED may-point records only for explicit live targets", () => {
    window.history.replaceState(null, "", "/");
    document.body.innerHTML = `
      <button data-orb-target="run-free-preflight" data-orb-aliases="scan my website|start free scan">
        Run a Free Preflight Scan
      </button>
      <button>Unmarked control</button>
    `;

    const records = collectLivePointerRecords();
    const record = records[0];

    expect(records.length).toBe(1);
    expect(record.target_id).toBe("run-free-preflight");
    expect(record.page_route).toBe("/");
    expect(record.confidence_class).toBe("VERIFIED");
    expect(record.runtime_policy.may_point).toBe(true);
    expect(record.semantic_locator).toBe('[data-orb-target="run-free-preflight"]');
    expect(Boolean(record.direct_aliases?.includes("scan my website"))).toBe(true);
  });
});
