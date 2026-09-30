# ISS Module development log

## 2026-09-29 — Production hardening

- Added explicit `TAI_UTC_OFFSET_NS` handling to live and historical timestamp paths.
- Preserved nanosecond precision on the live `time.time_ns()` path and documented the microsecond limit of explicit `datetime` inputs.
- Promoted uncertainty, proper-time, relativistic-correction, mission, source, clock, and reference-frame values to explicit canonical timestamp parameters.
- Added per-event reference-frame overrides through the API.
- Removed Earth-market/session data from the ISS core time scale.
- Made Julian Date conversion accept an optional datetime and corrected derived display formatting to use the supplied instant.
- Added type annotations across the core conversion and canonical-envelope functions.

## 2026-09-29 — Relativistic time doctrine

- Documented the separation between authoritative ISS coordinate time and local clock proper time.
- Defined `proper_time_ns`, `relativistic_correction_ns`, `uncertainty_ns`, clock identity, source, and reference frame as physical annotations.
- Documented the first-order weak-field/low-velocity model and the requirement for state-vector and ephemeris inputs.
- Preserved the rule that ISS never rewrites `iss_time_ns` or invents a correction when physical inputs are unavailable.

## 2026-09-28 — Tauri desktop widget and supervision

- Added a compact Tauri 2/Rust widget under `widget/`.
- Set the window to 360×190, borderless, draggable, non-resizable, and always-on-top.
- Added live rendering of Epoch, Standard, Julian, ISS, raw nanoseconds, reference frame, and anchor hash.
- Added 250 ms polling against `http://127.0.0.1:8000/api/time`.
- Added Linux user-systemd installation scripts for start-after-login/reboot and indefinite `Restart=always` crash recovery.
- Added `PROJECT_TREE.txt` and `SITE_MAP.md` as maintained repository records.
- Corrected the API response collision so `epoch_label` and numeric `epoch` are separate fields.
- Vite frontend build passes.
- Native Rust compilation remains pending because this development environment does not have `cargo` or `rustc` installed.

## Authority

The widget is a read-only display client. `iss_time_ns`, derived from the fixed 2000-01-01 TAI epoch, remains the sole authoritative ordering value.

The True Mark Vault System is the authoritative storage and audit system. ISS provides its canonical timestamp envelope; the Vault retains ownership of the event, payload, hash chain, and sealed record.
