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

