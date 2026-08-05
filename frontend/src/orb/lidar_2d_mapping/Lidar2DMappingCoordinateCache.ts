import {
  createLidar2DMappingState,
  type Lidar2DMappingState,
} from './Lidar2DMapping.state';
import type {
  LidarPointerCoordinate,
  LidarPointerRecord,
  LidarTelemetryFrame,
  LidarViewportCoordinate,
} from './Lidar2DMapping.types';

const DRIFT_THRESHOLD_PX = 12;
const RESIZE_DEBOUNCE_MS = 120;
const DRIFT_AUDIT_INTERVAL_MS = 30_000;

/**
 * LiDAR 2D Mapping coordinate cache.
 *
 * Performs one batched DOM sweep, stores world-frame coordinates, converts
 * them to viewport coordinates in O(1), and re-localizes after layout drift.
 * Cached geometry is evidence only: callers must revalidate the live target
 * immediately before pointer movement, Ping, navigation, or action.
 */
export class Lidar2DMappingCoordinateCache {
  private static instance: Lidar2DMappingCoordinateCache | null = null;
  private readonly state: Lidar2DMappingState;

  private constructor() {
    this.state = createLidar2DMappingState();
    this.bindScrollHandler();
    this.bindResizeHandler();
  }

  static getInstance(): Lidar2DMappingCoordinateCache {
    if (!Lidar2DMappingCoordinateCache.instance) {
      Lidar2DMappingCoordinateCache.instance = new Lidar2DMappingCoordinateCache();
    }
    return Lidar2DMappingCoordinateCache.instance;
  }

  load(records: LidarPointerRecord[]): void {
    if (this.state.status === 'scanning') return;

    this.state.status = this.state.cache.size > 0 ? 'rebuilding' : 'scanning';
    this.state.rawRecords = [...records];

    requestAnimationFrame(() => {
      const nextCache = new Map<string, LidarPointerCoordinate>();
      const scrollY = window.scrollY;
      const scrollX = window.scrollX;

      for (const record of records) {
        try {
          const element = document.querySelector(record.semantic_locator);
          if (!element) continue;
          const rect = element.getBoundingClientRect();
          nextCache.set(record.target_id, {
            target_id: record.target_id,
            absoluteTop: rect.top + scrollY,
            absoluteLeft: rect.left + scrollX,
            width: rect.width,
            height: rect.height,
            anchor_strategy: this.normalizeAnchor(record.anchor_strategy),
            last_resolved_at: Date.now(),
            semantic_locator: record.semantic_locator,
          });
        } catch (error) {
          console.warn(`[LiDAR 2D Mapping] Scan failed for ${record.target_id}`, error);
        }
      }

      this.state.cache = nextCache;
      this.state.scanTimestamp = Date.now();
      this.state.status = 'ready';
      console.info(`[LiDAR 2D Mapping] Grid locked: ${nextCache.size} targets.`);
    });
  }

  get(targetId: string): LidarViewportCoordinate | null {
    const world = this.state.cache.get(targetId);
    if (!world) return null;
    return {
      top: world.absoluteTop - window.scrollY,
      left: world.absoluteLeft - window.scrollX,
      width: world.width,
      height: world.height,
    };
  }

  getRecord(targetId: string): LidarPointerCoordinate | null {
    return this.state.cache.get(targetId) ?? null;
  }

  injectFrame(frame: LidarTelemetryFrame): void {
    this.state.cache.set(frame.target_id, {
      target_id: frame.target_id,
      absoluteTop: frame.absolute_top,
      absoluteLeft: frame.absolute_left,
      width: frame.width,
      height: frame.height,
      anchor_strategy: 'element_center',
      last_resolved_at: Date.now(),
    });
    this.state.scanTimestamp = Date.now();
    this.state.status = 'ready';
  }

  startDriftAudit(): void {
    if (this.state.driftAuditTimer) return;
    this.state.driftAuditTimer = setInterval(() => {
      if (this.state.status !== 'ready' || this.state.cache.size === 0) return;
      const samples = Array.from(this.state.cache.values()).slice(0, 3);
      for (const sample of samples) {
        if (!sample.semantic_locator) continue;
        try {
          const element = document.querySelector(sample.semantic_locator);
          if (!element) {
            this.state.status = 'stale';
            continue;
          }
          const rect = element.getBoundingClientRect();
          const driftY = Math.abs(rect.top + window.scrollY - sample.absoluteTop);
          const driftX = Math.abs(rect.left + window.scrollX - sample.absoluteLeft);
          if (driftY > DRIFT_THRESHOLD_PX || driftX > DRIFT_THRESHOLD_PX) {
            console.warn(`[LiDAR 2D Mapping] Drift detected on ${sample.target_id}. Re-localizing.`);
            this.load(this.state.rawRecords);
            return;
          }
        } catch (error) {
          console.warn(`[LiDAR 2D Mapping] Drift audit failed for ${sample.target_id}`, error);
        }
      }
    }, DRIFT_AUDIT_INTERVAL_MS);
  }

  stopDriftAudit(): void {
    if (!this.state.driftAuditTimer) return;
    clearInterval(this.state.driftAuditTimer);
    this.state.driftAuditTimer = null;
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

  getRawRecords(): LidarPointerRecord[] {
    return [...this.state.rawRecords];
  }

  clear(): void {
    this.state.cache.clear();
    this.state.rawRecords = [];
    this.state.scanTimestamp = 0;
    this.state.status = 'uninitialized';
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
        this.load(this.state.rawRecords);
        this.state.resizeTimer = null;
      }, RESIZE_DEBOUNCE_MS);
    });
  }

  private normalizeAnchor(value?: string): LidarPointerCoordinate['anchor_strategy'] {
    switch (value) {
      case 'element_top_left':
      case 'element_top_right':
      case 'element_bottom_left':
      case 'element_bottom_right':
        return value;
      default:
        return 'element_center';
    }
  }
}
