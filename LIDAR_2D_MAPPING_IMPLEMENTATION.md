# Spatial Intelligence 2D Mapping Implementation — Canonical Package Manifest

**Canonical product name:** Spatial Intelligence 2D Mapping / Coordinate Cache  
**Status:** Restored from the August 4, 2026 implementation artifact  
**Canonical client package:** `backend/motion_runtime/client/spatial_intelligence/`  
**Canonical server adapter:** `backend/motion_runtime/server/adapters/`

This manifest exists specifically so the implementation cannot disappear behind generic names such as pointer map, geometry, coordinate cache, telemetry, spatial runtime, SLAM, or DOM validation.

## Package files

```text
backend/motion_runtime/client/spatial_intelligence/
├── index.ts
├── SpatialIntelligence.types.ts
├── SpatialIntelligence.state.ts
├── SpatialCoordinateCache.ts
├── SpatialTelemetry.state.ts
├── SpatialTelemetryClient.ts
└── useSpatialIntelligence.ts

backend/motion_runtime/server/adapters/
└── spatial_intelligence_telemetry.py
```

## What it is

The Website ORB's Spatial Intelligence layer resolves pre-mapped Pointer Plot identities into live two-dimensional website geometry. It performs a batched DOM sweep, stores document/world-frame coordinates, converts them to viewport/camera-frame coordinates, monitors layout drift, and provides an optional bidirectional telemetry lane.

## What it is not

- It is not the old Python `EpistemicGravityField2D` movement field.
- It is not the Pointer Plot Map itself.
- It is not OCR.
- It is not authority to click or navigate.

The Pointer Plot Map owns target identity and permitted actions. Spatial Intelligence owns geometry acceleration and drift detection. The runtime must still perform final live DOM/accessibility verification before Point, Ping, navigation, or action.

## Naming rule

The phrase **Spatial Intelligence 2D Mapping** must remain visible in:

- directory names;
- public classes and hooks;
- logs and diagnostics;
- architecture documentation;
- tests and CI labels;
- future owner/admin status displays.

Do not replace this identity with a generic package name.

## Provenance

Recovered from the implementation artifact created August 4, 2026, which defined:

- coordinate cache state and implementation;
- telemetry client state and implementation;
- shared telemetry types;
- a FastAPI WebSocket adapter;
- a client integration hook.

The new names use an explicit `SpatialIntelligence` prefix throughout to prevent another loss through ambiguous naming.
