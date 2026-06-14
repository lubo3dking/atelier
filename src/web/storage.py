"""Job storage with privacy retention.

A `Job` owns a directory under ``workspace/web/jobs/<id>`` holding the uploaded
inspiration images and the generated documents (PDF/CSV/brief JSON). The
`JobStore` keeps jobs in memory and on disk, auto-deletes anything older than the
retention window (privacy: user photos are sensitive), and tracks which Stripe
payments have already been spent so a single payment buys exactly one tech pack.

Everything here is pure I/O — no LLM, no network — so it is unit-testable offline.
"""
from __future__ import annotations

import datetime
import json
import shutil
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .. import config


@dataclass
class Job:
    """One tech-pack generation request and its outputs."""

    id: str
    status: str = "queued"  # queued | awaiting_payment | running | done | error
    created_at: float = 0.0
    # request parameters
    notes: str = ""
    garment: str = ""
    size_system: str = "alpha"
    sizes: list[str] = field(default_factory=list)
    base: str = ""
    lang: str = "en"
    image_count: int = 0
    device_id: str = ""
    counts_as_free: bool = False  # a free-tier pack whose use is recorded on success
    # results
    error: str = ""
    brief: dict[str, Any] | None = None  # DesignBrief.model_dump() when done
    files: dict[str, str] = field(default_factory=dict)  # {"pdf": name, "csv": name}
    email_sent_to: str = ""

    def public(self) -> dict[str, Any]:
        """The status payload returned to the browser (no filesystem paths)."""
        return asdict(self)


