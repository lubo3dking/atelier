"""Parametric technical-flat engine.

Instead of asking the model to draw raw coordinates (unreliable), the Designer
classifies the garment into a `SketchSpec` (silhouette + options) and this module
generates clean, symmetric, correctly-proportioned flats in code. Everything is
built on the left of the centre-front line (x=50) and mirrored, so symmetry is
guaranteed. Line-weight `kind`s follow technical-flat convention.

Coordinate box: 100 wide x 140 tall, origin top-left (matches sketch.py).
"""
from __future__ import annotations

from ..schemas import FlatSketch, SketchLabel, SketchPath, SketchSpec

CF = 50.0  # centre front


def _n(v: float) -> str:
    return f"{v:.1f}"


def _mir(x: float) -> float:
    return 100.0 - x


def _circle(cx: float, cy: float, r: float) -> str:
    k = 0.5523 * r
    return (
        f"M{_n(cx - r)} {_n(cy)}"
        f"C{_n(cx - r)} {_n(cy - k)} {_n(cx - k)} {_n(cy - r)} {_n(cx)} {_n(cy - r)}"
        f"C{_n(cx + k)} {_n(cy - r)} {_n(cx + r)} {_n(cy - k)} {_n(cx + r)} {_n(cy)}"
        f"C{_n(cx + r)} {_n(cy + k)} {_n(cx + k)} {_n(cy + r)} {_n(cx)} {_n(cy + r)}"
        f"C{_n(cx - k)} {_n(cy + r)} {_n(cx - r)} {_n(cy + k)} {_n(cx - r)} {_n(cy)}Z"
    )


def _rib_band(x0: float, x1: float, y0: float, y1: float, step: float = 2.6) -> list[SketchPath]:
    """Vertical hatch lines for a knit rib band."""
    paths = []
    x = x0 + step
    while x < x1 - 0.1:
        paths.append(SketchPath(d=f"M{_n(x)} {_n(y0)} L{_n(x)} {_n(y1)}", kind="rib"))
        x += step
    return paths


# --- TOPS / DRESSES ---------------------------------------------------------

