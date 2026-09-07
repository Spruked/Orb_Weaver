import { useCallback, useEffect, useRef } from 'react';
import { LidarCoordinateCache } from './LidarCoordinateCache';
import { OrbTelemetryClient } from './OrbTelemetryClient';
import { Lidar2DMappingTelemetryClient } from './lidar_2d_mapping/Lidar2DMappingTelemetryClient';
import type { TelemetryFrame, ViewportCoordinate } from './types';

interface UseOrbTelemetryProps {
  wsUrl?: string;
  onTargetLock: (viewportCoord: ViewportCoordinate, frame: TelemetryFrame) => void;
  onStatusChange?: (status: string) => void;
}

export function useOrbTelemetry({ wsUrl, onTargetLock, onStatusChange }: UseOrbTelemetryProps) {
  const clientRef = useRef<OrbTelemetryClient | null>(null);
  const lidarClientRef = useRef<Lidar2DMappingTelemetryClient | null>(null);
  const lidarRef = useRef(LidarCoordinateCache.getInstance());

  const handleFrame = useCallback((frame: TelemetryFrame) => {
    // Telemetry coordinates are advisory transport data. Reacquire the live
    // DOM target and wait for stable geometry before allowing Point/Ping.
    void lidarRef.current.prepareForMovement(frame.target_id).then((viewport) => {
      if (viewport) {
        onTargetLock(viewport, frame);
      } else {
        console.warn(`[useOrbTelemetry] Live target verification blocked: ${frame.target_id}`);
      }
    });
  }, [onTargetLock]);

  useEffect(() => {
    const client = new OrbTelemetryClient(wsUrl);
    const lidarClient = new Lidar2DMappingTelemetryClient(
      wsUrl?.replace(/\/orb-pointer$/, '/lidar-2d-mapping'),
    );
    const lidar = lidarRef.current;
    clientRef.current = client;
    lidarClientRef.current = lidarClient;

    client.onFrameReceived(handleFrame);
    // The dedicated LiDAR channel is the geometry telemetry lane. Mirror its
    // frames into the existing active guidance cache so prepareForMovement()
    // still performs the final live DOM validation before Point/Ping.
    lidarClient.onFrameReceived((frame) => {
      lidar.injectFrame({
        event_type: frame.event_type,
        target_id: frame.target_id,
        absolute_top: frame.absolute_top,
        absolute_left: frame.absolute_left,
        width: frame.width,
        height: frame.height,
        semantic_intent: frame.semantic_intent,
        movement_vector: frame.movement_vector,
        confidence: frame.confidence,
        metadata: frame.metadata,
        timestamp_iso: frame.timestamp_iso,
      });
    });
    if (onStatusChange) {
      client.onStatusChange((status) => onStatusChange(status));
    }

    client.connect();
    lidarClient.connect();
    lidar.startDriftAudit();

    return () => {
      client.disconnect();
      lidarClient.disconnect();
      lidarClientRef.current = null;
      lidar.stopDriftAudit();
    };
  }, [handleFrame, onStatusChange, wsUrl]);

  return {
    reportDrift: (targetId: string) => clientRef.current?.reportDrift(targetId),
    getTelemetryStatus: () => clientRef.current?.getStatus() || 'disconnected',
    getLidarStatus: () => lidarRef.current.getStatus(),
  };
}
