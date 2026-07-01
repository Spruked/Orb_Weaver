# ORB_SKIN_PACKAGE_CONTRACT_v1.md

**Schema version:** 1.0
**Applies to:** Website ORB (Orb Weaver), Desktop ORB (Electron + Tauri), Browser ORB
**Status:** Scaffold — loose enforcement, tighten as conflicts resolve

---

## 1. What a `.orbskin` file is

A `.orbskin` file is a single ZIP archive with a renamed extension. To a user or
an installer, it is one file — buy it, drag it, drop it. Internally it always
contains the same shape:

```
my-orb-skin.orbskin
├── manifest.json        ← required, defines everything below
├── preview.png          ← required, marketplace thumbnail
├── body.png OR body.glb ← required, the ORB's visual body
├── docked-icon.svg      ← required, shown when ORB is collapsed/docked
├── animations/          ← optional, named animation files
├── particles/           ← optional, particle effect profiles
├── sounds/               ← optional, audio cues
└── license.json         ← optional, extended license terms beyond manifest.json
```

No code change is required to install a new skin. The runtime always does the
same four steps regardless of which skin it's given:

```
1. Receive .orbskin file
2. Validate it
3. Activate it (or reject it)
4. Keep the previous skin available for one-step rollback
```

---

## 2. manifest.json field reference

### `schema_version`
String. Must match the version this contract document describes (currently `"1.0"`).
If a runtime sees a higher schema version than it understands, it should warn and
attempt best-effort loading rather than hard-fail — this keeps old runtimes working
against newer skins where possible.

### `skin_id`
String. Globally unique identifier, format `orbskin_<ULID>`. Generated once at
creation time and never changes. This is the primary key everywhere — Weaver
storage, marketplace listings, provenance records, entitlement checks.

### `name`
String. Human-readable display name shown in marketplace and skin picker UI.

### `version`
String, semver. The skin's own revision number (e.g. a creator re-uploads with
fixed colors → `1.0.0` becomes `1.1.0`). Independent of `schema_version`.

### `description`
String, optional. Shown in marketplace listings.

---

### `creator` block

| Field | Type | Meaning |
|---|---|---|
| `creator_id` | string | `truemark_creator_<id>` — links to a creator account |
| `display_name` | string | Shown publicly on the listing |
| `verified` | boolean | Whether True Mark Mint has verified this creator's identity |

---

### `classification` block

| Field | Type | Meaning |
|---|---|---|
| `tier` | `basic \| premium \| collectible \| branded` | Determines which optional manifest sections matter |
| `edition_type` | `unlimited \| limited \| one_of_one` | Scarcity model |
| `supported_orbs` | array of `website \| desktop \| browser \| all` | Which ORB targets this skin can install onto |
| `commercial_use` | boolean | Whether business/enterprise use is permitted under the attached license |

**Tier guide:**
- `basic` — fixed price, unlimited edition, personal license. The $0.88 skin case.
- `premium` — richer animation/sound, may carry creator royalty terms.
- `collectible` — provenance-tracked, may be limited or 1-of-1, may be minted.
- `branded` — enterprise identity skins, commercial use explicitly granted.

---

### `visuals` block

| Field | Type | Meaning |
|---|---|---|
| `preview` | string | Filename of the marketplace thumbnail (PNG) |
| `body_asset` | string | Filename of the ORB body — `.png` (2D) or `.glb` (3D model) |
| `docked_icon` | string | Filename of the collapsed-state icon (SVG) |
| `animations` | array of strings | Filenames inside `animations/` — e.g. `["summon.json","idle.json","dock.json"]` |
| `particle_profile` | string, optional | Filename inside `particles/` describing particle behavior |
| `sounds` | array of strings, optional | Filenames inside `sounds/` |
| `theme_tokens` | object, optional | Key-value CSS-safe tokens (see below) |

**`theme_tokens` keys (all optional):**

```
orb_primary_color    hex color
orb_glow_color       hex color
orb_shadow_color     hex color
orb_docked_bg        hex color
orb_font_family      safe web font name (no external URLs)
orb_border_radius    CSS value, e.g. "50%" or "8px"
```

These are applied by the renderer as CSS custom properties on the ORB's root
element. A skin cannot inject arbitrary CSS, inline scripts, or external font
URLs through this mechanism — only the whitelisted token keys above are read.

---

### `behavior_limits` block — THE HARD WALL

This block exists so that **a skin can never be more than a skin.** Every field
here is enforced by the validator on both the Weaver side and the ORB runtime
side, independently. A skin that fails this check is rejected outright — there
is no partial-trust mode.

| Field | Required value | Why |
|---|---|---|
| `changes_visuals_only` | **must be `true`** | Declares the skin's entire scope |
| `may_change_voice_style` | `true` or `false` | Allowed for premium/branded tiers only — runtime-enforced |
| `may_change_personality_language` | `true` or `false` | Allowed for branded/enterprise only — runtime-enforced |
| `may_add_permissions` | **must be `false`** | Hard wall — no exceptions, any tier |
| `may_add_tools` | **must be `false`** | Hard wall — no exceptions, any tier |
| `may_add_network_access` | **must be `false`** | Hard wall — no exceptions, any tier |
| `may_add_llm_access` | **must be `false`** | Hard wall — no exceptions, any tier |

