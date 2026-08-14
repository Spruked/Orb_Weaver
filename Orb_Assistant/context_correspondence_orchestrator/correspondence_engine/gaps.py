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

STATUS INVARIANT (explicit, not left to inference):

  OPEN
    Design incomplete or implementation absent. Must not silently
    execute as complete — code behind an OPEN gap either raises
    NotImplementedError or is unreachable from any live path.

  IN_PROGRESS
    Design has been accepted and implementation may exist, but no
    production/live caller may rely on it as complete. Code existing
    is not the same thing as a gap being closed.

  CLOSED
    Implementation exists, tests pass, AND live integration actually
    uses the implementation. All three, not any one of them.

FORMAT NOTE: this is a restructuring of the plain-string registry
into dataclasses, per the cross-validation review's recommendation
(machine-readable `depends_on`, self-validation, split hidden
prerequisites out of GAP_STABILITY/GAP_DRIFT). This is a proposed
shape, not yet confirmed as canonical — the original plain-string
format is equally valid and simpler. Pick one before this file is
treated as authoritative; don't let two formats of the same registry
coexist.
"""

from dataclasses import dataclass, fields
from enum import Enum


class GapStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


@dataclass(frozen=True)
class Gap:
    id: str
    owner_module: str
    description: str
    blocks: str
    status: GapStatus
    depends_on: tuple = ()  # only populated where a dependency was explicitly stated


GAP_F = Gap(
    id="GAP_F",
    owner_module="claims.py / sublimator.py",
    description=(
        "KnowledgeClaim schema and lifecycle incomplete. Current "
        "schema in claims.py is a working draft. Open questions: "
        "subject/predicate/object extraction rules from irregular "
        "evidence text (SemanticSublimator.sublimate is a stub for "
        "this reason), contradiction representation, and the exact "
        "trigger for Claim -> Atom promotion."
    ),
    blocks=(
        "SemanticSublimator.sublimate() raises NotImplementedError "
        "unconditionally. No EvidenceItem list can be converted into "
        "a KnowledgeClaim until this closes. Deepest upstream blocker "
        "in the whole pipeline — GAP_A cannot be meaningfully closed "
        "on synthetic claims alone."
    ),
    status=GapStatus.OPEN,
)

GAP_A = Gap(
    id="GAP_A",
    owner_module="unowned",
    description=(
        "Correspondence vector computation has no owner. The "
        "Correspondence Substrate (CS) was frozen as the module "
        "responsible for producing CorrespondenceVector values. The "
        "current pipeline (sublimator -> claims -> atoms -> geometry) "
        "has no step that actually computes a vector from a claim. "
        "Resolve by explicitly choosing one: (1) revive CS as a "
        "standalone module between claims.py and atoms.py, (2) fold "
        "vector computation into SemanticSublimator, or (3) fold it "
        "into a new, clearly-scoped step in geometry.py — this would "
        "contradict geometry's current 'distance only' scope and "
        "needs re-justifying if chosen. Not yet decided."
    ),
    blocks=(
        "Nothing that depends on a populated CorrespondenceVector "
        "(geometry, re-challenge neighbor variance, HLSF placement) "
        "is real until this is resolved. Highest-priority gap in the "
        "registry."
    ),
    status=GapStatus.OPEN,
    depends_on=("GAP_F",),
)

GAP_COV_HISTORY = Gap(
    id="GAP_COV_HISTORY",
    owner_module="vault (unowned)",
    description=(
        "Vault statistical snapshot/history persistence. The vault "
        "does not currently retain its covariance matrix across "
        "updates at all — this is a data-availability gap, separate "
        "from the statistical policy question of what counts as "
        "'stable.' Split out from GAP_STABILITY so the module "
        "boundary between 'can we observe history' and 'is history "
        "stable' stays clean."
    ),
    blocks="GAP_STABILITY cannot be implemented without this.",
    status=GapStatus.OPEN,
)

GAP_VECTOR_HISTORY = Gap(
    id="GAP_VECTOR_HISTORY",
    owner_module="vault (unowned)",
    description=(
        "Per-atom correspondence-vector history over time. Same "
        "split as GAP_COV_HISTORY but for individual atoms rather "
        "than the vault's aggregate covariance — required so drift "
        "velocity measures atom-level change, not the covariance "
        "matrix's own rate of change (that's stability's job)."
    ),
    blocks="GAP_DRIFT cannot be implemented without this.",
    status=GapStatus.OPEN,
    depends_on=("GAP_A",),
)

GAP_STABILITY = Gap(
    id="GAP_STABILITY",
    owner_module="correspondence_geometry.covariance_stability_check",
    description=(
        "covariance_stability_check has no computable definition. "
        "Proposed but undecided: Frobenius norm of the change in the "
        "vault's covariance matrix across the last N updates, staying "
        "below some epsilon. Currently raises NotImplementedError "
        "rather than a fake True."
    ),
    blocks=(
        "MahalanobisGate condition 2 of 4 — the gate cannot engage "
        "until this closes."
    ),
    status=GapStatus.OPEN,
    depends_on=("GAP_COV_HISTORY",),
)

GAP_DRIFT = Gap(
    id="GAP_DRIFT",
    owner_module="correspondence_geometry.drift_velocity_check",
    description=(
        "drift_velocity_check has no computable definition, and risks "
        "redundancy with GAP_STABILITY if not defined distinctly. "
        "Proposed direction: measure the rate of change of individual "
        "atoms' correspondence vectors over time. If eventually "
        "implemented to measure the same underlying quantity as "
        "GAP_STABILITY, the two checks are redundant and one should "
        "be removed rather than both kept for symmetry."
    ),
    blocks=(
        "MahalanobisGate condition 4 of 4 — same effect as "
        "GAP_STABILITY: the gate cannot engage until this closes."
    ),
    status=GapStatus.OPEN,
    depends_on=("GAP_A", "GAP_VECTOR_HISTORY"),
)

GAP_C = Gap(
    id="GAP_C",
    owner_module="beams (unowned)",
    description=(
        "Beam role is possibly circular, not yet stated as "
        "intentional. Beams were proposed both as generators of "
        "evidence (upstream, feeding EvidenceItem) and as consumers "
        "of geometrically-placed knowledge (downstream). If both are "
        "true, the system is recursive: beams reason over atoms "
        "partly derived from their own prior output. May be "
        "acceptable, but needs an explicit invariant (e.g. a beam "
        "cannot be influenced by an atom it most recently produced "
        "without an intervening validation step) or it risks "
        "self-reinforcing drift."
    ),
    blocks="No enforced invariant currently exists against self-reinforcing drift.",
    status=GapStatus.OPEN,
)

GAP_D = Gap(
    id="GAP_D",
    owner_module="Fifth Mind (unowned)",
    description=(
        "Fifth Mind scope undecided. Recommendation on the table, not "
        "yet ratified or rejected: keep Fifth Mind scoped to "
        "beam-disagreement entropy only; introduce a separately-named "
        "signal ('correspondence variance') for uncertainty across "
        "the five correspondence dimensions, rather than overloading "
        "'entropy' to mean two different things."
    ),
    blocks="No downstream code currently depends on this being resolved.",
    status=GapStatus.OPEN,
)

GAP_ECM = Gap(
    id="GAP_ECM",
    owner_module="ECM (does not exist)",
    description=(
        "ECM does not exist yet. Confirmed directly by the project "
        "owner: ECM is spec-only, not built. Every reference in this "
        "scaffold to 'escalation' (re-challenge triggers, high "
        "variance, beam divergence) currently has no real "
        "destination. Either build ECM next, or give escalation an "
        "explicit interim destination (log / human-review queue / "
        "clearly marked no-op) so 'escalates to ECM' is never a "
        "documented behavior with nothing behind it."
    ),
    blocks="Every documented 'escalates to ECM' behavior in the scaffold.",
    status=GapStatus.OPEN,
)

GAP_FEEDBACK = Gap(
    id="GAP_FEEDBACK",
    owner_module="challenge.py (unowned addition)",
    description=(
        "No antifragile feedback loop on successful re-challenge. "
        "When a re-challenge reverses a finding, nothing currently "
        "propagates that correction back to the atom's source or "
        "provenance, and nothing down-weights that source for future "
        "corroboration. As specified, the system is robust (corrects "
        "the one atom) but not antifragile (doesn't get harder to "
        "fool the same way twice). Likely the single highest-value "
        "addition relative to the project's stated goal, once GAP_A "
        "and GAP_F are resolved."
    ),
    blocks="Source down-weighting and provenance-level correction propagation.",
    status=GapStatus.OPEN,
    depends_on=("GAP_A", "GAP_F"),
)

GAP_PROBATION = Gap(
    id="GAP_PROBATION",
    owner_module="unowned",
    description=(
        "No bounded window between 'error introduced' and 'error "
        "detectable.' A bad sublimation or a bad correspondence "
        "vector can sit in the vault, influencing retrieval, for up "
        "to max_cycles_without_revalidation cycles before a "
        "re-challenge trigger fires. Consider a probationary period "
        "for newly-placed atoms — tighter re-challenge sensitivity, "
        "reduced influence weight on neighbors — until an atom has "
        "survived some minimum number of cycles or been "
        "independently corroborated. Not yet designed."
    ),
    blocks="No probation mechanism currently limits a fresh atom's influence.",
    status=GapStatus.OPEN,
)

ALL_GAPS = {
    gap.id: gap
    for gap in (
        GAP_F, GAP_A, GAP_COV_HISTORY, GAP_VECTOR_HISTORY,
        GAP_STABILITY, GAP_DRIFT, GAP_C, GAP_D, GAP_ECM,
        GAP_FEEDBACK, GAP_PROBATION,
    )
}


def validate_registry() -> None:
    """
    Cheap deterministic self-check so this file can't silently drift
    out of consistency with itself.
    """
    seen = set()
    for key, gap in ALL_GAPS.items():
        if key != gap.id:
            raise ValueError(f"Registry key {key!r} does not match gap.id {gap.id!r}")
        if gap.id in seen:
            raise ValueError(f"Duplicate gap id: {gap.id}")
        seen.add(gap.id)
        for dep in gap.depends_on:
            if dep not in ALL_GAPS:
                raise ValueError(f"{gap.id} depends on unknown gap {dep}")


def open_gaps() -> list:
    """Gaps with status exactly OPEN (not IN_PROGRESS)."""
    return [g for g in ALL_GAPS.values() if g.status is GapStatus.OPEN]


def unresolved_gaps() -> list:
    """Gaps that are OPEN or IN_PROGRESS — i.e. not yet CLOSED."""
    return [g for g in ALL_GAPS.values() if g.status is not GapStatus.CLOSED]


def unresolved_dependencies(gap_id: str) -> list:
    """Why can't gap_id be closed yet? Its own unresolved prerequisites."""
    gap = ALL_GAPS[gap_id]
    return [ALL_GAPS[dep] for dep in gap.depends_on if ALL_GAPS[dep].status is not GapStatus.CLOSED]