import type {
  Lidar2DMappingStatus,
  LidarPointerCoordinate,
  LidarPointerRecord,
} from './Lidar2DMapping.types';

export interface Lidar2DMappingState {
  cache: Map<string, LidarPointerCoordinate>;
  status: Lidar2DMappingStatus;
  rawRecords: LidarPointerRecord[];
  scanTimestamp: number;
  resizeTimer: ReturnType<typeof setTimeout> | null;
  driftAuditTimer: ReturnType<typeof setInterval> | null;
  scrollY: number;
  scrollX: number;
  viewportWidth: number;
  viewportHeight: number;
}

export function createLidar2DMappingState(): Lidar2DMappingState {
  return {
    cache: new Map(),
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
