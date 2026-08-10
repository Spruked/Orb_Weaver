import { useCallback, useEffect, useRef } from 'react';
import { LidarCoordinateCache } from './LidarCoordinateCache';
import { OrbTelemetryClient } from './OrbTelemetryClient';
import type { TelemetryFrame, ViewportCoordinate } from './types';

interface UseOrbTelemetryProps {
  wsUrl?: string;
  onTargetLock: (viewportCoord: ViewportCoordinate, frame: TelemetryFrame) => void;
  onStatusChange?: (status: string) => void;
}

export function useOrbTelemetry({ wsUrl, onTargetLock, onStatusChange }: UseOrbTelemetryProps) {
  const clientRef = useRef<OrbTelemetryClient | null>(null);
  const lidarRef = useRef(LidarCoordinateCache.getInstance());

  const handleFrame = useCallback((frame: TelemetryFrame) => {
    const viewport = lidarRef.current.get(frame.target_id);
    if (viewport) {
      onTargetLock(viewport, frame);
    } else {
      console.warn(`[useOrbTelemetry] Frame received for unknown target: ${frame.target_id}`);
    }
  }, [onTargetLock]);

  useEffect(() => {
    const client = new OrbTelemetryClient(wsUrl);
    const lidar = lidarRef.current;
    clientRef.current = client;

    client.onFrameReceived(handleFrame);
    if (onStatusChange) {
      client.onStatusChange((status) => onStatusChange(status));
    }

    client.connect();
    lidar.startDriftAudit();

    return () => {
      client.disconnect();
      lidar.stopDriftAudit();
    };
  }, [handleFrame, onStatusChange, wsUrl]);

  return {
    reportDrift: (targetId: string) => clientRef.current?.reportDrift(targetId),
    getTelemetryStatus: () => clientRef.current?.getStatus() || 'disconnected',
    getLidarStatus: () => lidarRef.current.getStatus(),
  };
}