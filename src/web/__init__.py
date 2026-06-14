"""Atelier web app — a browser frontend + API around the tech-pack pipeline.

The CLI (`scripts/run_designer.py`) and this package call the *same* deterministic
core (`src.techpack`) and the *same* Designer agent (`src.agents.designer`). This
package only adds delivery: HTTP routes, background job processing, file storage
with privacy retention, optional email (Resend) and payments (Stripe).

`create_app()` builds the FastAPI application. The brief provider (the one piece
that calls Claude) is injectable on `app.state` so the whole web layer is
testable offline with a scripted brief.
"""
from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
