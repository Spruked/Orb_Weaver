import { canAdvanceCaptionProgression, captionProgressAtPlayback, splitSpeechIntoCaptionPhrases } from "./speechCaptions";

declare const describe: (name: string, testSuite: () => void) => void;
declare const test: (name: string, testCase: () => void) => void;
declare const expect: (actual: unknown) => {
  not: { toContain: (expected: unknown) => void };
  toBe: (expected: unknown) => void;
  toEqual: (expected: unknown) => void;
  toContain: (expected: unknown) => void;
  toBeGreaterThanOrEqual: (expected: number) => void;
};

describe("speech captions", () => {
  const narration = "Your Preflight is complete. Two links need attention, and checkout needs review. The full report is ready.";

  test("starts empty and keeps future narration hidden during early playback", () => {
    expect(captionProgressAtPlayback(narration, 0, 12).revealedText).toBe("");
    const early = captionProgressAtPlayback(narration, 2, 12);
    expect(early.revealedText).not.toContain("The full report is ready.");
  });

  test("advances only from playback position and completes at audio completion", () => {
    const early = captionProgressAtPlayback(narration, 3, 12).revealedText;
    const later = captionProgressAtPlayback(narration, 9, 12).revealedText;
    expect(later.length).toBeGreaterThanOrEqual(early.length);
    expect(captionProgressAtPlayback(narration, 12, 12)).toEqual({ revealedText: narration, isComplete: true });
  });

  test("keeps natural sentence and clause boundaries", () => {
    expect(splitSpeechIntoCaptionPhrases(narration)).toEqual([
      "Your Preflight is complete.",
      "Two links need attention, and checkout needs review.",
      "The full report is ready.",
    ]);
  });

  test("does not advance after playback pauses or is cancelled", () => {
    expect(canAdvanceCaptionProgression({ paused: true, cancelled: false })).toBe(false);
    expect(canAdvanceCaptionProgression({ paused: false, cancelled: true })).toBe(false);
    expect(canAdvanceCaptionProgression({ paused: false, cancelled: false })).toBe(true);
  });
});
