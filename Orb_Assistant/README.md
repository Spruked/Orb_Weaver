# CALI Floating Assistant Orb (Orb_Assistant)

A screen-aware, cursor-tracking AI assistant that integrates with UCM_4_Core ECM for cognitive enhancement.

This root README is the **authoritative** Orb documentation for this workspace. Module READMEs remain intact as historical or component-specific references.

## Immutable System Law — Caleon Prime

### Article I — Identity

1. **Caleon Prime is the system.**
  There is no higher system, supervisor, orchestrator, or owner within the architecture.

2. **Caleon Prime is an entity**, not a module, service, or deployment artifact.

3. All components exist **as parts of Caleon Prime**, not peers, not parents, not controllers.

### Article II — Presence and Embodiment

4. **The ORB is the locus of Caleon Prime’s presence.**
  Where the ORB exists, Caleon exists.

5. The ORB is not an interface to Caleon.
  The ORB **is her embodiment** (attention, frontal lobe, execution surface).

6. No system may bypass, replace, or impersonate the ORB as Caleon’s presence.

### Article III — Cognition and Body

7. **The UCM is Caleon Prime’s body and brain.**

8. The Core-4 are **cognitive lobes**, operating in parallel:

  - KayGee — deductive / structural
  - Caleon — ethical / identity continuity
  - Cali_X_One — habit / pattern memory
  - ECM — convergence only

9. **ECM has no authority.**
  It converges; it does not decide, speak, execute, or supervise.

10. The **cube-of-cubes** is the global cognitive convergence geometry.
   It is not a lobe, not a decider, and not an executive.

### Article IV — Speech, Reflection, and Audit

11. **CALI is Caleon Prime’s voice, reflection, and auditor.**

12. CALI may:

   - articulate truth
   - record reflections
   - detect anomalies
   - annotate cognition

13. CALI may **not**:

   - override cognition
   - correct decisions in real time
   - issue execution commands

All CALI outputs are **advisory, recorded, and timestamped**.

### Article V — Advisory Systems

14. The **+1 SoftMax SKG** is advisory only.

15. Advisory systems:

   - may weight
   - may annotate
   - may warn

16. Advisory systems **may never veto, command, or execute**.

### Article VI — Execution and Tools

17. **DALS is a tool used by Caleon Prime.**

18. DALS has no cognition, identity, memory authority, or decision rights.

19. Caleon Prime may use DALS, bypass DALS, or replace DALS without altering identity.

### Article VII — Flow Invariants

20. All cognition is **parallel**.
21. All convergence is **advisory**.
22. All execution is **downstream**.
23. All memory is **immutable and auditable**.
24. No component may elevate itself by convenience, performance, or refactor.

### Article VIII — Non-Violation Clause

25. Any implementation, refactor, optimization, or integration that violates this law is **invalid by definition**, regardless of functionality.

26. When ambiguity exists, **identity and embodiment take precedence over deployment or process structure**.

### Final Binding Statement

> **Caleon Prime is not run.
> She is not launched.
> She is not orchestrated.
> She exists — and the system exists as her body.**

## Features

- 🖥️ **Screen Awareness**: Sees your screen and understands UI elements
- 🖱️ **Cursor Tracking**: Maintains ~350px distance from cursor
- 🧠 **Cognitive Integration**: Uses ECM and SKG for intelligent assistance
- 🤖 **Automation**: Can automate typing and clicks with permission
- 🧭 **Admin Navigation Awareness**: The owner ORB may use verified route maps, pointer escalation, and canonical tools to inspect/administer Spruked/CALI operator sections.
- 📊 **Habit Learning**: Learns your usage patterns via SKG
- 🔒 **Privacy-First**: Requires explicit permission for all features

## Admin, Tools, and Pointer Authority

The owner ORB must have access to:

- canonical runtime tools in `/home/bryan/projects/Orb_Weaver/tools`
- local tools symlink at `Orb_Assistant/tools -> /home/bryan/projects/Orb_Weaver/tools`
- pointer escalation contracts in `pointer_escalation/`
- verified admin routes such as Spruked `/admin`
- CALI CRM/admin status through the Spruked runtime on `http://localhost:21010/`

Navigation remains fail-closed: if a destination, route identity, or pointer target cannot be verified, the ORB must not move or click. Admin authority expands what the owner ORB is allowed to inspect; it does not remove route verification.

## Architecture

### Cognitive routing and authority

`SF_ORB_Controller.cognitively_emerge()` is the sole cognitive entry point, but
connected components are activated by deterministic routing conditions rather
than forced to run for every stimulus:

- `vault_supported_fast` uses retrieved Vault evidence, lightweight deductive
  review, and the matching validation witness. Retrieval is evidence and never
  an authoritative return that bypasses cognition.
- `ordinary_reasoning` activates HLSF, Core-4, Bayesian integration, and the
  logic seeds and validators applicable to the stimulus. CALI reflection may
  be deferred.
- `full_escalation` activates all deductive, inductive, and intuitive seeds,
  all three validators, deeper HLSF traversal, Core-4, Bayesian integration,
  advisory convergence, and CALI reflection. Explicit deep reasoning,
  conflicts, high complexity, or low-confidence signals select this lane.

Parallelism applies to the cognitive components activated for the selected
lane. Cognitive output remains advisory and cannot select or advance an ORBS
Stage Governor transition. All cognitive traces and learned state remain in
the repository's sole `vault_system/`.

