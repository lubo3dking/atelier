"""CLI entrypoint.

Usage:
    python -m src.main "your goal here"

Requires ANTHROPIC_API_KEY in the environment (see .env.example).
"""
from __future__ import annotations

import sys

from .agents import Executor, Planner, Reviewer
from .llm.client import LLMClient
from .memory import get_memory
from .orchestrator import Orchestrator
from .tools.builtins import make_default_registry
from .tools.registry import ToolRegistry
from . import config


def build_orchestrator(client: LLMClient, registry: ToolRegistry) -> Orchestrator:
    planner = Planner.from_prompt_file("planner", client)
    executor = Executor.from_prompt_file("executor", client, tools=registry)
    reviewer = Reviewer.from_prompt_file("reviewer", client)
    memory = get_memory()  # backend chosen by AGENT_MEMORY_BACKEND
    return Orchestrator(planner, executor, reviewer, memory)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print('Usage: python -m src.main "your goal here"', file=sys.stderr)
        return 2

    goal = " ".join(argv)
    client = LLMClient()
    registry = make_default_registry(config.WORKSPACE_DIR)
    orchestrator = build_orchestrator(client, registry)

    result = orchestrator.run(goal)

    print("=" * 70)
    print(f"GOAL: {result.goal}")
    print("=" * 70)
    print("\nPLAN:")
    for i, step in enumerate(result.plan.steps, 1):
        print(f"  {i}. {step.description}")
    print(f"\nRESULT (after {result.attempts} attempt(s)):\n{result.result}")
    print(f"\nVERDICT: {'APPROVED' if result.verdict.approved else 'NOT APPROVED'} "
          f"(score {result.verdict.score})")
    if not result.verdict.approved:
        print(f"Reviewer feedback: {result.verdict.feedback}")
    return 0 if result.verdict.approved else 1


if __name__ == "__main__":
    raise SystemExit(main())