If any of the four hard-wall fields are anything other than `false`, the package
is rejected during validation, before any assets are extracted or applied. This
is true even if the package's signature is otherwise valid — a correctly signed
package that claims excess authority is still rejected.

---

### `marketplace` block (optional — required if the skin is sold)

| Field | Type | Meaning |
|---|---|---|
| `price_type` | `fixed \| market \| auction` | How the price is determined |
| `base_price_usd` | number | List price in USD |
| `marketplace_fee_percent` | number 0–100 | Platform cut |
| `creator_royalty_percent` | number 0–100 | Only applies when `rights.resellable = true` |

---

### `rights` block

| Field | Type | Meaning |
|---|---|---|
| `license_type` | `personal \| commercial \| enterprise` | Scope of legal use |
| `transferable` | boolean | Can ownership move to another account |
| `resellable` | boolean | Can the buyer resell it on the marketplace |
| `max_active_orbs` | integer | How many simultaneous ORB instances this license covers |
| `expiry_date` | ISO8601 string, optional | `null`/absent = perpetual license |

A skin whose `expiry_date` has passed is rejected at validation time on both
sides, even if every other check passes.

---

### `collectible` block (optional — required for `tier: collectible`)

| Field | Type | Meaning |
|---|---|---|
| `minted` | boolean | Whether this skin is tied to an on-chain token |
| `chain` | string or null | e.g. `"polygon"`, `"ethereum"` |
| `contract_address` | string or null | NFT contract, if minted |
| `token_id` | string or null | Token ID, if minted |
| `provenance_record_id` | string | `tmr_<ulid>` — always present, even for unminted collectibles, since True Mark Mint tracks provenance independent of blockchain status |
| `edition_number` | integer, optional | e.g. `12` |
| `edition_total` | integer, optional | e.g. `100` |

This is the section that expands for True Mark Mint mints — the install
mechanism underneath does not change. A `tier: collectible` skin installs
through the exact same four-step flow as a `tier: basic` skin.

---

### `integrity` block — THE TRUST WALL

| Field | Type | Meaning |
|---|---|---|
| `package_hash` | `sha256:<hex>` | SHA-256 of every file in the package except `manifest.json` itself |
| `manifest_hash` | `sha256:<hex>` | SHA-256 of the manifest JSON (with `package_hash` already filled in, `manifest_hash` itself blank during hashing) |
| `publisher_signature` | string | Signature over `skin_id + package_hash`, verified against the publisher's known key |
| `signed_at` | ISO8601 string | When the package was signed |
| `runtime_min_version` | semver string | Oldest ORB runtime version that can load this skin |
| `runtime_max_version` | semver string, optional | Newest compatible runtime, if there's a ceiling |

**The runtime never trusts a `.orbskin` extension alone.** Before activating
any package, both Weaver and ORB runtime independently verify, in this order:

1. **Package version** — `schema_version` is recognized
2. **Supported ORB type** — current target appears in `classification.supported_orbs`
3. **Asset integrity hashes** — recomputed `package_hash` matches the manifest's claim
4. **Publisher/creator identity** — `creator.creator_id` resolves to a known account
5. **Signature or marketplace authorization** — `publisher_signature` verifies against the publisher's key
6. **License/entitlement status** — `rights.expiry_date` hasn't passed, `max_active_orbs` isn't exceeded
7. **Permission boundary** — `behavior_limits` hard walls all check out false where required
8. **Runtime compatibility** — current runtime version falls within `runtime_min_version`/`runtime_max_version`

A failure at any step rejects the whole package. Nothing partial-installs.

---

## 3. Install flow (same on every target)

```
CurrentSkin.orbskin
   │
   ▼
NewSkin.orbskin received
   │
   ▼
Validate (8-step check above)
   │
   ├── FAIL → reject, CurrentSkin.orbskin stays active, error surfaced to UI
   │
   └── PASS → extract assets
                  │
                  ▼
            CurrentSkin.orbskin moved to rollback slot
                  │
                  ▼
            NewSkin.orbskin becomes active
                  │
                  ▼
            React renderer receives new SkinAssetBundle
                  │
                  ▼
            ORB visuals update — no restart, no manual file copying
```

Rollback reverses the last two steps: the rollback slot becomes active again,
and what was active moves to rollback. One level of undo is guaranteed; deeper
history is a Weaver-side storage decision, not a runtime requirement.

---

## 4. What this buys you

| Skin level | What changes in the manifest | What changes in the install code |
|---|---|---|
| Basic $0.88 skin | `marketplace`, minimal `visuals` | **Nothing** |
| Premium creator skin | richer `visuals.animations`, `rights.resellable` | **Nothing** |
| Branded enterprise skin | `classification.commercial_use`, `behavior_limits.may_change_personality_language` | **Nothing** |
| True Mark Mint collectible | full `collectible` block, `classification.tier: collectible` | **Nothing** |

One skin engine. One package format. One validator. Every tier of value rides
the same rails — the manifest gets richer, the install code never does.
