# ORB Identity and True Mark Boundary

This is the current implementation boundary for the commercial architecture
record supplied on 2026-09-29.

## Implemented in Orb Weaver

- Every packaged Website ORB receives an idempotent permanent serial in the
  form `ORB-SN-YYYY-NNNNNN`.
- The serial is stored in the canonical Vault identity registry at
  `vault_system/identity/orb_serial_registry.json`.
- The serial survives website, owner, skin, persona, role, and redeployment
  changes. A new build identity receives a new ORB identity.
- Package manifests contain the ORB identity and ISS timestamp envelope.
- Package generation records a pending True Mark certification request with the
  current `$12.88` B2B issuance fee and requested artifacts.
- Pending certification records are stored at
  `vault_system/integrations/true_mark/orb_certification_requests`.
- The ORB runtime does not depend on Polygon, a wallet, or True Mark
  availability.

## True Mark intake boundary

True Mark now exposes the dedicated intake route:

`POST /api/integrations/orb-weaver/certification-requests`

Orb Weaver signs the canonical JSON request with the shared
`TRUEMARK_ORB_INTEGRATION_SECRET` and sends it only when
`TRUEMARK_BASE_URL` and the secret are configured. True Mark stores the request
idempotently by request ID and ORB serial in its own Vault database and returns
`PENDING_EXTERNAL_ISSUANCE`. Missing configuration, transport failure, or
rejection is recorded explicitly; package generation does not fail open into a
false certification.

## True Mark authority boundary

True Mark remains responsible for issuing the Certificate of Authenticity,
KL-NFT, embedded license, provenance record, and any blockchain evidence. Orb
Weaver records a request and must not generate or display those artifacts as
real until True Mark returns them.

True Mark's existing generic payment/mint routes (`/payments/process` and
`/mint/complete`) remain separate from this intake route. Intake does not mint,
charge, create a certificate, create an NFT, or grant runtime authority.
True Mark must perform its own payment/order eligibility and issuance review.

## Still requiring external implementation

- idempotent issuance and retry contract;
- formal ORB license language;
- exact KL-NFT metadata and identifier prefix;
- Polygon contract and 3% royalty enforcement;
- certificate rendering/signature response;
- ownership transfer and secondary-sale records;
- legal review of ownership, licensing, royalty, and resale claims;
- format/reset verification and old-customer data purge workflow.

No simulated transaction hash, block number, certificate signature, NFT
identifier, or mint confirmation is accepted as production evidence.
