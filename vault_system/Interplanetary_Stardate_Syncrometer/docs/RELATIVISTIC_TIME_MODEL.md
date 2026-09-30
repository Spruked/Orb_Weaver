# ISS relativistic time model

The Interplanetary Stardate Syncrometer separates shared coordinate time from
local proper time. This is required because there is no physically universal
simultaneous “now” across the solar system.

## Coordinate time

`iss_time_ns` is the authoritative continuous nanosecond count from the ISS
epoch. It is used for ordering, correlation, archival records, and delayed
packet reconciliation. It is never rewritten to match a local clock.

For solar-system work, the default declared frame is
`solar-system-barycentric`. A record may override this with a more specific
frame such as `mars-centered`.

## Proper time and annotations

A local atomic clock measures proper time. Its relationship to coordinate time
is recorded as metadata rather than silently folded into the master value:

```text
iss_time_ns ≈ proper_time_ns + relativistic_correction_ns
```

The direction and sign convention must be declared by the clock adapter that
supplies the correction. ISS does not invent a correction when position,
velocity, gravitational potential, and clock measurements are unavailable.

Canonical records therefore accept:

- `proper_time_ns` — the local clock reading;
- `relativistic_correction_ns` — the adapter-computed offset;
- `uncertainty_ns` — confidence/error bound;
- `clock_id` and `source` — clock and event provenance;
- `reference_frame` — the coordinate frame used for the event.

## First-order engineering model

For a low-velocity, weak-field approximation:

```text
dτ/dt ≈ 1 + Φ/c² − v²/(2c²)
```

where `τ` is proper time, `t` is coordinate time, `Φ` is gravitational
potential, `v` is velocity relative to the selected frame, and `c` is the
speed of light. A production adapter may compute the correction from a state
vector and ephemerides. High-precision applications require the appropriate
post-Newtonian transformations and authoritative ephemeris data.

## Operational rule

ISS stores the shared coordinate timestamp plus the local physical evidence.
Mars, Earth, a transit vehicle, and a deep-space probe can therefore be
ordered on the same backbone without pretending their clocks share a local
“now”.
