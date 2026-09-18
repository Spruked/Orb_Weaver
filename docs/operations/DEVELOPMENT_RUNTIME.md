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

To inspect the configured local or remote llama.cpp lane without changing its
state, run from the repository root:

```bash
python3 scripts/verify_local_llm_runtime.py
```

When `LLAMACPP_BASE_URL` names a remote host, this check validates that remote
endpoint and does not require a GGUF file on the development machine.

The launcher supplies `REACT_APP_API_URL=http://127.0.0.1:16666`. It creates
disposable database, log, and PID state under a fresh `/tmp/orb-weaver-dev.*`
directory by default. Set `ORB_WEAVER_DEV_RUNTIME_ROOT` only when deliberately
preserving that development state between restarts.

Generated speech cache remains under `vault_system/development/runtime/tts_cache`
because the canonical-Vault guard enforces that boundary. It is runtime output,
not source material.

## Repeatable startup diagnosis

The following query controls exist only in a non-production frontend build:

```text
http://127.0.0.1:16667/?orbStartupReset=1&orbIntroVariant=am-echo&orbDevFullTour=1
```

- `orbStartupReset=1` clears only the current tab's startup/tour markers.
- `orbIntroVariant` accepts `am-echo`, `am-michael`, or `kokoro-host` and
  replays that selected intro for deterministic verification.
- `orbDevFullTour=1` lets an authenticated development session exercise the
  governed new-visitor tour after the intro. It changes only the frontend
  tour-eligibility decision: it does not sign a visitor out, change backend
  authorization, or persist account state.

Development console events are prefixed `[Weaver startup]` and are also
dispatched as `orbweaver:startup-trace`. In production builds the query
controls and trace emitter are disabled.

Run `npm run verify:weaver-startup` from `frontend/` to exercise all intro
variants, deliberate autoplay denial/recovery through Weaver's existing
speaker control, the authenticated override, and the normal authenticated
tour-skip path. Set `REQUIRE_FIRST_TOUR_SPEECH=1` only when the local cognition
gateway on `127.0.0.1:16520` is healthy; that mode fails unless the first
governed tour audio actually begins playback.

## Acceptance boundary

Passing local checks is development evidence. Gate approval additionally
requires the exact release candidate's full regression, browser/voice,
pointer, latency, deployment identity, and two-site evidence bundle described
by the September 11 launch command sheet.
