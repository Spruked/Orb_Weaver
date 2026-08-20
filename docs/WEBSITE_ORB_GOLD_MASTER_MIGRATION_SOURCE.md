# Website ORB Gold-Master Migration Source

Verified locally in the mounted Orb Weaver public website on 2026-08-20. This is the donor boundary for `Website_Orb_Final`; migrate these dependencies as one runtime contract.

## Proven Mounted Contract

The mounted ORB was exercised in Chromium with Kokoro-generated WAV speech injected through the browser's fake microphone device. The browser used the real `getUserMedia` and `MediaRecorder` path, automatic silence completion, Faster Whisper, the canonical resolver, articulation, Kokoro WAV playback, verified live-DOM guidance, and autonomous motion recovery.

The mounted proof covers:

- automatic awareness/listening without an ORB click and automatic rearming
- optional click/tap while moving, recording cancellation, playback interruption, and recovery
- exactly one Kokoro playback with no `speechSynthesis` fallback
- stillness only during audible playback and prompt autonomous movement afterward
- deterministic spoken `move_out_of_way` control with no model lane, brief acknowledgement, and a short local glide
- approximately `0.94` active opacity; five-minute inactivity rest in the upper-right at `0.55`; wake and movement recovery
- resolver-authoritative pointer identity, separate `may_point`/`may_click` policy, live-DOM verification, LiDAR coordinate evidence, visible MORB guidance, no real-cursor takeover, and no click
- temporary target loss, explicit guidance recovery, restored-target guidance, and normal motion afterward
- public route changes with one persistent ORB mount and no startup replay

Executable evidence:

- `frontend/scripts/orb-mounted-gold-master-proof.js`
- `frontend/scripts/orb-mounted-control-proof.js`
- `frontend/test-artifacts/orb-mounted-gold-master.json`
- `frontend/test-artifacts/orb-mounted-gold-master.png`
- `frontend/test-artifacts/orb-mounted-control-proof.json`
- `frontend/test-artifacts/orb-mounted-control-proof.png`

## Frontend Runtime

Mount and route persistence:

- `frontend/src/index.tsx` mounts `AutonomousOrb` outside the routed application.
- `frontend/src/App.tsx` and `frontend/src/components/PublicHeader.tsx` provide the public route lifecycle and verified header target.

Embodiment and behavior:

- `frontend/src/landing/AutonomousOrb.tsx` owns awareness, MediaRecorder/VAD, turn cancellation, playback, autonomous/rest/control motion, route state, pointer authority, MORB guidance, and mounted runtime evidence events.
- `frontend/src/landing/Orb.tsx` renders the ORB body and factory skin.
- `frontend/src/landing/Landing.css` supplies ORB, pointer bloom, and MORB presentation/motion states.
- `frontend/src/services/api.ts` defines the bootstrap, text, voice, TTS, pointer-map, and runtime response contracts.
- `frontend/src/orb/voiceLifecycle.ts` owns playback settlement, recovery ordering, and rearm rules.
- `frontend/src/orb/activeProjectContext.ts` carries project/domain/page-capsule context.
- `frontend/src/orb/targetValidation.ts` performs final live-DOM identity, visibility, route, and geometry validation.

Motion and guidance:

- `frontend/src/orb/robotics/movementController.ts`
- `frontend/src/orb/robotics/robotMovement.types.ts`
- `frontend/src/orb/robotics/webActuator.hal.ts`
- `frontend/src/orb/lidar_2d_mapping/Lidar2DMappingCoordinateCache.ts`
- `frontend/src/orb/lidar_2d_mapping/Lidar2DGuidanceMap.ts`
- `frontend/src/orb/lidar_2d_mapping/Lidar2DMapping.types.ts`
- `frontend/src/orb/lidar_2d_mapping/index.ts`

Required frontend packages are those declared by `frontend/package.json`, notably React, React Router, Framer Motion, and Lucide React. Playwright is the mounted acceptance driver.

## Backend Runtime

HTTP/runtime assembly:

- `backend/main.py`: `/api/orb/website-voice`, `/api/orb/website-text`, `/api/orb/pointer-map`, `/api/orb/tts`, cached WAV delivery, Faster Whisper call, pointer-map loading, and canonical result serialization.
- `backend/app/core/config.py`: `FASTER_WHISPER_STT_URL`, Kokoro endpoint/model/voice/format/payload mode, provider references, and vault root.
- `backend/app/core/storage.py`: canonical persistent Vault namespaces.

