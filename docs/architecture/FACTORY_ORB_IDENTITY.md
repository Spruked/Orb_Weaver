# Factory ORB Identity

## Canonical rule

The ORB artwork supplied by the owner on 2026-07-18 is the canonical first ORB every customer receives before any custom or owner-approved branded skin.

```text
identity_id: orb_factory_default_v1
identity_state: FACTORY_DEFAULT
display_name: O.R.B.S. Factory Default
applies_to: website, browser, desktop
customer_branding: none
owner_brand_consent_required: false
custom_skin_required: false
immutable_default: true
fallback_enabled: true
owner_editable: false
```

This identity is a complete production identity, not a placeholder, trial skin, or incomplete customization state.

## Activation order

```text
New ORB installation
  -> Factory Default activates
  -> runtime and Site World become available
  -> owner may remain on Factory Default indefinitely
  -> approved custom/brand skin may hot-swap later
```

No customer logo, colors, favicon, or company name may modify Factory Default. Those remain separate, opt-in Brand World permissions.

## Fallback and rollback

Factory Default is the immutable safe fallback when:

- no custom skin has been selected;
- a custom package fails validation;
- a custom entitlement expires or is revoked;
- a hot-swap fails;
- the owner revokes brand consent;
- the owner selects Factory Default again.

Returning to Factory Default is an immediate PATCH-class visual change. ORB runtime, Site World, Pointer Map, permissions, tools, voice policy, memory, and WebSocket connection remain unchanged. It does not remount or restart the ORB.

## Asset integrity requirement

The exact supplied artwork must be installed without generative recreation, substitution, cropping, recoloring, or logo/text changes. The current repository contains bow-tie `tuxorb.png` assets, but they are not the supplied Factory ORB and must not be used as substitutes.

Expected production asset path:

```text
frontend/public/orb-skins/factory-orb-v1.png
```

Before activation, record:

```text
asset_sha256
pixel_width
pixel_height
mime_type
alpha_channel
installed_at
source: owner_supplied
```

The repository and optimized local frontend build contain this verified asset. That is not a claim that the loader or Factory ORB has been deployed to public production; public deployment requires a separate controlled release and served-asset verification.

The exact original image is installed at the expected path. Its verified integrity record is:

```text
sha256: 8eb49c628211c7d077fb65f3591107f1489124ccbfa840dc0f2381157cd87e61
dimensions: 1492 x 1474
mime_type: image/png
color: RGBA, 8-bit
source: owner_supplied
```
