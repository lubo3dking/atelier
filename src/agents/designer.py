"""Designer agent — turns inspiration + notes into a structured DesignBrief.

This is the Atelier product's "Executor" for tech packs: it reads the brand
owner's inspiration images and free-text clarifications and returns a validated
`DesignBrief` (garment, fabric, points of measure, BOM, construction). Grading
and document generation downstream are deterministic and need no LLM.
"""
from __future__ import annotations

from typing import Any

from .. import config
from ..schemas import DesignBrief
from .base import Agent

# Human-readable names for supported output languages.
LANGUAGES = {"en": "English", "bg": "Bulgarian"}


class Designer(Agent):
    def brief(
        self,
        design_notes: str,
        image_blocks: list[dict[str, Any]] | None = None,
        garment_hint: str = "",
        language: str = "en",
    ) -> DesignBrief:
        """Produce a DesignBrief from notes and optional inspiration images.

        `image_blocks` are Anthropic image content blocks (base64 or URL), passed
        straight through so the caller controls encoding. `garment_hint` lets the
        UI nudge the garment type (e.g. "shirt") when the user has selected one.
        `language` ("en" | "bg") controls the language of the written fields.
        """
        text = "Design notes from the brand owner:\n" + (design_notes or "(none)")
        if garment_hint:
            text += f"\n\nGarment type hint: {garment_hint}"
        if language != "en":
            lang_name = LANGUAGES.get(language, language)
            text += (
                f"\n\nIMPORTANT: Write ALL human-readable text fields in {lang_name} "
                "(style_name, garment_type, fabric, every point-of-measure name, the BOM "
                "component and specification, design_notes, and all construction notes). "
                "Keep the point-of-measure codes as Latin letters (A, B, C…) and keep all "
                "numbers as numerals. Use correct industry terminology in that language."
            )
        if image_blocks:
            text += (
                f"\n\n{len(image_blocks)} inspiration image(s) are attached. "
                "Use them as the visual reference for silhouette, details, and proportions."
            )

        content: list[dict[str, Any]] = [{"type": "text", "text": text}]
        if image_blocks:
            content.extend(image_blocks)

        # DesignBrief times out the structured-output grammar compiler, so go
        # straight to JSON mode by default (one API call, ~half the latency).
        return self.client.parse(
            system=self.system_prompt,
            messages=[{"role": "user", "content": content}],
            schema=DesignBrief,
            json_mode=config.DESIGNER_JSON_MODE,
        )
