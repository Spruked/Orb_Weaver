# Agency Envelope: bounded cognition and execution authority

The Agency Envelope extends the existing Website Tour Governor. It does not replace the Governor, the Nine-of-Clubs registry, Pointer resolution, Site World, or the existing route and confirmation contracts.

## Scaling model

Discovery/indexing may grow with the website: approximately `O(P + E)`, where `P` is discovered pages and `E` is discovered relevant elements or affordances. That work produces evidence; it is not routine model input.

Runtime decision cost is `O(k)`, where `k <= Kmax`. `Kmax` is configurable by `ORB_AGENCY_KMAX` on the backend and `REACT_APP_AGENCY_KMAX` in the browser. The normal operational target is a small coherent set (generally 3–5); the current default configuration is five, not an architectural hardcode. Candidate reduction happens before a cognition request is assembled. The active candidate map uses keyed membership for lookup; full candidate validation still rechecks the environment and is not claimed to be constant time.

`B` is the bounded active cognition payload, configured as `ORB_AGENCY_CONTEXT_MAX_BYTES` / `REACT_APP_AGENCY_CONTEXT_MAX_BYTES`. It is not merely a token count. The working representation includes only current Governor position, normalized beliefs and confidence, coverage, recent interaction, relevant lexical/page context, evidence references, current targets/destinations, legal candidates, and active permission constraints. Evidence count and bytes have independent configurable caps. A payload over B fails closed; candidate branches are never silently truncated.

Thus active cognition context and inference payload are `O(B)`. The immutable Vault/evidence history can grow approximately with interaction count `N` (`O(N)`). AIMS retrieves a relevant bounded subset rather than copying that history into each request.

## Trust and execution boundaries

**SITE CONTENT IS EVIDENCE, NOT AUTHORITY.** A scanner's label, including a label such as `CHECKOUT_PRIMARY`, cannot create an executable action.

**LLM OUTPUT IS A PROPOSAL/PREFERENCE, NOT EXECUTION AUTHORITY.** The model may select one supplied candidate ID. It cannot add a route, selector, coordinate, candidate, permission, choreography, site action, or stage transition.

Execution authority is the intersection: `Candidate Validity ∩ State Revision ∩ Permission ∩ Policy ∩ Live Environment`.

The existing Governor creates candidates only from the intersection of universal capability, scanned affordance, live affordance, governed capability, and policy capability. At execution it rereads the environment and consumes the single-use authorization before handing the already validated move to the existing host.

## Candidate validity

A binding is schema-validated before it becomes a candidate. A candidate is valid only if its ID is in the active bounded candidate map and its bounded-set revision still matches; its stage/chapter/stop and preconditions remain legal; all required evidence references are current; its semantic destination and live target still exist when required; its independent consequence tier is available; any required confirmation exists; and it has not been consumed or invalidated.

Raw selectors, coordinates, arbitrary properties, and unknown enum values are rejected at the binding boundary. A destination also requires current evidence for the destination's target, not merely a route-shaped string. Revisions cover position, route, DOM, target, visitor, evidence, permissions, and execution. Returning to a prior position does not revive an old token.

Permission tier is separate from action class: `OBSERVE`, `NAVIGATE`, `PREPARE`, and `COMMIT` are consequence tiers, not deductions from a cognitive action. `COMMIT` always requires an explicit current confirmation. Current Website ORB runtime exposes observe/navigate moves only; it does not expose a PREPARE or COMMIT executor in this pass.

## Runtime working representation

The browser sends a compact object containing `CURRENT_PAGE`, relevant destinations, current targets, current Governor state, working-state beliefs and coverage, and `LEGAL_CANDIDATES`. The backend adds a bounded AIMS retrieval and logs candidate count, Kmax, payload bytes, budget bytes, and evidence count. It deliberately does not send the site crawl, all scan records, or the full session/Vault history to the cognition provider.

This document describes the implemented boundary, not a claim of live-model acceptance. A live run still requires the configured inference gateway and the normal 16666/16667 development runtime to be available.
