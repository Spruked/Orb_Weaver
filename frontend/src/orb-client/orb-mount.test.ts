import { resolveUniquePointerTarget } from "./orb-mount";

declare const describe: (name: string, testSuite: () => void) => void;
declare const it: (name: string, test: () => void) => void;
declare const expect: (value: unknown) => {
  toBe: (expected: unknown) => void;
  toHaveBeenCalledTimes: (expected: number) => void;
};
declare const jest: {
  fn: () => (...args: unknown[]) => void;
};

describe("universal loader pointer resolution", () => {
  it("rejects two equally valid matches before any target movement", () => {
    const first = document.createElement("button");
    const second = document.createElement("button");
    const scrollFirst = jest.fn();
    const scrollSecond = jest.fn();
    first.scrollIntoView = scrollFirst as never;
    second.scrollIntoView = scrollSecond as never;

    const result = resolveUniquePointerTarget([first, second], () => true);

    expect(result.status).toBe("ambiguous");
    if (result.status === "ambiguous") expect(result.matchCount).toBe(2);
    expect(scrollFirst).toHaveBeenCalledTimes(0);
    expect(scrollSecond).toHaveBeenCalledTimes(0);
  });
});