Canonical intelligence path:

- `backend/app/orb/turn_resolver.py`: control -> catalog -> A Priori -> verified A Posteriori -> Site World/TPC -> local provider -> external provider -> articulation.
- `backend/app/orb/catalog_repository.py`: deterministic SQLite commercial authority.
- `backend/app/orb/articulation.py`: final visitor-facing language shaping.
- `backend/app/orb/provider_router.py`: optional model escalation only after authoritative lanes.
- `backend/app/orb/site_learning.py` and `backend/app/orb/cco_runtime.py`: trace and eligible learning integration.

Pointer authority:

- `backend/app/orb/pointer_intent.py`
- `backend/app/orb/pointer_plot.py`
- `backend/app/orb/pointer_recovery.py`
- `backend/app/orb/execution_clamp.py`

The pointer record contract must preserve `target_id`, route, semantic locator, aliases, confidence class, pointer health, content fingerprint, and runtime policy. `may_point`, `may_click`, and `may_navigate` remain independent permissions. The browser must always revalidate the live element and must never infer click authority from point authority.

## Voice Services

- Faster Whisper: configurable `FASTER_WHISPER_STT_URL`; gold-master endpoint was `http://127.0.0.1:9000/stt`.
- Kokoro donor: `Orb_Assistant/user_dock_station/kokoro_openai_tts_server.py`.
- Kokoro launcher/reference configuration: `Orb_Assistant/user_dock_station/start_kokoro_tts.sh`.
- Gold-master Kokoro endpoint: `http://127.0.0.1:8880/speak`, model `kokoro`, voice `am_echo`, format `wav`, payload mode `kokoro-direct`.
- Backend TTS caching and single-flight behavior live in `backend/main.py`; cached audio is served from `/api/orb/tts/{audio_id}`.

Do not add browser `SpeechRecognition` or `speechSynthesis` as a production fallback. A voice turn has one recorder generation, one canonical result, one playback settlement, and one rearm decision.

## State Contract

State that must remain generation-owned:

- recording/turn sequence and `AbortController`
- active playback and playback settlement
- motion interruption sequence
- autonomous resume ownership
- control-motion ownership
- guidance sequence/controller ownership
- MORB lifecycle and target identity
- inactivity/rest transition

Session-scoped startup state uses `orbweaver-startup-greeting-played`, `orbweaver-landing-splash-played`, and `orbweaver-first-encounter-state`. Route changes update spatial/page context without remounting the ORB or replaying startup.

## Assets

- ORB skin: `frontend/public/orb-skins/tuxorb.png`
- Skin contract: `frontend/public/orb-skins/factory-orb-v1.manifest.json` and `frontend/public/orb-skins/registry.json`
- MORBs: `frontend/public/orb-morbs/purplemorb50px.png`, `morbblackred.ico`, and `camoorb65px.png`
- Guidance audio: `frontend/public/orb/voice/pointer-ping.mp3` and `travel-morb.mp3`
- Fixed/recovery phrase manifests: `frontend/public/orb/voice/fallback_responses.json`, `recovery_and_status.json`, and `latency_fillers.json`

## Manufactured Intelligence

The runtime payload source is the canonical output of:

- `manufacturing/website_orb/orchestrator.py`
- `manufacturing/website_orb/compile_vaults.py`
- `manufacturing/website_orb/schemas/`
- `backend/app/manufacturing/dock_station_builder.py`
- `backend/app/pack_generator/generator.py`

Required payload members are `site_config.json`, `catalog.db`, `site_world.json`, `pointers.json`, `pointer_correspondence.json`, `runtime_language.json`, `tool_cache.json`, A Priori ontology/QA/policies, payload and verification manifests, clean A Posteriori/customer-memory namespaces, and the single persistent Vault structure. Only a package that passes the orchestrator's delivery gate is a valid runtime source.

## Migration Rule

Do not migrate the standalone legacy `WebsiteFloatingOrb` or generated `orb-loader` runtime as a substitute for this donor. They are separate surfaces and do not prove the mounted awareness, motion, LiDAR/MORB, session, and recovery contract above. Extract from the proven files first, then rerun both mounted proof scripts against `Website_Orb_Final` before declaring parity.
