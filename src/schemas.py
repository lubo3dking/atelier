"""Structured-output schemas shared across agents.

These Pydantic models are passed to the Claude structured-outputs API so the
Planner and Reviewer return validated, typed objects rather than free text."""
from __future__ import annotations

from pydantic import BaseModel


class PlanStep(BaseModel):
    description: str
    rationale: str


class Plan(BaseModel):
    goal: str
    steps: list[PlanStep]


class ReviewVerdict(BaseModel):
    approved: bool
    score: int  # 0-100, the Reviewer's confidence the goal was met
    feedback: str  # actionable notes; consumed by the Executor on revision


# --- Tech-pack domain -------------------------------------------------------
# Models for the "Atelier" product: inspiration + notes -> a sewer-ready tech
# pack. The Designer agent fills a DesignBrief via structured output; grading
# and document generation are then deterministic (and fully unit-tested).


class PointOfMeasure(BaseModel):
    """One finished-garment measurement, specified at the base size.

    `grade_cm` is the increment added per size step up (and subtracted per step
    down) when the base spec is graded across a size run.
    """

    code: str  # short key shown on the flat sketch, e.g. "A", "B", "C"
    name: str  # e.g. "Chest (1/2, below armhole)"
    base_cm: float  # value at the base size
    tolerance_cm: float  # acceptable +/- deviation in production
    grade_cm: float  # per-size grade increment
    anchor: str = ""  # where it sits on the flat (vocabulary in SketchSpec docs)


class BomItem(BaseModel):
    """One line of the bill of materials."""

    component: str  # e.g. "Shell fabric", "Buttons"
    specification: str  # e.g. "Linen/cotton 55/45, 180 gsm"
    quantity: str = ""  # free-form, e.g. "1.6 m", "7 pcs"


class SketchLabel(BaseModel):
    """A code/label placed on a flat sketch at a point-of-measure location."""

    x: float  # in the 0-100 (width) sketch box
    y: float  # in the 0-140 (height) sketch box, origin top-left
    text: str  # usually the POM code, e.g. "A"


class SketchPath(BaseModel):
    """One path of a flat sketch, with its drawing role.

    `kind` drives the line-weight hierarchy / dash style when rendered, following
    technical-flat convention: outline heaviest, topstitch dashed, rib hatching
    lightest. Valid kinds: outline | seam | hem | topstitch | rib | detail.
    """

    d: str  # SVG path 'd' data (commands M L H V C Q Z only)
    kind: str = "seam"


class FlatSketch(BaseModel):
    """A rendered technical flat (front or back), built by the parametric engine.

    Drawn to the PDF with ReportLab's vector engine. Coordinates use a 100x140
    box, origin top-left, y increasing downward.
    """

    view: str  # "front" | "back"
    paths: list[SketchPath]  # the first path should be the garment outline
    labels: list[SketchLabel] = []


class SketchSpec(BaseModel):
    """A classification of the garment that drives the parametric flat engine.

    The Designer chooses these instead of drawing — the engine renders clean,
    symmetric, standard flats from them. Point-of-measure `anchor` values use this
    vocabulary so codes land at the right spot on the drawing:
    tops/dress: neck_width, neck_drop, shoulder, chest, bust, waist, hip, hem,
    length, sleeve_length, sleeve_opening, cuff, bicep, armhole.
    bottoms: waist, hip, rise, thigh, knee, leg_opening, inseam, outseam, length.
    """

    silhouette: str = "top"   # top | dress | bottom | skirt
    fit: str = "regular"      # regular | fitted | boxy | cropped
    neckline: str = "crew"    # crew | v | collar | hood
    sleeve: str = "long"      # none | short | long
    opening: str = "none"     # none | placket | full  (full = cardigan/zip front)
    hem: str = "plain"        # plain | rib | curved
    cuff: str = "plain"       # plain | rib
    pocket: str = "none"      # none | patch | chest
    buttons: int = 0          # number of front buttons (0 = none)
    # bottoms
    leg: str = "long"         # short | long (trousers) | mini | knee | midi | maxi (skirt)
    waistband: str = "plain"  # plain | elastic
    fly: bool = False


class DesignBrief(BaseModel):
    """A structured interpretation of the inspiration images + design notes.

    This is what the Designer agent produces; everything downstream (grading,
    PDF/CSV generation) is deterministic.
    """

    style_name: str
    style_code: str
    garment_type: str  # e.g. "Camp-collar shirt"
    fabric: str
    base_size: str  # must appear in the chosen size run, e.g. "M"
    design_notes: str  # the brand owner's clarifications, summarised
    points_of_measure: list[PointOfMeasure]
    bill_of_materials: list[BomItem]
    construction_notes: list[str]
    sketch_spec: SketchSpec = SketchSpec()  # drives the parametric flat engine
