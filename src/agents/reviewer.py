"""Reviewer agent — grades the Executor's result against the goal and plan."""
from __future__ import annotations

from ..schemas import Plan, ReviewVerdict
from .base import Agent


class Reviewer(Agent):
    def review(self, goal: str, plan: Plan, result: str) -> ReviewVerdict:
        steps = "\n".join(f"{i}. {s.description}" for i, s in enumerate(plan.steps, 1))
        user = (
            f"Goal:\n{goal}\n\n"
            f"Plan that was followed:\n{steps}\n\n"
            f"Executor's result:\n{result}\n\n"
            "Decide whether the goal is fully met. Approve only if it is. "
            "If not, give specific, actionable feedback the executor can act on."
        )
        return self.client.parse(
            system=self.system_prompt,
            messages=[{"role": "user", "content": user}],
            schema=ReviewVerdict,
        )
