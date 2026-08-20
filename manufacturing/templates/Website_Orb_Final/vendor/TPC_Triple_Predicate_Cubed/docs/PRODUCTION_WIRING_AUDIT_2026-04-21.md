# TPC Production Wiring Audit (2026-04-21)

## Scope
- Local-only audit on R: (no GitHub operations)
- Wiring surfaces: `TPC_Triple_Predicate_Cubed`, `tpc_substrate`, `orb_mesh`
- Excluded heavy historical vault payload traversal from Orb memory archives

## Verified Wiring
- Substrate root present: `R:\tpc_substrate`
- Orb handoff link present: `R:\orb_mesh\tpc_handoffs` -> `R:\tpc_substrate\orb_handoffs`
- Governance manifests present:
  - `R:\tpc_substrate\manifests\tpc_paths.json`
  - `R:\tpc_substrate\manifests\tpc_substrate_manifest.json`
- Health script present: `R:\tpc_substrate\health_check.ps1`

## Runtime Hardening Applied
1. Removed simulated audio fallback in ACP
- File: `acp_synthesis.py`
- Change: `ACP.process_audio()` now requires `AdaptiveCochlearProcessor` path and no longer falls back to synthetic FFT banding.

2. Enforced real cochlear dependency in API audio routes
- File: `api/main.py`
- Change: `_run_cochlear_correction()` no longer degrades silently to raw transcript.
- Behavior: `/transcribe` and `/reason-audio` return HTTP 503 when cochlear correction stack is unavailable.

3. Replaced permissive placeholder invariants with concrete checks
- File: `core/ecm.py`
- Change: placeholder pass-through checks replaced with concrete runtime validation predicates across ethical, geometric, consistency, operational, and safety groups.

4. Disabled random perceptual dropout in production path
- File: `cochlear_processor_3.0/perceptual_filter.py`
- Change: dropout stage is now optional and disabled by default (`enable_dropout=False`, `dropout_rate=0.0`) for deterministic real-runtime behavior.

## a_posteriori Clarification
- Active TPC governed target: `R:\tpc_substrate\vault\a_posteriori`
- Large Orb historical memory stores are separate archives:
  - `R:\Orb_Assistant_Desktop\CALI_System\memory\a_posteriori\vault.jsonl`
  - `R:\Orb_Assistant_Desktop\system\CALI_System\memory\a_posteriori\vault.jsonl`

## Notes
- Test/demo artifacts remain under test/research modules and are not part of live substrate wiring.
- Follow-up can include pruning demo files from non-runtime folders if desired, but this audit focused on runtime and wiring correctness.
