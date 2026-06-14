"""Grade a base design brief across a chosen size run.

Grading scales the base-size finished measurements up and down by each point's
per-size grade increment. The maths is intentionally simple and transparent:

    value(size) = base_cm + grade_cm * steps_from_base(size, base_size)

Rounded to one decimal (millimetre-ish), which matches how POM charts are spec'd.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..schemas import DesignBrief
from .sizes import DEFAULT_SYSTEM, steps_from_base, validate_size_run


@dataclass(frozen=True)
class GradedPoint:
    """One point of measure with its value computed for each size in the run."""

    code: str
    name: str
    tolerance_cm: float
    values_by_size: dict[str, float]  # size -> finished cm


@dataclass(frozen=True)
class GradedTechPack:
    """A fully resolved tech pack: the brief plus the graded POM table."""

    brief: DesignBrief
    sizes: list[str]  # ordered small -> large
    base_size: str
    points: list[GradedPoint]
    system: str = DEFAULT_SYSTEM


def grade(
    brief: DesignBrief,
    sizes: list[str],
    base_size: str | None = None,
    system: str = DEFAULT_SYSTEM,
) -> GradedTechPack:
    """Grade `brief` across `sizes` within a size `system` (alpha | eu-women | eu-men).

    `base_size` defaults to the brief's own base size. The base must be one of
    the chosen sizes (validated here).
    """
    base = base_size if base_size is not None else brief.base_size
    ordered, base = validate_size_run(sizes, base, system)

    points: list[GradedPoint] = []
    for pom in brief.points_of_measure:
        values = {
            size: round(pom.base_cm + pom.grade_cm * steps_from_base(size, base, system), 1)
            for size in ordered
        }
        points.append(
            GradedPoint(
                code=pom.code,
                name=pom.name,
                tolerance_cm=pom.tolerance_cm,
                values_by_size=values,
            )
        )

    return GradedTechPack(brief=brief, sizes=ordered, base_size=base, points=points, system=system)
