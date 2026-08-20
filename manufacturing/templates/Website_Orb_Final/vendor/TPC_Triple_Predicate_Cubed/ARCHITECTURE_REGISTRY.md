# TPC Architecture Registry

Single source of truth for module status, entrypoints, and integration tiers.

---

## Runtime Entrypoint

```
api/main.py
  └─ imports TPCSystem from Integration.py
       └─ imports tpc_cubed, acp_synthesis
```

---

## Core Pipeline Modules

### EGF_RUNTIME
```
file:    tpc_cubed.py → class EGF
status:  active production
role:    Stage 6 — certainty-gravity retrieval over GeometricGlyph vault entries
used by: Integration.py (self.egf = EGF(self.hlsf))
         tpc_system_orchestrator.py (same)
notes:   Inverse-square gravity law, no external deps, ~10 LOC hot path
```

### EGF_RESEARCH
```
file:    Epistemic_Gravity_Field/space_field.py → class SpaceFieldCognition
status:  research validated
role:    Full 32³ PyTorch tensor physics engine — radial temperature gradient,
         TTL renewal, diffusion channels, coherence states
used by: Epistemic_Gravity_Field tests only (CI-covered)
future:  Optional deep retrieval mode — EGF(mode="deep") delegates here
         when benchmarks justify the compute cost
```

### EGF_TESTS
```
file:    Epistemic_Gravity_Field/{stress_test,perturb_test,distribution_shift_test}.py
status:  active CI
ci:      .github/workflows/ci.yml — runs all three on every push
```

---

## Orchestration

### INTEGRATION (canonical runtime)
```
file:    Integration.py → class TPCSystem
status:  active production — canonical runtime orchestrator
role:    10-stage pipeline: ACP → HLSF → DepthRecursion → MultiBeam →
         PhaseCoherence → EGF → VaultSystem → ECM → TribunalSynthesizer → Output
used by: api/main.py (primary import)
```

### ORCHESTRATOR (retired — shim only)
```
file:    tpc_system_orchestrator.py
status:  RETIRED — re-exports TPCSystem from Integration.py for backwards compat
role:    Do not add features here; extend Integration.py instead
```

---

## Input / Synthesis

### ACP
```
file:    acp_synthesis.py → class ACP
status:  active production
role:    Stage 1 — synthesizes raw input into GeometricGlyph
used by: Integration.py, tpc_system_orchestrator.py
policy:  real-runtime only for audio path (AdaptiveCochlearProcessor required);
         no synthetic FFT fallback in production wiring
```

### VAULT_SYSTEM
```
file:    acp_synthesis.py → class VaultSystem
status:  active production
role:    A priori + a posteriori vault storage and retrieval
used by: Integration.py, tpc_system_orchestrator.py
```

### DRIFT_PING_CHAIN
```
file:    acp_synthesis.py → class DriftPingChain
status:  active production
role:    Handshake verification across all pipeline stages
used by: Integration.py, tpc_system_orchestrator.py
```

---

## Cochlear / Audio Pipeline

### COCHLEAR_V3 (canonical audio processor)
```
file:    cochlear_processor_3.0/cochlear_processor_v3.py → class CochlearProcessorV3
status:  active production
role:    Real Whisper STT + perceptual filtering + correction loop + vault tracing
used by: acp_synthesis.py → process_audio()
```

### ADAPTIVE_PLASTICITY
```
file:    cochlear_processor_3.0/adaptive_plasticity.py → class AdaptivePlasticityEngine
status:  active — wired into CochlearProcessorV3.__init__
role:    Experience memory, frequency mastery, context mastery, filter tuning
         Improves transcription quality over time from accumulated corrections
used by: cochlear_processor_v3.py (self.plasticity_engine, called in process_audio_human_like)
future:  Persist experience_log to disk; make learning_rate configurable
```

### FAST_COCHLEAR
```
file:    cochlear_processor_3.0/cochlear_processor_v3.py → class FastCochlearProcessor
status:  partial — fast-path logic references self.plasticity_engine and self.asr_cpp
         which are not yet fully initialized (asr_cpp is stub)
role:    Optimized real-time variant with JIT filters and fast-path bypass
action:  Wire asr_cpp backend or fall back to whisper when unavailable
```

---

## Reasoning Cores

