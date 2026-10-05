export type ViewportFootprint = {
  left: number;
  top: number;
  right: number;
  bottom: number;
};

export type CornerName = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';

export type CornerExclusion = {
  excluded: boolean;
  corners: CornerName[];
};

/**
 * Corners are traversable, but no rendered ORB + caption footprint may settle
 * in them. This is a candidate/stance rule, not an occupancy obstacle.
 */
export function inspectCornerExclusion(
  footprint: ViewportFootprint,
  viewport: { width: number; height: number },
  margin: number,
): CornerExclusion {
  const safeMargin = Math.max(0, Number.isFinite(margin) ? margin : 0);
  const overlaps = (zone: ViewportFootprint) => (
    Math.max(0, Math.min(footprint.right, zone.right) - Math.max(footprint.left, zone.left)) > 0 &&
    Math.max(0, Math.min(footprint.bottom, zone.bottom) - Math.max(footprint.top, zone.top)) > 0
  );
  const zones: Array<[CornerName, ViewportFootprint]> = [
    ['top-left', { left: 0, top: 0, right: safeMargin, bottom: safeMargin }],
    ['top-right', { left: viewport.width - safeMargin, top: 0, right: viewport.width, bottom: safeMargin }],
    ['bottom-left', { left: 0, top: viewport.height - safeMargin, right: safeMargin, bottom: viewport.height }],
    ['bottom-right', { left: viewport.width - safeMargin, top: viewport.height - safeMargin, right: viewport.width, bottom: viewport.height }],
  ];
  const corners = zones.filter(([, zone]) => overlaps(zone)).map(([name]) => name);
  return { excluded: corners.length > 0, corners };
}
