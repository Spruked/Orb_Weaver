export interface LidarRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type LidarOccupancyKind = 'obstacle' | 'free_space' | 'scroll_boundary' | 'dynamic_obstacle';
export type LidarFeatureKind = 'image' | 'canvas' | 'document_link' | 'text_block' | 'interactive' | 'container';
export type LidarPreflightStatus = 'unknown' | 'ocr_candidate' | 'ocr_ready' | 'verified' | 'stale';

export interface LidarOccupancyCell {
  id: string;
  kind: LidarOccupancyKind;
  rect: LidarRect;
  fixed: boolean;
  visible: boolean;
  blocksOrbMovement: boolean;
  sourceSelector?: string;
}

export interface LidarSemanticFeature {
  id: string;
  targetId?: string;
  kind: LidarFeatureKind;
  rect: LidarRect;
  documentRect: LidarRect;
  tagName: string;
  role?: string;
  accessibleName?: string;
  visibleText?: string;
  url?: string;
  zIndex: number;
  stackingOrder: number;
  pointerEvents: string;
  visible: boolean;
  occluded: boolean;
  preflightStatus: LidarPreflightStatus;
  tesseractResourceUrl?: string;
  distanceFromOrb?: number;
  guidancePotential?: number;
  /** Phase Zero hard exclusion: the ORB footprint may not overlap this feature. */
  hardExclusion: boolean;
}

export interface LidarGuidanceMap {
  schema: 'orb_weaver.lidar_guidance_map.v1';
  route: string;
  measuredAt: string;
  viewport: {
    width: number;
    height: number;
    scrollX: number;
    scrollY: number;
    documentWidth: number;
    documentHeight: number;
  };
  gridCellSize: number;
  occupancy: LidarOccupancyCell[];
  features: LidarSemanticFeature[];
  dynamicObstacleCount: number;
  preflightSignatureCount: number;
}

export interface BuildLidarGuidanceMapOptions {
  gridCellSize?: number;
  orbPosition?: { x: number; y: number };
  preflightByUrl?: Record<string, LidarPreflightStatus>;
  targetIdByElement?: WeakMap<Element, string>;
}

const finite = (value: number) => Number.isFinite(value) ? value : 0;

const rectFromClientRect = (rect: DOMRect): LidarRect => ({
  x: finite(rect.x),
  y: finite(rect.y),
  width: finite(rect.width),
  height: finite(rect.height),
});

const documentRect = (rect: DOMRect): LidarRect => ({
  x: finite(rect.x + window.scrollX),
  y: finite(rect.y + window.scrollY),
  width: finite(rect.width),
  height: finite(rect.height),
});

const numericZIndex = (style: CSSStyleDeclaration) => {
  const value = Number.parseInt(style.zIndex || '0', 10);
  return Number.isFinite(value) ? value : 0;
};

const elementUrl = (element: Element) => {
  if (element instanceof HTMLImageElement) return element.currentSrc || element.src || undefined;
  if (element instanceof HTMLAnchorElement) return element.href || undefined;
  if (element instanceof HTMLObjectElement) return element.data || undefined;
  if (element instanceof HTMLEmbedElement) return element.src || undefined;
  return undefined;
};

const isHardInteractiveExclusion = (element: Element): boolean => {
  if (element.matches(
    'button, a, input, select, textarea, [role="button"], [role="link"], [contenteditable="true"], [tabindex]:not([tabindex="-1"])'
  )) return true;
  if (element.matches(':focus')) return true;
  if (element instanceof HTMLLabelElement) {
    const labelledControl = element.htmlFor
      ? document.getElementById(element.htmlFor)
      : element.querySelector('input, select, textarea, button, [contenteditable="true"]');
    return Boolean(labelledControl);
  }
  return false;
};

