# ORB Skin System — Scaffold v0.1

## Structure

```
orbskin/
├── shared/               # Types, validator, hash — imported by all targets
│   ├── types/
│   │   └── orbskin.types.ts
│   ├── validator/
│   │   └── orbskin.validator.ts
│   └── hash/
│       └── orbskin.hash.ts
│
├── renderer/             # ONE React skin renderer — runs in all three webviews
│   ├── OrbSkinRenderer.tsx
│   ├── useSkinAssets.ts
│   └── SkinAssetBundle.ts
│
├── loaders/              # Per-target loaders — unpack .orbskin, feed renderer
│   ├── electron/
│   │   └── skin.loader.electron.ts   (Node.js main process)
│   ├── tauri/
│   │   └── skin_loader.rs            (Rust core)
│   └── web/
│       └── skin_loader.py            (FastAPI)
│
├── packer/               # Tool to build .orbskin packages
│   └── pack.py
│
└── docs/
    └── ORB_SKIN_CONTRACT_v1.md
```

## How it flows

```
.orbskin file
     │
     ├── [Electron]  skin.loader.electron.ts  (Node, main process)
     ├── [Tauri]     skin_loader.rs           (Rust core)
     └── [Web ORB]   skin_loader.py           (FastAPI)
          │
          └── All produce → SkinAssetBundle
                                │
                                └── OrbSkinRenderer.tsx  (React — same in all three)
```

## Status

- [x] shared/types
- [x] shared/validator
- [x] shared/hash
- [x] renderer
- [x] loader/electron
- [x] loader/tauri
- [x] loader/web
- [x] packer
- [x] docs/contract

## Wiring — Electron

1. `npm install jszip` in your Electron main process package.
2. Copy `loaders/electron/skin.loader.electron.ts` into your main process source tree.
3. In your `main.ts`, after creating your `BrowserWindow`, call `registerSkinIpc(win)`.
4. Copy `loaders/electron/skin.preload.electron.ts` into your preload — or merge its
   `contextBridge.exposeInMainWorld` block into your existing preload file. Do not
   register a second preload.
5. In your React ORB root, wrap with `<SkinProvider>` from `renderer/useSkinAssets.ts`,
   then call `useElectronSkinBridge()` once near the top of your ORB component tree.
6. Drop `<OrbSkinRenderer />` wherever your ORB currently renders its body/visuals.

## Wiring — Tauri

1. `cargo add zip sha2 serde serde_json hex chrono` (chrono only if not already present).
2. Copy `loaders/tauri/skin_loader.rs` into `src-tauri/src/`.
3. In `main.rs` / `lib.rs`, register the managed state and commands (see bottom
   comment block in `skin_loader.rs` for the exact builder snippet).
4. `npm install @tauri-apps/api` on the frontend side if not already present.
5. Copy `loaders/tauri/skin.bridge.tauri.ts` into your React source tree.
6. Wrap your ORB root with `<SkinProvider>`, call `useTauriSkinBridge()` once.
7. Drop `<OrbSkinRenderer />` into your ORB visual tree — same component as Electron.

## Wiring — Web ORB (FastAPI + React)

1. `pip install fastapi python-multipart` (multipart needed for file upload).
2. Copy `loaders/web/skin_loader.py` into your FastAPI backend, include the router:
   `app.include_router(skin_router, prefix="/api")`
3. Set `ORB_SKIN_STORE` env var to a writable directory, or accept the `./data/skins` default.
4. Copy `loaders/web/skin.bridge.web.ts` into your React source tree.
5. Wrap your ORB root with `<SkinProvider>`, call `useWebSkinBridge()` — it returns
   `{ loadSkin, rollback, clearSkin }` for your upload UI to call.
6. Drop `<OrbSkinRenderer />` into your ORB visual tree — same component, third time.

## Known conflict points to resolve next

These were intentionally left loose. Resolve when you're ready to tighten:

1. **Electron asset URLs use `file://`** — works for local dev, but Electron's
   security model may block `file://` in the renderer depending on your
   `webSecurity` setting. Production path: register a custom protocol
   (`orbskin://`) the same way Tauri uses `asset://`.
2. **Tauri `convertFileSrc` requires asset protocol scope** — your
   `tauri.conf.json` needs the skin cache directory allow-listed under
   `app.security.assetProtocol.scope`, or `convertFileSrc` calls will be
   blocked at runtime.
3. **Publisher signature verification is stubbed** — `skin_loader.rs` and
   `skin_loader.py` both check `package_hash` but not `publisher_signature`
   cryptographically yet. The TS validator has `validateManifestWithSignature()`
   as a reference for the HMAC approach; Rust and Python need the equivalent
   before this goes anywhere near production or marketplace skins.
4. **No real publisher key registry yet** — `creator_id` is trusted as-given.
   Before launch this needs to resolve against an actual Weaver-side or
   True Mark Mint-side key store.
5. **GLB rendering is a stub** — `OrbBodyAsset` in the renderer just tags a div
   with `data-orb-body="glb"` and the source URL. Needs to be wired to whatever
   3D engine (Three.js, Babylon) the ORB body actually uses.
6. **Web ORB state is in-memory** — `_state` dict in `skin_loader.py` resets on
   server restart. Fine for scaffold/dev, needs SQLite or similar before
   multi-user or production use.
7. **`max_active_orbs` entitlement is not enforced anywhere yet** — manifest
   declares it, validator doesn't check it against actual active install count
   on any side yet. Needs an entitlement service to track real usage.
