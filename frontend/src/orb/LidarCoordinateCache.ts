import { createLidarState, type LidarState } from './LidarCoordinateCache.state';
import { validateOrbPointerTarget, type OrbPointerRecord } from './targetValidation';
import type { PointerCoordinate, TelemetryFrame, ViewportCoordinate } from './types';

const DRIFT_THRESHOLD_PX = 12;
const RESIZE_DEBOUNCE_MS = 120;
const DRIFT_AUDIT_INTERVAL_MS = 30000;
const STALE_THRESHOLD_MS = 300000;
const GEOMETRY_STABILIZATION_FRAMES = 2;
const GEOMETRY_STABILIZATION_TIMEOUT_MS = 1600;

export class LidarCoordinateCache {
  private static instance: LidarCoordinateCache | null = null;

  private state: LidarState;

  private constructor() {
    this.state = createLidarState();
    this.bindScrollHandler();
    this.bindResizeHandler();
  }

  static getInstance(): LidarCoordinateCache {
    if (!LidarCoordinateCache.instance) {
      LidarCoordinateCache.instance = new LidarCoordinateCache();
    }
    return LidarCoordinateCache.instance;
  }

  load(records: OrbPointerRecord[]): void {
    if (this.state.status === 'scanning') return;

    this.state.status = this.state.status === 'uninitialized' ? 'scanning' : 'rebuilding';
    this.state.rawRecords = records;

    requestAnimationFrame(() => {
      const nextCache = new Map<string, PointerCoordinate>();
      const nextRecordIndex = new Map<string, OrbPointerRecord>();
      const nextElementCache = new Map<string, HTMLElement>();

      for (const record of records) {
        const validation = validateOrbPointerTarget(record, { logger: console });
        if (!validation.ok) continue;

        const rect = validation.rect;
        nextCache.set(record.target_id, {
          target_id: record.target_id,
          absoluteTop: rect.top + window.scrollY,
          absoluteLeft: rect.left + window.scrollX,
          width: rect.width,
          height: rect.height,
          anchor_strategy: this.normalizeAnchorStrategy((record as OrbPointerRecord & { anchor_strategy?: string }).anchor_strategy),
          last_resolved_at: Date.now(),
          semantic_locator: record.semantic_locator,
        });
        nextRecordIndex.set(record.target_id, record);
        nextElementCache.set(record.target_id, validation.element);
      }

      this.state.cache = nextCache;
      this.state.recordIndex = nextRecordIndex;
      this.state.elementCache = nextElementCache;
      this.state.scanTimestamp = Date.now();
      this.state.status = 'ready';
    });
  }

  get(target_id: string): ViewportCoordinate | null {
    const world = this.state.cache.get(target_id);
    if (!world) return null;
    if (Date.now() - world.last_resolved_at > STALE_THRESHOLD_MS) {
      this.state.status = 'stale';
    }
    return {
      top: world.absoluteTop - window.scrollY,
      left: world.absoluteLeft - window.scrollX,
      width: world.width,
      height: world.height,
    };
  }

  getRecord(target_id: string): PointerCoordinate | null {
    return this.state.cache.get(target_id) || null;
  }

  hasRecord(target_id: string): boolean {
    return this.state.cache.has(target_id);
  }

  getResolvedElement(target_id: string): HTMLElement | null {
    const element = this.state.elementCache.get(target_id);
    if (!element) return null;
    if (!element.isConnected || !document.body.contains(element)) return null;
    return element;
  }

  injectFrame(frame: TelemetryFrame): void {
    const existing = this.state.cache.get(frame.target_id);
    this.state.cache.set(frame.target_id, {
      target_id: frame.target_id,
      absoluteTop: frame.absolute_top > 0 ? frame.absolute_top : existing?.absoluteTop || 0,
      absoluteLeft: frame.absolute_left > 0 ? frame.absolute_left : existing?.absoluteLeft || 0,
      width: frame.width > 0 ? frame.width : existing?.width || 1,
      height: frame.height > 0 ? frame.height : existing?.height || 1,
      anchor_strategy: existing?.anchor_strategy || 'element_center',
      last_resolved_at: Date.now(),
      semantic_locator: existing?.semantic_locator,
    });
    this.state.scanTimestamp = Date.now();
  }

  async prepareForMovement(target_id: string): Promise<ViewportCoordinate | null> {
    const initial = this.ensureLiveMeasurement(target_id);
    if (!initial) return null;

    const element = this.getResolvedElement(target_id);
    if (!element) return null;

    element.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
    return this.waitForGeometryStabilization(target_id);
  }

  rebuild(): void {
    if (!this.state.rawRecords.length) return;
    this.load(this.state.rawRecords);
  }

  startDriftAudit(): void {
    if (this.state.driftAuditTimer) return;

    this.state.driftAuditTimer = setInterval(() => {
      if (this.state.status !== 'ready' || this.state.cache.size === 0) return;

      const samples = Array.from(this.state.cache.keys())
        .sort(() => Math.random() - 0.5)
        .slice(0, 3);

      for (const targetId of samples) {
        const measured = this.ensureLiveMeasurement(targetId);
        if (!measured) {
          this.state.status = 'stale';
          this.rebuild();
          return;
        }
      }
    }, DRIFT_AUDIT_INTERVAL_MS);
  }

