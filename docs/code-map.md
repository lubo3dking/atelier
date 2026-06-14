# Code Map

The system is a Python package under `src/`. The directory names below match the
original scaffold (`agents/`, `tools/`, `memory/`, `prompts/`, `tests/`); the
implementation lives under `src/` so it imports as a package.

## Entry point
`src/main.py` — CLI. Run: `python -m src.main "your goal"`

## Orchestration
`src/orchestrator.py` — the Planner -> Executor -> Reviewer loop with a revision
cap. Returns a `RunResult`.

## Agents (`src/agents/`)
- `base.py` — `Agent` base class; loads system prompts from `prompts/<name>.md`.
- `planner.py` — `Planner`: goal -> structured `Plan`.
- `executor.py` — `Executor`: runs the plan via a manual tool-use loop.
- `reviewer.py` — `Reviewer`: grades the result -> structured `ReviewVerdict`.
- `designer.py` — `Designer`: inspiration images + notes -> structured `DesignBrief`
  (the Atelier tech-pack flow).

## Tech packs (`src/techpack/`)
Deterministic pipeline that turns a `DesignBrief` into downloadable documents.
No LLM here — fully unit-tested offline.
- `sizes.py` — size systems (`alpha`, `eu-women` 32–50, `eu-men` 44–58) + size-run
  validation. Grading counts steps along the chosen system's scale.
- `standards.py` — EN 13402 / EN ISO 8559 body-measurement charts per EU size;
  rendered into the PDF as a reference size chart for EU size runs.
- `grading.py` — `grade()`: scales the base spec across a chosen size run ->
  `GradedTechPack`.
- `documents.py` — `write_pdf` / `write_pom_csv` / `generate`: render the tech
  pack to a PDF (ReportLab) and a POM CSV. `lang="en"|"bg"` localises the static
  labels; field values are localised by the Designer agent.
- `fonts.py` — resolves a Cyrillic-capable TTF (bundled DejaVu / system Arial
  Unicode) so Bulgarian PDFs render; falls back to Helvetica for English.
- `flats.py` — **parametric flat-sketch engine**. The Designer classifies the
  garment into a `SketchSpec` (silhouette + options) and this builds clean,
  symmetric, correctly-proportioned front/back flats in code (mirrored about the
  centre front), placing POM codes at named anchor points.
- `sketch.py` — renders a `FlatSketch` (SVG path data) to a ReportLab vector
  drawing via a small pure-Python SVG-path parser (no SVG lib), applying the
  line-weight hierarchy (outline → seam → dashed topstitch → rib). The PDF's final
  page shows the front/back flats with the graded size table.

Demo (no API key): `python scripts/demo_techpack.py [SIZES…]` writes a sample
tech pack to `workspace/techpacks/`.

Live (needs `ANTHROPIC_API_KEY`): `python scripts/run_designer.py --notes "…"
[--image PATH …] [--sizes …] [--size-system alpha|eu-women|eu-men] [--garment shirt]
[--lang en|bg]` runs Claude vision over inspiration images + notes -> DesignBrief ->
graded tech pack (with technical flats + EN 13402 size chart for EU systems). The
brief is also saved as JSON so documents can be re-rendered without another API
call. Image encoding for vision calls lives in `src/llm/images.py`.

## LLM access
`src/llm/client.py` — `LLMClient`, the single wrapper around the Anthropic SDK
(model id, adaptive thinking, effort, structured `.parse()`). Nothing else
touches the SDK directly. `.parse()` falls back to JSON mode + Pydantic validation
if the server's structured-output grammar compiler times out on a complex schema.

## Tools (`src/tools/`)
- `registry.py` — `Tool` + `ToolRegistry` (definitions + safe dispatch).
- `builtins.py` — sandboxed `read_file` / `write_file` / `list_dir`.

## Memory (`src/memory/`)
Pluggable backend recording past runs; feeds a digest to the Planner.
- `base.py` — `BaseMemory` interface (`add` / `recent`) + the shared
  `context_for` digest. New backends implement only `add` / `recent`.
- `store.py` — `MemoryStore`, the default JSON-file backend (zero deps).
- `supabase_store.py` — `SupabaseMemoryStore`, Postgres-backed via the `supabase`
  client (lazy-imported; optional dep).
- `__init__.py` — `get_memory()` factory; selects the backend from
  `AGENT_MEMORY_BACKEND` (`json` default | `supabase`).

Supabase table DDL: `docs/supabase-schema.sql`.

## Schemas
`src/schemas.py` — Pydantic models for structured outputs: `Plan`, `PlanStep`,
`ReviewVerdict`.

## Prompts (`prompts/`)
`planner.md`, `executor.md`, `reviewer.md` — system prompts loaded at runtime.

## Config
`src/config.py` — model, effort, revision/iteration caps, and paths (env-overridable).

## Tests (`tests/`)
`pytest` suite. Runs fully offline via a scripted LLM stand-in (`conftest.py`) —
no API key or network required.
