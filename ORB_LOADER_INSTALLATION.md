# Universal ORB Installation

## External script adapter

Install this exact script once at the site root so it loads on every route:

```html
<script
  src="https://orbweaver.spruked.com/orb-loader.js"
  data-orb-site-id="orb-weaver-campaign"
  data-orb-runtime="https://orbweaver.spruked.com/api/orb"
  data-orb-ws="wss://orbweaver.spruked.com/ws/orb"
  data-orb-version="1"
  data-orb-debug="true"
  defer
></script>
```

The production URL is an installation target, not a deployment assertion. The loader must be deployed before testing that URL.

## Native React/TypeScript adapter

If a platform rejects or strips external scripts, install the source adapter in the site project:

```tsx
import { OrbWeaverSiteAdapter } from './src/adapters/react-component';

export function SiteRoot() {
  return (
    <>
      {/* site application */}
      <OrbWeaverSiteAdapter
        siteId="orb-weaver-campaign"
        runtime="https://orbweaver.spruked.com/api/orb"
        ws="wss://orbweaver.spruked.com/ws/orb"
        version="1"
        debug
      />
    </>
  );
}
```

Both adapters call the same `src/orb-client` core and the same runtime contracts. The native adapter is not a second ORB implementation.

Every adapter activates the immutable `orb_factory_default_v1` **O.R.B.S. Factory Default** identity from `/orb-skins/factory-orb-v1.png` first. A custom skin changes only the in-memory visual selection. Failed custom assets and explicit PATCH-class rollback both restore Factory Default without remounting the loader, rebuilding Site World or Pointer Map, restarting runtime, or disconnecting WebSocket. Factory Default remains permanently registered, immutable, and owner-non-editable.

## Campaign scan binding

The registered site ID `orb-weaver-campaign` binds approved installation origins to the canonical Site World at `campaign.orbweaver.spruked.com`. This lets a ChatGPT Sites preview host and the final custom domain use one scan without confusing the installation hostname with the context hostname.

Current campaign truth:

- Legacy crawl job: `#24` (not lifecycle-evaluated and has no lifecycle evidence chain)
- Extracted pointer records: 137
- Runtime-normalized confidence: 1 safe `STABLE`, 136 `UNCERTAIN`
- Pointer quality: `POINTER_RECOVERY_REQUIRED`; count/no-duplicate checks do not make the map passed
- Pointer rule: only `VERIFIED` or `STABLE` targets whose live DOM identity matches may guide
- Non-canonical proof recovery: 8 renders, 104 viewport segments, 28 recovered, 109 unresolved
- Publication rule: the proof result did not overwrite the canonical pointer map
- Required next scan: a lifecycle ORB Scan before campaign deployment readiness can be evaluated

## Local proof commands

```bash
cd frontend
npm run build:orb-loader
npm run smoke:orb-loader
npm test -- --watchAll=false
npm run build

cd ..
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
```

The 25-check browser smoke test covers a plain HTML script install, Factory-first rendering, scaling, duplicate prevention, Shadow DOM isolation, route changes through `pushState`, `replaceState`, and back navigation, offline/reconnect, pointer and voice availability, custom-skin success, automatic Factory fallback, explicit Factory rollback, unchanged motion/runtime/WebSocket state, layout isolation, teardown, reinitialization, and zero console errors.

## External installation ladder

1. Plain static HTML (automated locally)
2. Local React application
3. Production Orb Weaver page
4. ChatGPT Site preview
5. Published `*.chatgpt.site` domain
6. `campaign.orbweaver.spruked.com` custom domain

Stages 3–6 require deployment or access to the relevant publishing surface. External-script preservation remains an experiment; rejection means use the native adapter.
