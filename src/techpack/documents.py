"""Render a `GradedTechPack` to downloadable documents: a PDF and a POM CSV.

The PDF is the sewer-facing tech pack (cover info, design notes, graded points
of measure, bill of materials, construction notes). The CSV is the same POM
table in a spreadsheet-friendly form. Both support `lang` ("en" | "bg"): the
static labels are localised and a Cyrillic-capable font is used for Bulgarian.

ReportLab is a pure-Python dependency, so generation works anywhere; the font
(`fonts.py`) is resolved from bundled/system locations.
"""
from __future__ import annotations

import csv
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .. import config
from .fonts import resolve_fonts
from .flats import build_sketches
from .grading import GradedTechPack
from .sketch import sketch_drawing
from .standards import body_chart

# Brand palette (matches design/preview.html).
_INDIGO = colors.HexColor("#6366F1")
_INDIGO_SOFT = colors.HexColor("#EEF0FE")
_INK = colors.HexColor("#1E2230")
_MUTED = colors.HexColor("#7C8398")
_LINE = colors.HexColor("#E7E9F0")

# Static-label translations. Field *values* are localised by the Designer agent;
# these are the document chrome.
LABELS = {
    "en": {
        "title_suffix": "Tech Pack",
        "design_notes": "Design notes",
        "pom": "Points of measure",
        "graded": "graded",
        "size_one": "size",
        "size_many": "sizes",
        "base": "base",
        "bom": "Bill of materials",
        "construction": "Construction notes",
        "tol_short": "Tol ±",
        "csv_code": "Code",
        "csv_pom": "Point of measure",
        "csv_tol": "Tolerance (cm)",
        "component": "Component",
        "specification": "Specification",
        "qty": "Qty",
        "flats_title": "Technical flats & sizes",
        "reference": "Reference images",
        "front": "Front",
        "back": "Back",
        "size_key": "Measurements by size",
        "size_chart": "European size chart — body (EN 13402)",
        "eu": "EU",
        "bust": "Bust",
        "chest": "Chest",
        "waist": "Waist",
        "hip": "Hip",
    },
    "bg": {
        "title_suffix": "Техническа спецификация",
        "design_notes": "Бележки по дизайна",
        "pom": "Точки на измерване",
        "graded": "градирани",
        "size_one": "размер",
        "size_many": "размера",
        "base": "база",
        "bom": "Списък с материали",
        "construction": "Бележки по конструкцията",
        "tol_short": "Тол. ±",
        "csv_code": "Код",
        "csv_pom": "Точка на измерване",
        "csv_tol": "Толеранс (см)",
        "component": "Компонент",
        "specification": "Спецификация",
        "qty": "Кол.",
        "flats_title": "Технически скици и размери",
        "reference": "Референтни снимки",
        "front": "Отпред",
        "back": "Отзад",
        "size_key": "Мерки по размер",
        "size_chart": "Европейска размерна таблица — тяло (EN 13402)",
        "eu": "EU",
        "bust": "Бюст",
        "chest": "Гръд",
        "waist": "Талия",
        "hip": "Ханш",
    },
}


def _t(lang: str, key: str) -> str:
    return LABELS.get(lang, LABELS["en"]).get(key, LABELS["en"][key])


