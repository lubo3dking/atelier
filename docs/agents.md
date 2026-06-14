# Agent Registry

All three agents extend `src/agents/base.py:Agent` and share one `LLMClient`.
System prompts live in `prompts/<name>.md`.

## Planner Agent
Purpose: turn a goal into an ordered, concrete `Plan` (list of `PlanStep`).
Uses structured output (`Plan` schema). Receives a digest of recent runs from
memory so it can avoid previously-rejected approaches.

## Executor Agent
Purpose: carry out the plan. Runs a **manual** tool-use loop against a
`ToolRegistry` (sandboxed file tools), so every tool call is gated and auditable.
Stops when the model finishes (no more `tool_use`) or hits the iteration cap,
then returns a summary.

## Reviewer Agent
Purpose: grade the Executor's result against the goal and plan. Returns a
structured `ReviewVerdict` (`approved`, `score`, `feedback`). When not approved,
its `feedback` is fed back into the Executor for the next revision attempt.

## Designer Agent (Atelier tech packs)
Purpose: turn inspiration images + the brand owner's design notes into a
structured `DesignBrief` (garment, fabric, points of measure, BOM, construction)
via structured output. It is the "Executor" of the tech-pack flow; everything
after it — grading across a chosen size run and rendering the PDF/CSV documents —
is deterministic and lives in `src/techpack/` (no LLM, fully unit-tested).

## Control flow
The Orchestrator (`src/orchestrator.py`) runs: plan once, then
execute -> review, looping on rejection up to `MAX_REVISIONS`, recording the
outcome in memory.

Memory is a pluggable backend (`get_memory()` — JSON by default, Supabase via
`AGENT_MEMORY_BACKEND=supabase`); the Planner consumes its `context_for` digest.
