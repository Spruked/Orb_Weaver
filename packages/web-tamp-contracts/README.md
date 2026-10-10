# Web-TAMP contracts

Canonical, factory-independent contracts for Orb Weaver's Web-TAMP
(Task-and-Harvest Planning) architecture.

The package deliberately separates planning from authorization:

```text
Planner -> Proposal -> Governor -> Authorization -> Primitive execution
```

The Planner may create or replace a `Proposal`, but it cannot create an
`Approval` or `Authorization`. The existing governor remains the only source
of execution authority. `candidate_*` data is never represented as
`approved_*` data.

The TypeScript and Python modules use the same snake_case JSON field names and
the same schema/version identifiers. The package is dependency-free on the
TypeScript side; Python validation uses the repository's existing Pydantic v2
dependency.

Factory and manufactured-runtime integration paths are intentionally deferred
to Web-TAMP Migration Step 2. The factory Python image and Orb Weaver frontend
consume this package through thin import boundaries; the manufactured runtime
must receive the same package as a deployment dependency. Step 1 establishes
the stable wire contracts without migrating crawler, planner, or template
behavior.
