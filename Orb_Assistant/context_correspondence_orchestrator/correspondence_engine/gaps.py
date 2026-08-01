"""
Explicit registry of open architectural questions.

This file exists so these gaps live in the codebase, not only in
conversation history — per the project's own stated principle: "the
architecture protects itself from its creator." Anyone (human or
Codex) extending this scaffold should read this file before touching
any of the modules that raise NotImplementedError.

Do not resolve a gap by writing a plausible-looking implementation
without also updating this file to mark it resolved and explain the
resolution. Silent resolution — a docstring claiming a property the
code doesn't enforce — is how the original v0.2 scoring bug happened.
"""

GAP_A = """
GAP_A — Correspondence vector computation has no owner.

The Correspondence Substrate (CS) was frozen as the module
responsible for producing CorrespondenceVector values. The current
pipeline (sublimator -> claims -> atoms -> geometry) has no step
that actually computes a vector from a claim. KnowledgeClaim.
promote_to_atom() and geometry.py both reference this gap and
refuse to silently paper over it.

Resolve by explicitly choosing one:
  1. Revive CS as a standalone module between claims.py and atoms.py
  2. Fold vector computation into SemanticSublimator
  3. Fold it into a new, clearly-scoped step in geometry.py
     (would contradict geometry's current "distance only" scope —
     re-justify if chosen)

This is the highest-priority gap. Nothing that depends on a
populated CorrespondenceVector (geometry, re-challenge neighbor
variance, HLSF placement) is real until this is resolved.
"""

GAP_C = """
GAP_C — Beam role is possibly circular, not yet stated as intentional.

Beams were proposed both as generators of evidence (upstream,
feeding EvidenceItem) and as consumers of geometrically-placed
knowledge (downstream, per the pipeline diagram). If both are true,
the system is recursive: beams reason over atoms partly derived
from their own prior output. This may be acceptable, but it needs
an explicit invariant (e.g. a beam cannot be influenced by an atom
it most recently produced without an intervening validation step)
or it risks self-reinforcing drift.
"""

GAP_D = """
GAP_D — Fifth Mind scope undecided.

Recommendation on the table, not yet ratified or rejected: keep
Fifth Mind scoped to beam-disagreement entropy only; introduce a
separately-named signal ("correspondence variance") for uncertainty
across the five correspondence dimensions, rather than overloading
"entropy" to mean two different things.
"""

GAP_ECM = """
GAP_ECM — ECM does not exist yet.

Confirmed directly by the project owner: ECM is spec-only, not
built. Every reference in this scaffold to "escalation"
(re-challenge triggers, high variance, beam divergence) currently
has no real destination. Either build ECM next, or give escalation
an explicit interim destination (log / human-review queue / clearly
marked no-op) so "escalates to ECM" is never a documented behavior
with nothing behind it.
"""

GAP_F = """
GAP_F — KnowledgeClaim schema and lifecycle incomplete.

Current schema in claims.py is a working draft. Open questions:
subject/predicate/object extraction rules from irregular evidence
text (SemanticSublimator.sublimate is a stub for this reason),
contradiction representation, and the exact trigger for Claim ->
Atom promotion.
"""

GAP_STABILITY = """
GAP_STABILITY — covariance_stability_check has no computable definition.

Proposed but undecided: Frobenius norm of the change in the vault's
covariance matrix across the last N updates, staying below some
epsilon. Requires the vault to retain covariance history, which it
does not currently do. Currently raises NotImplementedError rather
than a fake `True`.
"""

GAP_DRIFT = """
GAP_DRIFT — drift_velocity_check has no computable definition, and
risks redundancy with GAP_STABILITY if not defined distinctly.
Proposed direction: measure the rate of change of individual atoms'
correspondence vectors over time, not the covariance matrix's own
rate of change (that's stability's job). Currently raises
NotImplementedError.
"""

GAP_FEEDBACK = """
GAP_FEEDBACK — no antifragile feedback loop on successful re-challenge.

When a re-challenge (challenge.py) reverses a finding, nothing
currently propagates that correction back to the atom's source or
provenance, and nothing down-weights that source for future
corroboration. As specified, the system is robust (it corrects the
one atom) but not antifragile (it doesn't get harder to fool the
same way twice). Likely the single highest-value addition relative
to the project's stated goal, once GAP_A and GAP_F are resolved.
"""

GAP_PROBATION = """
GAP_PROBATION — no bounded window between "error introduced" and
"error detectable."

A bad sublimation or a bad correspondence vector can sit in the
vault, influencing retrieval, for up to max_cycles_without_
revalidation cycles before a re-challenge trigger fires. Consider a
probationary period for newly-placed atoms — tighter re-challenge
sensitivity, reduced influence weight on neighbors — until an atom
has survived some minimum number of cycles or been independently
corroborated. Not yet designed.
"""

ALL_GAPS = [
    GAP_A, GAP_C, GAP_D, GAP_ECM, GAP_F,
    GAP_STABILITY, GAP_DRIFT, GAP_FEEDBACK, GAP_PROBATION,
]
