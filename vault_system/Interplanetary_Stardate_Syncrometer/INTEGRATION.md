# Orb Weaver Integration

The Interplanetary Stardate Syncrometer is the canonical ordering clock for
Orb Weaver Vault events. Persisted audit and glyph records use `iss_time_ns`
for ordering and retain the complete timestamp envelope:

- Epoch nanoseconds
- UTC/ISO standard time
- Julian time
- ISS time and Stardate
- reference frame and clock ID
- proper-time, mission-elapsed, uncertainty, and relativistic-correction fields
- anchor hash

Legacy `created_at`, `updated_at`, `recorded_at`, and `timestamp` fields remain
for compatibility. They are display/compatibility fields, not the authoritative
ordering value.

The development repository may contain Git metadata for source control, but
the Syncrometer source is treated as a permanent repository component and the
manufactured Website ORB template carries a Git-free runtime copy.
