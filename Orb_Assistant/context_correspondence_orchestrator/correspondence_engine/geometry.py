"""
Correspondence Geometry — MANDATORY module boundary, PARTIAL
implementation.

Owns:
  weighted_euclidean_distance()      — implemented
  regularized_mahalanobis_distance() — implemented
  covariance_stability_check()       — STUB, see gaps.py: GAP_STABILITY
  drift_velocity_check()             — STUB, see gaps.py: GAP_DRIFT
  MahalanobisGate                    — structure frozen, checks stubbed

Does NOT own: claim extraction (sublimator.py), correspondence
vector computation (unowned — see gaps.py: GAP_A).

Metric selection uses hysteresis (engage-strict / release-loose),
following TPC's own HLSF vivacity decay pattern (trigger 700 /
release 520), rather than a single flip threshold that would flap
under ordinary vault noise.
"""

import math
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from .vectors import CorrespondenceVector


def weighted_euclidean_distance(
    a: CorrespondenceVector,
    b: CorrespondenceVector,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Default, always-available metric. Stable with small vault size.
    Correct and complete as specified — use this until the
    MahalanobisGate conditions are actually met.
    """
    dims = CorrespondenceVector.dimension_names()
    w = weights or {d: 1.0 for d in dims}
    total = 0.0
    for d in dims:
        diff = getattr(a, d) - getattr(b, d)
        total += w.get(d, 1.0) * (diff ** 2)
    return math.sqrt(total)


def regularized_mahalanobis_distance(
    a: CorrespondenceVector,
    b: CorrespondenceVector,
    inv_covariance: np.ndarray,
) -> float:
    """
    Covariance-aware distance. Only ever called once MahalanobisGate
    confirms all four activation conditions — this function itself
    does not check them, by design, so it can be unit-tested in
    isolation from vault-maturity logic.
    """
    va = np.array(a.as_tuple())
    vb = np.array(b.as_tuple())
    diff = (va - vb).reshape(-1, 1)
    dist_sq = float(diff.T @ inv_covariance @ diff)
    return math.sqrt(max(0.0, dist_sq))


def covariance_stability_check(vault, window: int, epsilon: float) -> bool:
    """
    STUB. Not implemented.

    Proposed but undecided definition: Frobenius norm of the change
    in the vault's covariance matrix S across the last `window`
    vault updates, staying below `epsilon`. Requires the vault to
    retain covariance history, which it does not currently do.

    See gaps.py: GAP_STABILITY. Deliberately raises rather than
    returning a placeholder `True` — a fake pass here would
    silently defeat the exact gate it exists to guard.
    """
    raise NotImplementedError(
        "covariance_stability_check is undesigned. See gaps.py: GAP_STABILITY."
    )


def drift_velocity_check(vault, window: int, max_velocity: float) -> bool:
    """
    STUB. Not implemented.

    Must measure something DIFFERENT from covariance_stability_check
    — e.g. rate of change of individual atoms' correspondence
    vectors over time, not the covariance matrix's own rate of
    change (that's stability's job). If implemented to measure the
    same thing, the two gates become redundant and one should be
    removed. See gaps.py: GAP_DRIFT.
    """
    raise NotImplementedError(
        "drift_velocity_check is undesigned. See gaps.py: GAP_DRIFT."
    )


@dataclass
class MahalanobisGateConfig:
    # NOTE: all values below are Phase 1 empirical targets, not final.
    min_claims_for_mahalanobis: int = 250       # TODO: validate empirically
    engage_condition_number_max: float = 1e6    # stricter — required to ENGAGE
    release_condition_number_max: float = 1e8   # looser — required to stay engaged (prevents flapping)
    stability_window: int = 20                  # TODO: validate empirically
    stability_epsilon: float = 1e-3             # TODO: validate empirically
    drift_window: int = 20                      # TODO: validate empirically
    drift_max_velocity: float = 0.1             # TODO: validate empirically


class MahalanobisGate:
    """
    Implements the 4-condition activation invariant with hysteresis:
      1. vault_maturity_passed       — vault size >= min_claims
      2. covariance_stability_passed — STUBBED
      3. condition_number_passed     — implemented, with hysteresis
      4. drift_velocity_nonchaotic   — STUBBED

    Because 2 and 4 are stubbed, this gate currently always raises
    NotImplementedError before it can engage Mahalanobis. That is
    intentional: it must fail loudly, never silently default to
    "safe," which would misrepresent this gate as complete.
    """

    def __init__(self, config: Optional[MahalanobisGateConfig] = None):
        self.config = config or MahalanobisGateConfig()
        self._engaged = False  # hysteresis state

    def _vault_maturity_passed(self, vault) -> bool:
        return len(vault.atoms) >= self.config.min_claims_for_mahalanobis

    def _condition_number_passed(self, covariance: np.ndarray) -> bool:
        cond = np.linalg.cond(covariance)
        threshold = (
            self.config.release_condition_number_max
            if self._engaged
            else self.config.engage_condition_number_max
        )
        return cond <= threshold

    def should_use_mahalanobis(self, vault) -> bool:
        if not self._vault_maturity_passed(vault):
            self._engaged = False
            return False

        covariance = vault.covariance_matrix()

        stable = covariance_stability_check(
            vault, self.config.stability_window, self.config.stability_epsilon
        )
        cond_ok = self._condition_number_passed(covariance)
        nonchaotic = drift_velocity_check(
            vault, self.config.drift_window, self.config.drift_max_velocity
        )

        self._engaged = stable and cond_ok and nonchaotic
        return self._engaged


def metric_selector_with_hysteresis(vault, gate: MahalanobisGate):
    """Returns ("mahalanobis", inv_covariance) or ("euclidean", None)."""
    if gate.should_use_mahalanobis(vault):
        cov = vault.covariance_matrix()
        inv_cov = np.linalg.pinv(cov)
        return "mahalanobis", inv_cov
    return "euclidean", None
