# LiDAR 2D Mapping Implementation

> 2026-09-06 source update: [Target One landing tour](../../../../docs/TARGET_ONE_LANDING_TOUR.md) reuses the existing cognition, TTS and verified Pointer/LiDAR paths with controller-owned concept progression and an explicit terminal visitor choice. Integrated validation is deferred; historical verification below does not cover this new slice.

This directory is the canonical, visibly named Website ORB **LiDAR 2D Mapping / Coordinate Cache** package.

It was recovered from the August 4, 2026 implementation artifact and renamed so it cannot disappear behind generic names such as `pointer map`, `geometry cache`, `telemetry`, or `spatial runtime`.

## Canonical package identity

- Package name: `LiDAR 2D Mapping`
- Source directory: `frontend/src/orb/lidar_2d_mapping/`
- Main class: `Lidar2DMappingCoordinateCache`
- Telemetry client: `Lidar2DMappingTelemetryClient`
- React hook: `useLidar2DMapping`
- Backend lane: `backend/app/routers/lidar_2d_mapping_telemetry.py`

## Files

- `Lidar2DMappingCoordinateCache.ts` — batched DOM sweep, world-frame cache, viewport conversion, resize re-localization, drift audit.
- `Lidar2DMapping.state.ts` — mutable mapping state.
- `Lidar2DMappingTelemetryClient.ts` — bidirectional WebSocket telemetry.
- `Lidar2DMappingTelemetry.state.ts` — telemetry connection state.
- `Lidar2DMapping.types.ts` — shared contracts.
- `useLidar2DMapping.ts` — React lifecycle integration.
- `index.ts` — explicit public package exports.

## Boundary with Pointer Plot Map

The Pointer Plot Map supplies stable target identity, route, intent, locators, confidence, and permitted actions. LiDAR 2D Mapping resolves those target identities into current 2D geometry.

```text
Pointer Plot Map
      ↓
LiDAR 2D Mapping coordinate cache
      ↓
Live DOM/accessibility verification
      ↓
Movement controller / Web Actuator HAL
      ↓
Point and Ping
```

Cached coordinates are evidence and latency acceleration, not pointer authority. A live DOM or accessibility verification remains mandatory immediately before movement, pointing, navigation, or action.

## Naming protection

Do not rename this directory or its public classes to generic geometry, map, cache, locator, or telemetry terms. Internal helpers may use technical terminology, but the package identity must remain visibly `LiDAR 2D Mapping` in repository trees, imports, logs, tests, documentation, and UI diagnostics.
