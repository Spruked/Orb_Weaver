# Weaver guidance and customer-site SKGs

These are deliberately different contracts sharing one lexical implementation.

| Scope | Contract | Runtime connection |
| --- | --- | --- |
| Orb Weaver's own host | `backend/app/orb/nine_of_clubs_skg.json` | Bounded speech policy for tour narration, interruptions, signup/login, Preflight, beta and investor conversations; Agency discovery keeps the canonical pattern registry. |
| Scanned customer sites | `manufacturing/templates/Website_Orb_Final/backend/skg/graph.py` | Mandatory scan-derived `payload/apriori/site_skg.json`, loaded by the manufactured runtime and used in route context, TPC input and answer fallback. |
| Both | `manufacturing/templates/Website_Orb_Final/backend/skg/lexicon.py` | Canonical labels and scan-supplied aliases resolve to candidate identities. Weaver uses its own server-loaded scan context; clones use their own compiled graph. |

The first owner's draft informs Weaver's visitor journey; it is **not** copied
into customer deployments. The agnostic draft supplies the customer graph
design; no `/signup`, `/preflight`, beta or investor destination is built into
that compiler. No model/provider configuration changes are part of this work.

## Revisions to the supplied drafts

- Existing Nine of Clubs patterns remain authoritative for Weaver discovery.
  They are not replaced by a new, competing visitor-state machine.
- Visitor answers, refusals, explicit destinations and questions matter. They
  are not forced through identical binary branches toward a predetermined sale.
- Source witnesses contain observed text or structural fields, source URL,
  source identifier and content hash. Missing evidence is never synthesized
  as “verified content.”
- Site graph nodes cover routes, concepts, entities, pointers and actions.
  Alias nodes connect to them with `aliases` edges. Canonical terms are only
  added when present in verified content; raw counts are not doubled as proof.
- An actionable route's distinct inbound links can suggest a destination.
  That suggestion needs owner approval; popularity is neither visitor consent
  nor permission to execute an action.
- Optional owner-approved `site_goals` produce precompiled next-hop tables.
  Paths have the length supported by observed links, not a fixed question
  count. Cycles terminate, single-page arrival has zero steps, and disconnected
  goals remain explicitly unreachable. No fabricated binary cut is inserted.
- Unknown aliases remain unmatched. Multiple matches remain ambiguous;
  neither fuzzy containment nor last-write-wins selects an action.
- Command prefixes can normalize vocabulary, but negation and alternatives
  remain intact. Language recognition and action authorization are separate.

## Scan and manufacturing integration

The scan adapter now reads actual stored page excerpts, internal links, pointer
observations and the lexical index instead of supplying an empty evidence list.
Failed fetches, known unresolved application shells and private/admin/system
routes are excluded from the visitor graph. Observation verification does not
replace the existing owner approval of the compiled payload.
Superseded canonical scan evidence is archived under the same client Vault
before the adapter replaces it for a newer scan.

`compile_all` always builds the graph. Manufacturing writes it beneath the
canonical build Vault, includes its checksum in the payload manifest and its
approval in the verification manifest, and requires it for delivery. Fresh
clones load it from `runtime/vault_system/payload/apriori/site_skg.json` only.
Missing, corrupt, empty, stale-scan or foreign-site graphs fail package
validation/startup rather than falling through to a different knowledge store.
Existing installed packages must be remanufactured to acquire this new required
artifact; editing the source template does not update a running installation.

`site_world.routes` is compiled from the same graph, including route-scoped
target identities and doctrine boundaries. Navigation reads resident context;
it does not re-crawl, construct a graph, or globally rank pointers on each page.
The graph and lexical match are advisory inputs to the existing runtime.

Optional goals in canonical evidence use this shape:

```json
{
  "site_goals": [
    {"goal_id": "reservation", "label": "Reserve a visit", "route": "/reservations", "owner_approved": true}
  ]
}
```

This does not create a new goal-editor UI or grant consent to visit/submit that
route. An unknown/unapproved destination is not turned into an active journey.

## Lexical limits and provenance

The index is serialized in the graph, not attached through an unserialized
side channel. It contains at most 4,000 normalized phrases, 24 mappings per
target and 240 characters per phrase. These are resource caps, not a claimed
page limit. The compilation report exposes unmatched keys, ambiguous keys and
cap truncation. No million-page performance claim is made.

Alias evidence records the lexical key, original phrase and target's source
witness. Generated phrases are labeled lexical evidence, not falsely quoted
as site body text. Runtime matching is exact after normalization. There is no
automatic fuzzy-match action fallback, and question phrasing does not mutate
the canonical discovery choices.

## Weaver's own live handoff

The frontend sends a short `guidance_mode` rather than an oversized private
protocol in the API objective. Signup and paused-tour voice turns bypass the
legacy tour-only transcription path. Experimental narration keeps authored
text in the bounded tour context instead of duplicating it in the 1,000-character
visitor transcript. This does not change tour destinations, pointer authority,
the inference model, or deployment state.

Provider-boundary tests prove prompt injection of the guidance/lexical context;
they do not prove a particular live model's performance. Package tests prove
graph injection, route lookup, lexical context in answers and missing-artifact
rejection. Full browser tour and real microphone/speech acceptance remain
separate runtime checks.
