# Project

Autonomous AI Agent System

# Rules

Always plan before coding.

Always explain architecture.

Keep agents modular.

Never create duplicate functionality.

Always test before finishing.

Always read:
- docs/agents.md
- docs/code-map.md

before modifying the system.

# Workflow

1. Analyze
2. Plan
3. Wait for approval
4. Implement
5. Verify (run the loop below)

# Post-implementation (verify-and-fix loop)

After ANY code change, always run this loop before finishing:

1. Run tests — pytest, fully offline (no API key/network). Use the project venv if present (`./.venv/bin/python -m pytest -q` or `python -m pytest -q`).
2. Check logs — read the full output and tracebacks, not just the exit code.
3. Identify failures — root-cause each one (file/line, why) before editing; tell a real code bug from a stale test.
4. Fix failures — make the smallest correct fix; state whether the code or the test was wrong.
5. Verify success — re-run and repeat steps 2–5 until fully green.

Never stop on a failing, errored, or skipped-to-hide suite. Report the final pass count; if you cannot reach green, say so plainly with the remaining failure output — do not claim success on a failing suite.

# Architecture

Planner Agent
Executor Agent
Reviewer Agent