const featureKind = (element: Element, hardInteractiveExclusion: boolean): LidarFeatureKind => {
  if (element instanceof HTMLImageElement) return 'image';
  if (element instanceof HTMLCanvasElement) return 'canvas';
  if (element instanceof HTMLAnchorElement && /\.(pdf|docx?|xlsx?|pptx?)(?:$|[?#])/i.test(element.href)) return 'document_link';
  if (hardInteractiveExclusion) return 'interactive';
  if (element.matches('.ow-cut-copy, [data-orb-copy-region]')) return 'text_block';
  if (element.matches('p, h1, h2, h3, h4, h5, h6, article')) return 'text_block';
  return 'container';
};

const isDynamicObstacle = (element: Element, style: CSSStyleDeclaration) =>
  style.position === 'fixed' || style.position === 'sticky' ||
  element.matches('[role="dialog"], [aria-modal="true"], dialog, [data-modal], [data-popover]');

// Weaver is rendered above the page so visitors can see her, but her own
// overlay must not make the readable page content beneath her disappear from
// the spatial model. The ORB + caption footprint is checked separately by
// Phase Zero when selecting a pose.
const isOrbRuntimeOverlay = (element: Element) => Boolean(
  element.closest('.ow-v2-orb-position, .ow-v2-pointer-bloom, [data-orb-caption-state]')
);

export function buildLidarGuidanceMap(options: BuildLidarGuidanceMapOptions = {}): LidarGuidanceMap {
  const gridCellSize = Math.max(4, options.gridCellSize || 10);
  const orb = options.orbPosition;
  const candidates = Array.from(document.querySelectorAll(
    'body *:not(script):not(style):not(meta):not(link):not(noscript)'
  )).filter((element) => !isOrbRuntimeOverlay(element));

  const occupancy: LidarOccupancyCell[] = [];
  const features: LidarSemanticFeature[] = [];
  let stackingOrder = 0;

  for (const element of candidates) {
    const rect = element.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) continue;

    const style = window.getComputedStyle(element);
    const visible = style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity || '1') > 0;
    if (!visible) continue;

    const url = elementUrl(element);
    const zIndex = numericZIndex(style);
    const pointX = Math.min(Math.max(rect.left + rect.width / 2, 0), window.innerWidth - 1);
    const pointY = Math.min(Math.max(rect.top + rect.height / 2, 0), window.innerHeight - 1);
    const topElement = document.elementsFromPoint(pointX, pointY)
      .find((candidate) => !isOrbRuntimeOverlay(candidate));
    const occluded = Boolean(topElement && topElement !== element && !element.contains(topElement));
    const dynamic = isDynamicObstacle(element, style);
    const hardInteractiveExclusion = isHardInteractiveExclusion(element);
    const id = `lidar-${stackingOrder++}`;

    occupancy.push({
      id,
      kind: dynamic ? 'dynamic_obstacle' : 'obstacle',
      rect: rectFromClientRect(rect),
      fixed: style.position === 'fixed' || style.position === 'sticky',
      visible,
      blocksOrbMovement: style.pointerEvents !== 'none',
      sourceSelector: element.id ? `#${element.id}` : undefined,
    });

    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const distance = orb ? Math.hypot(centerX - orb.x, centerY - orb.y) : undefined;
    const preflightStatus = (url && options.preflightByUrl?.[url]) || 'unknown';

    features.push({
      id,
      targetId: options.targetIdByElement?.get(element),
      kind: featureKind(element, hardInteractiveExclusion),
      rect: rectFromClientRect(rect),
      documentRect: documentRect(rect),
      tagName: element.tagName.toLowerCase(),
      role: element.getAttribute('role') || undefined,
      accessibleName: element.getAttribute('aria-label') || element.getAttribute('title') || undefined,
      visibleText: (element.textContent || '').trim().slice(0, 240) || undefined,
      url,
      zIndex,
      stackingOrder,
      pointerEvents: style.pointerEvents,
      visible,
      occluded,
      preflightStatus,
      tesseractResourceUrl: preflightStatus !== 'unknown' ? url : undefined,
      distanceFromOrb: distance,
      guidancePotential: distance === undefined ? undefined : 1 / Math.max(distance, 1),
      hardExclusion: hardInteractiveExclusion,
    });
  }

  return {
    schema: 'orb_weaver.lidar_guidance_map.v1',
    route: window.location.pathname + window.location.search,
    measuredAt: new Date().toISOString(),
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
      scrollX: window.scrollX,
      scrollY: window.scrollY,
      documentWidth: document.documentElement.scrollWidth,
      documentHeight: document.documentElement.scrollHeight,
    },
    gridCellSize,
    occupancy,
    features,
    dynamicObstacleCount: occupancy.filter((item) => item.kind === 'dynamic_obstacle').length,
    preflightSignatureCount: features.filter((item) => item.preflightStatus !== 'unknown').length,
  };
}