class JobStore:
    """Thread-safe registry of jobs persisted under one root directory."""

    def __init__(self, root: Path | None = None, retention_days: int | None = None) -> None:
        self.root = Path(root) if root else config.JOBS_DIR
        self.retention_days = (
            retention_days if retention_days is not None else config.RETENTION_DAYS
        )
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._jobs: dict[str, Job] = {}
        self._spent_path = self.root.parent / "spent_payments.json"
        self._spent: set[str] = self._load_spent()
        # Per-device access: {device_id: {"free_used": int, "unlocked": bool}}.
        # Accountless freemium — a device gets N free packs, then a one-time
        # payment unlocks unlimited use. Persisted so it survives restarts.
        self._devices_path = self.root.parent / "devices.json"
        self._devices: dict[str, dict[str, Any]] = self._load_devices()

    # --- job lifecycle ------------------------------------------------------
    def create(self, **params: Any) -> Job:
        with self._lock:
            job = Job(id=uuid.uuid4().hex[:12], created_at=time.time(), **params)
            self._jobs[job.id] = job
            self.job_dir(job.id).mkdir(parents=True, exist_ok=True)
            self._save(job)
            return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def save(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.id] = job
            self._save(job)

    def delete(self, job_id: str) -> bool:
        """Delete a job and its directory (the 'delete my data' action)."""
        with self._lock:
            self._jobs.pop(job_id, None)
            d = self.job_dir(job_id)
            existed = d.exists()
            if existed:
                shutil.rmtree(d, ignore_errors=True)
            return existed

    def job_dir(self, job_id: str) -> Path:
        return self.root / job_id

    def uploads_dir(self, job_id: str) -> Path:
        """Where a job's uploaded inspiration photos live (deleted after use)."""
        return self.job_dir(job_id) / "uploads"

    def file_path(self, job_id: str, name: str) -> Path:
        """Resolve a file inside a job dir, guarding against path traversal."""
        d = self.job_dir(job_id).resolve()
        p = (d / name).resolve()
        if d not in p.parents and p != d:
            raise ValueError("Refusing path outside the job directory.")
        return p

    # --- retention ----------------------------------------------------------
    def purge_expired(self, now: float | None = None) -> int:
        """Delete jobs older than the retention window. Returns count removed."""
        if self.retention_days <= 0:
            return 0
        now = now if now is not None else time.time()
        cutoff = now - self.retention_days * 86400
        removed = 0
        with self._lock:
            for job_id, job in list(self._jobs.items()):
                if job.created_at and job.created_at < cutoff:
                    self.delete(job_id)
                    removed += 1
            # Also sweep on-disk dirs with no in-memory record (after a restart).
            for d in self.root.iterdir() if self.root.exists() else []:
                if d.is_dir() and d.name not in self._jobs:
                    try:
                        if d.stat().st_mtime < cutoff:
                            shutil.rmtree(d, ignore_errors=True)
                            removed += 1
                    except OSError:
                        pass
        return removed

    # --- payments (spent Stripe sessions) -----------------------------------
    def is_spent(self, token: str) -> bool:
        with self._lock:
            return token in self._spent

    def mark_spent(self, token: str) -> None:
        with self._lock:
            self._spent.add(token)
            self._spent_path.parent.mkdir(parents=True, exist_ok=True)
            self._spent_path.write_text(json.dumps(sorted(self._spent)), encoding="utf-8")

    def _load_spent(self) -> set[str]:
        try:
            return set(json.loads(self._spent_path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return set()

    # --- per-device access (freemium + owner + rate limit) ------------------
    def _device(self, device_id: str) -> dict[str, Any]:
        d = self._devices.setdefault(device_id, {})
        d.setdefault("free_used", 0)
        d.setdefault("unlocked", False)
        d.setdefault("owner", False)
        d.setdefault("day", "")
        d.setdefault("day_count", 0)
        return d

    @staticmethod
    def _today() -> str:
        return datetime.datetime.now(datetime.timezone.utc).date().isoformat()

    def device_state(self, device_id: str) -> dict[str, Any]:
        with self._lock:
            d = self._device(device_id)
            return {
                "free_used": int(d["free_used"]),
                "unlocked": bool(d["unlocked"]),
                "owner": bool(d["owner"]),
            }

    def is_unlocked(self, device_id: str) -> bool:
        with self._lock:
            return bool(self._device(device_id)["unlocked"])

    def is_owner(self, device_id: str) -> bool:
        with self._lock:
            return bool(self._device(device_id)["owner"])

    def set_owner(self, device_id: str) -> None:
        """Mark a device as the owner: unlimited, free forever, no rate limit."""
        with self._lock:
            d = self._device(device_id)
            d["owner"] = True
            d["unlocked"] = True
            self._save_devices()

    def day_count(self, device_id: str) -> int:
        """Generations this (UTC) day for a device; resets when the day rolls over."""
        with self._lock:
            d = self._device(device_id)
            return int(d["day_count"]) if d["day"] == self._today() else 0

    def record_rate_use(self, device_id: str) -> None:
        with self._lock:
            d = self._device(device_id)
            today = self._today()
            if d["day"] != today:
                d["day"] = today
                d["day_count"] = 0
            d["day_count"] = int(d["day_count"]) + 1
            self._save_devices()

    def free_used(self, device_id: str) -> int:
        with self._lock:
            return int(self._device(device_id)["free_used"])

    def record_free_use(self, device_id: str) -> None:
        """Count one consumed free pack for a (not yet unlocked) device."""
        with self._lock:
            d = self._device(device_id)
            if not d["unlocked"]:
                d["free_used"] = int(d["free_used"]) + 1
                self._save_devices()

    def unlock_device(self, device_id: str) -> None:
        with self._lock:
            self._device(device_id)["unlocked"] = True
            self._save_devices()

    def _load_devices(self) -> dict[str, dict[str, Any]]:
        try:
            return json.loads(self._devices_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save_devices(self) -> None:
        self._devices_path.parent.mkdir(parents=True, exist_ok=True)
        self._devices_path.write_text(json.dumps(self._devices), encoding="utf-8")

    # --- internal -----------------------------------------------------------
    def _save(self, job: Job) -> None:
        meta = self.job_dir(job.id) / "job.json"
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text(json.dumps(job.public(), indent=2), encoding="utf-8")
