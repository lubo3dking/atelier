"""Offline tests for the tech-pack pipeline: sizes, grading, documents, Designer.

All deterministic — the Designer test injects a scripted LLM, and document
generation writes to a tmp path. No API key or network.
"""
import csv

import pytest

from src.agents.designer import Designer
from src.schemas import (
    BomItem,
    DesignBrief,
    FlatSketch,
    PointOfMeasure,
    SketchLabel,
    SketchPath,
)
from src.techpack import grade, order_sizes, validate_size_run
from src.techpack.documents import generate, write_pdf, write_pom_csv
from src.techpack.sketch import sketch_drawing
from src.techpack.standards import body_chart, has_body_chart


def _brief(base="M"):
    return DesignBrief(
        style_name="Test Shirt",
        style_code="ATL-001",
        garment_type="Camp-collar shirt",
        fabric="Linen 180 gsm",
        base_size=base,
        design_notes="Boxy fit, camp collar.",
        points_of_measure=[
            PointOfMeasure(code="A", name="Body length", base_cm=74.0, tolerance_cm=1.0, grade_cm=1.5),
            PointOfMeasure(code="B", name="Chest (1/2)", base_cm=62.0, tolerance_cm=1.0, grade_cm=2.0),
        ],
        bill_of_materials=[BomItem(component="Shell", specification="Linen 180 gsm", quantity="1.6 m")],
        construction_notes=["French seams, 1 cm SA."],
    )


# --- sizes ------------------------------------------------------------------

def test_order_sizes_sorts_and_dedupes():
    assert order_sizes(["XL", "S", "m", "S"]) == ["S", "M", "XL"]


def test_order_sizes_rejects_unknown():
    with pytest.raises(ValueError):
        order_sizes(["S", "HUGE"])


def test_validate_size_run_requires_base_in_run():
    ordered, base = validate_size_run(["S", "M", "L"], "m")
    assert ordered == ["S", "M", "L"] and base == "M"
    with pytest.raises(ValueError):
        validate_size_run(["S", "M", "L"], "XXL")


def test_validate_size_run_rejects_empty():
    with pytest.raises(ValueError):
        validate_size_run([], "M")


# --- grading ----------------------------------------------------------------

def test_grade_scales_up_and_down_from_base():
    pack = grade(_brief(), ["S", "M", "L", "XL"])
    assert pack.sizes == ["S", "M", "L", "XL"]
    assert pack.base_size == "M"
    chest = next(p for p in pack.points if p.code == "B")
    # base 62 at M, +2.0 per step up, -2.0 per step down
    assert chest.values_by_size == {"S": 60.0, "M": 62.0, "L": 64.0, "XL": 66.0}


def test_grade_handles_non_adjacent_size_run():
    # base M, but run skips to XXL — two steps up from M -> +2 * 1.5 on length
    pack = grade(_brief(), ["M", "XXL"])
    length = next(p for p in pack.points if p.code == "A")
    assert length.values_by_size["M"] == 74.0
    assert length.values_by_size["XXL"] == round(74.0 + 1.5 * 3, 1)  # M,L,XL,XXL = 3 steps


def test_grade_base_defaults_to_brief_base():
    pack = grade(_brief(base="L"), ["M", "L", "XL"])
    assert pack.base_size == "L"
    chest = next(p for p in pack.points if p.code == "B")
    assert chest.values_by_size["L"] == 62.0


# --- European size systems --------------------------------------------------

def test_order_sizes_eu_women():
    assert order_sizes(["40", "36", "38"], system="eu-women") == ["36", "38", "40"]


def test_eu_system_rejects_alpha_size():
    with pytest.raises(ValueError):
        order_sizes(["M"], system="eu-women")


def test_grade_eu_women_steps():
    pack = grade(_brief(), ["36", "38", "40"], base_size="38", system="eu-women")
    assert pack.system == "eu-women"
    chest = next(p for p in pack.points if p.code == "B")
    # base 62 at EU 38, +2.0 per step (one EU step)
    assert chest.values_by_size == {"36": 60.0, "38": 62.0, "40": 64.0}