def _build_top(spec: SketchSpec, dress: bool = False):
    fit = spec.fit
    neckline = spec.neckline
    sleeve = spec.sleeve
    opening = spec.opening

    shoulder_y, neck_y, underarm_y = 18.0, 15.0, 46.0
    hem_y = 132.0 if dress else (98.0 if fit == "cropped" else 122.0)
    waist_y = 66.0

    shoulder_x, chest_x = 18.0, 17.0
    if fit == "fitted":
        waist_x, hem_x = 25.0, 21.0
    elif fit == "boxy":
        waist_x, hem_x = 16.5, 15.5
    elif fit == "cropped":
        waist_x, hem_x = 20.0, 18.5
    else:
        waist_x, hem_x = 21.0, 18.0
    if dress:
        waist_x, hem_x = 27.0, 8.0  # nip the waist, flare the skirt

    neck_half = 9.0
    neck_dip = 42.0 if neckline == "v" else 23.0

    def torso(front: bool) -> str:
        nd = neck_dip if front else (neck_y + 4.0)  # back neck is shallow
        d = [f"M{_n(shoulder_x)} {_n(shoulder_y)}", f"L{_n(CF - neck_half)} {_n(neck_y)}"]
        if neckline == "v" and front:
            d.append(f"L{_n(CF)} {_n(nd)}L{_n(_mir(CF - neck_half))} {_n(neck_y)}")
        else:
            d.append(f"Q{_n(CF)} {_n(nd)} {_n(_mir(CF - neck_half))} {_n(neck_y)}")
        d.append(f"L{_n(_mir(shoulder_x))} {_n(shoulder_y)}")
        # right side down
        d.append(f"L{_n(_mir(chest_x))} {_n(underarm_y)}")
        d.append(f"Q{_n(_mir(chest_x - 2))} {_n(waist_y - 6)} {_n(_mir(waist_x))} {_n(waist_y)}")
        d.append(f"Q{_n(_mir(hem_x + 3))} {_n(hem_y - 14)} {_n(_mir(hem_x))} {_n(hem_y)}")
        # hem
        if spec.hem == "curved":
            d.append(f"Q{_n(CF)} {_n(hem_y + 6)} {_n(hem_x)} {_n(hem_y)}")
        else:
            d.append(f"L{_n(hem_x)} {_n(hem_y)}")
        # left side up
        d.append(f"Q{_n(hem_x + 3)} {_n(hem_y - 14)} {_n(waist_x)} {_n(waist_y)}")
        d.append(f"Q{_n(chest_x - 2)} {_n(waist_y - 6)} {_n(chest_x)} {_n(underarm_y)}")
        d.append(f"L{_n(shoulder_x)} {_n(shoulder_y)}Z")
        return "".join(d)

    def sleeves() -> list[SketchPath]:
        if sleeve == "none":
            return []
        if sleeve == "short":
            cuff_y, out_x, cuff_w = 66.0, 6.0, 16.0
        else:
            cuff_y, out_x, cuff_w = (hem_y - 6.0), 7.0, 9.0
        cuff_in = out_x + cuff_w
        out = []
        for m in (False, True):
            sx = _mir(shoulder_x) if m else shoulder_x
            ox = _mir(out_x) if m else out_x
            cin = _mir(cuff_in) if m else cuff_in
            cx = _mir(chest_x) if m else chest_x
            c1x = _mir(shoulder_x - 9) if m else (shoulder_x - 9)
            out.append(SketchPath(
                d=(f"M{_n(sx)} {_n(shoulder_y)}"
                   f"C{_n(c1x)} {_n(shoulder_y + 10)} {_n(ox)} {_n(underarm_y + 4)} {_n(ox)} {_n(cuff_y)}"
                   f"L{_n(cin)} {_n(cuff_y)}"
                   f"L{_n(cx)} {_n(underarm_y)}Z"),
                kind="outline"))
            if spec.cuff == "rib":
                lo, hi = (min(ox, cin), max(ox, cin))
                out += _rib_band(lo, hi, cuff_y - 8, cuff_y)
        return out

    def details(front: bool) -> list[SketchPath]:
        out = []
        if spec.hem == "rib":
            out += _rib_band(hem_x + 1, _mir(hem_x + 1), hem_y - 9, hem_y - 0.5)
        if front:
            top = neck_dip if neckline == "v" else 24.0
            if opening in ("placket", "full"):
                out.append(SketchPath(d=f"M{_n(CF - 3)} {_n(top)}L{_n(CF - 3)} {_n(hem_y)}", kind="detail"))
                out.append(SketchPath(d=f"M{_n(CF + 3)} {_n(top)}L{_n(CF + 3)} {_n(hem_y)}", kind="detail"))
            nb = spec.buttons if spec.buttons else (6 if opening == "full" else 0)
            if nb:
                y0, y1 = top + 5, hem_y - 7
                for i in range(nb):
                    cy = y0 + (y1 - y0) * (i / max(1, nb - 1))
                    out.append(SketchPath(d=_circle(CF, cy, 1.4), kind="detail"))
            if spec.pocket == "patch":
                out.append(SketchPath(d=f"M{_n(26)} {_n(74)}L{_n(40)} {_n(74)}L{_n(40)} {_n(90)}L{_n(26)} {_n(90)}Z", kind="detail"))
            elif spec.pocket == "chest":
                out.append(SketchPath(d=f"M{_n(24)} {_n(40)}L{_n(34)} {_n(40)}L{_n(34)} {_n(52)}L{_n(24)} {_n(52)}Z", kind="detail"))
        else:
            # back yoke for collared styles
            if neckline == "collar":
                out.append(SketchPath(d=f"M{_n(shoulder_x + 1)} {_n(28)}Q{_n(CF)} {_n(33)} {_n(_mir(shoulder_x + 1))} {_n(28)}", kind="seam"))
        return out

    front_paths = [SketchPath(d=torso(True), kind="outline")] + sleeves() + details(True)
    back_paths = [SketchPath(d=torso(False), kind="outline")] + sleeves() + details(False)

    cuff_y = (66.0 if sleeve == "short" else hem_y - 6.0)
    anchors = {
        "neck_width": (CF, neck_y - 1),
        "neck_drop": (CF + 4, (neck_y + neck_dip) / 2),
        "shoulder": ((shoulder_x + (CF - neck_half)) / 2, shoulder_y - 1),
        "chest": (chest_x + 8, underarm_y + 4),
        "bust": (chest_x + 8, underarm_y + 8),
        "armhole": (chest_x + 1, underarm_y - 8),
        "bicep": (out_x_anchor(spec), underarm_y + 2) if sleeve != "none" else (chest_x + 4, underarm_y + 2),
        "waist": (waist_x + 8, waist_y),
        "hip": (hem_x + 9, hem_y - 10),
        "hem": (CF - 16, hem_y - 2),
        "length": (_mir(chest_x) - 9, (neck_y + hem_y) / 2),
        "sleeve_length": (10, (shoulder_y + cuff_y) / 2),
        "sleeve_opening": (9, cuff_y - 4),
        "cuff": (9, cuff_y - 4),
    }
    return front_paths, back_paths, anchors, anchors


