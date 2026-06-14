"""Render a `FlatSketch` (SVG path data) to a ReportLab drawing — no SVG library.

Claude emits flat sketches as SVG path 'd' strings in a 100x140 box (origin
top-left, y down). We parse the common path commands (M L H V C Q Z, absolute
and relative) into ReportLab's vector `Path`, flipping y to ReportLab's
bottom-left origin. Unsupported commands (arcs, smooth curves) are intentionally
excluded — the Designer prompt tells the model not to use them.
"""
from __future__ import annotations

import re

from reportlab.graphics.shapes import Drawing, Path, String
from reportlab.lib import colors

from ..schemas import FlatSketch

BOX_W = 100.0
BOX_H = 140.0
_INK = colors.HexColor("#1E2230")
_INDIGO = colors.HexColor("#6366F1")

_TOKEN = re.compile(r"[MmLlHhVvCcQqZz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?")

# Line-weight hierarchy by path kind (technical-flat convention): outline
# heaviest, internal seams medium, topstitch thin + dashed, rib hatching light.
# (strokeWidth in box units; the drawing is scaled up to the page afterwards.)
_KIND_STYLE = {
    "outline": (1.6, None),
    "hem": (1.1, None),
    "seam": (0.8, None),
    "detail": (0.7, None),
    "rib": (0.5, None),
    "topstitch": (0.5, (1.4, 1.4)),  # dashed
}


def _svg_path_to_rl(d: str, stroke, width: float, dash=None) -> Path:
    """Parse one SVG path 'd' string into a ReportLab Path (y-flipped)."""
    tokens = _TOKEN.findall(d)
    path = Path(strokeColor=stroke, strokeWidth=width, fillColor=None)
    if dash:
        path.strokeDashArray = list(dash)
    i, n = 0, len(tokens)
    cx = cy = sx = sy = 0.0
    cmd = None
    started = False

    def num() -> float:
        nonlocal i
        v = float(tokens[i])
        i += 1
        return v

    def fy(y: float) -> float:
        return BOX_H - y

    while i < n:
        if tokens[i] in "MmLlHhVvCcQqZz":
            cmd = tokens[i]
            i += 1
        if cmd in ("M", "m"):
            x, y = num(), num()
            if cmd == "m" and started:
                x += cx; y += cy
            cx, cy = x, y
            sx, sy = x, y
            path.moveTo(cx, fy(cy))
            started = True
            cmd = "l" if cmd == "m" else "L"  # extra pairs become line-tos
        elif cmd in ("L", "l"):
            x, y = num(), num()
            if cmd == "l":
                x += cx; y += cy
            cx, cy = x, y
            path.lineTo(cx, fy(cy))
        elif cmd in ("H", "h"):
            x = num()
            cx = cx + x if cmd == "h" else x
            path.lineTo(cx, fy(cy))
        elif cmd in ("V", "v"):
            y = num()
            cy = cy + y if cmd == "v" else y
            path.lineTo(cx, fy(cy))
        elif cmd in ("C", "c"):
            x1, y1, x2, y2, x, y = num(), num(), num(), num(), num(), num()
            if cmd == "c":
                x1 += cx; y1 += cy; x2 += cx; y2 += cy; x += cx; y += cy
            path.curveTo(x1, fy(y1), x2, fy(y2), x, fy(y))
            cx, cy = x, y
        elif cmd in ("Q", "q"):
            qx, qy, x, y = num(), num(), num(), num()
            if cmd == "q":
                qx += cx; qy += cy; x += cx; y += cy
            # quadratic -> cubic control points
            c1x, c1y = cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy)
            c2x, c2y = x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y)
            path.curveTo(c1x, fy(c1y), c2x, fy(c2y), x, fy(y))
            cx, cy = x, y
        elif cmd in ("Z", "z"):
            path.closePath()
            cx, cy = sx, sy
        else:
            i += 1  # unknown token, skip defensively
    return path


def sketch_drawing(sketch: FlatSketch, target_w: float, label_font: str) -> Drawing:
    """Build a scaled ReportLab Drawing for one flat sketch.

    `target_w` is the desired width in points; height keeps the box aspect ratio.
    Malformed individual paths are skipped rather than failing the whole sketch.
    """
    d = Drawing(BOX_W, BOX_H)
    for idx, sp in enumerate(sketch.paths or []):
        # First path defaults to the outline if the model didn't tag it.
        kind = sp.kind if sp.kind in _KIND_STYLE else ("outline" if idx == 0 else "seam")
        width, dash = _KIND_STYLE[kind]
        try:
            d.add(_svg_path_to_rl(sp.d, _INK, width, dash))
        except (ValueError, IndexError):
            continue
    for lb in sketch.labels or []:
        try:
            d.add(String(lb.x, BOX_H - lb.y, str(lb.text),
                         fontName=label_font, fontSize=4.2, fillColor=_INDIGO))
        except (ValueError, TypeError):
            continue

    scale = target_w / BOX_W
    d.scale(scale, scale)
    d.width = BOX_W * scale
    d.height = BOX_H * scale
    return d
