"""Run the Designer agent LIVE: inspiration images + notes -> tech-pack PDF/CSV.

This is the real end-to-end path: Claude vision reads the inspiration images and
notes, returns a structured DesignBrief, then the deterministic engine grades it
across the chosen size run and writes downloadable documents.

Requires ANTHROPIC_API_KEY (from the environment or a local .env — never commit
it). Uses the network. The grading/document half is identical to the offline
demo (scripts/demo_techpack.py).

Usage (from the project root):
    ./.venv/bin/python scripts/run_designer.py \
        --notes "Boxy camp-collar linen shirt, dropped shoulder, chest patch pocket" \
        --image refs/shirt-front.jpg --image refs/shirt-detail.jpg \
        --sizes S M L XL --garment shirt

    # notes-only (no images) is allowed for a quick smoke test:
    ./.venv/bin/python scripts/run_designer.py --notes "Relaxed linen overshirt" --sizes S M L
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import config  # noqa: E402
from src.agents import Designer  # noqa: E402
from src.llm.client import LLMClient  # noqa: E402
from src.llm.images import image_block_from_path  # noqa: E402
from src.techpack import grade  # noqa: E402
from src.techpack.documents import generate  # noqa: E402
from src.techpack.sizes import order_sizes  # noqa: E402


def _load_dotenv(path: pathlib.Path) -> None:
    """Minimal .env loader: KEY=VALUE lines, no override of existing env vars."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a tech pack from inspiration + notes.")
    parser.add_argument("--notes", required=True, help="Design notes / clarifications.")
    parser.add_argument("--image", action="append", default=[], metavar="PATH",
                        help="Inspiration image (repeatable).")
    parser.add_argument("--sizes", nargs="+", default=["S", "M", "L", "XL"],
                        help="Size run, e.g. --sizes XS S M L XL XXL (alpha) or 36 38 40 42 (EU).")
    parser.add_argument("--size-system", default="alpha", choices=["alpha", "eu-women", "eu-men"],
                        help="Size system: alpha (S/M/L) or European numeric.")
    parser.add_argument("--garment", default="", help="Optional garment-type hint, e.g. 'shirt'.")
    parser.add_argument("--base", default="", help="Optional base size override (must be in the run).")
    parser.add_argument("--lang", default="en", choices=["en", "bg"],
                        help="Output language for the brief and documents (en | bg).")
    args = parser.parse_args(argv)

    _load_dotenv(config.PROJECT_ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Put it in the environment or a local .env "
              "(never commit it), then re-run.", file=sys.stderr)
        return 2

    try:
        image_blocks = [image_block_from_path(p) for p in args.image]
    except (OSError, ValueError) as exc:
        print(f"Could not read an inspiration image: {exc}", file=sys.stderr)
        return 1

    print(f"Designing from {len(image_blocks)} image(s) + notes "
          f"[{args.lang}] — calling Claude vision...")
    client = LLMClient()
    designer = Designer.from_prompt_file("designer", client)
    brief = designer.brief(
        args.notes, image_blocks=image_blocks, garment_hint=args.garment, language=args.lang
    )

    print(f"\nBrief: {brief.style_name} ({brief.style_code}) — {brief.garment_type}")
    print(f"  Fabric: {brief.fabric} | base size {brief.base_size}")
    print(f"  {len(brief.points_of_measure)} points of measure, "
          f"{len(brief.bill_of_materials)} BOM items, "
          f"{len(brief.construction_notes)} construction notes")

    # Base size: use --base if given, else the middle of the chosen run (works
    # for any system, since the model's base size may not match EU numbering).
    if args.base:
        base = args.base
    else:
        ordered = order_sizes(args.sizes, args.size_system)
        base = ordered[len(ordered) // 2]

    pack = grade(brief, args.sizes, base_size=base, system=args.size_system)
    out_dir = config.WORKSPACE_DIR / "techpacks"
    paths = generate(pack, out_dir, lang=args.lang)

    # Persist the brief so documents can be re-rendered without another API call.
    json_path = out_dir / f"{paths['pdf'].stem}.json"
    json_path.write_text(brief.model_dump_json(indent=2), encoding="utf-8")

    print(f"\nGraded across [{pack.system}]: {', '.join(pack.sizes)} (base {pack.base_size})")
    print(f"  PDF:   {paths['pdf']}")
    print(f"  CSV:   {paths['csv']}")
    print(f"  Brief: {json_path}")
    print("\nOK — live tech pack generated from inspiration + notes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
