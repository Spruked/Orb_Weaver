# Dock Station Owner Configuration

Dock Station keeps owner configuration understandable and subordinate to Orb
Weaver's locked runtime behavior. Owners provide business context; they do not
replace doctrine, verification, authorization, Site World evidence, or action
controls.

## Configuration layers

### Business Objectives

Business Objectives describe the outcomes that matter to the website, such as
helping visitors understand a service, completing registrations, guiding a
qualified purchase, reducing abandoned workflows, or encouraging contact with
the team. They influence how the ORB prioritizes helpful next steps.

They do not override safety, privacy, verification, authorization, or Site
World rules.

### Additional Guide Rails

Additional Guide Rails are standing, business-specific preferences. They can
describe when to recommend contacting the team, how to handle special
requests, what should be referred to a human, or practices not captured by
website data.

They supplement built-in behavior and cannot override locked safety, privacy,
verification, authorization, payment, Site World, or action-control rules.

### Situational Guide Rails

Situational Guide Rails are conditional instructions: when a specific visitor,
route, workflow, confidence, or business condition occurs, they describe the
preferred response or next step. Examples include refund requests, confusion,
human-assistance requests, unavailable information, sensitive topics, and
workflow stages.

They supplement built-in behavior and Business Objectives. They cannot override
locked safety, privacy, verification, authorization, payment, Site World, or
action-control rules.

## Compilation boundary

Orb Weaver reviews owner additions during compilation. Each addition is
classified as compatible, redundant, conflicting, unsupported, or requiring
review. Conflicting, unsupported, and unresolved instructions block
publication; owner approval cannot turn an invalid instruction into runtime
authority.

The runtime still enforces critical rules independently of model behavior:
pointer verification, permission checks, payment/entitlement checks,
authorization boundaries, Site World grounding, and no-false-Ping behavior.
