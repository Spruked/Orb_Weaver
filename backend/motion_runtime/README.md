# motion_runtime

Generic, site-agnostic motion runtime for orbital behaviors, spatial sensing (LiDAR), and pointer / MORB control.

## Boundary

```
       SITE / DEPLOYMENT CONFIGURATION
                   │
                   │ targets, behavior profile,
                   │ permitted actions, visual config
                   ▼
          ┌───────────────────┐
          │  MOTION RUNTIME   │
          │                   │
          │ Orbital SKG       │
          │ LiDAR             │
          │ Pointer/MORBs     │
          └─────────┬─────────┘
                    │
             motion snapshot
```

### What it may know
- viewport, DOM geometry, target, anchor, obstacle
- cursor, position / velocity, behavioral intent
- ambient / hold / guided state
- Point / Ping, MORB deployment, movement vectors
- LiDAR confidence, route/viewport changes, physical presence

### What it must not know
No hard-coded product names, customer names, URLs, routes, selectors, target IDs, coordinates, tour scripts, or business rules. Those arrive only through configuration and host-driven inputs.

## Layout

```
lib/motion_runtime/
├── orbital_behavior_skg/   # Situation–Knowledge–Goal behavior layer
├── lidar/                  # Spatial sensing & repulsion
├── pointer/                # MORB / pointer integration
├── types.ts                # Shared contracts
├── MotionRuntime.ts        # Orchestrator
└── index.ts                # Public exports
```

## Quick start

```ts
import { MotionRuntime } from './motion_runtime';

const runtime = new MotionRuntime({
  behavior: {
    defaultState: 'ambient',
    orbitRadius: 72,
    maxSpeed: 400,
    damping: 0.86,
  },
  permittedActions: ['idle', 'approach', 'orbit', 'follow', 'retreat', 'hold', 'ping'],
  lidar: { enabled: true, sampleIntervalMs: 100 },
  visual: { defaultMorbVisualRef: 'default-orb' }, // opaque to runtime
});

// Host supplies target geometries (runtime never queries site-specific selectors)
runtime.setTargets([
  {
    id: 'hero-cta',
    kind: 'element',
    priority: 10,
    geometry: {
      rect: { x: 100, y: 200, width: 160, height: 48 },
      center: { x: 180, y: 224 },
      inViewport: true,
      visibility: 1,
    },
  },
]);

runtime.on('snapshot', (e) => {
  const snap = e.payload as import('./motion_runtime').MotionSnapshot;
  // Drive your visual layer from snap.morbs, snap.intent, etc.
});

runtime.start();
```

## Host responsibilities

1. **Configuration** — pass `MotionRuntimeConfig` at construction or via `updateConfig`.
2. **Geometry** — call `setTargets`, `setAnchors`, `setCandidateRects`, `setExtraObstacles` whenever layout changes.
3. **Route changes** — call `notifyRouteChange(opaqueToken)` on navigation.
4. **Rendering** — subscribe to `snapshot` / `intent` / `ping` events and map them to your visual system. The runtime does not touch the DOM beyond listening for pointer, resize, and scroll.

## License

Use freely in any website deployment.
