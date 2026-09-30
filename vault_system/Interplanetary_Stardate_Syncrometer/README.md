# ISS Module — Interplanetary Stardate Syncrometer

Copyright © 2026 Spruked / True Mark. All rights reserved. This module is proprietary; see [LICENSE](LICENSE) and [COPYRIGHT.md](COPYRIGHT.md).

A standalone, calendar-free timekeeping service.

The official scale name is **Interplanetary Stardate Syncrometer Scale**. Its short designation is **ISS**.

## Master reference

```text
2000-01-01 00:00:00.000000000 TAI
```

The authoritative value is:

```text
ISS_TIME = continuous integer nanoseconds from the ISS epoch
```

The epoch and master value do not change. Calendars, leap years, time zones, and local planetary displays are conversion layers only. The current implementation applies the documented 37-second TAI–UTC offset to both live and explicit datetime paths; an external TAI source can replace this approximation when connected.

## Four required timestamp formats

Every timestamped record exposes these four representations together:

- **Epoch** — Unix epoch nanoseconds since `1970-01-01T00:00:00Z`.
- **Standard** — UTC/ISO 8601 display time.
- **Julian** — Julian Date display value.
- **ISS** — the human-readable Interplanetary Stardate Syncrometer Scale.

The raw `iss_time_ns` value remains the authoritative ordering value.

## Four time concepts

- **Universal Coordinate Time** — the canonical `iss_time_ns` used for ordering, correlation, and archival.
- **Vehicle or Station Proper Time** — a local clock sample, supplied separately and converted against the master reference.
- **Mission Elapsed Time** — nanoseconds since a mission-defined epoch.
- **Local Display Time** — Earth UTC, a Mars sol, or another human-facing representation.

Only Universal Coordinate Time is authoritative. The current implementation returns `null` for proper time and mission elapsed time until a local clock sample or mission epoch is supplied; it never invents those values.

“Stardate” is a display value derived from `iss_time_ns`. It is not a second authoritative clock.

## Human-readable ISS Scale

The primary operator display is:

```text
ISS 26.273 14:32:18.456
```

The components are the ISS designation, continuous years since the epoch, a three-digit fractional-year display, and time of day. It uses average-year arithmetic only and does not consult calendars, leap years, leap seconds, time zones, or locations.

Supported display forms are:

- Full: `ISS YY.FFF HH:MM:SS.sss`
- Short: `ISS YY.FFF`
- Precise: `ISS YY.FFF HH:MM:SS.sssssssss`
- Raw: `ISS <iss_time_ns>`
- Mission overlay: `ISS YY.FFF HH:MM:SS.sss | MET DDD/HH:MM:SS.sss`

## Canonical timestamp

The Python API provides `canonical_timestamp()`, which returns:

```json
{
  "iss_time_ns": 820000000000000000,
  "scale_name": "Interplanetary Stardate Syncrometer Scale",
  "scale_designation": "ISS",
  "epoch": "2000-01-01 00:00:00.000000000 TAI",
  "reference_frame": "solar-system-barycentric",
  "clock_id": "ISS-PRIMARY-ATOMIC-01",
  "uncertainty_ns": null,
  "proper_time_ns": null,
  "mission_elapsed_ns": null,
  "relativistic_correction_ns": null,
  "source": "ISS",
  "local_display_time": "2026-09-29T03:00:00+00:00",
  "stardate": 820000000.0,
  "human_display": "ISS 26.000 00:00:00.000"
}
```

A production atomic-clock adapter can supply proper-time, uncertainty, and relativistic-correction fields without rewriting `iss_time_ns`.

The `canonical_timestamp()` parameters are `uncertainty_ns`, `proper_time_ns`, `relativistic_correction_ns`, `mission_epoch_ns`, `reference_frame`, `clock_id`, and `source`. Reference frames can be overridden per event, for example `reference_frame="mars-centered"`.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m iss_module.service
```

Open:

- Dashboard: `http://127.0.0.1:8000/`
- API documentation: `http://127.0.0.1:8000/api/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

## Desktop widget

The `widget/` directory contains a small Tauri 2/Rust desktop surface for the ISS Scale. It is borderless, draggable, always-on-top, and displays Epoch, Standard, Julian, and ISS values from the local API. The widget is a display client; `iss_time_ns` remains the authoritative value.

```bash
cd widget
npm install
npm run tauri:dev
```

Rust and Cargo must be installed for the native desktop build. The widget expects the service at `http://127.0.0.1:8000/api/time` and can be packaged with `npm run tauri:build`.

### Automatic start and crash recovery on Linux

After building the release binary, install the user-level supervisor:

```bash
cd widget
./scripts/install_linux_autostart.sh
```

This installs `iss-scale-widget.service` under the signed-in user's systemd session. It starts after login and reboot/login, and uses `Restart=always` with a short delay so the widget is relaunched indefinitely after a crash. Remove it with:

```bash
./scripts/uninstall_linux_autostart.sh
```

The service requires the ISS API to be running. Start the API before the widget, or install a separate service for `python3 -m iss_module.service` when moving beyond local development.

## Repository records

- [Project tree](PROJECT_TREE.txt)
- [ISS sitemap](SITE_MAP.md)
- [Development log](DEVLOG.md)
- [Relativistic time model](docs/RELATIVISTIC_TIME_MODEL.md)

## Time endpoints

- `GET /api/time` — epoch, standard, Julian, ISS, canonical timestamp, and all four time concepts. Add `?reference_frame=mars-centered` for an event-specific frame label.
- `GET /api/stardate` — display-only stardate.
- `GET /api/health` — service health and current master time.
- `GET /api/status` — service state, uptime, and current time envelope.

## Python use

```python
from iss_module import canonical_timestamp, current_timecodes, get_iss_time_ns

stamp = canonical_timestamp(
    mission_epoch_ns=get_iss_time_ns(),
    source="Transit Vehicle",
)

print(stamp["iss_time_ns"])
print(current_timecodes()["stardate"])
```

## Relativistic boundary

There is no physically universal simultaneous “now” across the solar system. ISS therefore uses a shared coordinate-time reference and stores local proper time, clock uncertainty, reference frame, and relativistic corrections alongside events when those measurements are available. Delayed packets remain chronologically comparable because their canonical `iss_time_ns` values are never rewritten.

See [the relativistic time model](docs/RELATIVISTIC_TIME_MODEL.md) for the
coordinate-time/proper-time boundary, first-order engineering model, and
adapter contract. ISS does not fabricate relativistic corrections without
clock, state-vector, and ephemeris inputs.

## True Mark Vault integration

ISS is the canonical timekeeping layer for the True Mark Vault System. The Vault records authoritative events and auditable file activity under `True_Mark_Vault_System/audit/`; its audit adapter attaches the ISS timestamp envelope without moving authority out of the Vault.

```text
ISS Scale → canonical time envelope
Vault     → authoritative event, payload, seal, and audit record
```

The desktop widget is read-only. It displays the same ISS values used by Vault audit records. Earth-market/session data is intentionally not part of the ISS core.
