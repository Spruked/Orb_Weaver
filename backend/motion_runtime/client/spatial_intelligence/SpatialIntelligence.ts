import type {
  LidarReading,
  MotionRuntimeConfig,
  Obstacle,
  Rect,
  Target,
  Viewport,
} from '../../shared/types/types';

export interface SpatialIntelligenceSampleInput {
  now: number;
  viewport: Viewport;
  candidateRects: Rect[];
  targets: Target[];
  extraObstacles?: Obstacle[];
}

/** Generic viewport-space sensing used by the motion runtime. */
export class SpatialIntelligence {
  private lastReading: LidarReading | null = null;
  private lastSampleAt = 0;
  private config: NonNullable<MotionRuntimeConfig['lidar']>;

  constructor(config: MotionRuntimeConfig['lidar'] = {}) {
    this.config = {
      enabled: true,
      sampleIntervalMs: 100,
      confidenceThreshold: 0.4,
      ...config,
    };
  }

  updateConfig(config: MotionRuntimeConfig['lidar'] = {}): void {
    this.config = { ...this.config, ...config };
  }

  getLastReading(): LidarReading | null {
    return this.lastReading;
  }

  sample(input: SpatialIntelligenceSampleInput): LidarReading | null {
    if (this.config.enabled === false) return null;
    const interval = this.config.sampleIntervalMs ?? 100;
    if (input.now - this.lastSampleAt < interval && this.lastReading) return this.lastReading;
    this.lastSampleAt = input.now;

    const obstacles: Obstacle[] = [
      ...input.candidateRects.flatMap((rect, index) => {
        if (rect.width < 4 || rect.height < 4) return [];
        const coverage = (rect.width * rect.height) / Math.max(1, input.viewport.width * input.viewport.height);
        if (coverage > 0.85) return [];
        return [{ id: `rect-${index}`, rect, kind: 'soft' as const, repulsion: 0.6 }];
      }),
      ...(input.extraObstacles ?? []),
    ];

    const occupiedArea = obstacles.reduce((sum, obstacle) => sum + obstacle.rect.width * obstacle.rect.height, 0);
    const viewportArea = Math.max(1, input.viewport.width * input.viewport.height);
    const reading: LidarReading = {
      confidence: obstacles.length === 0 ? 1 : Math.max(0, Math.min(1, 1 - occupiedArea / viewportArea)),
      obstacles,
      freeSpaceRatio: Math.max(0, Math.min(1, 1 - occupiedArea / viewportArea)),
      timestamp: input.now,
    };
    this.lastReading = reading;
    return reading;
  }
}

export function computeRepulsion(position: { x: number; y: number }, obstacles: Obstacle[]) {
  return obstacles.reduce(
    (acc, obstacle) => {
      const center = {
        x: obstacle.rect.x + obstacle.rect.width / 2,
        y: obstacle.rect.y + obstacle.rect.height / 2,
      };
      const dx = position.x - center.x;
      const dy = position.y - center.y;
      const distance = Math.max(1, Math.hypot(dx, dy));
      const strength = (obstacle.repulsion ?? 1) / distance;
      return { vx: acc.vx + (dx / distance) * strength, vy: acc.vy + (dy / distance) * strength };
    },
    { vx: 0, vy: 0 },
  );
}
