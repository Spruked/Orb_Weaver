# ISS Timestamp System

Orb Weaver uses the Interplanetary Stardate Syncrometer (ISS) as the
authoritative ordering clock for persisted Vault events, glyph traces, SKG
provenance, lifecycle evidence, governance artifacts, inference telemetry, and
manufactured Website ORB runtime audits.

The canonical ordering value is `iss_time_ns`. Every stamped record also
retains the complete envelope:

- Epoch nanoseconds
- UTC/ISO standard timestamp
- Julian timestamp
- ISS timestamp and Stardate
- local display time
- reference frame and clock ID
- proper-time, mission-elapsed, uncertainty, and relativistic-correction fields
- anchor hash and timestamp schema

Legacy `timestamp`, `recorded_at`, `created_at`, and `updated_at` fields remain
for compatibility. They are display/compatibility fields; `iss_time_ns` is the
ordering value.

The source module lives permanently at:

`vault_system/Interplanetary_Stardate_Syncrometer`

The manufactured Website ORB carries a Git-free runtime copy under:

`backend/vendor/interplanetary_stardate_syncrometer`

and uses `backend/timekeeping/iss.py` as its package-local adapter. The
manufactured Vault audit streams remain under the canonical installed
`runtime/vault_system/audit/glyph_trace` path.
