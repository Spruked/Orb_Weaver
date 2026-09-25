export interface LidarRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type LidarOccupancyKind = 'obstacle' | 'free_space' | 'scroll_boundary' | 'dynamic_obstacle';
export type LidarFeatureKind = 'image' | 'canvas' | 'document_link' | 'text_block' | 'interactive' | 'container';
export type LidarPreflightStatus = 'unknown' | 'ocr_candidate' | 'ocr_ready' | 'verified' | 'stale';
export type LidarSurfaceType = 'obstacle' | 'free_surface' | 'waypoint' | 'semantic_anchor';
export type LidarEvidenceState = 'dom_observed' | 'occluded';
export type LidarAuthorityState = 'unmapped' | 'pointer_candidate';

export interface LidarOccupancyCell {
  id: string;
  kind: LidarOccupancyKind;
  rect: LidarRect;
  fixed: boolean;
  visible: boolean;
  blocksOrbMovement: boolean;
  sourceSelector?: string;
  surfaceType: LidarSurfaceType;
  baseRank: number;
  rankEvidence: string[];
  navigationCost: number;
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
  surfaceType: LidarSurfaceType;
  baseRank: number;
  effectiveRank: number;
  baseRankEvidence: string[];
  baseRankSource: 'compiled_site_scan' | 'runtime_dom_fallback';
  purposeMatch: boolean;
  effectivePriority: number;
  evidenceState: LidarEvidenceState;
  /** A mapped identity is only a candidate; live Pointer validation grants authority. */
  authorityState: LidarAuthorityState;
  dynamic: boolean;
  motionChanged: boolean;
  geometryRevision: number;
  mapRevision: number;
  observedAt: string;
  detectionMethods: Array<'dom' | 'computed_style' | 'hit_test'>;
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
  freeSpaceCellSize: number;
  mapRevision: number;
  purposeReference?: string;
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
  rankByElement?: WeakMap<Element, { baseRank: number; rankEvidence: string[] }>;
  purpose?: string;
  /** New implementation parameter: additive priority for matching purpose. */
  purposePromotion?: number;
  /** Full body + active caption bounding box, relative to the ORB's top-left pose. */
  orbFootprint?: { offsetX: number; offsetY: number; width: number; height: number };
  clearancePx?: number;
}

let mapRevision = 0;
let nextObservationId = 0;
const observationIds = new WeakMap<Element, string>();
const geometryHistory = new WeakMap<Element, { signature: string; revision: number }>();

const observationId = (element: Element) => {
  let id = observationIds.get(element);
  if (!id) {
    id = `lidar-observation-${++nextObservationId}`;
    observationIds.set(element, id);
  }
  return id;
};

const geometryRevisionFor = (element: Element, rect: DOMRect) => {
  const signature = [rect.x, rect.y, rect.width, rect.height].map(value => Math.round(value)).join(':');
  const previous = geometryHistory.get(element);
  const revision = previous ? previous.revision + Number(previous.signature !== signature) : 1;
  geometryHistory.set(element, { signature, revision });
  return { revision, changed: Boolean(previous && previous.signature !== signature) };
};

const overlapArea = (a: LidarRect, b: LidarRect) =>
  Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x)) *
  Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y));

const intentTokens = (value: string) => new Set(
  value.toLowerCase().match(/[a-z0-9]{3,}/g)?.filter(token =>
    !['the', 'and', 'for', 'with', 'what', 'where', 'how', 'explain', 'show', 'find', 'about'].includes(token)
  ) || []
);