def write_pom_csv(pack: GradedTechPack, path: str | Path, lang: str = "en") -> Path:
    """Write the graded points-of-measure table to a CSV file. Returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = [_t(lang, "csv_code"), _t(lang, "csv_pom"), _t(lang, "csv_tol"), *pack.sizes]
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for pt in pack.points:
            row = [pt.code, pt.name, f"{pt.tolerance_cm:g}"]
            row += [f"{pt.values_by_size[s]:g}" for s in pack.sizes]
            writer.writerow(row)
    return path


def write_pdf(
    pack: GradedTechPack,
    path: str | Path,
    lang: str = "en",
    images: list[str | Path] | None = None,
) -> Path:
    """Render the tech pack to a PDF file. Returns the path.

    `images` are the uploaded inspiration photos; embedded as a visual reference
    so the pack shows the actual garment.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    brief = pack.brief
    fonts = resolve_fonts(require_cyrillic=(lang != "en"))

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"{brief.style_name} — {_t(lang, 'title_suffix')}",
        author="Atelier",
    )

    n = len(pack.sizes)
    size_word = _t(lang, "size_one") if n == 1 else _t(lang, "size_many")
    pom_heading = (
        f"{_t(lang, 'pom')} — {_t(lang, 'graded')} "
        f"({n} {size_word}, {_t(lang, 'base')} {pack.base_size})"
    )

    story = []
    story += _header(brief, fonts, lang)
    ref = _reference_flowables(images, fonts, lang)
    if ref:
        story += _section(_t(lang, "reference"), ref, fonts)
    story += _section(_t(lang, "design_notes"), _paragraph(brief.design_notes or "—", fonts), fonts)
    story += _section(pom_heading, _pom_table(pack, fonts, lang), fonts)
    chart = body_chart(pack.system, pack.sizes)
    if chart:
        girth_label, rows = chart
        story += _section(
            _t(lang, "size_chart"), _size_chart_table(rows, girth_label, fonts, lang), fonts
        )
    story += _section(_t(lang, "bom"), _bom_table(brief, fonts, lang), fonts)
    story += _section(_t(lang, "construction"), _construction(brief, fonts), fonts)
    # The parametric flats are generic and may not match a specific garment, so
    # they're off by default. Graded measurements are already in the table above.
    if config.INCLUDE_FLATS:
        story += _flats_page(pack, fonts, lang)
    doc.build(story)
    return path


def generate(
    pack: GradedTechPack,
    out_dir: str | Path,
    stem: str | None = None,
    lang: str = "en",
    images: list[str | Path] | None = None,
) -> dict[str, Path]:
    """Write both the PDF and the POM CSV into `out_dir`. Returns {'pdf', 'csv'}."""
    out_dir = Path(out_dir)
    stem = stem or _slug(pack.brief.style_code or pack.brief.style_name)
    return {
        "pdf": write_pdf(pack, out_dir / f"{stem}.pdf", lang=lang, images=images),
        "csv": write_pom_csv(pack, out_dir / f"{stem}-pom.csv", lang=lang),
    }


# --- internal building blocks ----------------------------------------------


def _styles(fonts):
    ss = getSampleStyleSheet()
    base = ss["BodyText"]
    base.fontName = fonts[0]
    base.fontSize = 9.5
    base.leading = 13
    base.textColor = _INK
    return base


def _paragraph(text: str, fonts) -> Paragraph:
    return Paragraph(_escape(text), _styles(fonts))


def _header(brief, fonts, lang) -> list:
    title = ParagraphStyle(
        "Title", fontName=fonts[1], fontSize=20, textColor=_INK, leading=23, spaceAfter=2
    )
    sub = ParagraphStyle(
        "Sub", fontName=fonts[0], fontSize=9.5, textColor=_MUTED, leading=13, spaceAfter=2
    )
    # Escape each part first, then join with the separator markup (escaping the
    # whole joined string would turn the &nbsp; entities into literal text).
    parts = [
        _escape(x)
        for x in [brief.style_code, brief.garment_type, brief.fabric,
                  f"{_t(lang, 'base')} {brief.base_size}"]
        if x
    ]
    return [
        Paragraph(_escape(brief.style_name), title),
        Paragraph(" &nbsp;·&nbsp; ".join(parts), sub),
        Spacer(1, 5 * mm),
    ]


def _section(heading: str, body, fonts) -> list:
    h = ParagraphStyle(
        "H", fontName=fonts[1], fontSize=8.5, textColor=_INDIGO,
        leading=12, spaceBefore=6, spaceAfter=4, alignment=TA_LEFT,
    )
    items = [Paragraph(_escape(heading.upper()), h)]
    items += body if isinstance(body, list) else [body]
    items.append(Spacer(1, 4 * mm))
    return items


