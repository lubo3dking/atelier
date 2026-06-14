# Autonomous AI Agent System

A modular **Planner → Executor → Reviewer** agent loop built on the Anthropic
Claude API (`claude-opus-4-8`, adaptive thinking).

```
goal ──▶ Planner ──▶ Plan ──▶ Executor ──▶ result
                                  │
                                  ▼
                               Reviewer ──▶ approved? ── yes ──▶ done
                                  │
                                  └─ no (+feedback) ──▶ Executor   (≤ MAX_REVISIONS)
```

- **Planner** turns a goal into an ordered plan (structured output).
- **Executor** carries out the plan via a manual, auditable tool-use loop over a
  sandboxed file toolset (`read_file` / `write_file` / `list_dir`).
- **Reviewer** grades the result; on rejection its feedback drives a revision.
- **Memory** records each run and feeds a digest back to the Planner.

Everything reaches Claude through one wrapper (`src/llm/client.py`), so the model
config lives in one place and the whole system is testable offline.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=sk-ant-...   # or rely on .env via your shell
```

## Run

```bash
python -m src.main "Create a JSON config file with sensible defaults for a web server"
```

## Atelier web app (browser frontend)

Atelier turns inspiration photos + design notes into a sewer-ready **tech pack**
(PDF + POM CSV, EN/BG). The web app wraps the exact same pipeline as the CLI.

```bash
# Local — opens at http://localhost:8000 (needs ANTHROPIC_API_KEY in .env)
./.venv/bin/python scripts/serve.py
```

It's a **single screen** (add photos + notes, pick sizes, generate) and an
**installable PWA** — the same link works in a browser and "Add to Home Screen"
installs it like an app. **Optional features self-enable from environment variables:**

| Capability | Enable by setting | Behaviour when unset |
|---|---|---|
| **Sellable** — freemium: N free packs, then a one-time **unlock** (Stripe) for unlimited use | `STRIPE_SECRET_KEY` | Free & unlimited, no paywall |
| **Sendable** — email the pack to a sewer (Resend) | `RESEND_API_KEY` | Download-only |
| **Live** — correct redirect/email links | `ATELIER_PUBLIC_URL` | `http://localhost:8000` |

The free quota (`ATELIER_FREE_PACKS`, default 3) and one-time unlock price
(`ATELIER_UNLOCK_CENTS`, default €29) are configurable.

Privacy is built in: a consent checkbox is required, uploaded photos are deleted
right after generation, packs auto-delete after `ATELIER_RETENTION_DAYS` (default
14), and there's a "delete my data" action. See `.env.example` for all settings.

### Deploy (live)

A `Dockerfile` (bundles DejaVu fonts for Bulgarian PDFs), `railway.json`, and
`render.yaml` are included. Push to Railway/Render, set `ANTHROPIC_API_KEY` (and
any optional keys) in the host's secret settings, and point your domain at it.
`GO_LIVE_PLAN.md` is the full step-by-step. Health check: `GET /healthz`.

## Test

The suite runs fully offline (no API key, no network) — Claude is replaced by a
scripted stand-in:

```bash
python -m pytest
```

## Layout

See `docs/code-map.md` for the file-by-file map and `docs/agents.md` for the
agent registry. Configuration (model, effort, caps) is in `src/config.py` and
overridable via environment variables.
