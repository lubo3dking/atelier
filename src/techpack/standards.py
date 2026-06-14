"""European standard body-measurement reference (EN 13402 / EN ISO 8559).

These are the *body* measurements (in cm) the European numeric sizes are designed
to fit — not finished-garment measurements. They are included in the tech pack as
a reference size chart so a workshop can sanity-check the spec against the
standard. Values follow EN 13402-3 (women: bust = size + 50, +4 cm/step; men:
chest = size x 2, +4 cm/step).
"""
from __future__ import annotations

# size -> (bust, waist, hip) for women; (chest, waist, hip) for men.
EU_WOMEN_BODY: dict[str, tuple[int, int, int]] = {
    "32": (76, 60, 84),
    "34": (80, 64, 88),
    "36": (84, 68, 92),
    "38": (88, 72, 96),
    "40": (92, 76, 100),
    "42": (96, 80, 104),
    "44": (100, 84, 108),
    "46": (104, 88, 112),
    "48": (108, 92, 116),
    "50": (112, 96, 120),
}

EU_MEN_BODY: dict[str, tuple[int, int, int]] = {
    "44": (88, 76, 92),
    "46": (92, 80, 96),
    "48": (96, 84, 100),
    "50": (100, 88, 104),
    "52": (104, 92, 108),
    "54": (108, 96, 112),
    "56": (112, 100, 116),
    "58": (116, 104, 120),
}

# Which girth label heads the chart for each system.
_GIRTH_LABEL = {"eu-women": "bust", "eu-men": "chest"}
_TABLE = {"eu-women": EU_WOMEN_BODY, "eu-men": EU_MEN_BODY}


def has_body_chart(system: str) -> bool:
    return system in _TABLE


def body_chart(system: str, sizes: list[str]) -> tuple[str, list[tuple[str, int, int, int]]] | None:
    """Return (girth_label, rows) for the chosen sizes, or None if no standard chart.

    Each row is (size, girth, waist, hip). Sizes absent from the standard table
    are skipped (e.g. an out-of-range custom size).
    """
    if system not in _TABLE:
        return None
    table = _TABLE[system]
    rows = [(s, *table[s]) for s in sizes if s in table]
    if not rows:
        return None
    return _GIRTH_LABEL[system], rows
