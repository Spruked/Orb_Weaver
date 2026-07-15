# ORB Pointer Runtime Model

This document locks the runtime boundary between full scan intelligence and the lightweight Website ORB installed on a customer site.

Pointer guidance is a baseline ORB capability. Every ORB gets a Pointer Plot Map, runtime pointer resolution, and verified visual guidance. This includes Orb Weaver's demo ORB, Basic customer Website ORBs, Enhanced/Premium Website ORBs, Desktop ORBs, and future branded or industry ORBs.

What changes by tier is not whether pointing exists. Tiers only change how broad, dense, maintained, branded, and adaptive the pointer intelligence becomes. Desktop MCP/tool adapters are gated; pointer guidance is not.

## Four Layers

| Layer | Purpose | Format |
| --- | --- | --- |
| Pointer Plot Map | Full scan output for every pointable element: DOM locator, context, confidence, actions, and aliases. | `website_orb_context/pointer_plot_map.json` |
| Runtime Intent Manifest | Curated visitor intents per page that map intent ids to one or more pointer ids. | small JSON |
| Voice Manifest | Pre-generated audio clips keyed to stable intent ids, not raw pointer ids. | audio files + JSON |
| Warm LLM | Handles questions outside the fast lane with fallback guidance. | model + prompt |

The full pointer map can be large. The installed Basic Website ORB should use a curated runtime intent manifest and voice manifest for zero-latency guidance.

## Target Identity

Pointer records use deterministic ids derived from:

```text
route + target_type + semantic_locator + parent_locator + content_fingerprint
```

This avoids duplicate ids when repeated text appears in multiple sections. Target ids use the `target_<hash>` prefix.

## Alias Split

Pointer records expose:

- `direct_aliases`: short, specific phrases suitable for fast-lane intent matching.
- `topic_aliases`: broader topical phrases suitable for warm LLM context.
- `intent_aliases`: compatibility field that mirrors `direct_aliases`.

Runtime intent manifests should prefer `direct_aliases`. Broad topic handling belongs to the warm LLM path.

## Scoped Resolution

Runtime resolution must verify identity before pointing:

1. Build a scoped selector from `structural_context.parent_locator` and `semantic_locator`.
2. Query matching elements.
3. Verify tag/context and visible text against the record identity.
4. Fall back to raw `semantic_locator` only after scoped lookup fails.
5. If identity cannot be verified, do not point. Speak a fallback instead.

This prevents generic selectors such as `p:nth-of-type(1)` from causing mispointing after a DOM change.

## Product Boundary

Basic customer Website ORBs use:

- pointer plot map
- curated runtime intent manifest
- voice manifest
- static `tool_cache.json`
- approved website context

They do not probe Desktop MCP. Orb Weaver's own showcase ORB may build an enhanced cache with MCP metadata only when `ORB_BUILD_ALLOW_MCP=true` or `--allow-mcp` is explicitly set.

## Tier Depth

- Basic: full pointer capability for important visitor routes, forms, navigation, service/contact paths, and major conversions.
- Enhanced: denser target coverage, more route-specific intents, stronger recovery, and more maintained target mapping.
- Premium: complete/high-priority target map, branded behavior, richer movement/presence, deeper contextual guidance, stronger verification, and maintenance.
- Desktop: same pointer doctrine, extended to desktop/app-window targets where applicable.
