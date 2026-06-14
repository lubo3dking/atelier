# Atelier — Project Handoff

**Product:** Atelier — an AI agent that turns garment **inspiration photos + design notes** into a **sewer-ready tech pack** (technical flat sketches + points of measure + bill of materials + construction notes), exportable as a downloadable **PDF** and **CSV**, in **English or Bulgarian**.

**Built on:** an existing Python **Planner → Executor → Reviewer** agent system using the Anthropic Claude API.

**Location:** `~/Desktop/imago website/Autonomous AI Agents for Sale`
**Status:** Working CLI **and web app**, verified end-to-end live (CLI on real photos; web app on a live notes→PDF run). Web app is deploy-ready; going live needs the owner's host/domain/Stripe accounts.
**Last updated:** 2026-06-14
**Tests:** 87 passing, fully offline (no API key/network needed).

---

## 1. Completed work

### Product & pipeline (Atelier tech packs)
- **Designer agent** (`src/agents/designer.py`, `prompts/designer.md`) — Claude vision reads inspiration images + notes and returns a structured `DesignBrief` (garment, fabric, base size, points of measure, BOM, construction notes, and a `SketchSpec` classification).
- **Grading** (`src/techpack/grading.py`) — grades the base spec across a chosen size run; `value(size) = base + grade × steps`.
- **Size systems** (`src/techpack/sizes.py`) — `alpha` (XXS–XXXL), `eu-women` (32–50), `eu-men` (44–58).
- **European standards** (`src/techpack/standards.py`) — EN 13402 / EN ISO 8559 body-measurement charts per EU size, rendered into the PDF as a reference size chart.
- **Parametric flat-sketch engine** (`src/techpack/flats.py`) — generates clean, symmetric front + back technical flats in code (tops, dresses, trousers, skirts). **Off by default in the PDF** (`ATELIER_INCLUDE_FLATS=1` to re-enable): the silhouettes are *generic* and were judged not to faithfully represent specific garments (e.g. a fitted ribbed-waist cardigan rendered as a boxy top), so they hurt credibility more than they help. Graded measurements are in the POM table regardless. The engine + label de-collision are kept and tested for when faithful, garment-specific silhouettes exist.
- **Sketch renderer** (`src/techpack/sketch.py`) — pure-Python SVG-path → ReportLab vector renderer with the standard **line-weight hierarchy** (outline → seam → dashed topstitch → rib hatching). No SVG system libraries required.
- **Documents** (`src/techpack/documents.py`) — generates the **PDF tech pack** (cover, **embedded reference photo(s)** — the user's own uploads, via Pillow, so the visual matches the real garment; design notes; graded POM table; EN 13402 size chart for EU runs; BOM; construction notes) and the **POM CSV**. Parametric flats are off by default (see below). Fully localized EN/BG.
- **Cyrillic fonts** (`src/techpack/fonts.py`) — resolves a Cyrillic-capable TTF so Bulgarian PDFs render (bundled DejaVu / system Arial Unicode), falls back to Helvetica for English.
- **Image encoding** (`src/llm/images.py`) — turns image files into Claude vision blocks.
- **LLM robustness** (`src/llm/client.py`) — single Anthropic wrapper; `.parse()` now **falls back to JSON mode + Pydantic validation** if the server's structured-output grammar compiler times out.

### Web app (`src/web/`) — working, sendable, sellable, deploy-ready
- **FastAPI backend** (`src/web/app.py`) — runs the existing pipeline from the browser. Routes: `GET /api/config` (drives the dynamic UI), `POST /api/jobs` (consent-gated multipart upload), `POST /api/jobs/{id}/pay` (Stripe confirm), `GET /api/jobs/{id}` (status), `GET /api/jobs/{id}/files/{pdf|csv}` (download), `POST /api/jobs/{id}/email` (send to sewer), `DELETE /api/jobs/{id}` (delete my data), `GET /healthz`.
- **Background jobs** (`src/web/pipeline.py`, `storage.py`) — a thread pool runs generation; the one LLM touch point (the brief provider) is **injectable**, so the whole web layer is tested offline. Uploaded photos are saved per-job, read at generation time, then **deleted right after** the pack is produced (privacy).
- **Frontend** (`src/web/static/`) — brand-matched **single screen** (add photos + notes, pick sizes, generate; garment/size-system/base behind "More options") with EN/BG UI, drag-drop uploads, live PDF preview, downloads, email box, and "delete my data". Plus **real** bilingual `privacy.html` / `terms.html` (controller **Stagove EOOD**, Bulgaria).
- **Free-launch guards** — a per-device **daily rate limit** (`ATELIER_RATE_LIMIT_PER_DAY`, default 10) protects the API budget when there's no paywall. An **owner key** (`ATELIER_OWNER_KEY`): visiting `/?owner=<key>` once marks that browser unlimited & free forever (exempt from the rate limit and any future paywall); the browser re-asserts it each load so it survives server restarts.
- **Installable PWA** — `manifest.webmanifest` + service worker (`sw.js`, caches the app shell) + PNG icons. The same link works in a browser and installs to the home screen / desktop as a standalone app.
- **Sendable** (`src/web/email.py`) — emails the PDF+CSV to a sewer via **Resend** (optional; enabled by `RESEND_API_KEY`, else download-only). No SDK (urllib).
- **Sellable — freemium unlock** (`src/web/payments.py`) — each device gets `ATELIER_FREE_PACKS` (default 3) free tech packs, then **one Stripe payment unlocks unlimited** use forever (`ATELIER_UNLOCK_CENTS`, default €29). Accountless: free quota + unlock are tracked per device id in `storage.py` (persisted to `workspace/web/devices.json`). Optional; enabled by `STRIPE_SECRET_KEY`, else **free & unlimited** out of the box. The `stripe` SDK is imported lazily.
- **Deploy** — `Dockerfile` (installs `fonts-dejavu-core` so Bulgarian PDFs render on Linux), `railway.json`, `render.yaml`, `.dockerignore`. Start command: `uvicorn src.web:create_app --factory`.
- **Privacy/consent** — consent checkbox enforced server-side; retention auto-delete (`ATELIER_RETENTION_DAYS`, default 14) swept on boot + each job; per-job delete endpoint.

### Scripts
- `scripts/serve.py` — run the **web app** locally (loads `.env`, starts uvicorn). `--port`, `--reload`.
- `scripts/demo_techpack.py` — generates a sample tech pack **offline** (no API key) to `workspace/techpacks/`.
- `scripts/run_designer.py` — **live** end-to-end CLI: `--notes`, `--image` (repeatable), `--sizes`, `--size-system`, `--garment`, `--base`, `--lang`. Saves the brief as JSON so documents can be re-rendered without another API call.
- `scripts/check_supabase.py` — live connectivity check for the optional Supabase memory backend.

### Design assets (`design/`)
- `atelier-icon.svg` — app icon / thumbnail (light modern mark).
- `preview.html` — clickable static UI mockup: Inspiration → **Size run** → flats → Tech pack, with an **EN/BG** toggle and brand palette (indigo `#6366F1`, coral `#FF6B5E`, canvas `#F4F5F8`).

### Agent framework (pre-existing, still in use)
- `src/agents/` (Planner, Executor, Reviewer, Designer), `src/orchestrator.py`, `src/llm/client.py`, `src/tools/`, `src/memory/` (JSON default, optional Supabase backend), `src/main.py`.

### Tooling & process
- **Claude Code subagents** in `.claude/agents/`: `architecture`, `implementation`, `prompt-engineering`, `research`.
- **CLAUDE.md** encodes a mandatory **post-implementation verify-and-fix loop** (run tests → check logs → identify → fix → re-run until green).
- **MCP servers** configured in `.mcp.json`: `github` (HTTP) and `playwright` (stdio).
- **Localization**: full English + Bulgarian, including the PDF documents.

### Verified
- 64 offline tests passing.
- Live end-to-end runs on a real cardigan photo, in EN and BG, with alpha and EU-women sizing; all outputs rendered and visually checked.

---

## 2. Pending work

### Frontend / delivery (built — see `src/web/`)
- **Web app** — responsive single-screen browser frontend is **done**, and it's an **installable PWA** (manifest + service worker + icons). Not yet wrapped for the native app stores (Capacitor).
- **Backend API** — FastAPI is **done**. It uses an **in-process thread pool**, not Redis; fine for low/moderate volume. Swap to a Redis/RQ worker if you need horizontal scaling or durable queues.
- **Going live** (owner actions) — buy a domain, create a host account (Railway/Render), set `ANTHROPIC_API_KEY` + `ATELIER_PUBLIC_URL` in host secrets, deploy with the included config. See `GO_LIVE_PLAN.md`.
- **Capacitor shell** — wrap for App Store / Play (fixes iOS 720p camera cap, enables push). *Still pending.*

### Productization
- **Privacy/consent foundation (Phase 0)** — consent UX, short retention/auto-delete, a delete action, and **real EN/BG privacy + terms** (Stagove EOOD) are **built**. Still recommended before scaling: a signed **DPA with Anthropic** (ideally ZDR), a lawyer/Termly review of the policy, and at-rest encryption if your host doesn't provide it.
- **Payments** — Stripe Checkout (per-pack) is **built and gated by env**. Owner must create the Stripe account + connect a bank; test mode → €1 live test → refund (see `GO_LIVE_PLAN.md` Day 4).
- **Accounts / multi-tenant** (per-customer measurement & style profiles, saved history, subscriptions) — *still pending*; the current payment model is accountless (one payment = one pack).

### Engine / feature depth
- **More garment silhouettes** in the flat engine: structured **blazer with lapels**, **hoodie**, **outerwear**, knitwear variants. Unusual garments currently fall back to a generic top/bottom and may miss specifics.
- **Richer flat detail**: drawn collars, varied pockets, darts/pleats/gathers, zippers.
- **Pattern export**: DXF (AAMA/ASTM) + tiled-PDF pattern handoff (researched; not built).
- **Multi-image angles** (front/back/detail) — supported by the CLI but only lightly exercised.

### Backend memory
- **Supabase memory live wiring** — backend coded + tested offline, but never connected to a live project (needs the `runs` table created and credentials set; see `docs/supabase-schema.sql`).

---

## 3. Architecture decisions

1. **Product pivot: body-measurement → inspiration-to-tech-pack.** Photo-based body girth accuracy is only ~2–4 cm (researched), too low to "replace a tailor." Generating tech packs from inspiration sidesteps that and is genuinely sellable. The earlier body-measurement idea was dropped.
2. **Deterministic core, LLM only for classification.** Grading, document generation, and the flat engine are **pure, deterministic, fully unit-tested offline**. Claude is used only to produce the `DesignBrief` (including the `SketchSpec`). This keeps the system testable without an API key and makes outputs reproducible.
3. **Parametric flat engine instead of AI-drawn coordinates.** Letting the LLM emit raw SVG path coordinates produced inconsistent, often "messed-up" flats. The engine generates silhouettes in code (mirrored for guaranteed symmetry, realistic proportions, standard line weights); the LLM only **classifies** the garment. This trades flexibility (fixed silhouette set) for reliable, professional output.
4. **ReportLab (pure-Python) for PDFs.** Chosen over WeasyPrint and svglib/renderPM because those need system Cairo/pkg-config, which is not available in this environment. ReportLab needs no system libraries.
5. **Cyrillic via TTF registration.** Helvetica can't render Cyrillic; a Unicode TTF (system Arial Unicode / bundled DejaVu) is registered for Bulgarian. English falls back to Helvetica; Bulgarian raises a clear error if no Cyrillic font is found.
6. **European sizing via EN 13402 / EN ISO 8559.** EU numeric size scales + standard body charts encoded from research; grade increment ~4 cm girth per size step.
7. **Structured output with a JSON fallback.** Native Anthropic structured output is primary; on grammar-compiler timeout the client falls back to JSON mode + Pydantic validation (see Known issues).
8. **Single LLM wrapper.** All Claude access goes through `src/llm/client.py` so the model id, adaptive thinking, effort, and the fallback live in one place and the rest of the system is trivially testable with a scripted stand-in.
9. **Delivery plan:** responsive PWA → Capacitor shell; sell subscriptions on web (Stripe); Python FastAPI + Redis backend holds the API key. (Plan only; not built.)
10. **Naming/brand:** "Atelier", light modern palette (indigo + coral on off-white).

---

## 4. Known issues

1. **Structured-output grammar timeout — FIXED.** The Anthropic structured-output grammar compiler times out on the `DesignBrief` schema. The Designer now goes **straight to JSON mode** (`LLMClient.parse(json_mode=True)`, driven by `config.DESIGNER_JSON_MODE`, default on), skipping the doomed structured call. Generation dropped from **~1.5–2 min to ~30 s** (one API call instead of two). Set `ATELIER_DESIGNER_JSON_MODE=0` to restore the native structured path if Anthropic fixes the compiler. *(The Planner/Reviewer still use native structured output — their small schemas compile fine.)*
2. **No local PDF rasterizer.** `renderPM`/`svglib` need system Cairo (unavailable), so PDFs can only be previewed via macOS `qlmanage` (first page) — fine for runtime (PDF generation works), but inconvenient for automated visual QA of later pages.
3. **Flat engine silhouette coverage is limited.** Only tops, dresses, trousers, skirts. Garments with distinctive structure (blazer lapels, hoods, complex outerwear) render as a generic silhouette and lose specifics.
4. **Bundled font not actually present.** Bulgarian rendering currently relies on macOS `Arial Unicode.ttf`. A **Linux server must install or bundle DejaVu** (`assets/fonts/DejaVuSans.ttf`) or Bulgarian PDFs will error.
5. **Base size vs size system.** The model's chosen `base_size` may not be valid in the selected EU system; `run_designer.py` overrides it with the **middle of the chosen run**. Pass `--base` to control it explicitly.
6. **Old brief JSONs are incompatible.** Brief JSON files saved before the schema change (e.g. earlier `workspace/techpacks/*.json` using `flat_sketches`) won't validate against the current schema; regenerate them.
7. **Prompt quality is not unit-tested.** Tests cover structure/format and the deterministic core, not the *quality* of Claude's design judgments — that's validated manually.
8. **Photo body-measurement accuracy is intentionally not used.** If a future requirement reintroduces measuring people from photos, expect ~2–4 cm girth error and design a hybrid (reference object + tape anchors + fit sample) per the research.
9. **Supabase memory is not live.** Coded and tested with a fake client only.

---

## 5. How to run

```bash
cd "~/Desktop/imago website/Autonomous AI Agents for Sale"

# Tests (offline, no key needed) — 79 passing
./.venv/bin/python -m pytest -q

# Web app (browser) — needs ANTHROPIC_API_KEY in .env; opens http://localhost:8000
./.venv/bin/python scripts/serve.py

# Sample tech pack, no API key
./.venv/bin/python scripts/demo_techpack.py XS S M L XL

# Live: inspiration photo + notes -> tech pack (needs ANTHROPIC_API_KEY in .env)
./.venv/bin/python scripts/run_designer.py \
  --notes "your design clarifications" \
  --image refs/your-photo.jpg \
  --size-system eu-women --sizes 36 38 40 42 \
  --garment cardigan --lang en
# Outputs (PDF, CSV, brief JSON) -> workspace/techpacks/
```

**Secrets:** `ANTHROPIC_API_KEY` goes in `.env` (git-ignored). Never commit it. Optional: `SUPABASE_URL` / `SUPABASE_KEY` for the Supabase memory backend.

---

## 6. Key files

```
CLAUDE.md                     Project rules + post-implementation verify-and-fix loop
Dockerfile, railway.json,     Deploy config (web app). DejaVu fonts for Bulgarian PDFs.
  render.yaml, .dockerignore
.mcp.json                     MCP servers (github, playwright)
.claude/agents/               Claude Code subagents (architecture/implementation/prompt-eng/research)
design/
  atelier-icon.svg            App icon / thumbnail
  preview.html                Static UI mockup (open in a browser)
docs/
  agents.md, code-map.md      System docs (read before modifying)
  supabase-schema.sql         Memory backend table DDL
prompts/
  designer.md                 Designer agent system prompt (incl. SketchSpec rules)
  planner.md, executor.md, reviewer.md
src/
  schemas.py                  DesignBrief, PointOfMeasure, BomItem, SketchSpec, FlatSketch…
  llm/client.py               Anthropic wrapper + JSON fallback
  llm/images.py               Image -> vision blocks
  agents/designer.py          Inspiration+notes -> DesignBrief
  techpack/
    sizes.py                  Size systems (alpha, eu-women, eu-men)
    grading.py                Grade spec across a size run
    standards.py              EN 13402 body-measurement charts
    flats.py                  Parametric flat-sketch engine
    sketch.py                 SVG-path -> ReportLab vector renderer
    fonts.py                  Cyrillic font resolution
    documents.py              PDF + CSV generation (EN/BG)
  web/                        Browser app (FastAPI) over the same pipeline
    app.py                    Routes (config, jobs, pay, download, email, delete)
    pipeline.py               Background generation; injectable brief provider
    storage.py                Per-job storage, retention auto-delete, spent payments
    payments.py               Stripe Checkout (optional, env-gated)
    email.py                  Resend email-to-sewer (optional, env-gated)
    static/                   index.html, app.js, styles.css, privacy/terms,
                              manifest.webmanifest, sw.js, icons (PWA)
scripts/
  serve.py                    Run the web app locally (loads .env)
  run_designer.py             Live end-to-end CLI
  demo_techpack.py            Offline sample generator
  check_supabase.py           Supabase connectivity check
tests/                        79 offline tests (incl. test_web.py)
workspace/techpacks/          Generated PDFs/CSVs/brief JSON (git-ignored)
refs/                         Inspiration photos (git-ignored)
```

---

## 7. Suggested next step

The web app, sending, payments (freemium unlock), privacy, deploy config, and the latency fix are **built and verified** (see `src/web/`). What's left is mostly **owner go-live**:

1. **Go live (owner, ~1 day).** Buy a domain, deploy to Railway/Render with the included config, set `ANTHROPIC_API_KEY` + `ATELIER_PUBLIC_URL`, add an Anthropic spend cap. (`GO_LIVE_PLAN.md` Day 3.)
2. **Turn on selling/sending when ready (owner).** Add `STRIPE_SECRET_KEY` (Day 4) and `RESEND_API_KEY` (Day 2) — both already wired, just env-gated.
3. **Before wide public launch:** a real privacy policy/terms (templates in place) + an Anthropic DPA; consider account-backed entitlements (the current unlock is per-device).
4. **Product depth (later):** broaden the flat engine (blazer/hoodie/outerwear), richer flat detail, pattern (DXF) export.
