# Orb Weaver Documentation

This directory is the central home for authored Orb Weaver documentation.

Start with [Documentation authority](DOCUMENT_AUTHORITY.md). It identifies
which documents are current release/operational authority and which are
historical or future-product context. Do not use a tree snapshot or a dated
checkpoint as current runtime instruction.

## Release and current operations

- [September 11 release-evidence command sheet](planning/Orb_Weaver_Web_Weaver_90_Day_Launch_Command_Sheet_RELEASE_EVIDENCE_REVISION_2026-09-11.docx)
- [Development log](DEV_LOG.md)
- [Isolated development runtime — backend 16666 / frontend 16667](operations/DEVELOPMENT_RUNTIME.md)
- [Reviewed Docker/public deployment guide — backend 16500 / frontend 16510](DEPLOYMENT_ORB_WEAVER_SPRUKED.md)

## Architecture

- [Target One landing-page tour — current scope and handoff](TARGET_ONE_LANDING_TOUR.md)
- [Immutable Vault Storage Law](../IMMUTABLE_VAULT_STORAGE_LAW.md)
- [Focused live-system map](../structure_tree.txt) — source and authority boundaries only; excludes generated runtime state

- [Factory ORB identity](architecture/FACTORY_ORB_IDENTITY.md)
- [Universal loader installation](architecture/ORB_LOADER_INSTALLATION.md)
- [ORB robotics architecture](architecture/ORB_Robotics_Architecture_Build_Summary.md)
- [Pointer Recovery doctrine](architecture/POINTER_RECOVERY_DOCTRINE.md)
- [Visitor interaction doctrine](architecture/VISITOR_INTERACTION_DOCTRINE.md)
- [Marketplace architecture](ORB_MARKETPLACE_ARCHITECTURE.md)
- [Pointer runtime model](ORB_POINTER_RUNTIME_MODEL.md)
- [Intelligence graph specification](ORB_WEAVER_INTELLIGENCE_GRAPH_SPEC.md)
- [V1 transactional doctrine](ORB_WEAVER_V1_TRANSACTIONAL_DOCTRINE.md)
- [Standard Website ORB blueprint](STANDARD_WEBSITE_ORB_BLUEPRINT.md)
- [Website ORB commercial readiness](WEBSITE_ORB_COMMERCIAL_READINESS.md) — historical snapshot
- [Website Dock Station download strategy](WEBSITE_DOCK_STATION_DOWNLOAD_STRATEGY.md) — future productization

## Voice

- [Voice runtime replication report](ORB_VOICE_RUNTIME_REPLICATION_REPORT.md)
- [Voice setup pattern](ORB_VOICE_SETUP_PATTERN.md)

## Operations

- [Pack contract](PACK_CONTRACT_V0_1.md)
- [Intelligence preservation](INTELLIGENCE_PRESERVATION.md)
- [Failure inventory](ORB_WEAVER_FAILURE_INVENTORY.md)
- [Tool wiring and validation](TOOLS_WIRING.md)

## Planning and handoffs

- [Product-plan handoff](handoffs/HANDOFF_PRODUCT_PLAN.md)
- [Brand World handoff](handoffs/HANDOFF_BRAND_WORLD.md)
- [Live route and voice handoff](handoffs/ORB_WEAVER_HANDOFF_LIVE_ORB_ROUTE_AND_VOICE.md)
- [Target One and manufactured-Vault marker handoff](handoffs/HANDOFF_2026-09-08_TARGET_ONE_VAULT_MARKER.md)
- [Website ORB CCO and learning-loop handoff](handoffs/HANDOFF_2026-07-30_WEBSITE_ORB_CCO_LEARNING.md)
- [Product-plan development notes](planning/DEV_NOTES_PRODUCT_PLAN.md)
- [Feature board](planning/Orb_Weaver_feature_board_v2.md)
- [Engineering plan](planning/engineering-plan.md)

## Reference snapshots and history

Generated trees, source manifests, and historical architecture references live in [`reference/`](reference/). They are documentation snapshots, not runtime path authorities. Archive/move historical material only with link migration; it remains valuable provenance but cannot override the release command sheet, doctrine, contracts, or current operations.

Operational files remain beside the components that consume them. This includes the root `README.md`, package-level READMEs, `backend/requirements.txt`, `frontend/public/robots.txt`, and all governed records under `vault_system/`.