  stopDriftAudit(): void {
    if (this.state.driftAuditTimer) {
      clearInterval(this.state.driftAuditTimer);
      this.state.driftAuditTimer = null;
    }
  }

  isReady(): boolean {
    return this.state.status === 'ready';
  }

  getStatus(): string {
    return this.state.status;
  }

  getSize(): number {
    return this.state.cache.size;
  }

  clear(): void {
    this.state.cache.clear();
    this.state.recordIndex.clear();
    this.state.elementCache.clear();
    this.state.status = 'uninitialized';
    this.state.rawRecords = [];
    this.state.scanTimestamp = 0;
  }

  getRawRecords(): OrbPointerRecord[] {
    return [...this.state.rawRecords];
  }

  private bindScrollHandler(): void {
    window.addEventListener('scroll', () => {
      this.state.scrollY = window.scrollY;
      this.state.scrollX = window.scrollX;
    }, { passive: true });
  }

  private bindResizeHandler(): void {
    window.addEventListener('resize', () => {
      this.state.viewportWidth = window.innerWidth;
      this.state.viewportHeight = window.innerHeight;

      if (this.state.resizeTimer) clearTimeout(this.state.resizeTimer);
      this.state.resizeTimer = setTimeout(() => {
        this.rebuild();
        this.state.resizeTimer = null;
      }, RESIZE_DEBOUNCE_MS);
    });
  }

  private ensureLiveMeasurement(target_id: string): PointerCoordinate | null {
    const cached = this.state.cache.get(target_id);
    const cachedElement = this.getResolvedElement(target_id);

    if (cached && cachedElement) {
      const rect = cachedElement.getBoundingClientRect();
      const absoluteTop = rect.top + window.scrollY;
      const absoluteLeft = rect.left + window.scrollX;
      const driftY = Math.abs(absoluteTop - cached.absoluteTop);
      const driftX = Math.abs(absoluteLeft - cached.absoluteLeft);

      if (rect.width > 0 && rect.height > 0 && driftY <= DRIFT_THRESHOLD_PX && driftX <= DRIFT_THRESHOLD_PX) {
        const updated = {
          ...cached,
          absoluteTop,
          absoluteLeft,
          width: rect.width,
          height: rect.height,
          last_resolved_at: Date.now(),
        };
        this.state.cache.set(target_id, updated);
        return updated;
      }
    }

    const record = this.state.recordIndex.get(target_id);
    if (!record) return null;

    const validation = validateOrbPointerTarget(record, { logger: console });
    if (!validation.ok) {
      this.state.elementCache.delete(target_id);
      return null;
    }

    const refreshed: PointerCoordinate = {
      target_id,
      absoluteTop: validation.rect.top + window.scrollY,
      absoluteLeft: validation.rect.left + window.scrollX,
      width: validation.rect.width,
      height: validation.rect.height,
      anchor_strategy: this.normalizeAnchorStrategy((record as OrbPointerRecord & { anchor_strategy?: string }).anchor_strategy),
      last_resolved_at: Date.now(),
      semantic_locator: record.semantic_locator,
    };
    this.state.cache.set(target_id, refreshed);
    this.state.elementCache.set(target_id, validation.element);
    this.state.status = 'ready';
    return refreshed;
  }

  private waitForGeometryStabilization(target_id: string): Promise<ViewportCoordinate | null> {
    return new Promise((resolve) => {
      const startedAt = Date.now();
      let stableFrames = 0;
      let lastSignature = '';

      const tick = () => {
        const measurement = this.ensureLiveMeasurement(target_id);
        if (!measurement) {
          resolve(null);
          return;
        }

        const viewport = this.get(target_id);
        if (!viewport) {
          resolve(null);
          return;
        }

        const signature = [
          Math.round(viewport.top),
          Math.round(viewport.left),
          Math.round(viewport.width),
          Math.round(viewport.height),
        ].join(':');

        if (signature === lastSignature) {
          stableFrames += 1;
        } else {
          stableFrames = 0;
          lastSignature = signature;
        }

        if (stableFrames >= GEOMETRY_STABILIZATION_FRAMES) {
          resolve(viewport);
          return;
        }

        if (Date.now() - startedAt >= GEOMETRY_STABILIZATION_TIMEOUT_MS) {
          resolve(viewport);
          return;
        }

        requestAnimationFrame(tick);
      };

      requestAnimationFrame(tick);
    });
  }

  private normalizeAnchorStrategy(value?: string): PointerCoordinate['anchor_strategy'] {
    if (
      value === 'element_top_left'
      || value === 'element_top_right'
      || value === 'element_bottom_left'
      || value === 'element_bottom_right'
    ) {
      return value;
    }
    return 'element_center';
  }
}