# Folder Structure

```text
Website_ORB/
  compiled_orb/
    site_world.json              # generated SKG/site-world artifact
    pointer_plot_map.json         # scan-time pointer records
    runtime_language.json         # ORB identity, tools, boundaries
    tool_cache.json               # preflight/runtime tool cache
    latest_context.json           # source scan intelligence
    self_scan_summary.json        # source scan summary
  backend/
    app.py                        # FastAPI lookup runtime
    config.py                     # package paths and settings
    models.py                     # request/response contracts
    runtime/                      # in-memory site world and route lookup
    cognition/                    # TPC/Doctrine lookup facade
    pointer/                      # pointer map index
    dock_adapter/                 # DockStation adapter only; no Electron
  frontend/
    src/
      WebsiteORB.tsx              # primary embeddable ORB shell
      OrbVisual.tsx               # copied site ORB visual
      WebsiteORB.css              # movement, status, pointer ping styles
      api.ts                      # runtime API client
      pointer/                    # copied pointer map runtime/resolver
      dock/                       # browser-to-dock adapter boundary
  tools/
    compile_site_world.py         # build-time SKG compiler
    validate_package.py           # package contract checks
  tests/
    test_route_lookup.py
    test_pointer_index.py
    test_guiderails.py
```

The package copies source material into a reviewable folder without moving existing repo files.

