# Orb Weaver Spruked Deployment

## Status and scope

This document defines the reviewed Docker/public runtime boundary. It is not a
local-development guide and does not authorize a rebuild or restart. Gate 1
approval remains governed by the September 11 release-evidence command sheet.

The public hostname is `orbweaver.spruked.com`. The API route must be resolved
before the frontend catch-all route.

| Runtime | Backend | Frontend |
| --- | ---: | ---: |
| Reviewed Docker/public lane | `16500` | `16510` |
| Isolated source-development lane | `16666` | `16667` |

Use [Isolated Development Runtime](operations/DEVELOPMENT_RUNTIME.md) for
source work. Do not point source development to `16500` / `16510`, and do not
reuse historical `16600`, `16610`, or `19667` instructions.

## Deployment invariants

- `/api/*` routes to the backend before the frontend `/*` route.
- The deployment has one canonical persistent root: `/app/vault_system`,
  mounted from the repository's `vault_system/` only.
- `DATABASE_URL`, generated TTS cache, client/site intelligence, audit evidence
  and governed state resolve beneath that canonical Vault.
- Do not create `.docker-data`, `.docker-substrate`, `backend/data`, or
  `substrate/clients` as alternate persistence roots.
- The basic Website ORB does not require Desktop MCP, a Dock Station, or a
  desktop relay to serve visitor guidance.
- Secrets enter through the deployment environment or governed secret store;
  no credentials, Windows user paths, tunnel identifiers, or service tokens
  belong in this document.

## Pre-deployment release identity

Before changing the reviewed runtime, record the exact Git tag/commit, source
tree status, image digest, generated bundle identity, and timestamped evidence
bundle. Deploy only that identified release candidate. After deployment, prove
the running image and served frontend originate from the same release identity.

The required evidence includes current health/readiness behavior, frontend and
backend regression results, startup/voice proof, pointer positive and negative
proof, and the two-site weave/install evidence required by Gate 1. Historical
Docker success does not substitute for this release-candidate evidence.

## Required checks

```bash
docker compose config --quiet
curl -fsS http://127.0.0.1:16500/health
curl -fsS http://127.0.0.1:16510/
```

The health/readiness check must report real dependency state and fail
truthfully. A successful HTTP response alone is not Gate approval.

## Cloudflare boundary

Cloudflare configuration is environment-owned operational state. Verify the
active tunnel, credentials location, DNS route, and ingress configuration in
the environment before modifying them. The required ingress order is:

```text
orbweaver.spruked.com /api/*  -> reviewed backend :16500
orbweaver.spruked.com /*      -> reviewed frontend :16510
catch-all                     -> 404
```

Keep Spruked navigation as a link to the Orb Weaver application; do not merge
the Spruked website router with the Orb Weaver backend.