const classifySurface = (
  element: Element, kind: LidarFeatureKind, dynamic: boolean,
  hardExclusion: boolean, purposeMatch: boolean,
): { surfaceType: LidarSurfaceType; baseRank: number } => {
  const criticalMessage = element.matches('[role="alert"], [aria-live="assertive"], .error, [data-error]');
  if (dynamic && criticalMessage && purposeMatch) return { surfaceType: 'semantic_anchor', baseRank: 5 };
  if (dynamic && !element.matches('a, button, input, select, textarea')) return { surfaceType: 'obstacle', baseRank: 1 };
  if (element.matches('p, [role="alert"], [data-error]') ||
    (hardExclusion && element.matches('input, textarea, select, form, [role="form"]'))) {
    return { surfaceType: 'semantic_anchor', baseRank: 5 };
  }
  if (element.matches('h1, h2, h3, h4, h5, h6, a, button, [role="tab"], [role="link"]')) {
    return { surfaceType: 'waypoint', baseRank: 3 };
  }
  if (kind === 'text_block') return { surfaceType: 'semantic_anchor', baseRank: 5 };
  return { surfaceType: 'obstacle', baseRank: 1 };
};

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
  if (element.matches('p, h1, h2, h3, h4, h5, h6, [role="alert"]')) return 'text_block';
  return 'container';
};

const isDynamicObstacle = (element: Element, style: CSSStyleDeclaration) =>
  element.matches('[role="dialog"], [aria-modal="true"], dialog, [data-modal], [data-popover]') ||
  ((style.position === 'fixed' || style.position === 'sticky') && style.pointerEvents !== 'none');

// Weaver is rendered above the page so visitors can see her, but her own
// overlay must not make the readable page content beneath her disappear from
// the spatial model. The ORB + caption footprint is checked separately by
// Phase Zero when selecting a pose.
const isOrbRuntimeOverlay = (element: Element) => Boolean(
  element.closest('.ow-v2-orb-position, .ow-v2-pointer-bloom, [data-orb-caption-state]')
);

/** Advisory pose evidence. Phase Zero still applies its live footprint and
 * hard-exclusion checks before authorizing a settled position. */
export function evaluateLidarPose(map: LidarGuidanceMap, pose: { x: number; y: number }, footprint: LidarRect) {
  const center = { x: footprint.x + footprint.width / 2, y: footprint.y + footprint.height / 2 };
  const freeCells = map.occupancy.filter(cell => cell.kind === 'free_space');
  const nearestFreeDistance = freeCells.length
    ? Math.min(...freeCells.map(cell => Math.hypot(pose.x - cell.rect.x, pose.y - cell.rect.y)))
    : Number.POSITIVE_INFINITY;
  const matched = map.features.filter(feature => feature.purposeMatch &&
    (feature.surfaceType === 'semantic_anchor' || feature.surfaceType === 'waypoint'));
  const nearestRelevantDistance = matched.length
    ? Math.min(...matched.map(feature => Math.hypot(
      center.x - (feature.rect.x + feature.rect.width / 2),
      center.y - (feature.rect.y + feature.rect.height / 2),
    )))
    : Number.POSITIVE_INFINITY;
  const footprintClear = footprint.x >= 0 && footprint.y >= 0 &&
    footprint.x + footprint.width <= map.viewport.width &&
    footprint.y + footprint.height <= map.viewport.height &&
    !map.occupancy.some(cell => cell.blocksOrbMovement && overlapArea(footprint, cell.rect) > 0);
  return {
    footprintClear,
    freeSpaceProximity: Number.isFinite(nearestFreeDistance)
      ? Math.max(0, 1 - nearestFreeDistance / map.freeSpaceCellSize) : 0,
    purposeProximity: Number.isFinite(nearestRelevantDistance)
      ? Math.max(0, 1 - nearestRelevantDistance / Math.max(map.viewport.width, map.viewport.height)) : 0,
    nearestFreeDistance,
    nearestRelevantDistance,
  };
}

