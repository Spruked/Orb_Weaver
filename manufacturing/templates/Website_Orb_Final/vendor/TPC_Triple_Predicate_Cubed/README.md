# TPC — Triple Predicate Cubed

A geometric symbolic reasoning engine. No token prediction — pure probabilistic state machines operating in 18-dimensional phasor space, governed by a formal ethics gate and four concurrent philosopher inference beams.

Every claim is evaluated as: **ADMIT · SUSPEND · REJECT**

---

## Architecture — Three Axes

```
Axis 1 — Input Trinity
  ACP   Adaptive Cochlear Processor   text/audio → 18D GeometricGlyph (golden-ratio phasor)
  HLSF  High-Level Semantic Field     vivacity-weighted graph of all prior glyphs
  EGF   Epistemic Gravity Field       certainty-as-gravity vault retrieval (inverse-square law)

Axis 2 — Reasoning Trinity
  Depth Recursion   K⁰ → K¹ → K²  (surface → abstract → deep synthesis)
  Four Beams        Hume · Kant · Locke · Spinoza  (parallel, 25% weight each)
  Phase Coherence   softmax alignment score across all four beam outputs

Axis 3 — Resolution Trinity
  A Priori Vault    immutable ethical certainties seeded at init
  A Posteriori Vault empirical learning store, accumulated from prior queries
  ECM               30 runtime invariants + hard 0.95 confidence cap + escalation gate
```

**Pipeline** (10 stages, every query): ACP → HLSF → Depth Recursion → 4 Beams → Phase Coherence → EGF → Vault → ECM → Tribunal Synthesis → Drift Ping Verification

---

## Quick Start

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8003
```

### 3. Start the UI (separate terminal)

```bash
cd ui && npm install && npm run dev
```

UI: http://localhost:5173  
API: http://localhost:8003

### 4. Wire into `R:\` substrate (production)

This repository now supports a substrate-native governance flow:

```
Swarm/Orb input -> POST /govern -> ADMIT|SUSPEND|REJECT -> substrate folders + orb handoff
```

Default substrate root (override with `TPC_SUBSTRATE_ROOT`):

```
R:\tpc_substrate
```

Important paths:

```
R:\tpc_substrate\pending
R:\tpc_substrate\vault\a_posteriori
R:\tpc_substrate\suspended
R:\tpc_substrate\quarantine
R:\tpc_substrate\orb_handoffs
R:\tpc_substrate\logs\tpc_governance.log
```

Start API in production mode (no reload):

```bat
start_tpc_api.bat
```

Create orb mesh handoff link:

```powershell
powershell -ExecutionPolicy Bypass -File tools\substrate\wire_orb_mesh_handoff.ps1
```

Register Windows scheduled tasks (startup + daily health):

```powershell
powershell -ExecutionPolicy Bypass -File tools\substrate\register_tpc_tasks.ps1
```

Daily health check script:

```powershell
R:\tpc_substrate\health_check.ps1
```

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/reason` | Text → full 10-stage pipeline → verdict |
| POST | `/govern` | Substrate governance route with verdict routing to ADMIT/SUSPEND/REJECT folders |
| POST | `/transcribe` | Audio file → Whisper STT → Cochlear correction |
| POST | `/reason-audio` | Audio file → STT → correction → full pipeline |
| POST | `/speak` | Text → Kokoro TTS → WAV stream |
| GET | `/run-tests` | Run 10 diagnostic tests, persist to results vault |
| GET | `/health` | Liveness + query count |

```bash
curl -X POST http://localhost:8003/reason \
  -H "Content-Type: application/json" \
  -d '{"text": "the sky is blue"}'
```

Response fields: `verdict`, `confidence`, `philosopher_results`, `synthesis`, `invariants`, `escalation`, `drift_ping`, `vault_status`, `phase_coherence`, `latency_ms`

---

## Real Runtime Policy (No Simulated Fallbacks)

- Audio correction routes require the real Cochlear 3.0 stack and return `503` if unavailable.
- ACP audio synthesis uses `AdaptiveCochlearProcessor` only; simulation fallback paths are disabled.
- Perceptual dropout injection is disabled by default for deterministic production audio behavior.
- ECM invariants execute concrete runtime checks and no longer use permissive placeholder passes.

---

## a_posteriori Storage Clarification

- TPC governance output target: `R:\tpc_substrate\vault\a_posteriori`
- Orb historical memory archive (separate system): `R:\Orb_Assistant_Desktop\...\a_posteriori\vault.jsonl`

