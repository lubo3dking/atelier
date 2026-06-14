"""Generate a sample tech pack (PDF + POM CSV) with no API key or network.

Demonstrates the deterministic half of Atelier: a `DesignBrief` -> graded spec
-> downloadable documents. In the real app the brief comes from the Designer
agent (Claude vision over inspiration images); here we hard-code one so the
output pipeline can be exercised and the PDF inspected.

Usage (from the project root):
    ./.venv/bin/python scripts/demo_techpack.py            # sizes S M L XL
    ./.venv/bin/python scripts/demo_techpack.py XS S M L XL XXL
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import config  # noqa: E402
from src.schemas import BomItem, DesignBrief, PointOfMeasure  # noqa: E402
from src.techpack import grade  # noqa: E402
from src.techpack.documents import generate  # noqa: E402

SAMPLE_BRIEF = DesignBrief(
    style_name="Camp-Collar Shirt",
    style_code="ATL-031",
    garment_type="Camp-collar short-sleeve shirt",
    fabric="Linen/cotton 55/45, 180 gsm",
    base_size="M",
    design_notes=(
        "Oversized boxy fit with a dropped shoulder. Camp (open) collar, chest "
        "patch pocket, short Cuban-style sleeve with ~24 cm opening. Relaxed, "
        "resort feel."
    ),
    points_of_measure=[
        PointOfMeasure(code="A", name="Body length from HPS", base_cm=74.0, tolerance_cm=1.0, grade_cm=1.5),
        PointOfMeasure(code="B", name="Chest (1/2, 2.5 cm below armhole)", base_cm=62.0, tolerance_cm=1.0, grade_cm=2.0),
        PointOfMeasure(code="C", name="Across shoulder (seam to seam)", base_cm=52.0, tolerance_cm=0.6, grade_cm=1.0),
        PointOfMeasure(code="D", name="Sleeve length from shoulder seam", base_cm=24.0, tolerance_cm=0.6, grade_cm=0.5),
        PointOfMeasure(code="E", name="Sleeve opening (1/2)", base_cm=24.0, tolerance_cm=0.5, grade_cm=0.5),
        PointOfMeasure(code="F", name="Bottom sweep (1/2)", base_cm=63.0, tolerance_cm=1.0, grade_cm=2.0),
        PointOfMeasure(code="G", name="Neck width (HPS to HPS)", base_cm=19.0, tolerance_cm=0.5, grade_cm=0.5),
    ],
    bill_of_materials=[
        BomItem(component="Shell fabric", specification="Linen/cotton 55/45, 180 gsm", quantity="1.6 m"),
        BomItem(component="Buttons", specification="Corozo, matte, 15 mm", quantity="7 pcs"),
        BomItem(component="Interlining", specification="Fusible, collar & placket", quantity="0.2 m"),
        BomItem(component="Sewing thread", specification="Tex 40, tonal", quantity="1 cone"),
        BomItem(component="Labels", specification="Woven main + care/content", quantity="1 set"),
    ],
    construction_notes=[
        "French seams throughout, 1 cm seam allowance.",
        "2.5 cm clean-finished bottom hem.",
        "Bartack both top corners of the patch pocket.",
        "Topstitch collar and placket at 6 mm.",
        "Single-needle felled armhole.",
    ],
)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    sizes = argv or ["S", "M", "L", "XL"]

    pack = grade(SAMPLE_BRIEF, sizes)
    out_dir = config.WORKSPACE_DIR / "techpacks"
    paths = generate(pack, out_dir)

    print(f"Graded '{pack.brief.style_name}' across sizes: {', '.join(pack.sizes)} "
          f"(base {pack.base_size})")
    print(f"  PDF: {paths['pdf']}")
    print(f"  CSV: {paths['csv']}")
    print("\nOK — downloadable tech-pack documents generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
