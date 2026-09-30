# ISS Scale sitemap

This is the navigation and integration map for the standalone Interplanetary Stardate Syncrometer repository.

```text
ISS Module
├── Browser surface
│   ├── /                         Dashboard HTML
│   ├── /dashboard                Dashboard alias
│   └── /api/docs                 OpenAPI documentation
├── Time API
│   ├── /api/health               Liveness and current scale sample
│   ├── /api/status               Service state and uptime
│   ├── /api/time                 Epoch + Standard + Julian + ISS envelope
│   └── /api/stardate             Display-only stardate shortcut
├── Python module
│   ├── iss_module.core.utils     Canonical timestamp and conversion functions
│   ├── iss_module.core.ISS       Service heartbeat/status
│   └── iss_module.service        Uvicorn entry point
└── Desktop widget
    ├── widget/src/main.js         Polls /api/time every 250 ms
    ├── widget/src/styles.css      Small visual display
    ├── widget/src-tauri           Tauri 2/Rust native shell
    └── widget/scripts              Login start + indefinite crash restart
```

## Data path

```text
ISS service → GET /api/time → Tauri widget → Epoch / Standard / Julian / ISS display
       └── iss_time_ns remains the single authoritative ordering value
```

## Authority boundary

The widget never creates, edits, or reinterprets authoritative time. It renders the service response. The service derives display values from the immutable epoch and exposes the raw `iss_time_ns` for machine-to-machine and auditable records.

## Startup path

```text
User login/reboot → systemd --user → iss-scale-widget.service
                  → Tauri binary → local ISS API
Crash              → Restart=always → relaunch after 3 seconds
```