The Orb archive can be very large. It is historical memory storage, not the active TPC routing directory.

---

## Project Structure

```
TPC_Triple_Predicate_Cubed/
│
├── Integration.py                  CANONICAL ORCHESTRATOR — 10-stage pipeline
├── tpc_cubed.py                    Core classes: GeometricGlyph, HLSF, EGF, ECM,
│                                   MultiBeamRunner, PhaseCoherence, TribunalSynthesizer
│                                   30 real semantic invariants, 0.95 confidence cap
├── acp_synthesis.py                ACP, VaultSystem, DriftPingChain
├── results_vault.py                Persistent evidence trail (results/ dir)
│
├── api/
│   └── main.py                     FastAPI app — port 8003
│
├── ui/
│   ├── src/
│   │   ├── App.jsx                 Dashboard: verdict, beams, pipeline, diagnostics log
│   │   └── Orb.jsx                 Floating canvas assistant (5 states, cursor-avoidance)
│   └── vite.config.js              Vite proxy → API on 8003
│
├── cochlear_processor_3.0/
│   ├── cochlear_processor_v3.py    CochlearProcessorV3 — Whisper STT + SKG correction
│   ├── adaptive_plasticity.py      AdaptivePlasticityEngine — learns from corrections
│   ├── skg_perceptual_filter.py    Speaker Knowledge Graph perceptual model
│   ├── correction_loop.py          Real-time word-level correction
│   └── hearing_skg.json            SKG state
│
├── Epistemic_Gravity_Field/
│   ├── space_field.py              SpaceFieldCognition — 32³ PyTorch tensor physics
│   │                               (research-validated; EGF_RUNTIME is in tpc_cubed.py)
│   ├── stress_test.py              CI: memory leaks, boundary conditions
│   ├── perturb_test.py             CI: attractor self-repair test
│   └── distribution_shift_test.py CI: resilience to input polarity shifts
│
├── philosophers/
│   ├── base.py                     Vault-backed beams — DEFERRED (see ARCHITECTURE_REGISTRY.md)
│   └── seed_{hume,kant,locke,spinoza}.json
│
├── tools/
│   └── visualization/
│       └── tpc_architecture_visualization.py   Architecture diagram generator
│
├── demo_test.py                    10 diagnostic tests (used by /run-tests endpoint)
├── ARCHITECTURE_REGISTRY.md        Single source of truth: module status + integration tiers
├── requirements.txt
└── .gitignore
```

---

## Running Tests

```bash
# Diagnostic suite (10 tests, all must PASS)
python -c "from demo_test import run_all_tests; r=run_all_tests(); print(sum(x['passed'] for x in r), '/ 10 PASS')"

# EGF research tests
pytest Epistemic_Gravity_Field/

# Generate architecture diagram
python tools/visualization/tpc_architecture_visualization.py
```

---

## Key Constants

| Constant | Value | Where |
|----------|-------|-------|
| HLSF dimensions | 18 | `tpc_cubed.py::GeometricGlyph` |
| Golden ratio φ | 1.6180339… | `tpc_cubed.py` (phasor damping) |
| Confidence cap | 0.95 | `tpc_cubed.py::ECM.apply_confidence_cap` |
| Invariant count | 30 | `tpc_cubed.py::ECM.check_invariants` |
| Philosopher beams | 4 × 25% | `tpc_cubed.py::MultiBeamRunner` |
| EGF gravity law | G·certainty / distance² | `tpc_cubed.py::EGF.compute_gravity` |

---

## Persistence

All queries and test runs are saved automatically:

```
results/
  index.json                        rolling index
  YYYY-MM-DD/query_NNNN.json        per-query audit trail
  tests/hard_tests_YYYYMMDD_HHMM.json
```

---

## Module Status

See [ARCHITECTURE_REGISTRY.md](ARCHITECTURE_REGISTRY.md) for the full status of every module (active production / research validated / deferred / retired).
| Edge-cutter trigger | 700 nodes | `core/geometric_primitives.py` |
| Edge-cutter release | 520 nodes | `core/geometric_primitives.py` |
| Confidence cap | 0.95 | `core/ecm.py` |
| ECM invariants | 30 | `core/ecm.py` |
| EGF voxel grid | 32³ | `Epistemic_Gravity_Field/space_field.py` |

## Dependencies

```
numpy scipy torch matplotlib librosa soundfile pytest
```

See `cochlear_processor_3.0/requirements.txt` for the full list.
