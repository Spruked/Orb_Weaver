# Brand World — Next Implementation Slice

## Product rule

Detected brand assets are evidence, not permission. Every ORB starts as the neutral, immutable **O.R.B.S. Factory Default**. No detected logo, color, favicon, or company name is used in a deployed ORB without explicit owner consent.

The canonical neutral identity is `orb_factory_default_v1`, the owner-supplied **O.R.B.S. Factory ORB** documented in `FACTORY_ORB_IDENTITY.md`. Every customer receives it first and may keep it indefinitely. It is Orb Weaver's own default identity, not detected customer branding.

## Pipeline

```text
Website Scan
  -> Site World
  -> Pointer Map
  -> Brand World
  -> Factory ORB
  -> Owner Preview and Consent
  -> Brand ORB or Neutral ORB
  -> Versioned Deployment
```

## Brand World evidence

Store detected candidates without applying them:

- company and brand names
- primary and alternate logos
- favicon
- primary and secondary color palettes
- typography
- icon style
- light/dark theme
- tone and industry
- source URL, extraction method, confidence, content hash, and scan revision for every candidate

## Ownership is a project-level gate

- New public projects begin as `PUBLIC_EXTERNAL`.
- Generate a unique, random, project-bound verification token that cannot be replayed for another project.
- Support DNS TXT, a well-known verification file, and a `<meta>` tag.
- Verification is asynchronous: pending/checking/verified/failed/expired states and recheck are required because DNS propagation may take up to 48 hours.
- Site Scan and Factory Default previews may continue while verification is pending.
- A public scan may report that brand assets were detected, but must not expose candidate files, detailed asset records, selection controls, or authorization controls.
- Brand asset review, Brand Edition preview, and all personalization controls remain unavailable until the project is `OWNER_AUTHORIZED`.
- Successful ownership proof promotes the project scan contract to `OWNER_AUTHORIZED` and unlocks deeper owner-authorized scans generally, not only branding.

## Consent is a separate gate

After domain control and authorized-representative verification, the deployment wizard presents unchecked controls:

- Use my company logo
- Use my brand colors
- Use my favicon
- Use company name in greeting

Consent is per asset and per use. Never provide blanket branding consent. Record each grant or revocation as:

```text
site_id
authorized_owner_id
asset_id
consent_scope
consent_state
timestamp
deployment_version
previous_state_hash
record_hash
```

Include every decision in the signed/hash-chained deployment evidence manifest.

Ownership never implies brand consent. Brand consent never substitutes for ownership.

## Preview and choices

Once ownership is verified, provide a live, one-click preview for:

- Factory Default
- Brand Edition
- Professional Edition
- Fully Custom

Do not universally label Brand Edition as recommended. Contextual guidance may be considered later, but neutral identity must remain a respected first-class choice for regulated or policy-bound organizations.

## Revocation and deployment

- Revocation must be as easy as opt-in.
- Switching back to Factory Default is an immediate, reversible, atomic PATCH-class cosmetic hot-swap with no reinstall, runtime restart, or WebSocket disconnect.
- Preserve runtime, Site World, and pointer behavior across identity changes.
- Update only the versioned skin configuration; do not rebuild Site World or the pointer map.
- Record the revocation and new deployment revision in the evidence chain.
- Never allow a branded deployment unless both current ownership proof and the required per-asset consents are valid.

## First stopping checkpoint

Implement the data contracts and migrations for Brand World candidates, ownership verification, authorized-representative confirmation, per-asset consent evidence, signed approval, and versioned ORB identity selection. Add API tests for non-replayable tokens, pending rechecks, tier promotion, candidate/control secrecy before verification, deployment denial, consent logging, signed approval, and hot-swap revocation.