def test_body_chart_eu_women_and_none_for_alpha():
    girth, rows = body_chart("eu-women", ["36", "38", "40"])
    assert girth == "bust"
    assert rows[1] == ("38", 88, 72, 96)  # EN 13402 body values
    assert not has_body_chart("alpha")
    assert body_chart("alpha", ["S", "M"]) is None


def test_pdf_eu_system_includes_size_chart(tmp_path):
    pack = grade(_brief(), ["36", "38", "40"], base_size="38", system="eu-women")
    path = write_pdf(pack, tmp_path / "eu.pdf")
    assert path.read_bytes().startswith(b"%PDF")


# --- documents --------------------------------------------------------------

def test_write_pom_csv_has_header_and_size_columns(tmp_path):
    pack = grade(_brief(), ["S", "M", "L"])
    path = write_pom_csv(pack, tmp_path / "pom.csv")
    rows = list(csv.reader(path.open(encoding="utf-8-sig")))
    assert rows[0] == ["Code", "Point of measure", "Tolerance (cm)", "S", "M", "L"]
    chest_row = next(r for r in rows if r[0] == "B")
    assert chest_row[3:] == ["60", "62", "64"]


def test_write_pdf_creates_real_pdf(tmp_path):
    pack = grade(_brief(), ["S", "M", "L", "XL"])
    path = write_pdf(pack, tmp_path / "pack.pdf")
    assert path.exists()
    data = path.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 1500  # a non-trivial document


def test_generate_writes_both_documents(tmp_path):
    pack = grade(_brief(), ["S", "M", "L"])
    paths = generate(pack, tmp_path)
    assert paths["pdf"].exists() and paths["pdf"].suffix == ".pdf"
    assert paths["csv"].exists() and paths["csv"].suffix == ".csv"


# --- flat sketches ----------------------------------------------------------

_SIMPLE_SKETCH = FlatSketch(
    view="front",
    paths=[
        SketchPath(d="M20 20 L80 20 L80 130 L20 130 Z", kind="outline"),  # absolute
        SketchPath(d="M20 20 Q50 40 80 20", kind="seam"),                 # quad curve
        SketchPath(d="m35 60 l30 0", kind="topstitch"),                   # relative, dashed
    ],
    labels=[SketchLabel(x=50, y=15, text="A"), SketchLabel(x=50, y=58, text="B")],
)


def test_sketch_drawing_scales_to_target_width():
    d = sketch_drawing(_SIMPLE_SKETCH, target_w=144.0, label_font="Helvetica")
    assert round(d.width, 1) == 144.0
    assert round(d.height, 1) == round(144.0 * 140 / 100, 1)


def test_sketch_drawing_tolerates_malformed_path():
    bad = FlatSketch(view="front", paths=[
        SketchPath(d="M10 10 L", kind="outline"),
        SketchPath(d="not a path at all", kind="seam"),
    ])
    # should not raise — malformed paths are skipped
    d = sketch_drawing(bad, target_w=100.0, label_font="Helvetica")
    assert d.width == 100.0


def test_build_sketches_returns_front_back_with_anchored_labels():
    from src.schemas import PointOfMeasure as P
    from src.schemas import SketchSpec
    from src.techpack.flats import build_sketches

    pts = [
        P(code="A", name="chest", base_cm=1, tolerance_cm=1, grade_cm=1, anchor="chest"),
        P(code="Z", name="x", base_cm=1, tolerance_cm=1, grade_cm=1, anchor=""),
    ]
    sk = build_sketches(SketchSpec(silhouette="top"), pts)
    assert [s.view for s in sk] == ["front", "back"]
    assert any(p.kind == "outline" for p in sk[0].paths)
    codes = [lb.text for lb in sk[0].labels]
    assert "A" in codes and "Z" not in codes  # only anchored POMs get a label