def _reference_flowables(images, fonts, lang) -> list:
    """Embed the uploaded inspiration photo(s) as a visual reference.

    Loaded via Pillow (handles JPG/PNG/WebP/GIF) and re-encoded to JPEG so
    ReportLab embeds them reliably. One photo is shown large; several form a
    2-column grid. Any unreadable image is skipped, never fatal.
    """
    if not images:
        return []
    from io import BytesIO

    try:
        from PIL import Image as PILImage
    except Exception:  # pragma: no cover - Pillow always present in this stack
        return []

    content_w = A4[0] - 36 * mm  # page width minus 18 mm margins each side
    loaded: list[tuple[BytesIO, int, int]] = []
    for p in images:
        try:
            im = PILImage.open(p)
            im.load()
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            buf = BytesIO()
            im.save(buf, format="JPEG", quality=85)
            buf.seek(0)
            loaded.append((buf, im.width, im.height))
        except Exception:
            continue
    if not loaded:
        return []

    if len(loaded) == 1:
        buf, w, h = loaded[0]
        iw = min(content_w, 95 * mm)
        ih = iw * h / w
        if ih > 120 * mm:
            ih, iw = 120 * mm, 120 * mm * w / h
        img = Image(buf, width=iw, height=ih)
        img.hAlign = "LEFT"
        return [img]

    # Several photos -> a compact 2-column grid.
    cell_w = (content_w - 6 * mm) / 2
    cells = []
    for buf, w, h in loaded:
        iw, ih = cell_w, cell_w * h / w
        if ih > 80 * mm:
            ih, iw = 80 * mm, 80 * mm * w / h
        cells.append(Image(buf, width=iw, height=ih))
    rows = [cells[i : i + 2] for i in range(0, len(cells), 2)]
    if len(rows[-1]) == 1:
        rows[-1].append("")
    table = Table(rows, colWidths=[content_w / 2, content_w / 2])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return [table]


def _pom_table(pack: GradedTechPack, fonts, lang) -> Table:
    # Wrap the (potentially long) measure name in a Paragraph so it line-wraps
    # within its column instead of overrunning into the numeric columns.
    cell = ParagraphStyle("PomCell", fontName=fonts[0], fontSize=8.5, leading=10.5, textColor=_INK)
    header = ["#", _t(lang, "csv_pom"), _t(lang, "tol_short"), *pack.sizes]
    data = [header]
    for pt in pack.points:
        row = [pt.code, Paragraph(_escape(pt.name), cell), f"{pt.tolerance_cm:g}"]
        row += [f"{pt.values_by_size[s]:g}" for s in pack.sizes]
        data.append(row)

    # Size the name column to whatever space the page leaves after the fixed and
    # per-size columns, so the table always fits the content width.
    n = len(pack.sizes)
    code_w, tol_w, size_col = 10 * mm, 12 * mm, 13 * mm
    content_w = 174 * mm  # A4 (210mm) minus 18mm margins each side
    name_w = max(40 * mm, min(96 * mm, content_w - code_w - tol_w - size_col * n))
    table = Table(
        data, repeatRows=1, colWidths=[code_w, name_w, tol_w] + [size_col] * n
    )
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _INDIGO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), fonts[1]),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 1), (-1, -1), fonts[0]),
        ("FONTNAME", (0, 1), (0, -1), fonts[1]),
        ("TEXTCOLOR", (0, 1), (0, -1), _INDIGO),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, _LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _INDIGO_SOFT]),
    ]
    if pack.base_size in pack.sizes:
        bi = 3 + pack.sizes.index(pack.base_size)
        style.append(("FONTNAME", (bi, 1), (bi, -1), fonts[1]))
    table.setStyle(TableStyle(style))
    return table


