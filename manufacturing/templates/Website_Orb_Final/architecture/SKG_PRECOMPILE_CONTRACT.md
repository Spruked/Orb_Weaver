# SKG Precompile Contract

This package follows the v2 correction: the page context is not assembled at runtime.

Each route record in `compiled_orb/site_world.json` must include:

- `page_purpose`
- `summary`
- `target_tiering.top_value_targets`
- `target_tiering.secondary_targets`
- `target_tiering.full_route_scoped_targets`
- `permitted_action_boundaries`
- `doctrine_conditions`
- `tpc_output_classes`
- `playbooks`
- `guiderails`

Runtime code may look up these fields, filter them, and return them. Runtime code must not crawl, scan, rank the full map, or build a new capsule on navigation.

## Mandatory agnostic site graph and lexicon

Every newly manufactured clone must also contain
`runtime/vault_system/payload/apriori/site_skg.json` (`orb_weaver.site_skg.v1`).
The reusable compiler and lexical layer are in `backend/skg/`; site data is
never stored in that code directory.

The graph is compiled from that site's canonical full-scan evidence. It carries
source witnesses, route/concept/entity/action/pointer nodes, alias nodes and
`aliases` edges, a serialized lexical index, advisory destination candidates,
and precompiled next hops for explicitly owner-approved goals. No fixed funnel
length, Weaver-specific route names or invented evidence is permitted.

Manufacturing approval and manifest hashing cover this artifact. Runtime boot
rejects a missing, invalid, stale-scan or foreign-site graph. Route/answer paths
load the resident graph and preserve ambiguous matches for clarification.
Lexical matches never grant pointer, navigation, form or purchase authority.

The scanner → registry → live DOM validation → governor → pointer boundary
remains unchanged. The host-only Nine of Clubs sales policy is not a clone
template dependency.