def out_x_anchor(spec):
    return 12.0


# --- BOTTOMS ----------------------------------------------------------------

def _build_bottom(spec: SketchSpec, skirt: bool = False):
    waist_y, hip_y, crotch_y, hem_y = 12.0, 34.0, 48.0, 132.0
    if skirt and spec.leg == "mini":
        hem_y = 78.0
    elif skirt and spec.leg in ("knee",):
        hem_y = 98.0
    elif skirt and spec.leg == "midi":
        hem_y = 116.0
    if not skirt and spec.leg == "short":
        hem_y = 80.0

    waist_x, hip_x = 30.0, 26.0

    paths = []
    if skirt:
        hem_x = 12.0  # A-line flare
        d = (f"M{_n(waist_x)} {_n(waist_y)}"
             f"Q{_n(hip_x - 1)} {_n(hip_y)} {_n(hem_x)} {_n(hem_y)}"
             f"Q{_n(CF)} {_n(hem_y + 5)} {_n(_mir(hem_x))} {_n(hem_y)}"
             f"Q{_n(_mir(hip_x - 1))} {_n(hip_y)} {_n(_mir(waist_x))} {_n(waist_y)}"
             f"Q{_n(CF)} {_n(waist_y - 4)} {_n(waist_x)} {_n(waist_y)}Z")
        paths.append(SketchPath(d=d, kind="outline"))
        anchors = {
            "waist": (waist_x + 6, waist_y + 2),
            "hip": (hip_x + 4, hip_y),
            "length": (_mir(hip_x) - 4, (waist_y + hem_y) / 2),
            "hem": (CF, hem_y - 3),
            "leg_opening": (CF, hem_y - 3),
        }
    else:
        out_top, hem_out, hem_in = 22.0, 22.0, 42.0
        d = (f"M{_n(waist_x)} {_n(waist_y)}"
             f"L{_n(hip_x)} {_n(hip_y)}"
             f"L{_n(hem_out)} {_n(hem_y)}"
             f"L{_n(hem_in)} {_n(hem_y)}"
             f"L{_n(CF)} {_n(crotch_y)}"
             f"L{_n(_mir(hem_in))} {_n(hem_y)}"
             f"L{_n(_mir(hem_out))} {_n(hem_y)}"
             f"L{_n(_mir(hip_x))} {_n(hip_y)}"
             f"L{_n(_mir(waist_x))} {_n(waist_y)}"
             f"L{_n(waist_x)} {_n(waist_y)}Z")
        paths.append(SketchPath(d=d, kind="outline"))
        # crease lines
        paths.append(SketchPath(d=f"M{_n((hip_x + hem_out) / 2 + 2)} {_n(hip_y + 4)}L{_n((hem_out + hem_in) / 2)} {_n(hem_y - 2)}", kind="detail"))
        paths.append(SketchPath(d=f"M{_n(_mir((hip_x + hem_out) / 2 + 2))} {_n(hip_y + 4)}L{_n(_mir((hem_out + hem_in) / 2))} {_n(hem_y - 2)}", kind="detail"))
        if spec.fly:
            paths.append(SketchPath(d=f"M{_n(CF)} {_n(waist_y + 2)}Q{_n(CF - 5)} {_n((waist_y + crotch_y) / 2)} {_n(CF - 2)} {_n(crotch_y - 2)}", kind="topstitch"))
        anchors = {
            "waist": (waist_x + 6, waist_y + 1),
            "hip": (hip_x + 4, hip_y),
            "rise": (CF - 5, (waist_y + crotch_y) / 2),
            "thigh": (hem_in - 6, crotch_y + 6),
            "knee": (hem_in - 8, (crotch_y + hem_y) / 2),
            "inseam": (hem_in - 4, (crotch_y + hem_y) / 2 + 10),
            "outseam": (hem_out - 4, (hip_y + hem_y) / 2),
            "leg_opening": ((hem_out + hem_in) / 2, hem_y - 3),
            "length": (_mir(hem_out) + 2, (waist_y + hem_y) / 2),
        }

    # waistband
    wb = "elastic" if spec.waistband == "elastic" else "plain"
    paths.append(SketchPath(d=f"M{_n(waist_x)} {_n(waist_y + 4)}L{_n(_mir(waist_x))} {_n(waist_y + 4)}", kind="seam"))
    if wb == "elastic":
        paths += _rib_band(waist_x + 1, _mir(waist_x + 1), waist_y - 2, waist_y + 4, step=3.0)
    return paths, list(paths), anchors, anchors


