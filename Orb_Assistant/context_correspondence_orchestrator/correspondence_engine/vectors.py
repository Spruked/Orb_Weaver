"""
CorrespondenceVector — MANDATORY / FROZEN.

Replaces the bare `dict` originally proposed for correspondence
vectors. A bare dict allowed silent misspellings, missing dimensions,
and out-of-range values to pass through undetected — the same
failure class that broke the v0.2 scoring engine. This class makes
that class of error impossible to construct.

NOTE: nothing in this file computes a CorrespondenceVector from a
claim or from evidence. See gaps.py: GAP_A — no module currently
owns that computation. This file only defines the validated shape
once a vector exists.

All correspondence dimensions are finite numeric values normalized
to the closed interval [0.0, 1.0].

This object is immutable. Downstream geometry may read its values,
but may not mutate the vector after construction.
"""

import math
from dataclasses import dataclass, fields
from typing import Tuple


@dataclass(frozen=True)
class CorrespondenceVector:
    reality: float
    representation: float
    purpose: float
    personhood: float
    continuity: float

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)

            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"{f.name} must be numeric, got "
                    f"{type(value).__name__}"
                )

            if not math.isfinite(float(value)):
                raise ValueError(
                    f"{f.name} must be finite, got {value}"
                )

            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(
                    f"{f.name} must be in [0,1], got {value}"
                )

    def as_tuple(self) -> Tuple[float, float, float, float, float]:
        return (
            self.reality,
            self.representation,
            self.purpose,
            self.personhood,
            self.continuity,
        )

    @staticmethod
    def dimension_names() -> Tuple[str, str, str, str, str]:
        return (
            "reality",
            "representation",
            "purpose",
            "personhood",
            "continuity",
        )