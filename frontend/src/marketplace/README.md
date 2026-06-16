# ORB Marketplace Module

This folder contains the isolated Marketplace experience for Orb Weaver.

## Purpose
- Keep marketplace UI and routing separate from dashboard pages.
- Preserve standalone-ready architecture for future extraction.
- Provide a premium "library vault" browse flow for ORB products.

## Route Surface
- `/marketplace`
- `/marketplace/category/:id`
- `/marketplace/product/:id`
- `/marketplace/collection/:id`
- `/marketplace/collections`
- `/marketplace/search`

Primary route wiring is in `frontend/src/marketplace/MarketplaceRoutes.tsx`.

## Structure
- `components/`: Marketplace shell, nav, cards, shelf and index UI blocks.
- `pages/`: Route pages (home, category, product, collections, search).
- `hooks/`: Shared marketplace state and behavior (`useMarketplace`).
- `services/`: API bridge (`marketplaceApi`) for catalog and cart actions.
- `data/`: Local fallback marketplace data and collection metadata.
- `styles/`: Marketplace-only visual system (`market-theme.css`).

## Cart Behavior
Add to Cart remains connected through:
- `marketplaceApi.addToCart(...)` -> `api.upsertCartItem(...)`

Non-purchasable records are displayed as planned entries and are not submitted.

## Design Direction
Current visual doctrine:
- Dark library vault shell
- Cream catalog-card surfaces
- Market Index Code as call number
- Shelf-based browsing for featured and category collections

Palette anchors:
- Background: `#07090D`
- Shell: `#121018`
- Panel: `#171223`
- Card: `#F3E8D2`
- Gold: `#F4B84A`
- Violet: `#8B5CF6`
- ORB glow: `#37C6FF`
- Bone text: `#F7F1E4`
- Ink text: `#1B1720`

## Notes
- No backend marketplace model expansion in this module pass.
- No NFT logic in this module pass.
- Keep this module independently maintainable for future standalone deployment.
