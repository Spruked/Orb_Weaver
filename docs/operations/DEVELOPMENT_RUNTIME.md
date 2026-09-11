# Isolated Development Runtime

## Authority

This is the current local development procedure. It does not build, restart,
or modify the reviewed Docker runtime.

| Surface | Address |
| --- | --- |
| Backend | `http://127.0.0.1:16666` |
| Frontend | `http://127.0.0.1:16667` |
| Reviewed Docker backend | `16500` |
| Reviewed Docker frontend | `16510` |

Earlier `16600`, `16610`, and `19667` pairings are historical only.

## Start and verify

From the repository root:

```bash
./scripts/start-dev-runtime.sh
curl -fsS http://127.0.0.1:16666/health
curl -fsS http://127.0.0.1:16667/
cd frontend && npm run verify:weaver-startup
```

The launcher supplies `REACT_APP_API_URL=http://127.0.0.1:16666`. It creates
disposable database, log, and PID state under a fresh `/tmp/orb-weaver-dev.*`
directory by default. Set `ORB_WEAVER_DEV_RUNTIME_ROOT` only when deliberately
preserving that development state between restarts.

Generated speech cache remains under `vault_system/development/runtime/tts_cache`
because the canonical-Vault guard enforces that boundary. It is runtime output,
not source material.

## Acceptance boundary

Passing local checks is development evidence. Gate approval additionally
requires the exact release candidate's full regression, browser/voice,
pointer, latency, deployment identity, and two-site evidence bundle described
by the September 11 launch command sheet.