# --- public -----------------------------------------------------------------

def build_sketches(spec: SketchSpec, points) -> list[FlatSketch]:
    """Build front and back FlatSketches for a garment spec, labelling POM codes."""
    if spec.silhouette == "skirt":
        fp, bp, fa, ba = _build_bottom(spec, skirt=True)
    elif spec.silhouette == "bottom":
        fp, bp, fa, ba = _build_bottom(spec, skirt=False)
    elif spec.silhouette == "dress":
        fp, bp, fa, ba = _build_top(spec, dress=True)
    else:
        fp, bp, fa, ba = _build_top(spec)

    return [
        FlatSketch(view="front", paths=fp, labels=_labels(points, fa)),
        FlatSketch(view="back", paths=bp, labels=_labels(points, ba)),
    ]


# Minimum gap (box units) between two POM code labels so they never overlap.
_LABEL_GAP = 6.0


def _labels(points, anchors) -> list[SketchLabel]:
    """Place POM code letters at their anchors, de-collided and off the placket.

    Several points of measure share (or sit very near) the same anchor — e.g.
    chest and bust, or the neck cluster — and the centre-front column carries the
    button placket. Without spacing, the letters pile up and read as broken. We
    nudge each label off the centre line and then stack any remaining collisions
    so every code stays legible.
    """
    placed: list[tuple[float, float]] = []
    out: list[SketchLabel] = []
    for pom in points or []:
        pos = anchors.get((pom.anchor or "").strip().lower())
        if not pos:
            continue
        x, y = float(pos[0]), float(pos[1])
        # Keep labels out of the centre-front placket / button column.
        if abs(x - CF) < 7:
            x = CF - 11
        # Stack downward (then step to a new column) until clear of placed labels.
        for _ in range(40):
            clash = any(abs(px - x) < _LABEL_GAP and abs(py - y) < _LABEL_GAP for px, py in placed)
            if not clash:
                break
            y += _LABEL_GAP
            if y > 134:
                y = float(pos[1])
                x -= _LABEL_GAP
        placed.append((x, y))
        out.append(SketchLabel(x=round(x, 1), y=round(y, 1), text=pom.code))
    return out
