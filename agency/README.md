# Orb Weaver Agency Layer

This directory contains the shared agency contract imported from the Grok `glow-amber-trail-quartz` export and adapted to the real Orb Weaver runtime.

## Architecture

- RAL = kernel contract and cycle semantics.
- Weaver = website habitat adapter.
- Skin Studio = expressive body/costume layer.
- NATS or the in-process event bus = nerves.
- ROS = physical body adapter when present.
- Existing Orb Weaver Core-4 remains the authoritative cognition/tribunal implementation. This integration does not replace or redesign it.

## Canonical artifacts

- `AGENCY_CONTRACT.md` — shared WorldState / ActionProposal / CycleEnvelope boundary.
- `primitives.yaml` — canonical motion, speech, and expression vocabulary.

Runtime code lives under `backend/app/agency/` and exposes a read-only status surface through the existing ORB telemetry router. The owner dashboard consumes that status so contract presence, registry version, validation state, and active ORB telemetry connections are visible.

## Integration rule

Adapters consume authorized primitives; they do not invent authority. Website-specific code may implement DOM and ORB-compositor behavior, but it must preserve the canonical contract and primitive ids.

Source snapshot imported from `Spruked/glow-amber-trail-quartz` commit `e151c5640d933dc488dc8629b1c6a8f0e6d8fcb2`.