export function buildLidarGuidanceMap(options: BuildLidarGuidanceMapOptions = {}): LidarGuidanceMap {
  const gridCellSize = Math.max(4, options.gridCellSize || 10);
  const revision = ++mapRevision;
  const observedAt = new Date().toISOString();
  const purposeTokens = intentTokens(options.purpose || '');
  const purposePromotion = Math.max(0, options.purposePromotion ?? 2);
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
    const topElement = (document.elementsFromPoint?.(pointX, pointY) || [])
      .find((candidate) => !isOrbRuntimeOverlay(candidate));
    const occluded = Boolean(topElement && topElement !== element && !element.contains(topElement));
    const dynamic = isDynamicObstacle(element, style);
    const hardInteractiveExclusion = isHardInteractiveExclusion(element);
    const id = observationId(element);
    const order = stackingOrder++;
    const kind = featureKind(element, hardInteractiveExclusion);
    const label = [element.getAttribute('aria-label'), element.getAttribute('title'), element.id,
      kind === 'container' ? '' : element.textContent?.slice(0, 240)].filter(Boolean).join(' ');
    const labelTokens = intentTokens(label);
    const purposeMatch = purposeTokens.size > 0 && [...purposeTokens].some(token => labelTokens.has(token));
    const classification = classifySurface(element, kind, dynamic, hardInteractiveExclusion, purposeMatch);
    const compiledRank = options.rankByElement?.get(element);
    const hasCompiledRank = Boolean(compiledRank && Number.isInteger(compiledRank.baseRank) &&
      compiledRank.baseRank >= 1 && compiledRank.baseRank <= 5);
    const baseRank = hasCompiledRank ? compiledRank!.baseRank : classification.baseRank;
    const effectiveRank = purposeTokens.size
      ? purposeMatch ? Math.min(5, baseRank + purposePromotion) : Math.max(1, baseRank - 1)
      : baseRank;
    const geometry = geometryRevisionFor(element, rect);
    // pointer-events:none only changes mouse hit testing; readable copy and
    // imagery still occupy pixels and must remain protected from the ORB.
    const blocksOrbMovement = dynamic || hardInteractiveExclusion ||
      kind === 'text_block' || kind === 'image' || kind === 'canvas';

    // Parent layout containers are evidence, not blanket obstacles. Their
    // readable/actionable descendants contribute their own occupancy.
    if (blocksOrbMovement) occupancy.push({
      id,
      kind: dynamic ? 'dynamic_obstacle' : 'obstacle',
      rect: rectFromClientRect(rect),
      fixed: style.position === 'fixed' || style.position === 'sticky',
      visible,
      blocksOrbMovement,
      sourceSelector: element.id ? `#${element.id}` : undefined,
      surfaceType: classification.surfaceType,
      baseRank,
      rankEvidence: hasCompiledRank ? compiledRank!.rankEvidence : ['runtime_dom_role_fallback'],
      navigationCost: hardInteractiveExclusion ? Number.POSITIVE_INFINITY : dynamic ? 3 : 1,
    });

    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const distance = orb ? Math.hypot(centerX - orb.x, centerY - orb.y) : undefined;
    const preflightStatus = (url && options.preflightByUrl?.[url]) || 'unknown';

    features.push({
      id,
      targetId: options.targetIdByElement?.get(element),
      kind,
      rect: rectFromClientRect(rect),
      documentRect: documentRect(rect),
      tagName: element.tagName.toLowerCase(),
      role: element.getAttribute('role') || undefined,
      accessibleName: element.getAttribute('aria-label') || element.getAttribute('title') || undefined,
      visibleText: (element.textContent || '').trim().slice(0, 240) || undefined,
      url,
      zIndex,
      stackingOrder: order,
      pointerEvents: style.pointerEvents,
      visible,
      occluded,
      preflightStatus,
      tesseractResourceUrl: preflightStatus !== 'unknown' ? url : undefined,
      distanceFromOrb: distance,
      guidancePotential: distance === undefined ? undefined : 1 / Math.max(distance, 1),
      hardExclusion: hardInteractiveExclusion,
      surfaceType: classification.surfaceType,
      baseRank,
      effectiveRank,
      baseRankEvidence: hasCompiledRank ? compiledRank!.rankEvidence : ['runtime_dom_role_fallback'],
      baseRankSource: hasCompiledRank ? 'compiled_site_scan' : 'runtime_dom_fallback',
      purposeMatch,
      effectivePriority: effectiveRank,
      evidenceState: occluded ? 'occluded' : 'dom_observed',
      authorityState: options.targetIdByElement?.has(element) ? 'pointer_candidate' : 'unmapped',
      dynamic: dynamic || geometry.changed,
      motionChanged: geometry.changed,
      geometryRevision: geometry.revision,
      mapRevision: revision,
      observedAt,
      detectionMethods: topElement ? ['dom', 'computed_style', 'hit_test'] : ['dom', 'computed_style'],
    });
  }

  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const freeSpaceCellSize = Math.max(gridCellSize, Math.ceil(Math.sqrt(viewportWidth * viewportHeight / 600)));
  const clearance = Math.max(0, options.clearancePx || 0);
  const footprint = options.orbFootprint || { offsetX: 0, offsetY: 0, width: 1, height: 1 };
  const blocking = occupancy.filter(cell => cell.blocksOrbMovement);
  for (let y = 0; y < viewportHeight; y += freeSpaceCellSize) {
    for (let x = 0; x < viewportWidth; x += freeSpaceCellSize) {
      const candidate: LidarRect = {
        x: x + footprint.offsetX - clearance,
        y: y + footprint.offsetY - clearance,
        width: footprint.width + clearance * 2,
        height: footprint.height + clearance * 2,
      };
      if (candidate.x < 0 || candidate.y < 0 ||
        candidate.x + candidate.width > viewportWidth || candidate.y + candidate.height > viewportHeight ||
        blocking.some(cell => overlapArea(candidate, cell.rect) > 0)) continue;
      occupancy.push({
        id: `lidar-free-${revision}-${x}-${y}`,
        kind: 'free_space',
        rect: { x, y, width: Math.min(freeSpaceCellSize, viewportWidth - x), height: Math.min(freeSpaceCellSize, viewportHeight - y) },
        fixed: false,
        visible: true,
        blocksOrbMovement: false,
        surfaceType: 'free_surface',
        baseRank: 2,
        rankEvidence: ['live_orb_caption_footprint_clearance'],
        navigationCost: 0,
      });
    }
  }
  for (const [edge, rect] of [
    ['top', { x: 0, y: 0, width: viewportWidth, height: 1 }],
    ['right', { x: Math.max(0, viewportWidth - 1), y: 0, width: 1, height: viewportHeight }],
    ['bottom', { x: 0, y: Math.max(0, viewportHeight - 1), width: viewportWidth, height: 1 }],
    ['left', { x: 0, y: 0, width: 1, height: viewportHeight }],
  ] as const) occupancy.push({
    id: `lidar-boundary-${edge}`, kind: 'scroll_boundary', rect,
    fixed: true, visible: true, blocksOrbMovement: false,
    surfaceType: 'obstacle', baseRank: 1, rankEvidence: ['viewport_boundary'],
    navigationCost: Number.POSITIVE_INFINITY,
  });

  return {
    schema: 'orb_weaver.lidar_guidance_map.v1',
    route: window.location.pathname + window.location.search,
    measuredAt: observedAt,
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
      scrollX: window.scrollX,
      scrollY: window.scrollY,
      documentWidth: document.documentElement.scrollWidth,
      documentHeight: document.documentElement.scrollHeight,
    },
    gridCellSize,
    freeSpaceCellSize,
    mapRevision: revision,
    purposeReference: options.purpose ? 'current_intent' : undefined,
    occupancy,
    features,
    dynamicObstacleCount: occupancy.filter((item) => item.kind === 'dynamic_obstacle').length,
    preflightSignatureCount: features.filter((item) => item.preflightStatus !== 'unknown').length,
  };
}
