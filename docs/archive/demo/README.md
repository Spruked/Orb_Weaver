# Deprecated Demonstration Station Archive

Status: **DEPRECATED — NOT SERVED**

Deprecated on: 2026-07-29

The scripted Orb Weaver Demonstration Station has been replaced by the real Website ORB experience on the Orb Weaver campaign site. The campaign installation will use a fresh ORBS instance, its own Site World, its own pointer map, and a choreographed page-to-signup walkthrough.

## Preserved Git objects

The complete prior implementation remains recoverable byte-for-byte through Git history:

- Authenticated React wrapper: `frontend/src/pages/Demo.tsx`
  - Last active blob: `a856bbb16796d56914267b36b8f579a02233abbe`
- Served station: `frontend/public/demonstration-station.html`
  - Last active blob: `e6427f6cebe7cad03c93956b261e4e8383fea0af`
- Root working/reference copy: `demonstration_Station.html`
  - Last active blob: `608ea1727cb970340b179ca1e0c82f2c89c85a98`

These files were removed from active routes and public build output. The `/demo` route is retained only as a backward-compatible redirect to the Orb Weaver home page until the campaign hostname is verified for direct handoff.

## Replacement doctrine

The campaign site is a separate website and therefore a separate scan/evidence project. Its ORB may use the Orb Weaver runtime, but campaign page data must not be merged into the `orbweaver.spruked.com` audit or Site World.
