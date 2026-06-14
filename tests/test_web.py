"""Offline tests for the web app.

The only LLM touch point (the brief provider) is replaced with a scripted
`DesignBrief`, so these run with no API key and no network — the document
generation, storage, retention, consent, and download paths are all real.
"""
from __future__ import annotations

import base64
import time

import pytest
from fastapi.testclient import TestClient

from src.schemas import BomItem, DesignBrief, PointOfMeasure
from src.web import create_app
from src.web.storage import JobStore

# A tiny valid 1x1 PNG (so the upload + image-block path is exercised).
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

SAMPLE = DesignBrief(
    style_name="Test Shirt",
    style_code="ATL-T01",
    garment_type="Camp-collar shirt",
    fabric="Linen 180 gsm",
    base_size="M",
    design_notes="Boxy, dropped shoulder.",
    points_of_measure=[
        PointOfMeasure(code="A", name="Body length", base_cm=74.0, tolerance_cm=1.0, grade_cm=1.5),
        PointOfMeasure(code="B", name="Chest (1/2)", base_cm=62.0, tolerance_cm=1.0, grade_cm=2.0),
    ],
    bill_of_materials=[BomItem(component="Shell", specification="Linen", quantity="1.6 m")],
    construction_notes=["French seams."],
)


def _provider(**kwargs):
    return SAMPLE


@pytest.fixture()
def client(tmp_path):
    store = JobStore(root=tmp_path / "jobs", retention_days=14)
    app = create_app(brief_provider=_provider, store=store)
    with TestClient(app) as c:
        c.store = store
        yield c