def _bom_table(brief, fonts, lang) -> Table:
    cell = ParagraphStyle("BomCell", fontName=fonts[0], fontSize=8.5, leading=10.5, textColor=_INK)
    data = [[_t(lang, "component"), _t(lang, "specification"), _t(lang, "qty")]]
    if brief.bill_of_materials:
        for item in brief.bill_of_materials:
            data.append([
                Paragraph(_escape(item.component), cell),
                Paragraph(_escape(item.specification), cell),
                Paragraph(_escape(item.quantity or "—"), cell),  # wrap qty too
            ])
    else:
        data.append(["—", "—", "—"])
    # Widths sum to 174mm (the content width) so nothing is clipped on the right.
    table = Table(data, repeatRows=1, colWidths=[40 * mm, 96 * mm, 38 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _INDIGO_SOFT),
                ("TEXTCOLOR", (0, 0), (-1, 0), _INDIGO),
                ("FONTNAME", (0, 0), (-1, 0), fonts[1]),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("FONTNAME", (0, 1), (-1, -1), fonts[0]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, _LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _size_chart_table(rows, girth_label, fonts, lang) -> Table:
    """EN 13402 body-measurement reference chart (one row per chosen EU size)."""
    header = [_t(lang, "eu"), _t(lang, girth_label), _t(lang, "waist"), _t(lang, "hip")]
    data = [header] + [[s, str(g), str(w), str(h)] for (s, g, w, h) in rows]
    table = Table(data, repeatRows=1, colWidths=[24 * mm, 26 * mm, 26 * mm, 26 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _INDIGO_SOFT),
                ("TEXTCOLOR", (0, 0), (-1, 0), _INDIGO),
                ("FONTNAME", (0, 0), (-1, 0), fonts[1]),
                ("FONTNAME", (0, 1), (-1, -1), fonts[0]),
                ("FONTNAME", (0, 1), (0, -1), fonts[1]),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, _LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _construction(brief, fonts) -> list:
    if not brief.construction_notes:
        return [_paragraph("—", fonts)]
    bullet = ParagraphStyle("Bullet", parent=_styles(fonts), leftIndent=10, bulletIndent=0, spaceAfter=2)
    return [Paragraph(f"• {_escape(n)}", bullet) for n in brief.construction_notes]


def _flats_page(pack: GradedTechPack, fonts, lang) -> list:
    """Final page: technical flat sketches (if any) with the graded size table."""
    story = [PageBreak()]
    flats = _flats_table(pack, fonts, lang)
    if flats is not None:
        story += _section(_t(lang, "flats_title"), flats, fonts)
        story += _section(_t(lang, "size_key"), _pom_table(pack, fonts, lang), fonts)
    else:
        # No sketches available — still put the size table on its own final page.
        story += _section(_t(lang, "flats_title"), _pom_table(pack, fonts, lang), fonts)
    return story


def _flats_table(pack, fonts, lang):
    """Two-column table of front/back flat drawings from the parametric engine."""
    sketches = {s.view: s for s in build_sketches(pack.brief.sketch_spec, pack.brief.points_of_measure)}
    front, back = sketches.get("front"), sketches.get("back")
    if front is None and back is None:
        return None

    label_style = ParagraphStyle(
        "View", fontName=fonts[1], fontSize=9.5, textColor=_INDIGO, alignment=TA_CENTER, spaceAfter=3
    )
    target_w = 72 * mm

    def cell(view_key, sk):
        label = Paragraph(_escape(_t(lang, view_key)), label_style)
        if sk is None:
            return label, _paragraph("—", fonts)
        try:
            drawing = sketch_drawing(sk, target_w, fonts[0])
            drawing.hAlign = "CENTER"
            return label, drawing
        except Exception:
            return label, _paragraph("—", fonts)

    fl, fd = cell("front", front)
    bl, bd = cell("back", back)
    table = Table([[fl, bl], [fd, bd]], colWidths=[87 * mm, 87 * mm])
    table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, 0), 0),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
            ]
        )
    )
    return table


def _escape(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _slug(text: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in str(text)]
    slug = "".join(keep).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "tech-pack"