def test_sketch_labels_never_overlap():
    """Many POMs share/cluster anchors; labels must be de-collided so they're legible."""
    from src.schemas import PointOfMeasure as P
    from src.schemas import SketchSpec
    from src.techpack.flats import _LABEL_GAP, build_sketches

    # Several POMs deliberately on the same / adjacent anchors + the centre line.
    anchors = ["chest", "bust", "chest", "neck_width", "neck_drop", "shoulder",
               "waist", "hip", "hem", "length", "sleeve_length", "cuff", "armhole"]
    pts = [P(code=chr(65 + i), name=a, base_cm=1, tolerance_cm=1, grade_cm=1, anchor=a)
           for i, a in enumerate(anchors)]
    sk = build_sketches(SketchSpec(silhouette="top", opening="full", buttons=8), pts)

    for sketch in sk:
        labels = sketch.labels
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                dx = abs(labels[i].x - labels[j].x)
                dy = abs(labels[i].y - labels[j].y)
                assert dx >= _LABEL_GAP - 0.05 or dy >= _LABEL_GAP - 0.05, (
                    f"labels {labels[i].text}/{labels[j].text} overlap at "
                    f"({labels[i].x},{labels[i].y}) ({labels[j].x},{labels[j].y})"
                )


def test_pdf_top_includes_parametric_flats(tmp_path):
    from src.schemas import SketchSpec
    brief = _brief()
    brief.sketch_spec = SketchSpec(silhouette="top", opening="full", hem="rib", buttons=6)
    brief.points_of_measure[0].anchor = "chest"
    pack = grade(brief, ["S", "M", "L"])
    data = write_pdf(pack, tmp_path / "flats.pdf").read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 3000


def test_pdf_bottom_silhouette_generates(tmp_path):
    from src.schemas import SketchSpec
    brief = _brief()
    brief.sketch_spec = SketchSpec(silhouette="bottom", fly=True)
    pack = grade(brief, ["S", "M"])
    assert write_pdf(pack, tmp_path / "b.pdf").read_bytes().startswith(b"%PDF")


# --- designer agent ---------------------------------------------------------

# --- localisation (Bulgarian) ----------------------------------------------

def test_csv_header_localised_bg(tmp_path):
    pack = grade(_brief(), ["S", "M"])
    path = write_pom_csv(pack, tmp_path / "pom.csv", lang="bg")
    rows = list(csv.reader(path.open(encoding="utf-8-sig")))
    assert rows[0][:3] == ["Код", "Точка на измерване", "Толеранс (см)"]
    assert rows[0][3:] == ["S", "M"]  # size codes stay as-is


def test_resolve_fonts_returns_name_pair():
    from src.techpack.fonts import resolve_fonts
    normal, bold = resolve_fonts(require_cyrillic=False)
    assert isinstance(normal, str) and isinstance(bold, str)


def test_pdf_bg_renders_cyrillic(tmp_path):
    from src.techpack.fonts import resolve_fonts
    try:
        resolve_fonts(require_cyrillic=True)
    except RuntimeError:
        pytest.skip("no Cyrillic-capable font available in this environment")

    brief = _brief()
    brief.style_name = "Ленена риза с яка тип камп"
    brief.points_of_measure[0].name = "Дължина на тялото (от ВТР)"
    pack = grade(brief, ["S", "M", "L"])
    path = write_pdf(pack, tmp_path / "bg.pdf", lang="bg")
    assert path.read_bytes().startswith(b"%PDF")
    assert path.stat().st_size > 1500


def test_designer_emits_language_instruction(scripted_llm):
    client = scripted_llm(design_brief=_brief())
    designer = Designer(name="designer", system_prompt="sys", client=client)
    designer.brief("Boxy linen shirt", language="bg")
    text = client.parse_calls[-1]["messages"][0]["content"][0]["text"]
    assert "Bulgarian" in text


def test_designer_returns_brief_and_sends_images(scripted_llm):
    expected = _brief()
    client = scripted_llm(design_brief=expected)
    designer = Designer(name="designer", system_prompt="sys", client=client)

    image_blocks = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "x"}}]
    result = designer.brief("Boxy camp-collar shirt", image_blocks=image_blocks, garment_hint="shirt")

    assert result is expected
    call = client.parse_calls[-1]
    assert call["schema"] is DesignBrief
    content = call["messages"][0]["content"]
    # text block first, then the image block passed through
    assert content[0]["type"] == "text"
    assert "shirt" in content[0]["text"]
    assert image_blocks[0] in content
