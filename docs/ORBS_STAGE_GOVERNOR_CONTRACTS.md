# ORBS Stage Governor Contracts

These contracts are the authoritative boundary between Orb Weaver, guided
onboarding, and the read-only Orb Assistant integration. They do not grant the
ORB, frontend, or a language model transition authority.

## Locked contract identifiers

- `orb_weaver.orbs_stage_snapshot.v1`
- `orb_weaver.orbs_stage_action_request.v1`
- `orb_weaver.orbs_stage_action_result.v1`
- `orb_weaver.orbs_guest_session.v1`
- `orb_weaver.orbs_guest_merge_request.v1`
- `orb_weaver.orbs_guest_merge_result.v1`

The machine-readable JSON Schemas live under `vault_system/schemas/`. The
runtime validation models live in `backend/app/orbs_contracts.py`. Changes to a
locked v1 contract require a new schema version or an explicitly approved,
backward-compatible contract amendment.

## Authority rules

1. A stage snapshot is customer-, project-, build-order-, and version-bound.
2. Only actions in `allowed_actions` may be submitted.
3. Every allowed action declares confirmation, permitted inputs, verified
   destination, and idempotency requirements.
4. An action result always carries a fresh authoritative snapshot.
5. A guest session stores only approved, non-sensitive pre-account progress.
6. A guest session is not customer, project, entitlement, payment, or workflow
   authority.
7. Guest merge runs server-side as one deterministic, idempotent operation.
8. The merge creates or attaches the first project, writes the authoritative
   onboarding record, consumes the guest session, and returns a fresh snapshot.
9. Consumed, expired, cross-customer, mismatched, and sensitive guest data fail
   closed.
10. All contract records persist through the sole Vault-backed database.

## Guest merge flow

```text
guest session
→ authenticated customer validation
→ website project create/attach
→ authoritative onboarding record
→ guest session consumed
→ fresh Stage Governor snapshot
```

The original CTA destination is preserved as data. It does not authorize a
transition. The returned snapshot determines the next legal action—normally
`run_preflight` for a newly created project.

No frontend or Orb Assistant code may perform or infer this merge locally.

