# Website ORB Deployment Standard

## Decision

Every manufactured Website ORB will be delivered as a Docker Compose package
for a single customer-controlled host.

Docker Compose is the deployment boundary. Kubernetes is explicitly out of
scope for the Website ORB appliance and must not be added as an alternative
or prerequisite.

## Package contract

The manufactured package is intended to contain and orchestrate:

- the Website ORB runtime and API;
- the gateway and bundled small local model;
- Kokoro TTS and any required STT service;
- the site-specific Vault/Site World and customer configuration;
- the selected skin, Work ORB factory fallback, and loader;
- health checks, restart policies, persistent storage, and backup boundaries.

The customer should install one Compose package rather than separately
installing Ollama, Kokoro, model weights, or other runtime services.

## Non-goals

- No Kubernetes manifests, Helm charts, or cluster control plane.
- No dependency on Orb Weaver's factory API, database, checkout, or runtime
  after the customer package has been manufactured.
- No browser-only package that silently requires separately installed speech
  or cognition services.

## Manufacturing acceptance gate

A package is not considered a complete installable Website ORB until the
manufacturing pipeline can validate the Compose package on a clean host:

1. `docker compose config` succeeds without factory-only paths or secrets.
2. All required images/assets/models are present or pulled by the package's
   documented Compose flow.
3. Every service has a health check and a deterministic dependency boundary.
4. Persistent Vault/storage paths are explicit and backupable.
5. The loader reaches the packaged runtime through the documented customer
   origin configuration.
6. A clean-host smoke test proves startup, text guidance, speech, and safe
   pointer behavior before the `.orbpack` is released.

The existing Python-template installer remains a legacy development/runtime
path until this Compose acceptance gate is implemented. It must not be
described as the final self-contained appliance.