### TPCCUBED (main reasoning module)
```
file:    tpc_cubed.py
status:  active production
exports: GeometricGlyph, HLSF, EGF, DepthRecursion, MultiBeamRunner,
         PhaseCoherence, ECM, TribunalSynthesizer, PhilosopherCore,
         HumeBeam, KantBeam, LockeBeam, SpinozaBeam
invariants: 30 real semantic checks (ECM.check_invariants)
confidence: hard cap 0.95 (ECM.apply_confidence_cap)
```

### PHILOSOPHERS (seed data — deferred integration)
```
files:   philosophers/seed_{hume,kant,locke,spinoza}.json
         philosophers/base.py → HumeBeam, KantBeam, LockeBeam, SpinozaBeam
status:  citation layer — formally deferred
role:    Vault-backed beam implementations richer than inline tpc_cubed.py beams;
         load empirical parameters, performance metrics, and reasoning entries
         from JSON vault files
deferred because: live API uses tpc_cubed.py beams; wiring requires replacing
         MultiBeamRunner.beams and verifying PhilosopherVerdict↔Verdict interface
integration path (when ready):
  1. Replace tpc_cubed.MultiBeamRunner.beams with instances from philosophers/base.py
  2. Verify field compatibility between PhilosopherVerdict and tpc_cubed.Verdict
  3. Run demo_test.run_all_tests() — all 10 must still PASS
notes:   Do not delete. Do not import as runtime until integration path is complete.
```

---

## API & UI

### API
```
file:    api/main.py
status:  active production
port:    8003
routes:  POST /reason, POST /transcribe, POST /reason-audio, POST /speak,
         GET  /run-tests, GET /health
command: uvicorn api.main:app --host 0.0.0.0 --port 8003
policy:  audio routes fail closed (HTTP 503) if Cochlear correction is unavailable
```

### UI
```
file:    ui/src/
status:  active production
port:    5173 (default Vite)
stack:   React + Vite
command: npm run dev (from ui/)
key components: App.jsx (dashboard — verdict, philosopher beams, pipeline status,
                diagnostics log, expandable test cards)
proxy:   /api → http://localhost:8003
```

---

## Persistence

### RESULTS_VAULT
```
file:    results_vault.py → save_query_result, save_test_run
status:  active — wired into api/main.py
role:    Persistent evidence trail — JSON per query under results/
wired:   /reason  → save_query_result({**result, "_input_text": text})
         /run-tests → save_test_run(results_dict)
notes:   Vault I/O is best-effort; never raises into API response
```

### TPC_SUBSTRATE_GOVERNANCE
```
path:    R:\tpc_substrate\
status:  active production wiring
flow:    pending -> ADMIT|SUSPEND|REJECT -> vault/a_posteriori|suspended|quarantine
handoff: R:\orb_mesh\tpc_handoffs (symbolic link) -> R:\tpc_substrate\orb_handoffs
note:    This is distinct from Orb historical a_posteriori JSONL archives.
```

### VAULT_TRACES
```
dir:     vault_traces/ (created at runtime)
status:  active — written by cochlear_processor_v3.vault_write_trace()
role:    Per-audio correction trace, never blocks pipeline
```

---

## Tooling

### ARCHITECTURE_VISUALIZATION
```
file:    tools/visualization/tpc_architecture_visualization.py  (canonical)
         tpc_architecture_visualization.py                      (root shim → delegates above)
status:  tooling / documentation asset — not a runtime module
role:    Matplotlib diagram of full TPC architecture for demos and onboarding
usage:   python tools/visualization/tpc_architecture_visualization.py [--output path.png]
         Writes to outputs/TPC_Architecture_Visualization.png by default
```

### DEMO_TEST
```
file:    demo_test.py → run_all_tests()
status:  active — 10 tests, all PASS
used by: api/main.py GET /run-tests endpoint
```

---

## EGF Mode Roadmap

```
EGF(mode="fast")   →  current: tpc_cubed.py::EGF — inverse-square, no deps
EGF(mode="deep")   →  future:  delegates to SpaceFieldCognition (PyTorch 32³ cube)
                       trigger: only when latency budget allows
                       gate:    benchmark must show meaningful retrieval improvement
```

**Rule: do not replace fast mode with deep mode. Add deep as opt-in.**