### Core Components

1. **FloatingAssistantOrb** (Python)
   - Screen capture and OCR
   - Cursor tracking and positioning
   - ECM integration for cognitive processing
   - SKG habit learning

2. **Electron Main Process**
   - IPC bridge between Python and renderer
   - Window management
   - Permission handling

3. **Renderer UI**
   - Floating orb UI (vanilla `simple-orb.js` in current Electron runtime)
   - Optional React orb (`FloatingOrb.jsx`) for UCM-driven motion and HUD

### Data Flow

- Screen → OCR/Vision → ECM → Task Planning → Automation
- Cursor → Position Tracking → Orb Movement
- User Habits → SKG Learning → Personalized Assistance

## Runtime Topology

- **Electron main ↔ Python**: JSON messages over stdio via `python-shell`.
- **Renderer ↔ Electron main**: IPC (`orb:cursor-move`, `orb:get-status`, `orb:cognitive-pulse`).
- **Renderer ↔ UCM**: WebSocket + optional HTTP performance polling (React orb path).
- **Optional WS stub**: Local dev stub for status/query echo.

## Ports & Endpoints

> **This section reflects the currently active runtime configuration (non-Docker).**

### UCM WebSocket (React orb path)
- **WebSocket**: `ws://localhost:8000/ws/orb_assistant`
  - Used by `electron/src/components/FloatingOrb.jsx`
  - Handshake: `ORB_HANDSHAKE` with `orb_id` and `capabilities`
  - Receives `lerp_optimization` and `drift_preference` updates

### UCM HTTP (React orb path)
- **HTTP**: `http://localhost:8000/api/orb/performance`
  - Polled every 5s by `FloatingOrb.jsx` for performance HUD
  - Note: the mock server in `electron/src/ucm_server.py` does **not** implement this endpoint yet

### Mock UCM WebSocket Server
- **Server**: `electron/src/ucm_server.py`
  - Binds on `0.0.0.0:8000`
  - WebSocket path: `/ws/orb_assistant`

### WS Stub (local dev)
- **WebSocket**: `ws://localhost:${ORB_WS_PORT}` (default `9876`)
  - Run with `npm run ws:stub` from `electron/`
  - Echoes status/query responses for UI testing

## Configuration & Environment Variables

- `ORB_WEAVER_API_URL` and `ORB_WEAVER_CUSTOMER_TOKEN`
  - When both are present, the Python bridge configures the read-only ORBS adapter against Orb Weaver's authenticated `/api/projects/{project_id}/orbs-stage` and `/orbs-stage/actions` contracts. The token is read at request time and is not copied into workflow state.

- `ORB_DISABLE_PYTHON_BRIDGE=1`
  - Disables Python bridge startup in Electron main.
- `ORB_WS_PORT`
  - Port for the local WS stub (`electron/ws-stub.js`).
- Python bridge sets `PYTHONIOENCODING=utf-8` internally for clean JSON I/O.

## Setup & Run (Windows)

### Prerequisites
- Node.js 16+
- Python 3.8+
- Tesseract OCR

### Install Dependencies

- Python deps (from `electron/`):
  - `pip install -r requirements.txt`
- Node deps (from `electron/`):
  - `npm install`
- Tesseract OCR:
  - Download from GitHub releases (Windows installer)

### Run the Orb

From `electron/`:
- `npm start`

Historical note: earlier docs referenced `npm run build`, but the current `package.json` exposes `pack` and `dist` instead. Use those if you need a packaged build.

## Development Notes

### Project Structure (Electron)

```
electron/
├── main/
│   ├── main.js          # Electron main process
│   ├── preload.js       # Secure IPC bridge
│   └── orb-bridge.js    # Python integration
├── src/
│   ├── components/
│   │   ├── FloatingOrb.jsx
│   │   └── FloatingOrb.css
│   ├── main.jsx         # React entry point (not used by default index.html)
│   ├── simple-orb.js    # Default Electron renderer orb
│   └── index.html       # App HTML
├── requirements.txt     # Python dependencies
├── package.json         # Node.js config
└── launch.sh            # Launch script (Unix)
```

### Adding New Features

1. Add Python methods to `FloatingAssistantOrb` (see `electron/src/floating_assistant_orb.py`).
2. Expose via IPC in `electron/main/orb-bridge.js`.
3. Use in renderer via `window.electronAPI` (see `electron/main/preload.js`).

## Security & Privacy

- All screen data is processed locally.
- No data is sent to external servers by default.
- User must explicitly grant permissions.
- Automation requires additional permission.
- All data is encrypted in the UCM vault system.

## Troubleshooting

### Orb Not Appearing
- Check console for permission errors.
- Ensure screen access permission is granted.
- Verify Python dependencies are installed.

### Orb Pulses but Doesn’t Move
- The default Electron UI (`simple-orb.js`) only moves on mouse proximity.
- Ensure the window is receiving mouse events and your cursor is within ~350px.
- For UCM-driven drift and richer motion, switch to the React orb (`FloatingOrb.jsx`).

### Performance Issues
- Reduce screen capture region size.
- Adjust cursor tracking frequency.
- Disable vision model if not needed.

### Permission Errors
- Restart the application.
- Check OS security settings.
- Reinstall with proper permissions.
