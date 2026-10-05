/**
 * motion_runtime — public entry
 *
 * Generic motion runtime for orbital behaviors, LiDAR sensing,
 * and pointer / MORB control. Site-specific knowledge is injected
 * only via MotionRuntimeConfig and host-driven setters.
 */

export { MotionRuntime } from './MotionRuntime';
export { OrbitalBehaviorSKG } from './client/orbital_behavior_skg';
export { SpatialIntelligence, computeRepulsion } from './client/spatial_intelligence/SpatialIntelligence';
export { PointerController } from './client/pointer';

export type * from './shared/types/types';
