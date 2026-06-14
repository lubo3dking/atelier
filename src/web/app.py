"""FastAPI application for Atelier — upload inspiration, get a tech pack.

The app is a thin delivery layer over the existing pipeline. Optional features
(payments, email) self-enable from environment variables, so it runs out of the
box locally (free, download-only) and becomes sellable/sendable once keys are set.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import config
from ..llm.images import media_type_for
from ..techpack.sizes import SIZE_SYSTEMS, order_sizes, validate_size_run
from . import email as email_mod
from . import payments
from .pipeline import live_brief_provider, run_job
from .storage import JobStore

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Garments the parametric flat engine renders well (advertised at launch).
GARMENTS = ["shirt", "t-shirt", "dress", "trousers", "skirt", "cardigan", "blouse", "top"]
LANGUAGES = {"en": "English", "bg": "Български"}


def _parse_sizes(raw: str) -> list[str]:
    """Accept sizes as JSON array, comma- or space-separated."""
    raw = (raw or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            return [str(s).strip() for s in json.loads(raw) if str(s).strip()]
        except ValueError:
            pass
    return [s for s in raw.replace(",", " ").split() if s]


def create_app(brief_provider=live_brief_provider, store: JobStore | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store.purge_expired()  # privacy sweep on boot
        yield
        app.state.executor.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(
        title=f"{config.BRAND_NAME} — tech packs",
        docs_url=None, redoc_url=None, lifespan=lifespan,
    )
    app.state.brief_provider = brief_provider
    app.state.store = store or JobStore()
    app.state.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="atelier-job")

    # --- public config (drives the dynamic frontend) ------------------------
    @app.get("/api/config")
    def get_config() -> dict[str, Any]:
        return {
            "brand": config.BRAND_NAME,
            "languages": LANGUAGES,
            "size_systems": {k: list(v) for k, v in SIZE_SYSTEMS.items()},
            "garments": GARMENTS,
            "max_images": config.MAX_IMAGES,
            "max_image_mb": config.MAX_IMAGE_MB,
            "retention_days": config.RETENTION_DAYS,
            "payments_enabled": payments.payments_enabled(),
            "free_packs": config.FREE_PACKS if payments.payments_enabled() else 0,
            "price_label": payments.price_label() if payments.payments_enabled() else "",
            "email_enabled": email_mod.email_enabled(),
            "rate_limit_per_day": config.RATE_LIMIT_PER_DAY,
        }

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # --- per-device access state (drives the button label) ------------------
    @app.get("/api/me")
    def me(device: str = "") -> dict[str, Any]:
        store: JobStore = app.state.store
        owner = bool(device) and store.is_owner(device)
        used_today = store.day_count(device) if device else 0
        rl = config.RATE_LIMIT_PER_DAY
        day_left = None if (owner or rl <= 0) else max(0, rl - used_today)
        if owner or not payments.payments_enabled() or not device:
            return {
                "unlocked": True, "owner": owner, "free_used": 0, "free_left": None,
                "payments_enabled": payments.payments_enabled(),
                "day_left": None if owner else day_left,
            }
        st = store.device_state(device)
        return {
            "unlocked": st["unlocked"], "owner": False,
            "free_used": st["free_used"],
            "free_left": max(0, config.FREE_PACKS - st["free_used"]),
            "payments_enabled": True,
            "day_left": None if st["unlocked"] else day_left,
        }

    # --- owner unlock (free forever on this device) -------------------------
    @app.post("/api/owner")
    def claim_owner(key: str = Form(...), device_id: str = Form(...)) -> dict[str, Any]:
        if not config.OWNER_KEY or key != config.OWNER_KEY:
            raise HTTPException(403, "Invalid owner key.")
        if not device_id:
            raise HTTPException(400, "Missing device id.")
        app.state.store.set_owner(device_id)
        return {"status": "owner", "device_id": device_id}

    # --- payments: start the one-time unlock Checkout for a held job --------
    @app.post("/api/checkout")
    def checkout(job_id: str = Form(...), device_id: str = Form("")) -> dict[str, str]:
        if not payments.payments_enabled():
            raise HTTPException(400, "Payments are not configured.")
        if app.state.store.get(job_id) is None:
            raise HTTPException(404, "Job not found.")
        success = f"{config.PUBLIC_URL}/?paid={{CHECKOUT_SESSION_ID}}&job={job_id}&device={device_id}"
        cancel = f"{config.PUBLIC_URL}/?canceled=1&job={job_id}"
        try:
            return payments.create_checkout_session(success, cancel)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"Could not start checkout: {exc}") from None

    # --- create a job -------------------------------------------------------
    @app.post("/api/jobs")
    async def create_job(
        notes: str = Form(""),
        garment: str = Form(""),
        size_system: str = Form("alpha"),
        sizes: str = Form(""),
        base: str = Form(""),
        lang: str = Form("en"),
        consent: bool = Form(False),
        device_id: str = Form(""),
        images: list[UploadFile] = File(default=[]),
    ) -> JSONResponse:
        store: JobStore = app.state.store
        store.purge_expired()

        if not consent:
            raise HTTPException(400, "Consent is required before uploading photos.")
        if lang not in LANGUAGES:
            raise HTTPException(400, f"Unsupported language '{lang}'.")
        if size_system not in SIZE_SYSTEMS:
            raise HTTPException(400, f"Unknown size system '{size_system}'.")

        size_list = _parse_sizes(sizes)
        if not size_list:
            raise HTTPException(400, "Pick at least one size for the run.")
        try:
            # No explicit base -> middle of the run (same rule as run_job).
            ordered = order_sizes(size_list, size_system)
            base_for_check = base or ordered[len(ordered) // 2]
            validate_size_run(size_list, base_for_check, size_system)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

        if not notes.strip() and not images:
            raise HTTPException(400, "Add design notes or at least one inspiration photo.")
        if len(images) > config.MAX_IMAGES:
            raise HTTPException(400, f"Too many images (max {config.MAX_IMAGES}).")

        # Owner + paid devices are exempt from the daily rate limit; everyone else
        # on the free public launch is capped to protect the API budget.
        exempt = store.is_owner(device_id) or store.is_unlocked(device_id)
        rate_key = device_id or "anon"
        if not exempt and config.RATE_LIMIT_PER_DAY > 0:
            if store.day_count(rate_key) >= config.RATE_LIMIT_PER_DAY:
                return JSONResponse(
                    {"detail": f"Daily limit reached ({config.RATE_LIMIT_PER_DAY}/day). "
                               "Please come back tomorrow.", "rate_limited": True},
                    status_code=429,
                )

        job = store.create(
            notes=notes,
            garment=garment,
            size_system=size_system,
            sizes=size_list,
            base=base,
            lang=lang,
            device_id=device_id,
        )

        # Persist uploads to the job dir (validate type/size first). run_job reads
        # them from there, and they are deleted after generation / on retention.
        uploads = store.uploads_dir(job.id)
        uploads.mkdir(parents=True, exist_ok=True)
        saved = 0
        for idx, up in enumerate(images):
            data = await up.read()
            if not data:
                continue
            if len(data) > config.MAX_IMAGE_MB * 1024 * 1024:
                store.delete(job.id)
                raise HTTPException(413, f"'{up.filename}' exceeds {config.MAX_IMAGE_MB} MB.")
            try:
                media = media_type_for(up.filename or "")
            except ValueError as exc:
                store.delete(job.id)
                raise HTTPException(400, str(exc)) from None
            ext = media.split("/")[-1].replace("jpeg", "jpg")
            (uploads / f"{idx:02d}.{ext}").write_bytes(data)
            saved += 1
        job.image_count = saved
        store.save(job)

        # Freemium gate. Free & unlimited when payments are off. Otherwise: free
        # until the device's quota runs out, then hold the job until it unlocks.
        if payments.payments_enabled() and not store.is_unlocked(device_id):
            if store.free_used(device_id) >= config.FREE_PACKS:
                job.status = "awaiting_payment"
                store.save(job)
                return JSONResponse(
                    {"job_id": job.id, "status": job.status, "checkout_required": True},
                    status_code=402,
                )
            job.counts_as_free = True  # recorded only if generation succeeds
            store.save(job)

        if not exempt and config.RATE_LIMIT_PER_DAY > 0:
            store.record_rate_use(rate_key)  # count it now that it will hit Claude
        app.state.executor.submit(run_job, job, store, app.state.brief_provider)
        return JSONResponse({"job_id": job.id, "status": job.status}, status_code=202)

    # --- confirm the unlock payment, then run the held job ------------------
    @app.post("/api/jobs/{job_id}/pay")
    def confirm_payment(
        job_id: str, paid_token: str = Form(...), device_id: str = Form("")
    ) -> JSONResponse:
        store: JobStore = app.state.store
        job = store.get(job_id)
        if job is None:
            raise HTTPException(404, "Job not found (it may have expired).")
        if job.status not in ("awaiting_payment", "error"):
            return JSONResponse({"job_id": job.id, "status": job.status}, status_code=202)
        if store.is_spent(paid_token) or not payments.session_is_paid(paid_token):
            raise HTTPException(402, "Payment not found or already used.")
        store.mark_spent(paid_token)
        store.unlock_device(device_id or job.device_id)  # one payment = unlimited
        job.status = "queued"
        store.save(job)
        app.state.executor.submit(run_job, job, store, app.state.brief_provider)
        return JSONResponse({"job_id": job.id, "status": job.status}, status_code=202)

    # --- job status ---------------------------------------------------------
    @app.get("/api/jobs/{job_id}")
    def job_status(job_id: str) -> dict[str, Any]:
        job = app.state.store.get(job_id)
        if job is None:
            raise HTTPException(404, "Job not found (it may have expired).")
        return job.public()

    # --- downloads ----------------------------------------------------------
    @app.get("/api/jobs/{job_id}/files/{kind}")
    def download(job_id: str, kind: str):
        if kind not in ("pdf", "csv"):
            raise HTTPException(404, "Unknown file.")
        job = app.state.store.get(job_id)
        if job is None or job.status != "done" or kind not in job.files:
            raise HTTPException(404, "File not ready.")
        path = app.state.store.file_path(job_id, job.files[kind])
        if not path.exists():
            raise HTTPException(404, "File not found.")
        media = "application/pdf" if kind == "pdf" else "text/csv"
        style = (job.brief or {}).get("style_code") or "techpack"
        return FileResponse(path, media_type=media, filename=f"{style}.{kind}")

    # --- email to a sewer ---------------------------------------------------
    @app.post("/api/jobs/{job_id}/email")
    def email_pack(job_id: str, to: str = Form(...), message: str = Form("")):
        if not email_mod.email_enabled():
            raise HTTPException(400, "Email is not configured.")
        job = app.state.store.get(job_id)
        if job is None or job.status != "done":
            raise HTTPException(404, "Tech pack not ready.")
        attachments = [
            app.state.store.file_path(job_id, name) for name in job.files.values()
        ]
        style = (job.brief or {}).get("style_name") or "Tech pack"
        try:
            email_mod.send_techpack(
                to=to, style_name=style, attachments=attachments,
                message=message, lang=job.lang,
            )
        except RuntimeError as exc:
            raise HTTPException(502, str(exc)) from None
        job.email_sent_to = to
        app.state.store.save(job)
        return {"status": "sent", "to": to}

    # --- delete my data -----------------------------------------------------
    @app.delete("/api/jobs/{job_id}")
    def delete_job(job_id: str) -> dict[str, Any]:
        existed = app.state.store.delete(job_id)
        if not existed:
            raise HTTPException(404, "Nothing to delete.")
        return {"status": "deleted", "job_id": job_id}

    # --- PWA manifest (explicit so the MIME type is correct) ----------------
    @app.get("/manifest.webmanifest")
    def manifest():
        return FileResponse(
            STATIC_DIR / "manifest.webmanifest",
            media_type="application/manifest+json",
        )

    # --- static frontend (mounted last so /api/* wins) ----------------------
    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app
