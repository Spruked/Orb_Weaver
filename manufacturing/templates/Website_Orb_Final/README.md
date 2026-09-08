# Website ORB Final

`Website_Orb_Final` is the cloneable golden deployment template used to manufacture a site-specific Website ORB. It is not a standalone customer website. Orb Weaver supplies fresh site intelligence, the template supplies the reusable runtime, and the resulting instance can be validated and packaged for deployment.

## Current Runtime Architecture

The active answer path is **canonical-Vault-first with TPC fallback for a knowledge miss**.

1. A visitor speaks or submits a message.
2. The Website ORB runtime attempts a fast deterministic vault resolution.
3. `QueryRouter` classifies the vault intent and extracts known catalog entities.
4. `VaultCoordinator` resolves through A Priori and A Posteriori namespaces injected beneath `runtime/vault_system/`.
5. A successful vault result returns immediately without invoking TPC.
6. A genuine vault knowledge miss falls through to the existing Website intent -> TPC -> doctrine-gate path. A missing, substituted, or invalid canonical Vault is a fail-closed package-integrity error and never falls through.
7. Pointer guidance remains governed by the pointer subsystem and live DOM verification. Knowledge resolution does not independently authorize pointing, clicking, or navigation.
8. Voice, motion, and pointer behavior remain runtime presentation/action layers around the resolved knowledge and verified site state.

Operational knowledge misses can use the existing governed runtime. Storage-root integrity failures cannot: they must stop rather than create or consult a second authority.

## ORB Vault System

The integrated vault package lives at:

`Orb_Vault_System/orb_vault_skg/`

Its runtime code is under:

`Orb_Vault_System/orb_vault_skg/vault/`

The source template retains legacy SKG fixture material for source maintenance,
but a manufactured package strips `Orb_Vault_System/orb_vault_skg/vaults/`.
The physical site-knowledge containers in an installed package are only under:

`runtime/vault_system/`

### A Priori Vault

`A_Priori_Vault` is the settled site-truth layer. Its current data contract includes:

- `catalog.json` - products/services, pricing, availability, SKUs/IDs, attributes, and specifications when available.
- `ontology.json` - structured site entities and relationships / SKG-oriented knowledge.
- `qa.json` - verified question/answer correspondences.
- `policies.json` - site and business policy knowledge.

The A Priori path is `runtime/vault_system/payload/apriori/` and is intended for fast deterministic resolution before heavier cognition.

### A Posteriori Vault

A Posteriori state lives at `runtime/vault_system/posteriori/orb_vault_skg/`. It captures successful interaction patterns as candidates and provides verification, reinforcement, promotion, contradiction handling, merging, and utility/validity-based pruning. A newly manufactured customer ORB begins with clean site-specific state rather than inheriting another customer's learned history.

## Site Payload

The reusable engine and the site-specific payload are deliberately separated.

Current compiled site artifacts live in `compiled_orb/`, including:

- `site_world.json`
- `pointer_plot_map.json`
- `runtime_language.json`
- `self_scan_summary.json`
- `tool_cache.json`
- `latest_context.json`

The A Priori vault files form the semantic knowledge portion of the site payload. `compiled_orb` forms the operating/site-world portion. Together they allow the ORB to connect what a visitor means, what is known about the site, and where verified targets exist on the site.

## Main Runtime Folders

- `backend/` - Website ORB backend, answer engine, TPC fallback, doctrine gate, runtime routing, pointer services, and DockStation adapter boundary.
- `frontend/` - embeddable Website ORB UI, visual/motion behavior, pointer runtime, and Dock bridge.
- `compiled_orb/` - resident site-world, pointer, runtime-language, tool-cache, and scan-derived payload data.
- `Orb_Vault_System/orb_vault_skg/` - deterministic SKG implementation code. It has no package-local durable store after manufacture.
- `tools/` - build-time compilation and package validation utilities.
- `tests/` - runtime/static validation tests.
- `architecture/` and `docs/` - architecture and deployment/reference material.
- `vendor/TPC_Triple_Predicate_Cubed/` - TPC runtime dependency used as the cognition fallback lane.

## Manufacturing Model

The intended production flow is:

```text
Orb Weaver full site scan
        |
        +--> Site World / routes / pointer targets
        +--> catalog extraction
        +--> ontology / SKG compilation
        +--> verified QA compilation
        +--> policy compilation
        |
        v
site-specific payload
        |
        v
clone Website_Orb_Final
        |
        +--> inject compiled_orb data
        +--> inject A Priori data into runtime/vault_system/payload/apriori
        +--> initialize clean A Posteriori state in runtime/vault_system/posteriori/orb_vault_skg
        |
        v
validate manufactured instance
        |
        v
package customer Website ORB
```

Orb Weaver is the manufacturer. `Website_Orb_Final` is the reusable golden template. The manufactured Website ORB is the site-specific deployment product.

## Pointer, Motion, and Voice Boundary

The knowledge vault does **not** directly control the pointer, motion system, or TTS engine.

- The vault determines what is known and returns structured resolution metadata.
- The pointer subsystem determines whether a corresponding target exists and is valid in the live DOM.
- The doctrine/action layer determines what actions are permitted and whether confirmation is required.
- The motion layer determines ORB movement/attention behavior.
- The voice layer speaks the selected response.

This separation preserves deterministic knowledge retrieval without bypassing pointer verification or Website ORB action doctrine.

## Current Development Status

The vault-first answer path is present in `backend/cognition/answer_engine.py`: it loads the integrated SKG code, passes explicit canonical paths from `backend/storage.py` to `QueryRouter` + `VaultCoordinator`, and retains the existing TPC path only for a valid knowledge miss. SKG resolution provenance is appended under `runtime/vault_system/audit/glyph_trace/`.

The remaining manufacturing work is primarily on the Orb Weaver side. Before the next authoritative full-site rescan, Orb Weaver must be able to generate and inject the new site payload contracts, including catalog data and the required A Priori knowledge artifacts, and preserve semantic correspondence to routes/pointer targets where applicable.

The next end-to-end acceptance target is a fresh full Orb Weaver scan, including its Marketplace catalog, followed by manufacture of a clean Website ORB instance and validation of direct A Priori answers, voice delivery, verified pointer guidance, fallback behavior, and A Posteriori learning.

## Development Principle

Do not customize the golden template for an individual customer. Site-specific knowledge belongs in the generated payload. Changes to reusable runtime behavior belong in the template. Orb Weaver should clone the template, inject verified site data, validate the resulting instance, and then package it.
