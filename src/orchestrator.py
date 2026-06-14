"""Orchestrator — wires the three agents into the plan → execute → review loop.

    goal -> Planner -> Plan
                         |
                         v
            Executor -> result -> Reviewer -> approved? -- yes --> done
                ^                     |
                |                     no (+feedback)
                +---------------------+   (up to MAX_REVISIONS)
"""
from __future__ import annotations

from dataclasses import dataclass

from . import config
from .agents import Executor, Planner, Reviewer
from .memory.store import MemoryStore
from .schemas import Plan, ReviewVerdict


@dataclass
class RunResult:
    goal: str
    plan: Plan
    result: str
    verdict: ReviewVerdict
    attempts: int


class Orchestrator:
    def __init__(
        self,
        planner: Planner,
        executor: Executor,
        reviewer: Reviewer,
        memory: MemoryStore,
        max_revisions: int = config.MAX_REVISIONS,
    ) -> None:
        self.planner = planner
        self.executor = executor
        self.reviewer = reviewer
        self.memory = memory
        self.max_revisions = max_revisions

    def run(self, goal: str) -> RunResult:
        plan = self.planner.plan(goal, self.memory.context_for(goal))

        feedback: str | None = None
        result = ""
        verdict: ReviewVerdict | None = None
        attempts = 0

        for attempts in range(1, self.max_revisions + 1):
            result = self.executor.execute(goal, plan, feedback)
            verdict = self.reviewer.review(goal, plan, result)
            if verdict.approved:
                break
            feedback = verdict.feedback

        assert verdict is not None  # loop runs at least once
        self.memory.add(
            {
                "goal": goal,
                "approved": verdict.approved,
                "score": verdict.score,
                "attempts": attempts,
            }
        )
        return RunResult(goal=goal, plan=plan, result=result, verdict=verdict, attempts=attempts)
