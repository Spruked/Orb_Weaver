import type { OrbPointerRecord } from './targetValidation';
import type { PointerCoordinate, LidarCacheStatus } from './types';

export interface LidarState {
  cache: Map<string, PointerCoordinate>;
  recordIndex: Map<string, OrbPointerRecord>;
  elementCache: Map<string, HTMLElement>;
  status: LidarCacheStatus;
  rawRecords: OrbPointerRecord[];
  scanTimestamp: number;
  resizeTimer: ReturnType<typeof setTimeout> | null;
  driftAuditTimer: ReturnType<typeof setInterval> | null;
  scrollY: number;
  scrollX: number;
  viewportWidth: number;
  viewportHeight: number;
}

export function createLidarState(): LidarState {
  return {
    cache: new Map(),
    recordIndex: new Map(),
    elementCache: new Map(),
    status: 'uninitialized',
    rawRecords: [],
    scanTimestamp: 0,
    resizeTimer: null,
    driftAuditTimer: null,
    scrollY: window.scrollY,
    scrollX: window.scrollX,
    viewportWidth: window.innerWidth,
    viewportHeight: window.innerHeight,
  };
}