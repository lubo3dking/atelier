"""Run one tech-pack generation for a job.

This wraps the exact same steps as the CLI (`scripts/run_designer.py`): the
Designer agent turns inspiration images + notes into a `DesignBrief`, then the
deterministic engine grades it and writes the PDF/CSV. The only LLM touch point —
producing the brief — is a pluggable callable so the web layer is testable offline.
"""
from __future__ import annotations

import shutil
from typing import Any, Callable, Protocol

from ..llm.images import image_block_from_path
from ..schemas import DesignBrief
from ..techpack import grade
from ..techpack.documents import generate
from ..techpack.sizes import order_sizes
from .storage import Job, JobStore

# A brief provider: (notes, image_blocks, garment_hint, language) -> DesignBrief.
BriefProvider = Callable[..., DesignBrief]


class _LiveDesigner(Protocol):
    def brief(self, *args: Any, **kwargs: Any) -> DesignBrief: ...


def live_brief_provider(
    notes: str,
    image_blocks: list[dict[str, Any]],
    garment_hint: str,
    language: str,
) -> DesignBrief:
    """Default provider: call Claude vision via the Designer agent.

    Imported lazily so that importing the web app (and running offline tests)
    never requires the Anthropic SDK or an API key.
    """
    from ..agents import Designer
    from ..llm.client import LLMClient

    designer = Designer.from_prompt_file("designer", LLMClient())
    return designer.brief(
        notes, image_blocks=image_blocks, garment_hint=garment_hint, language=language
    )


def run_job(
    job: Job,
    store: JobStore,
    brief_provider: BriefProvider,
) -> None:
    """Execute a job end to end, updating its status in the store.

    Reads the uploaded inspiration photos from the job's uploads dir, generates
    the tech pack, then deletes the source photos (privacy: keep only the derived
    documents). Never raises: any failure is recorded on the job as
    status="error" so the HTTP status endpoint can report it cleanly.
    """
    try:
        job.status = "running"
        store.save(job)

        uploads = store.uploads_dir(job.id)
        image_paths = [p for p in sorted(uploads.glob("*")) if p.is_file()] if uploads.exists() else []
        image_blocks = [image_block_from_path(p) for p in image_paths]

        brief = brief_provider(
            notes=job.notes,
            image_blocks=image_blocks,
            garment_hint=job.garment,
            language=job.lang,
        )

        # Base size: explicit override, else the middle of the chosen run (the
        # model's base may not be valid in the selected size system).
        if job.base:
            base = job.base
        else:
            ordered = order_sizes(job.sizes, job.size_system)
            base = ordered[len(ordered) // 2]

        pack = grade(brief, job.sizes, base_size=base, system=job.size_system)
        out_dir = store.job_dir(job.id)
        # Embed the uploaded photos as the visual reference in the pack itself.
        paths = generate(pack, out_dir, stem="techpack", lang=job.lang, images=image_paths)

        # Persist the brief next to the documents (re-render without another call).
        (out_dir / "techpack.json").write_text(
            brief.model_dump_json(indent=2), encoding="utf-8"
        )

        job.brief = brief.model_dump()
        job.base = pack.base_size
        job.files = {"pdf": paths["pdf"].name, "csv": paths["csv"].name}
        job.status = "done"
        store.save(job)

        # Freemium: only a successful free-tier pack counts toward the free quota.
        if job.counts_as_free and job.device_id:
            store.record_free_use(job.device_id)

        # Privacy: drop the source photos once the tech pack exists.
        shutil.rmtree(uploads, ignore_errors=True)
    except Exception as exc:  # noqa: BLE001 — surface any failure to the client
        job.status = "error"
        job.error = f"{type(exc).__name__}: {exc}"
        store.save(job)
