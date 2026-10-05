# Pointer Escalation

This package is the canonical escalation authority for two related paths:

1. Pointer escalation when ordinary live resolution is insufficient.
2. Human escalation when a visitor explicitly requests or requires a person.

It is not obsolete, and it must not become a second competing runtime.
Its doctrine and recovery logic should be integrated into Orb Weaver's one
canonical pointer system alongside the live LiDAR, telemetry, and micro-MORB
implementation.

## Canonical control flow

Pointer escalation:

Pointer Plot authority
-> target intent and permissions
-> resolution and recovery chain
-> LiDAR coordinate cache
-> Prime ORB safe standoff
-> micro-MORB exact pointing
-> verified completion
-> micro-MORB dissolves

Human escalation:

visitor requests or requires a person
-> ORB stops handling that issue
-> temporary human-escalation chat box appears
-> visitor communicates with support
-> escalation ends or is cancelled
-> chat box disappears
-> ORB resumes only when policy permits

## Authoritative modules

`pointer_plot_schema.py`
Shared authoritative pointer-record contract.

`pointerPlotTypes.ts`
TypeScript mirror of the pointer-record contract.

`scan_extraction.py`
Produces Pointer Plot candidates during scanning.

`promotion.py`
Prevents single-session anomalies from overwriting the authoritative pointer map.
Recovered targets remain candidate corrections until repeated evidence and scan
verification promote them.

`pointerResolution.ts`
Owns the resolution hierarchy:
semantic locator
-> content fingerprint
-> accessibility identity
-> localized Tesseract verification

`pointerRuntime.ts`
Owns the pointer-runtime choreography and refusal rules.

`orbState.ts`
Separates primary ORB state, guidance state, and human-escalation case state.

`orbEscalation.ts`
Owns temporary human-support escalation, suppression of ORB competition on the
human-owned issue, and the temporary escalation UI lifecycle.

## Integration boundaries

The pointer system controls what may be pointed to.
LiDAR determines where the permitted target is now.
The choreography system determines how the Prime ORB approaches.
The micro-MORB performs the exact point.

This package should feed and constrain those layers. It should not be replaced
by them.

## Tesseract recovery

Tesseract belongs inside localized recovery, not as an open-ended site scan.
The intended fallback order remains:

semantic locator
-> content fingerprint
-> accessibility identity
-> localized Tesseract verification
-> safe refusal if still unresolved

Localized visual verification must stay scoped to the current page, section,
or viewport evidence chain.

## Persistence and vault ownership

Persistent pointer evidence must remain under the single deployment vault.
This package must never create an independent parallel store.

Authoritative pointer map:
stored in the deployment's canonical vault-backed ORB context.

Candidate corrections and recovery evidence:
stored as non-authoritative promotion inputs until repeated evidence and fresh
scan verification approve promotion.

Failure and stale-hit evidence:
stored in the same canonical vault-backed runtime evidence path.

## Dormant or incomplete pieces

These files contain real doctrine and real control-flow, but several integration
surfaces are intentionally incomplete and must remain governed:

- fingerprint resolution implementation is incomplete
- accessibility-role resolution implementation is incomplete
- localized Tesseract verification hook-up is incomplete
- scan extraction still expects a placeholder crawler shape
- stable locator generation is incomplete
- persistence hooks are incomplete
- human escalation classifier and vendor handoff hooks are incomplete

Installed code is not equivalent to permitted runtime authority.

## Guardrails

- Do not create a second parallel pointer runtime.
- Do not let visitor-session recovery overwrite the authoritative map directly.
- Do not let human escalation suppress the ORB globally; suppression remains
  scoped to the human-owned issue.
- Do not advertise dormant tools or unresolved recovery paths as fully enabled.
- Do not let LiDAR or telemetry bypass Pointer Plot authority and permissions.

## Package hygiene

`__pycache__/` and `*.py[cod]` should remain excluded from source control.
This package should only contain source doctrine, not compiled byproducts.
