"""Central configuration. All tunable settings live here, sourced from the
environment with sensible defaults so nothing is hard-coded in two places."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = PROJECT_ROOT / "prompts"
MEMORY_FILE = PROJECT_ROOT / "memory" / "runs.json"
WORKSPACE_DIR = PROJECT_ROOT / "workspace"

# Model + inference settings. Opus 4.8 with adaptive thinking is the default.
MODEL = os.environ.get("AGENT_MODEL", "claude-opus-4-8")
EFFORT = os.environ.get("AGENT_EFFORT", "high")  # low | medium | high | max
MAX_TOKENS = int(os.environ.get("AGENT_MAX_TOKENS", "16000"))

# How many times the Reviewer may bounce work back to the Executor.
MAX_REVISIONS = int(os.environ.get("AGENT_MAX_REVISIONS", "3"))

# The Designer's DesignBrief schema reliably times out the server-side structured-
# output grammar compiler, so the Designer goes straight to JSON mode (one call
# instead of a failed structured call + a JSON retry — ~halves latency & cost).
# Set ATELIER_DESIGNER_JSON_MODE=0 to force the native structured path instead.
DESIGNER_JSON_MODE = os.environ.get("ATELIER_DESIGNER_JSON_MODE", "1") not in ("0", "false", "False")

# Hard cap on tool-call iterations within a single Executor run (loop guard).
MAX_TOOL_ITERATIONS = int(os.environ.get("AGENT_MAX_TOOL_ITERATIONS", "12"))

# Memory backend: "json" (default, file-backed) or "supabase".
MEMORY_BACKEND = os.environ.get("AGENT_MEMORY_BACKEND", "json")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "runs")

# --- Web app -----------------------------------------------------------------
# Where the browser app stores uploads + generated tech packs (per job).
WEB_DIR = WORKSPACE_DIR / "web"
JOBS_DIR = WEB_DIR / "jobs"

# Public URL the app is reachable at (used for Stripe redirects + email links).
# Defaults to localhost for local dev; set ATELIER_PUBLIC_URL on the host.
PUBLIC_URL = os.environ.get("ATELIER_PUBLIC_URL", "http://localhost:8000").rstrip("/")

# Privacy: uploaded photos + generated packs are auto-deleted after N days.
RETENTION_DAYS = int(os.environ.get("ATELIER_RETENTION_DAYS", "14"))

# Upload guard rails.
MAX_IMAGES = int(os.environ.get("ATELIER_MAX_IMAGES", "8"))
MAX_IMAGE_MB = int(os.environ.get("ATELIER_MAX_IMAGE_MB", "12"))

# --- Payments (optional; "sellable") -----------------------------------------
# Freemium model: a device gets ATELIER_FREE_PACKS free tech packs, then a single
# one-time payment (ATELIER_UNLOCK_CENTS) unlocks UNLIMITED use forever.
# When STRIPE_SECRET_KEY is unset the app runs FREE & UNLIMITED (no paywall) so it
# works out of the box locally. Set the key on the host to start selling.
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
# Free tech packs before the unlock prompt appears.
FREE_PACKS = int(os.environ.get("ATELIER_FREE_PACKS", "3"))
# One-time price to unlock unlimited use, in the smallest currency unit (cents).
# (ATELIER_PRICE_CENTS kept as an alias for backwards compatibility.)
UNLOCK_PRICE_CENTS = int(
    os.environ.get("ATELIER_UNLOCK_CENTS", os.environ.get("ATELIER_PRICE_CENTS", "1999"))
)
CURRENCY = os.environ.get("ATELIER_CURRENCY", "eur").lower()

# Abuse/cost guard for the free public launch: max generations per device per day.
# Applies to everyone EXCEPT owner devices and (once selling) unlocked devices.
# Set to 0 to disable.
RATE_LIMIT_PER_DAY = int(os.environ.get("ATELIER_RATE_LIMIT_PER_DAY", "10"))

# Owner unlock: visiting the app once at /?owner=<OWNER_KEY> marks that browser/
# device as the owner — unlimited, free forever, exempt from the rate limit and
# any future paywall. Keep this key secret. Empty = owner unlock disabled.
OWNER_KEY = os.environ.get("ATELIER_OWNER_KEY", "")

# --- Email (optional; "sendable") --------------------------------------------
# When RESEND_API_KEY is unset, the app offers download-only (no email button).
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
# Verified sender for Resend, e.g. "Atelier <techpacks@yourdomain.com>".
EMAIL_FROM = os.environ.get("ATELIER_EMAIL_FROM", "Atelier <onboarding@resend.dev>")

# Brand label shown in the UI / documents / emails.
BRAND_NAME = os.environ.get("ATELIER_BRAND", "Atelier")
