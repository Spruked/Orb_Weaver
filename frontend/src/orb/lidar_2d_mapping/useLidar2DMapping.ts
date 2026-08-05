import { useCallback, useEffect, useRef } from 'react';
import { Lidar2DMappingCoordinateCache } from './Lidar2DMappingCoordinateCache';
import { Lidar2DMappingTelemetryClient } from './Lidar2DMappingTelemetryClient';
import type {
  LidarPointerRecord,
  LidarTelemetryFrame,
  LidarViewportCoordinate,
} from './Lidar2DMapping.types';

interface UseLidar2DMappingOptions {
  records: LidarPointerRecord[];
  telemetryUrl?: string;
  enableTelemetry?: boolean;
  onTargetLock?: (coordinate: LidarViewportCoordinate, frame: LidarTelemetryFrame) => void;
  onStatusChange?: (status: string) => void;
}

/**
 * React lifecycle bridge for the visible LiDAR 2D Mapping implementation.
 * It loads the coordinate cache and optionally opens the telemetry lane.
 */
export function useLidar2DMapping({
  records,
  telemetryUrl,
  enableTelemetry = false,
  onTargetLock,
  onStatusChange,
}: UseLidar2DMappingOptions) {
  const cacheRef = useRef(Lidar2DMappingCoordinateCache.getInstance());
  const clientRef = useRef<Lidar2DMappingTelemetryClient | null>(null);

  const handleFrame = useCallback((frame: LidarTelemetryFrame) => {
    const coordinate = cacheRef.current.get(frame.target_id);
    if (coordinate) onTargetLock?.(coordinate, frame);
  }, [onTargetLock]);

  useEffect(() => {
    cacheRef.current.load(records);
    cacheRef.current.startDriftAudit();
    return () => cacheRef.current.stopDriftAudit();
  }, [records]);

  useEffect(() => {
    if (!enableTelemetry) return;
    const client = new Lidar2DMappingTelemetryClient(telemetryUrl);
    clientRef.current = client;
    client.onFrameReceived(handleFrame);
    if (onStatusChange) client.onStatusChange(onStatusChange);
    client.connect();
    return () => {
      client.disconnect();
      clientRef.current = null;
    };
  }, [enableTelemetry, telemetryUrl, handleFrame, onStatusChange]);

  return {
    getCoordinate: (targetId: string) => cacheRef.current.get(targetId),
    getLidar2DMappingStatus: () => cacheRef.current.getStatus(),
    getMappedTargetCount: () => cacheRef.current.getSize(),
    reportDrift: (targetId: string) => clientRef.current?.reportDrift(targetId),
  };
}