def _wait_done(client, job_id, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish in time")


def test_config_defaults_free_and_download_only(client):
    cfg = client.get("/api/config").json()
    assert cfg["payments_enabled"] is False
    assert cfg["email_enabled"] is False
    assert "alpha" in cfg["size_systems"]
    assert cfg["retention_days"] == 14


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_generate_end_to_end_with_image(client):
    resp = client.post(
        "/api/jobs",
        data={"notes": "boxy shirt", "size_system": "alpha",
              "sizes": "S M L", "base": "M", "lang": "en", "consent": "true"},
        files=[("images", ("ref.png", _PNG, "image/png"))],
    )
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["job_id"]

    job = _wait_done(client, job_id)
    assert job["status"] == "done", job
    assert job["brief"]["style_name"] == "Test Shirt"
    assert set(job["files"]) == {"pdf", "csv"}

    pdf = client.get(f"/api/jobs/{job_id}/files/pdf")
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"
    csv = client.get(f"/api/jobs/{job_id}/files/csv")
    assert csv.status_code == 200 and b"," in csv.content

    # Source photos are deleted after generation (privacy).
    assert not (client.store.uploads_dir(job_id)).exists()


def test_notes_only_is_allowed(client):
    resp = client.post(
        "/api/jobs",
        data={"notes": "relaxed overshirt", "size_system": "alpha",
              "sizes": "S M L", "lang": "en", "consent": "true"},
    )
    assert resp.status_code == 202
    assert _wait_done(client, resp.json()["job_id"])["status"] == "done"


def test_consent_required(client):
    resp = client.post(
        "/api/jobs",
        data={"notes": "x", "sizes": "S M", "consent": "false"},
    )
    assert resp.status_code == 400


def test_sizes_required(client):
    resp = client.post(
        "/api/jobs",
        data={"notes": "x", "sizes": "", "consent": "true"},
    )
    assert resp.status_code == 400


def test_empty_input_rejected(client):
    resp = client.post(
        "/api/jobs",
        data={"notes": "", "sizes": "S M", "consent": "true"},
    )
    assert resp.status_code == 400


def test_delete_my_data(client):
    job_id = client.post(
        "/api/jobs",
        data={"notes": "x", "sizes": "S M L", "consent": "true"},
    ).json()["job_id"]
    _wait_done(client, job_id)
    assert client.delete(f"/api/jobs/{job_id}").status_code == 200
    assert client.get(f"/api/jobs/{job_id}").status_code == 404


def test_retention_purges_old_jobs(client):
    job = client.store.create(notes="old", sizes=["S"], size_system="alpha")
    # Backdate it well beyond the retention window.
    job.created_at = time.time() - 30 * 86400
    client.store.save(job)
    removed = client.store.purge_expired()
    assert removed >= 1
    assert client.store.get(job.id) is None


def test_device_store_freemium(tmp_path):
    store = JobStore(root=tmp_path / "jobs")
    dev = "d_abc"
    assert store.free_used(dev) == 0 and store.is_unlocked(dev) is False
    store.record_free_use(dev)
    store.record_free_use(dev)
    assert store.free_used(dev) == 2
    store.unlock_device(dev)
    assert store.is_unlocked(dev) is True
    store.record_free_use(dev)  # unlocked -> no longer counts
    assert store.free_used(dev) == 2
    # Persists across reloads.
    assert JobStore(root=tmp_path / "jobs").is_unlocked(dev) is True


def test_me_endpoint_is_unlimited_in_free_mode(client):
    me = client.get("/api/me?device=d_x").json()
    assert me["unlocked"] is True and me["payments_enabled"] is False


def test_config_exposes_free_packs_when_paid(client, monkeypatch):
    from src.web import payments
    monkeypatch.setattr(payments, "payments_enabled", lambda: True)
    cfg = client.get("/api/config").json()
    assert cfg["payments_enabled"] is True and cfg["free_packs"] >= 1


def test_freemium_gate_blocks_after_quota(client, monkeypatch):
    from src import config
    from src.web import payments
    monkeypatch.setattr(payments, "payments_enabled", lambda: True)
    monkeypatch.setattr(config, "FREE_PACKS", 1)
    dev = "d_quota"

    # First pack is free and counts toward the quota.
    r1 = client.post("/api/jobs", data={
        "notes": "x", "sizes": "S M L", "consent": "true", "device_id": dev})
    assert r1.status_code == 202
    assert _wait_done(client, r1.json()["job_id"])["status"] == "done"
    assert client.get(f"/api/me?device={dev}").json()["free_left"] == 0

    # Quota spent -> next request is held for the one-time unlock (402).
    r2 = client.post("/api/jobs", data={
        "notes": "x", "sizes": "S M L", "consent": "true", "device_id": dev})
    assert r2.status_code == 402 and r2.json()["checkout_required"] is True


def test_rate_limit_blocks_after_daily_quota(client, monkeypatch):
    from src import config
    monkeypatch.setattr(config, "RATE_LIMIT_PER_DAY", 2)
    dev = "d_rl"
    for _ in range(2):
        r = client.post("/api/jobs", data={
            "notes": "x", "sizes": "S M L", "consent": "true", "device_id": dev})
        assert r.status_code == 202
    r3 = client.post("/api/jobs", data={
        "notes": "x", "sizes": "S M L", "consent": "true", "device_id": dev})
    assert r3.status_code == 429 and r3.json()["rate_limited"] is True
    assert client.get(f"/api/me?device={dev}").json()["day_left"] == 0


def test_owner_key_grants_unlimited(client, monkeypatch):
    from src import config
    monkeypatch.setattr(config, "OWNER_KEY", "secret123")
    monkeypatch.setattr(config, "RATE_LIMIT_PER_DAY", 1)
    dev = "d_owner"

    assert client.post("/api/owner", data={"key": "wrong", "device_id": dev}).status_code == 403
    ok = client.post("/api/owner", data={"key": "secret123", "device_id": dev})
    assert ok.status_code == 200
    assert client.get(f"/api/me?device={dev}").json()["owner"] is True

    # Owner bypasses the (tiny) rate limit entirely.
    for _ in range(3):
        r = client.post("/api/jobs", data={
            "notes": "x", "sizes": "S M L", "consent": "true", "device_id": dev})
        assert r.status_code == 202


def test_owner_disabled_without_key(client):
    # No OWNER_KEY configured -> owner claims are rejected.
    assert client.post("/api/owner", data={"key": "anything", "device_id": "d"}).status_code == 403


def test_download_traversal_is_blocked(client):
    job_id = client.post(
        "/api/jobs", data={"notes": "x", "sizes": "S M", "consent": "true"},
    ).json()["job_id"]
    _wait_done(client, job_id)
    # Unknown file kind -> 404, never serves arbitrary paths.
    assert client.get(f"/api/jobs/{job_id}/files/secret").status_code == 404
