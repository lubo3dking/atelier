"""Size systems and size-run validation.

Sizes are graded relative to a base size, so each system is a single ordered
scale and grading counts steps along it. Three systems are supported:

- ``alpha``    — XXS … XXXL (default).
- ``eu-women`` — European women's numeric 32 … 50 (EN 13402, +4 cm bust/step).
- ``eu-men``   — European men's numeric 44 … 58 (chest girth, +4 cm/step).

Brand owners pick which sizes from a system to include in a product's run.
"""
from __future__ import annotations

SIZE_SYSTEMS: dict[str, tuple[str, ...]] = {
    "alpha": ("XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL"),
    "eu-women": ("32", "34", "36", "38", "40", "42", "44", "46", "48", "50"),
    "eu-men": ("44", "46", "48", "50", "52", "54", "56", "58"),
}
DEFAULT_SYSTEM = "alpha"

# Conventional base size (centre of the run) per system, used when none is given.
DEFAULT_BASE = {"alpha": "M", "eu-women": "38", "eu-men": "50"}

# Backwards-compatible alias (the original alpha-only scale).
SIZE_ORDER: tuple[str, ...] = SIZE_SYSTEMS["alpha"]


def _check_system(system: str) -> None:
    if system not in SIZE_SYSTEMS:
        raise ValueError(
            f"Unknown size system: {system}. Valid: {', '.join(SIZE_SYSTEMS)}"
        )


def _index_map(system: str) -> dict[str, int]:
    return {s: i for i, s in enumerate(SIZE_SYSTEMS[system])}


def _normalise(size: str) -> str:
    return size.strip().upper()


def order_sizes(sizes: list[str], system: str = DEFAULT_SYSTEM) -> list[str]:
    """Return the given sizes deduplicated and sorted along the system's scale."""
    _check_system(system)
    idx = _index_map(system)
    cleaned = {_normalise(s) for s in sizes}
    unknown = sorted(s for s in cleaned if s not in idx)
    if unknown:
        raise ValueError(
            f"Unknown size(s) for {system}: {', '.join(unknown)}. "
            f"Valid: {', '.join(SIZE_SYSTEMS[system])}"
        )
    return sorted(cleaned, key=lambda s: idx[s])


def validate_size_run(
    sizes: list[str], base_size: str, system: str = DEFAULT_SYSTEM
) -> tuple[list[str], str]:
    """Validate a size run and its base, returning them normalised.

    The base size must be one of the chosen sizes. Returns (ordered_sizes, base).
    """
    _check_system(system)
    if not sizes:
        raise ValueError("A size run must contain at least one size.")
    ordered = order_sizes(sizes, system)
    base = _normalise(base_size)
    if base not in _index_map(system):
        raise ValueError(
            f"Unknown base size for {system}: {base_size}. "
            f"Valid: {', '.join(SIZE_SYSTEMS[system])}"
        )
    if base not in ordered:
        raise ValueError(
            f"Base size {base} must be one of the chosen sizes: {', '.join(ordered)}"
        )
    return ordered, base


def steps_from_base(size: str, base_size: str, system: str = DEFAULT_SYSTEM) -> int:
    """Signed number of size steps `size` is from `base_size` (negative = smaller)."""
    idx = _index_map(system)
    return idx[_normalise(size)] - idx[_normalise(base_size)]
