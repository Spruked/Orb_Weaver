# Runtime Flow

## Build Time

`tools/compile_site_world.py` reads the existing website context and pointer plot map, then writes one resident SKG-style artifact:

`compiled_orb/site_world.json`

Every route record contains precompiled page purpose, summary, pointer target tiers, action boundaries, TPC output classes, and guiderails.

## Route Change

The frontend sends the current route to `/orb/route-context`. The backend normalizes the path and performs a dictionary lookup. No target ranking, context slicing, scan, or capsule assembly runs on route change.

## Visitor Question

The runtime path is intentionally small:

1. Intent classification against the loaded route and site-world records.
2. TPC facade reads the resident route record and produces a candidate answer/action class.
3. Doctrine gate checks the candidate against precompiled route boundaries.
4. Pointer map lookup returns candidate target IDs.
5. Frontend pointer resolver verifies the live DOM before any visual guidance.

