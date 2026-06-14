"""Tech-pack generation: design brief -> graded spec -> downloadable documents.

The Atelier product turns inspiration images + design notes into a sewer-ready
tech pack. This package holds the deterministic core:

- `sizes`     — the canonical size order and validation helpers.
- `grading`   — grade a base `DesignBrief` across a chosen size run.
- `documents` — render a `GradedTechPack` to a PDF and a POM CSV.

The Designer agent (`src/agents/designer.py`) produces the `DesignBrief`; nothing
in this package calls the LLM, so it is fully unit-tested offline.
"""
from __future__ import annotations

from .grading import GradedPoint, GradedTechPack, grade
from .sizes import SIZE_ORDER, order_sizes, validate_size_run

__all__ = [
    "grade",
    "GradedPoint",
    "GradedTechPack",
    "SIZE_ORDER",
    "order_sizes",
    "validate_size_run",
]
