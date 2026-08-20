# Extractable Install Notes

This folder can be reviewed or copied as a Website ORB package. It is not connected to the current site build.

Backend review:

```bash
python3 -m uvicorn backend.app:app --host 127.0.0.1 --port 8787
```

Frontend review:

- Import `frontend/src/WebsiteORB.tsx` into the host site's React shell.
- Provide `apiBase` if the backend is not served from the same origin.
- Keep `compiled_orb/site_world.json` generated before deployment.

DockStation review:

- Use `backend/dock_adapter/orb_desktop_mcp.py` only as an adapter boundary.
- Do not include Electron in the Website ORB runtime bundle.

