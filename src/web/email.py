"""Email a finished tech pack to a sewer (optional, via Resend).

Enabled only when ``RESEND_API_KEY`` is set; otherwise the app is download-only.
Uses urllib so no extra dependency is required. Attachments are the generated
PDF and POM CSV.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

from .. import config

_RESEND_URL = "https://api.resend.com/emails"


def email_enabled() -> bool:
    return bool(config.RESEND_API_KEY)


def _attachment(path: Path) -> dict[str, str]:
    return {
        "filename": path.name,
        "content": base64.standard_b64encode(path.read_bytes()).decode("ascii"),
    }


def send_techpack(
    *,
    to: str,
    style_name: str,
    attachments: list[Path],
    message: str = "",
    lang: str = "en",
) -> None:
    """Send the tech pack to `to`. Raises RuntimeError on a provider error."""
    if not email_enabled():
        raise RuntimeError("Email is not configured (set RESEND_API_KEY).")

    intro = {
        "en": f"Here is the tech pack for “{style_name}”, generated with {config.BRAND_NAME}.",
        "bg": f"Ето техническия пакет за „{style_name}“, създаден с {config.BRAND_NAME}.",
    }.get(lang, "")
    body_lines = [intro]
    if message:
        body_lines += ["", message]
    html = "<p>" + "</p><p>".join(line or "&nbsp;" for line in body_lines) + "</p>"

    payload = {
        "from": config.EMAIL_FROM,
        "to": [to],
        "subject": f"{config.BRAND_NAME} tech pack — {style_name}",
        "html": html,
        "attachments": [_attachment(p) for p in attachments if p.exists()],
    }
    req = urllib.request.Request(
        _RESEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 — fixed HTTPS host
            if resp.status >= 300:
                raise RuntimeError(f"Resend returned HTTP {resp.status}.")
    except urllib.error.HTTPError as exc:  # pragma: no cover — network path
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"Resend error HTTP {exc.code}: {detail}") from None
    except urllib.error.URLError as exc:  # pragma: no cover — network path
        raise RuntimeError(f"Could not reach Resend: {exc.reason}") from None
