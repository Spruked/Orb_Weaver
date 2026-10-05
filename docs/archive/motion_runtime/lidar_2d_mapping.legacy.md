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

## Corner exclusion placement rule

Viewport corners are traversable path space, but they are not valid settled
space. Phase Zero rejects a candidate when the complete rendered footprint—the
ORB body, active caption, and LiDAR safety padding—overlaps any corner
exclusion zone. This applies to ambient stance, WAIT/PRESENT/Focus placement,
and target-adjacent guidance. It does not turn the corners into collision
obstacles: a transit curve or bounded recovery may pass through them when live
geometry requires it.

If every candidate in a live pass is rejected by this rule, the runtime fails
closed, records `corner_exclusion`, and waits for the next live map/search
cycle or reports a bounded guidance recovery. It never promotes a corner to a
fallback resting pose. The rejection telemetry includes whether the caption
was part of the evaluated footprint.

## Semantic map and explicit importance ranking

**Existing doctrine:** Pointer identities and live validation retain action
authority. The Stage Governor retains route authority. The coordinate cache
retains world/viewport conversion and drift checks.

**Verified current implementation fact before this change:** The guidance-map
type declared `free_space`, but its builder emitted every DOM element as an
obstacle and produced no free-space cells. Generic parent containers could
therefore appear to occupy their readable child whitespace.

**New reconciled LiDAR enhancement:** A scan assigns each Pointer observation
an integer `baseRank` from 1 to 5 and a `rankEvidence` list based on witnessed
page structure, topical terms, entities, workflow controls, and route class.
Manufacturing carries the rank into `site_skg.json`, `site_world.json`, and
`pointers.json`; approved site goals can raise matching destinations during
compilation. Rank is a sequence preference, never a Point/Ping grant.

At runtime, the current purpose produces a bounded `effectiveRank` in the
same 1–5 range; `baseRank` is retained unchanged. An unresolved or legacy
DOM observation receives an explicitly marked `runtime_dom_fallback` rank.
It must not be presented as a compiled scan rank. `purposePromotion` defaults
to 2; a nonmatching object drops one effective rank while a matching object
can rise by up to two, both clipped to 1–5. These are new implementation
parameters, not historical robotics constants.

The current map emits Obstacle, Free Surface, Waypoint, and Semantic Anchor
observations. Free Surface cells are generated only where the supplied
ORB+caption footprint and clearance fit within the viewport without
overlapping observed occupancy. `freeSpaceCellSize` adapts to viewport area
with an approximately 600-cell budget; the DOM and Pointer records remain
the evidence sources. OCR/vision results are not added to this map without
actual sensor output. Ambient and target-adjacent stance selection read these
map facts and record rank, clearance, purpose, travel, and score evidence.

## Naming protection

Do not rename this directory or its public classes to generic geometry, map, cache, locator, or telemetry terms. Internal helpers may use technical terminology, but the package identity must remain visibly `LiDAR 2D Mapping` in repository trees, imports, logs, tests, documentation, and UI diagnostics.
