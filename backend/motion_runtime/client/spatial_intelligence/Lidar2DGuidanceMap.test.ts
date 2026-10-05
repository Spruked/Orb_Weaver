import { buildLidarGuidanceMap, evaluateLidarPose } from './Lidar2DGuidanceMap';

declare const test: (name: string, testCase: () => void) => void;
declare const expect: (value: unknown) => {
  toBe: (expected: unknown) => void;
  toBeGreaterThan: (expected: number) => void;
  toEqual: (expected: unknown) => void;
};

const place = (element: Element, x: number, y: number, width: number, height: number) => {
  element.getBoundingClientRect = () => ({
    x, y, left: x, top: y, right: x + width, bottom: y + height,
    width, height, toJSON: () => ({}),
  } as DOMRect);
};

const fixture = () => {
  document.body.innerHTML = `
    <main id="layout">
      <h2 id="security-title">Security overview</h2>
      <p id="security-copy">Security controls protect visitor information.</p>
      <h2 id="signup-title">Signup</h2>
      <p id="signup-copy">Sign up for the founding beta.</p>
      <button id="submit">Continue</button>
    </main>
    <div id="modal" role="dialog"><p id="modal-error" role="alert">Security error</p></div>`;
  place(document.getElementById('layout')!, 0, 0, 900, 700);
  place(document.getElementById('security-title')!, 100, 80, 220, 40);
  place(document.getElementById('security-copy')!, 100, 130, 330, 70);
  place(document.getElementById('signup-title')!, 550, 80, 150, 40);
  place(document.getElementById('signup-copy')!, 550, 130, 280, 70);
  place(document.getElementById('submit')!, 550, 240, 100, 44);
  place(document.getElementById('modal')!, 400, 350, 280, 200);
  place(document.getElementById('modal-error')!, 420, 380, 230, 60);
};

test('maps four surfaces without letting a parent container consume all free space', () => {
  fixture();
  const map = buildLidarGuidanceMap({
    purpose: 'security',
    orbFootprint: { offsetX: 0, offsetY: 0, width: 90, height: 90 },
    clearancePx: 10,
  });
  expect(map.features.find(item => item.tagName === 'h2')?.surfaceType).toBe('waypoint');
  expect(map.features.find(item => item.tagName === 'p')?.surfaceType).toBe('semantic_anchor');
  expect(map.features.find(item => item.role === 'dialog')?.surfaceType).toBe('obstacle');
  expect(map.occupancy.some(cell => cell.kind === 'free_space')).toBe(true);
  expect(map.occupancy.some(cell => cell.id === map.features.find(item => item.tagName === 'main')?.id)).toBe(false);
  expect(map.occupancy.filter(cell => cell.kind === 'scroll_boundary').length).toBe(4);
  expect(map.features.find(item => item.tagName === 'button')?.hardExclusion).toBe(true);
  expect(map.dynamicObstacleCount).toBeGreaterThan(0);
});

test('purpose changes semantic priority while pointer authority stays candidate only', () => {
  fixture();
  const targetIdByElement = new WeakMap<Element, string>();
  const rankByElement = new WeakMap<Element, { baseRank: number; rankEvidence: string[] }>();
  targetIdByElement.set(document.getElementById('security-copy')!, 'security-pointer');
  rankByElement.set(document.getElementById('security-copy')!, { baseRank: 4, rankEvidence: ['matches_site_scan_topical_terms'] });
  rankByElement.set(document.getElementById('signup-copy')!, { baseRank: 3, rankEvidence: ['observed_target_type:paragraph'] });
  const security = buildLidarGuidanceMap({ purpose: 'security', targetIdByElement, rankByElement });
  const signup = buildLidarGuidanceMap({ purpose: 'signup', targetIdByElement, rankByElement });
  const find = (map: typeof security, x: number) => map.features.find(item => item.tagName === 'p' && item.rect.x === x)!;
  expect(find(security, 100).effectivePriority).toBeGreaterThan(find(security, 550).effectivePriority);
  expect(find(signup, 550).effectivePriority).toBeGreaterThan(find(signup, 100).effectivePriority);
  expect(find(security, 100).authorityState).toBe('pointer_candidate');
  expect(find(signup, 550).authorityState).toBe('unmapped');
  expect(find(security, 100).baseRank).toBe(4);
  expect(find(signup, 100).baseRank).toBe(4);
  expect(find(security, 100).baseRankEvidence).toEqual(['matches_site_scan_topical_terms']);
});

test('caption footprint, controls and new geometry change free-space evidence', () => {
  fixture();
  const footprint = { offsetX: -30, offsetY: 0, width: 170, height: 100 };
  const before = buildLidarGuidanceMap({ orbFootprint: footprint });
  expect(evaluateLidarPose(before, { x: 510, y: 220 }, { x: 480, y: 220, width: 170, height: 100 }).footprintClear).toBe(false);
  expect(evaluateLidarPose(before, { x: 50, y: 420 }, { x: 20, y: 420, width: 170, height: 100 }).footprintClear).toBe(true);
  const modal = document.getElementById('modal')!;
  place(modal, 30, 400, 280, 200);
  const after = buildLidarGuidanceMap({ orbFootprint: footprint });
  expect(after.mapRevision).toBeGreaterThan(before.mapRevision);
  expect(after.features.find(item => item.role === 'dialog')?.motionChanged).toBe(true);
  expect(evaluateLidarPose(after, { x: 50, y: 420 }, { x: 20, y: 420, width: 170, height: 100 }).footprintClear).toBe(false);
});
