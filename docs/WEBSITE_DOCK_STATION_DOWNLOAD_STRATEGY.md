# Website Dock Station Download Strategy

Date: 2026-08-01

## Live v2.1 Source

The local Dock Station v2.1 app currently running from Zed is outside this repo:

```text
Windows path: C:\Users\bryan\Desktop\Dock-Station\orb-dock-station_v2.1
WSL path:     /mnt/c/Users/bryan/Desktop/Dock-Station/orb-dock-station_v2.1
Backend:      http://127.0.0.1:8000
Frontend:     http://localhost:5173
```

The v2.1 backend advertises:

```text
ORB Dock Station FastAPI backend v2.1
app version 2.1.0
```

Its current domain model is `OrbProfile` with draft/published lifecycle, speech settings, personality blend, model lanes, tools, appearance/motion, deployment targets, and Live Test sessions. This should be treated as the owner-control surface and template repo source, while Orb Weaver remains the authority for Website ORB evidence, compiled operating policy, single-vault package rules, CCO traces, and release/download generation.

## Decision

The Website ORB download should become a **Website Dock Station release repo bundle**, not only a vault data pack.

The bundle should contain the basic Website Dock Station runtime, a blank Website ORB template already mounted inside it, the compiled site data, and the published owner operating policy. The installed customer artifact should run as one repo with one storage authority and one Website ORB runtime contract.

The Premium DockStation and the Website Dock Station should not be forks of the ORB brain. They should share the same runtime contracts, schema names, policy compiler, loader bootstrap shape, movement/pointing rules, learning-loop files, and Live Test gates. Premium can add deeper adapters and desktop/local capabilities, but the Website ORB should continue to use the same published operating-policy shape so upgrades do not require re-teaching the ORB.

## Current State

The project already has the important pieces, but they are not assembled into a full downloadable repo yet.

- Dock Station policy contracts live in `backend/app/orb_dock.py`.
- Dock Station UI lives in `frontend/src/pages/OrbDockStation.tsx`.
- Runtime bootstrap exposes `operating_policy` through `/api/orb/bootstrap`.
- Website ORB text and voice paths include CCO tracing.
- Pack generation lives in `backend/app/pack_generator/generator.py`.
- Generated `.orbpack` files currently include a single `vault_system/` and clean-slate `website_orb_learning/` files.

The missing piece is the release assembly layer that turns those parts into a runnable Website Dock Station repo.

## v2.1 To Orb Weaver Contract Map

Dock Station v2.1 should not publish its raw `OrbProfile` directly to installed Website ORBs. It should export a draft or published owner profile that Orb Weaver compiles into the shared Website ORB operating policy.

```text
Dock Station v2.1 OrbProfile
  personality              -> behavior tone/persona directives
  speech                   -> greeting, listening, mute/sleep, voice posture
  intelligence.lanes       -> llm provider/model policy metadata
  tools                    -> permitted tool requests, still Stage Governor checked
  appearance               -> skin and motion preferences
  stage_directives         -> additional/situational guide rails
  deployment               -> channel/install target metadata

Orb Weaver compiled policy
  schema                   -> orb_weaver.website_orb_operating_policy.v1
  locked_doctrine          -> immutable ORB rules
  enforcement              -> verified routes/tools only
  source_evidence          -> Site World and approved tools
  public_runtime_policy    -> read-only runtime contract for Website ORB
```

This keeps the Premium DockStation and Website Dock Station consistent: v2.1 can have richer panels and local owner workflow, but the installed ORB still receives the same compiled runtime policy shape as Premium.

## Target Bundle Shape

```text
website-dock-station/
  README.md
  package.json
  dock.config.json
  orb-template/
    manifest.json
    runtime-policy.schema.json
    site-world.schema.json
    owner-settings.schema.json
    src/
    public/
  app/
    website-orb-runtime/
    orb-client/
    dock-station/
  public/
    orb-loader.js
    orb-skins/
    orb/voice/
  vault_system/
    vault-manifest.json
    clients/<domain>/
      current/scan_data.json
      website_orb_context/latest_context.json
      website_orb_learning/
        learning-loop-template.json
        posteriori/interactions.jsonl
        stump_ledger/stump-ledger.json
        promotion_queue/promotion-queue.json
        verified_cases.json
        apriori-promotion-template.json
  manifests/
    build-manifest.json
    live-test-report.json
    compiled-policy.json
```

The blank template belongs in the Website Dock Station repo under `orb-template/`. Orb Weaver should never mutate the template in place. It should copy the template into a build workspace, inject site data and owner settings, test the assembled ORB, then package the finished result.

## Build Flow

```text
Dock Station draft
-> compile Dock Station policy
-> require publishable policy
-> copy blank Website ORB template
-> inject Site World, scan data, owner settings, skin, voice manifests, and compiled policy
-> assemble Website Dock Station runtime repo
-> run Live Test against the assembled repo
-> write live-test-report.json
-> package as .orbpack or .zip
-> expose download
```

The existing `tpc-pack` endpoint should become a legacy-compatible wrapper around this flow. Internally, a new release builder should call the existing pack generator only for vault payloads, then add runtime files, template files, manifests, and Live Test evidence.

## Shared Runtime Contract

Website Dock Station and Premium DockStation must share these contracts:

- `orb_weaver.orb_dock_configuration.v1`
- `orb_weaver.website_orb_operating_policy.v1`
- `orb_weaver.loader_bootstrap.v1`
- `orb_weaver.single_vault.v1`
- `orb_weaver.cco_runtime_trace.v1`
- Website ORB answer states: `known`, `resolved`, `clarification_required`, `unknown`
- Pointer and movement behavior from the existing `orb-client` and target validation contracts
- Site-scoped learning files under `website_orb_learning/`

Premium may extend the contract by entitlement, but it should not rename or replace the Website ORB runtime policy. A Premium upgrade should mainly change entitlements, adapters, available tools, and service depth while preserving the ORB's learned site namespace and published owner policy.

## Live Test Gate

The release builder should block download unless Live Test passes.

Minimum Live Test checks:

- template bootstraps with the generated `site_id`, domain, loader URL, and runtime URL;
- `compiled-policy.json` validates against the current Dock policy schema;
- `/api/orb/bootstrap` returns the expected public operating policy;
- `/api/orb/website-text` returns a governed answer state and `cco_trace`;
- Factory Default skin loads, and selected skin falls back safely;
- `vault_system/` is the only storage authority;
- `website_orb_learning/` starts clean for the installed site;
- no owner notes, API keys, raw credentials, or unrelated customer data are packaged.

## Implementation Path

1. Add `backend/app/orb_release_builder/`.
2. Move the blank Website ORB template into a versioned repo path such as `templates/website-dock-station/basic-v2.1/`.
3. Add a release manifest schema with template version, runtime contract versions, site ID, domain, policy hash, generated files, and Live Test result.
4. Change `/api/projects/{project_id}/tpc-pack` to call the release builder and keep the current download URL shape.
5. Add tests that inspect the archive for runtime files, template files, compiled policy, clean learning files, single-vault compliance, and no secret leakage.
6. Add a Live Test runner that can execute against the assembled build workspace before packaging.

## Non-Goals For This Step

- Do not make broad self-serve customer install promises yet.
- Do not wire Premium-only desktop/MCP tools into the basic Website Dock Station.
- Do not create a second Dock Station policy schema for the Website ORB.
- Do not allow the ORB template to self-learn into Site World without owner-approved promotion.
