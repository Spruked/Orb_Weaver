import { inspectCornerExclusion } from './cornerExclusion';

declare const test: (name: string, testCase: () => void) => void;
declare const expect: (value: unknown) => {
  toEqual: (expected: unknown) => void;
};

const viewport = { width: 1000, height: 800 };

test('rejects a rendered footprint in each viewport corner', () => {
  expect(inspectCornerExclusion({ left: 20, top: 40, right: 180, bottom: 190 }, viewport, 160).corners).toEqual(['top-left']);
  expect(inspectCornerExclusion({ left: 840, top: 40, right: 980, bottom: 190 }, viewport, 160).corners).toEqual(['top-right']);
  expect(inspectCornerExclusion({ left: 20, top: 650, right: 180, bottom: 790 }, viewport, 160).corners).toEqual(['bottom-left']);
  expect(inspectCornerExclusion({ left: 840, top: 650, right: 980, bottom: 790 }, viewport, 160).corners).toEqual(['bottom-right']);
});

test('allows the footprint to travel through the middle of an edge', () => {
  expect(inspectCornerExclusion({ left: 440, top: 40, right: 560, bottom: 180 }, viewport, 160)).toEqual({ excluded: false, corners: [] });
});

test('checks the complete footprint, including a caption extension', () => {
  expect(inspectCornerExclusion({ left: 180, top: 180, right: 340, bottom: 340 }, viewport, 160)).toEqual({ excluded: false, corners: [] });
  expect(inspectCornerExclusion({ left: 180, top: 180, right: 340, bottom: 340 }, viewport, 200)).toEqual({ excluded: true, corners: ['top-left'] });
});
