"""Resolve a Cyrillic-capable TrueType font for PDF rendering.

ReportLab's built-in Helvetica only covers Latin-1, so Bulgarian (Cyrillic) text
renders blank. We register a Unicode TTF that includes Cyrillic — preferring a
bundled DejaVu (portable, has a bold face), then common Linux locations, then
macOS's Arial Unicode. English falls back to Helvetica if none is found; Bulgarian
requires one (we raise a clear error otherwise).
"""
from __future__ import annotations

from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .. import config

FONT_NORMAL = "AtelierSans"
FONT_BOLD = "AtelierSans-Bold"

_FONT_DIR = config.PROJECT_ROOT / "assets" / "fonts"

_NORMAL_CANDIDATES = [
    _FONT_DIR / "DejaVuSans.ttf",
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
]
_BOLD_CANDIDATES = [
    _FONT_DIR / "DejaVuSans-Bold.ttf",
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
]

_HELVETICA = ("Helvetica", "Helvetica-Bold")
_registered = False


def _first_existing(paths: list[Path]) -> Path | None:
    return next((p for p in paths if p.exists()), None)


def resolve_fonts(require_cyrillic: bool = False) -> tuple[str, str]:
    """Return (normal, bold) font names usable by ReportLab.

    Registers a Unicode font on first use. If none is found: raise when
    `require_cyrillic` (e.g. Bulgarian), else fall back to Helvetica.
    """
    global _registered

    normal = _first_existing(_NORMAL_CANDIDATES)
    if normal is None:
        if require_cyrillic:
            raise RuntimeError(
                "No Cyrillic-capable font found for Bulgarian output. "
                "Install DejaVu fonts or bundle assets/fonts/DejaVuSans.ttf."
            )
        return _HELVETICA

    if not _registered:
        pdfmetrics.registerFont(TTFont(FONT_NORMAL, str(normal)))
        bold = _first_existing(_BOLD_CANDIDATES) or normal  # reuse normal if no bold face
        pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold)))
        pdfmetrics.registerFontFamily(
            FONT_NORMAL, normal=FONT_NORMAL, bold=FONT_BOLD,
            italic=FONT_NORMAL, boldItalic=FONT_BOLD,
        )
        _registered = True

    return (FONT_NORMAL, FONT_BOLD)
