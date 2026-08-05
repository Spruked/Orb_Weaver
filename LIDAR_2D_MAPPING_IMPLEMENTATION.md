# LiDAR 2D Mapping Implementation — Canonical Package Manifest

**Canonical product name:** LiDAR 2D Mapping / Coordinate Cache  
**Status:** Restored from the August 4, 2026 implementation artifact  
**Canonical frontend package:** `frontend/src/orb/lidar_2d_mapping/`  
**Canonical backend telemetry module:** `backend/app/routers/lidar_2d_mapping_telemetry.py`

This manifest exists specifically so the implementation cannot disappear behind generic names such as pointer map, geometry, coordinate cache, telemetry, spatial runtime, SLAM, or DOM validation.

## Package files

```text
frontend/src/orb/lidar_2d_mapping/
├── README.md
├── index.ts
├── Lidar2DMapping.types.ts
├── Lidar2DMapping.state.ts
├── Lidar2DMappingCoordinateCache.ts
├── Lidar2DMappingTelemetry.state.ts
├── Lidar2DMappingTelemetryClient.ts
└── useLidar2DMapping.ts

backend/app/routers/
└── lidar_2d_mapping_telemetry.py
```

## What it is

The Website ORB's LiDAR 2D Mapping layer resolves pre-mapped Pointer Plot Map identities into live two-dimensional website geometry. It performs a batched DOM sweep, stores document/world-frame coordinates, converts them to viewport/camera-frame coordinates, monitors layout drift, and provides an optional bidirectional telemetry lane.

## What it is not

- It is not the old Python `EpistemicGravityField2D` movement field.
- It is not the Pointer Plot Map itself.
- It is not OCR.
- It is not authority to click or navigate.

The Pointer Plot Map owns target identity and permitted actions. LiDAR 2D Mapping owns geometry acceleration and drift detection. The runtime must still perform final live DOM/accessibility verification before Point, Ping, navigation, or action.

## Naming rule

The phrase **LiDAR 2D Mapping** must remain visible in:

- directory names;
- public classes and hooks;
- logs and diagnostics;
- architecture documentation;
- tests and CI labels;
- future owner/admin status displays.

Do not replace this identity with a generic package name.

## Provenance

Recovered from the implementation artifact created August 4, 2026, which defined:

- `LidarCoordinateCache.ts`;
- `LidarCoordinateCache.state.ts`;
- `OrbTelemetryClient.ts`;
- `OrbTelemetryClient.state.ts`;
- shared telemetry types;
- a FastAPI WebSocket bridge;
- a React integration hook.

The restored names add the explicit `Lidar2DMapping` prefix throughout to prevent another loss through ambiguous naming.
